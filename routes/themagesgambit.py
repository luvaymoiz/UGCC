import json
import logging
from flask import request, jsonify
from routes import app

# Logger setup
name = __name__
logger = logging.getLogger(name)

# Set the logging level to DEBUG for more detailed information
logging.basicConfig(level=logging.DEBUG)

def _validate_payload(item):
    logger.debug("Validating payload: %s", item)
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
    logger.debug("Payload validated successfully")

def _earliest_time_minutes(intel, reserve, stamina_max):
    """
    Refined time calculation with respect to edge cases and constraints.
    """
    time = 0
    mp = reserve
    stamina = stamina_max
    prev_front = None
    previous_action_was_cast = False

    logger.debug("Starting time calculation")
    for idx, (front, cost) in enumerate(intel):
        logger.debug("Casting spell %d: front=%d, cost=%d, mp=%d, stamina=%d", idx + 1, front, cost, mp, stamina)

        # If resources are exhausted (MP or stamina), cooldown is required
        if stamina == 0 or mp < cost:
            logger.debug("Not enough resources, triggering cooldown")
            time += 10  # cooldown
            mp = reserve
            stamina = stamina_max
            prev_front = None
            previous_action_was_cast = False

        # Cast the spell; no additional time if it's on the same front consecutively
        cast_time = 0 if (previous_action_was_cast and prev_front == front) else 10
        time += cast_time
        mp -= cost
        stamina -= 1
        prev_front = front
        previous_action_was_cast = True

        logger.debug("After casting: time=%d, mp=%d, stamina=%d", time, mp, stamina)

    # Final cooldown after all undead are defeated
    time += 10
    logger.debug("Final cooldown added, total time: %d", time)
    return time

@app.route("/the-mages-gambit", methods=["POST"])
def the_mages_gambit():
    try:
        data = request.get_json(force=True, silent=False)
        logger.debug("Received data: %s", data)
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
            logger.debug("Processing item: %s", item)
            _validate_payload(item)
            time_minutes = _earliest_time_minutes(
                intel=item["intel"],
                reserve=item["reserve"],
                stamina_max=item["stamina"],
            )
            results.append({"time": time_minutes})
            logger.debug("Calculated time for item: %d", time_minutes)
    except ValueError as ve:
        logger.warning("Validation error: %s", ve)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({"error": "Internal server error"}), 500

    # Always return a JSON array as per the samples
    logger.debug("Returning results: %s", results)
    return jsonify(results), 200
