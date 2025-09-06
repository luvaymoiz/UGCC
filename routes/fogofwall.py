import json
import logging
from flask import request, jsonify, Response
from routes import app

# Initialize logger
logger = logging.getLogger(__name__)

@app.route("/fog-of-wall", methods=["POST"])
def fog_of_wall():
    # Parse the incoming JSON data from the request
    data = request.get_json(force=True, silent=False)

    # Log the incoming data for debugging purposes
    logger.info("Received data: %s", data)

    # Check if this is an initial test case request (contains 'test_case')
    if 'test_case' in data:
        test_case = data['test_case']
        challenger_id = data['challenger_id']
        game_id = data['game_id']
        
        # For the initial request, simulate a scan action.
        crow_id = test_case['crows'][0]['id']  # Choose the first crow for example
        action_type = "scan"  # Simulating a scan action

        # Log the scan action
        logger.info(f"Starting scan action for crow {crow_id} in game {game_id}.")

        # Explicitly constructing the response in the correct order
        response_data = {
            "challenger_id": challenger_id,
            "game_id": game_id,
            "crow_id": crow_id,
            "action_type": action_type
        }

        # Manually create and return the Response
        return Response(
            json.dumps(response_data),  # Convert to JSON string
            mimetype='application/json'  # Set content type to JSON
        )

    # Handle move action (contains 'previous_action' and 'your_action' is 'move')
    if 'previous_action' in data and data['previous_action'].get('your_action') == 'move':
        prev_action = data['previous_action']
        crow_id = prev_action['crow_id']
        direction = prev_action['direction']
        
        # Log the move action
        logger.info(f"Crow {crow_id} is moving {direction}.")

        # Explicitly construct the response in the correct order
        response_data = {
            "challenger_id": data['challenger_id'],
            "game_id": data['game_id'],
            "crow_id": crow_id,
            "action_type": "move",
            "direction": direction
        }

        # Manually create and return the Response
        return Response(
            json.dumps(response_data),  # Convert to JSON string
            mimetype='application/json'  # Set content type to JSON
        )

    # If it's a scan action (contains 'previous_action' and 'your_action' is 'scan')
    if 'previous_action' in data and data['previous_action'].get('your_action') == 'scan':
        prev_action = data['previous_action']
        crow_id = prev_action['crow_id']
        scan_result = prev_action['scan_result']

        # Extract wall positions (W) from the scan result (column-row format)
        submission = []
        for i in range(len(scan_result)):
            for j in range(len(scan_result[i])):
                if scan_result[i][j] == "W":
                    # Use the raw indices (no +1, directly using 0-based indexing)
                    submission.append(f"{j}-{i}")  # Add the coordinates as "column-row"

        # Log the detected walls
        logger.info(f"Crow {crow_id} has detected the following wall positions: {submission}")

        # Explicitly construct the response in the correct order with submission
        response_data = {
            "challenger_id": data['challenger_id'],
            "game_id": data['game_id'],
            "action_type": "submit",
            "submission": submission
        }

        # Manually create and return the Response
        return Response(
            json.dumps(response_data),  # Convert to JSON string
            mimetype='application/json'  # Set content type to JSON
        )

    # If it's a submit action (contains 'submission')
    if 'submission' in data:
        submission = data['submission']
        
        # Log the wall positions submitted
        logger.info(f"Wall positions submitted: {submission}")

        # Explicitly construct the response in the correct order
        response_data = {
            "challenger_id": data['challenger_id'],
            "game_id": data['game_id'],
            "action_type": "submit",
            "submission": submission
        }

        # Manually create and return the Response
        return Response(
            json.dumps(response_data),  # Convert to JSON string
            mimetype='application/json'  # Set content type to JSON
        )

    # If the request format doesn't match any of the expected types, return an error
    return jsonify({"error": "Invalid request format"}), 400
