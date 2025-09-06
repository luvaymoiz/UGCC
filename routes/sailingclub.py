import logging
from flask import request, jsonify
from routes import app   

logger = logging.getLogger(__name__)

def merge_slots(bookings):
    if not bookings:
        return []

    bookings.sort(key=lambda x: x[0])
    merged = [bookings[0]]

    for current in bookings[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            last[1] = max(last[1], current[1])
        else:
            merged.append(current[:])
    return merged

def min_boats(bookings):
    starts = sorted([s for s, e in bookings])
    ends = sorted([e for s, e in bookings])
    boats = 0
    max_boats = 0
    i = j = 0

    while i < len(starts) and j < len(ends):
        if starts[i] < ends[j]:
            boats += 1
            max_boats = max(max_boats, boats)
            i += 1
        else:
            boats -= 1
            j += 1
    return max_boats

@app.route("/sailing-club/submission", methods=["POST"])
def sailing_club_submission():
    try:
        data = request.get_json(force=True, silent=False)
        solutions = []

        for case in data.get("testCases", []):
            bookings = [list(slot) for slot in case.get("input", [])]
            merged = merge_slots(bookings)
            boats = min_boats(bookings)

            solutions.append({
                "id": case["id"],
                "sortedMergedSlots": merged,
                "minBoatsNeeded": boats
            })

        return jsonify({"solutions": solutions})
    except Exception:
        logger.exception("Error in /sailing-club/submission")
        return jsonify({"error": "internal error"}), 500
