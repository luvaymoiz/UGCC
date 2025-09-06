import json
import logging
from flask import request, jsonify
from routes import app


logger = logging.getLogger(__name__)

def _validate_payload(item):
    # required keys
    for k in ("intel", "reserve", "fronts", "stamina"):
        if k not in item:
            raise ValueError(f"missing key: {k}")

    intel = item["intel"]
    reserve = item["reserve"]
    fronts = item["fronts"]
    stamina = item["stamina"]

    # basic type/value checks
    if not isinstance(intel, list) or any(
        (not isinstance(p, list) or len(p) != 2) for p in intel
    ):
        raise ValueError("intel must be a list of [front, mp] pairs")
    if not all(isinstance(x, int) for x in (reserve, fronts, stamina)):
        raise ValueError("reserve, fronts, and stamina must be integers")
    if reserve <= 0 or fronts <= 0 or stamina <= 0:
        raise ValueError("reserve, fronts, and stamina must be positive")

    # constraints from the spec
    for idx, (front, mp) in enumerate(intel, start=1):
        if not isinstance(front, int) or not isinstance(mp, int):
            raise ValueError(f"intel[{idx}] values must be integers")
        if front < 1 or front > fronts:
            raise ValueError(f"intel[{idx}] front out of range 1..{fronts}")
        if mp < 1 or mp > reserve:
            raise ValueError(f"intel[{idx}] mp out of range 1..{reserve}")

def _earliest_time_minutes(intel, reserve, stamina_max):
    """
    Rules implemented per 'The Mage's Gambit':
    - Each spell normally costs 10 minutes to set target.
    - If the next spell is immediately on the SAME front (no cooldown between),
      it can be 'extended' with 0 extra minutes.
    - Must follow intel order; cannot skip/reorder.
    - Casting consumes MP and 1 stamina. If next cast would exceed MP or stamina,
      do a cooldown: +10 minutes, then MP and stamina fully recover.
    - After all undead are defeated, Klein must be in cooldown: add a final +10 minutes.
    """
    time = 0
    mp = reserve
    stamina = stamina_max
    prev_front = None
    previous_action_was_cast = False

    for front, cost in intel:
        # recover if needed before this cast
        if stamina == 0 or mp < cost:
            time += 10  # cooldown
            mp = reserve
            stamina = stamina_max
            prev_front = None
            previous_action_was_cast = False

        # cast this spell
        cast_time = 0 if (previous_action_was_cast and prev_front == front) else 10
        time += cast_time
        mp -= cost
        stamina -= 1
        prev_front = front
        previous_action_was_cast = True

    # final cooldown so Klein can immediately join expedition
    time += 10
    return time

@app.route("/the-mages-gambit", methods=["POST"])
def the_mages_gambit():
    try:
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        logger.exception("Invalid JSON payload")
        return jsonify({"error": "Invalid JSON"}), 400

    # Accept either a single object or a list of objects
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return jsonify({"error": "Payload must be an object or an array of objects"}), 400

    results = []
    try:
        for item in items:
            _validate_payload(item)
            time_minutes = _earliest_time_minutes(
                intel=item["intel"],
                reserve=item["reserve"],
                stamina_max=item["stamina"],
            )
            results.append({"time": time_minutes})
    except ValueError as ve:
        logger.warning("Validation error: %s", ve)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({"error": "Internal server error"}), 500

    # Always return a JSON array as per the samples
    return jsonify(results), 200
