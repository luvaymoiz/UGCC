from flask import Flask, request, jsonify
from collections import deque
import json

app = Flask(__name__)

# This dictionary will store the state for each game instance.
# In a real-world scenario, this would be a database.
game_states = {}

# Game state keys:
# 'map': 2D list representing the discovered maze,
#        0 for empty, 1 for wall, -1 for unknown.
# 'crows': list of crow dictionaries [{'id': '1', 'x': 0, 'y': 0}, ...]
# 'known_walls': set of wall coordinates in "x-y" format
# 'num_of_walls': total number of walls to find
# 'length_of_grid': size of the grid
# 'scanned_cells': set of cells that have been scanned

def _update_map_from_scan(game_state, scan_result, crow_id):
    """
    Updates the global game map with the results of a scan action.
    """
    crow = next(c for c in game_state['crows'] if c['id'] == crow_id)
    crow_x, crow_y = crow['x'], crow['y']

    for i in range(5):
        for j in range(5):
            scan_char = scan_result[i][j]
            # Calculate absolute grid coordinates from relative scan coordinates
            map_x = crow_x + (j - 2)
            map_y = crow_y + (i - 2)

            if 0 <= map_x < game_state['length_of_grid'] and 0 <= map_y < game_state['length_of_grid']:
                if scan_char == 'W':
                    game_state['map'][map_y][map_x] = 1 # Wall
                    game_state['known_walls'].add(f"{map_x}-{map_y}")
                elif scan_char == '_':
                    game_state['map'][map_y][map_x] = 0 # Empty
    
    # Add the crow's current position to the set of scanned cells
    game_state['scanned_cells'].add((crow_x, crow_y))
    
def _is_valid_move(game_state, x, y):
    """
    Checks if a position is valid and not a known wall.
    """
    if 0 <= x < game_state['length_of_grid'] and 0 <= y < game_state['length_of_grid']:
        # We can move into an unknown cell (-1) or an empty cell (0)
        return game_state['map'][y][x] in [-1, 0]
    return False

def _find_next_target(game_state, crow_pos):
    """
    Finds the nearest unscanned or unknown cell using BFS.
    Returns the target position (x, y) or None if all cells are known.
    """
    q = deque([(crow_pos, [])]) # (position, path)
    visited = {crow_pos}
    
    # Directions: N, S, E, W
    directions = [(0, -1), (0, 1), (1, 0), (-1, 0)]
    
    while q:
        (x, y), path = q.popleft()
        
        # Check if this cell is a valid scan target
        if (x, y) not in game_state['scanned_cells']:
            return (x, y)

        for dx, dy in directions:
            next_x, next_y = x + dx, y + dy
            if (next_x, next_y) not in visited and _is_valid_move(game_state, next_x, next_y):
                visited.add((next_x, next_y))
                q.append(((next_x, next_y), path + [(next_x, next_y)]))

    return None

def _get_next_action(game_state):
    """
    The main AI logic for determining the next move or scan.
    """
    # Check if all walls have been found.
    if len(game_state['known_walls']) == game_state['num_of_walls']:
        return {
            "action_type": "submit",
            "submission": sorted(list(game_state['known_walls']))
        }
    
    # Simple strategy: Find a crow at an unscanned location and command it to scan.
    for crow in game_state['crows']:
        if (crow['x'], crow['y']) not in game_state['scanned_cells']:
            return {
                "crow_id": crow['id'],
                "action_type": "scan"
            }

    # If all crows are in scanned locations, move one towards an unknown area.
    best_crow = None
    best_path = float('inf')
    best_target = None
    
    # Simple strategy for now: pick the first crow and find a target.
    # In a more advanced solution, we could pick the crow closest to the next target.
    crow = game_state['crows'][0]
    target_pos = _find_next_target(game_state, (crow['x'], crow['y']))
    
    if target_pos:
        # Find the path to the target and get the first step.
        q = deque([((crow['x'], crow['y']), [])])
        visited = {(crow['x'], crow['y'])}
        path_to_target = None
        
        directions = [(0, -1, 'N'), (0, 1, 'S'), (1, 0, 'E'), (-1, 0, 'W')]
        
        while q:
            (x, y), path = q.popleft()
            if (x, y) == target_pos:
                path_to_target = path
                break
            
            for dx, dy, direction in directions:
                next_x, next_y = x + dx, y + dy
                if (next_x, next_y) not in visited and _is_valid_move(game_state, next_x, next_y):
                    visited.add((next_x, next_y))
                    q.append(((next_x, next_y), path + [direction]))
        
        if path_to_target and len(path_to_target) > 0:
             return {
                "crow_id": crow['id'],
                "action_type": "move",
                "direction": path_to_target[0]
            }

    # If no more unexplored areas, submit what we have found.
    return {
        "action_type": "submit",
        "submission": sorted(list(game_state['known_walls']))
    }


@app.route('/fogofwall', methods=['POST'])
def fog_of_wall():
    """
    Main endpoint for the Fog of Wall challenge.
    """
    try:
        payload = request.get_json()
        game_id = payload.get("game_id")
        
        if not game_id:
            return jsonify({"error": "game_id is required."}), 400
            
        # Initial request
        if "test_case" in payload:
            test_case = payload["test_case"]
            length_of_grid = test_case["length_of_grid"]
            num_of_walls = test_case["num_of_walls"]
            
            # Initialize game state
            game_states[game_id] = {
                'map': [[-1] * length_of_grid for _ in range(length_of_grid)],
                'crows': test_case['crows'],
                'known_walls': set(),
                'num_of_walls': num_of_walls,
                'length_of_grid': length_of_grid,
                'scanned_cells': set()
            }
            # Initial action: Scan with the first crow to get a starting map
            return jsonify({
                "challenger_id": payload['challenger_id'],
                "game_id": game_id,
                "crow_id": test_case['crows'][0]['id'],
                "action_type": "scan"
            })
            
        # Subsequent request with results
        elif "previous_action" in payload:
            game_state = game_states.get(game_id)
            if not game_state:
                return jsonify({"error": "Game state not found."}), 404
            
            prev_action = payload['previous_action']
            crow_id = prev_action['crow_id']
            
            if prev_action['your_action'] == 'scan':
                _update_map_from_scan(game_state, prev_action['scan_result'], crow_id)
            elif prev_action['your_action'] == 'move':
                # Find the crow and update its position
                crow = next(c for c in game_state['crows'] if c['id'] == crow_id)
                new_pos = prev_action['move_result']
                crow['x'] = new_pos[0]
                crow['y'] = new_pos[1]
                
            # Get the next action based on the updated state
            next_action = _get_next_action(game_state)
            
            # Add common payload fields and return
            next_action['challenger_id'] = payload['challenger_id']
            next_action['game_id'] = game_id
            
            return jsonify(next_action)
            
        else:
            return jsonify({"error": "Invalid payload format."}), 400

    except Exception as e:
        app.logger.error(f"An error occurred: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500
