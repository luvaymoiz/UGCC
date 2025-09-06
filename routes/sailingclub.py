from flask import request, jsonify
from routes import app

def merge_slots(slots):
    if not slots:
        return []
    slots = sorted((int(s), int(e)) for s, e in slots)
    merged = []
    cs, ce = slots[0]
    for s, e in slots[1:]:
        if s <= ce:          # overlaps OR touches (s == ce)
            ce = max(ce, e)
        else:
            merged.append([cs, ce])
            cs, ce = s, e
    merged.append([cs, ce])
    return merged

def min_boats_needed(slots):
    if not slots:
        return 0
    events = []
    for s, e in slots:
        s, e = int(s), int(e)
        events.append((s, +1))
        events.append((e, -1))  
    events.sort(key=lambda t: (t[0], t[1]))
    cur = best = 0
    for _, delta in events:
        cur += delta
        if cur > best:
            best = cur
    return best

@app.route("/sailing-club/submission", methods=["POST"])
def sailing_club_submission():
    data = request.get_json(silent=True) or {}
    tcs = data.get("testCases", [])
    if not isinstance(tcs, list):
        return jsonify({"error": "Body must contain key 'testCases' as a list"}), 400

    solutions = []
    for tc in tcs:
        tc_id = tc.get("id")
        raw = tc.get("input", [])
        if not tc_id:
            return jsonify({"error": "Each test case must have an 'id'"}), 400
        # Part 1
        merged = merge_slots(raw)
        # Part 2
        boats = min_boats_needed(raw)
        solutions.append({
            "id": tc_id,
            "sortedMergedSlots": merged,
            "minBoatsNeeded": boats
        })

    return jsonify({"solutions": solutions})
