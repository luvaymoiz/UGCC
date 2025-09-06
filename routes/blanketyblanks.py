# routes/blankety.py
import math
import logging
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def _impute_one(row):
    """
    Fill nulls by linear interpolation, extending edges.
    Preserve known values exactly.
    """
    n = len(row)
    out = [None] * n

    # indices of known values
    known = [i for i, v in enumerate(row) if v is not None]
    if not known:
        return [0.0] * n  # if row is entirely null

    # copy known values
    for i in known:
        out[i] = float(row[i])

    # extend left
    first = known[0]
    for i in range(0, first):
        out[i] = out[first]

    # extend right
    last = known[-1]
    for i in range(last + 1, n):
        out[i] = out[last]

    # fill gaps linearly
    for a, b in zip(known, known[1:]):
        va, vb = out[a], out[b]
        span = b - a
        if span > 1:
            for j in range(1, span):
                t = j / span
                out[a + j] = va + t * (vb - va)

    # sanity: fill any stragglers with 0
    return [0.0 if v is None or not math.isfinite(v) else v for v in out]

@app.route("/blankety", methods=["POST"])
def blankety():
    """
    Input:  { "series": [ [float|null]*1000 ]*100 }
    Output: { "answer": [ [float]*1000 ]*100 }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "series" not in data:
        return jsonify({"error": "Expected JSON with key 'series'"}), 400

    series = data["series"]
    if not isinstance(series, list) or len(series) != 100:
        return jsonify({"error": "Expected 100 lists in 'series'"}), 400

    answer = []
    for idx, row in enumerate(series):
        if not isinstance(row, list) or len(row) != 1000:
            return jsonify({"error": f"series[{idx}] must be length-1000 list"}), 400
        try:
            answer.append(_impute_one(row))
        except Exception:
            logger.exception("Imputation failed at series[%d]", idx)
            answer.append([0.0] * len(row))

    return jsonify({"answer": answer})
