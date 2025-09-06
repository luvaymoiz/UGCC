from flask import Flask, jsonify, request
from flask_cors import CORS
from routes import app
import logging


logger = logging.getLogger(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Placeholder for game state
game_state = {
    'grid': [[0] * 4 for _ in range(4)],  # Empty 4x4 grid
    'score': 0
}

# API to start a new game
@app.route('/new_game', methods=['GET'])
def new_game():
    global game_state
    game_state = {
        'grid': [[0] * 4 for _ in range(4)],  # Reset grid
        'score': 0
    }
    return jsonify(game_state)

# API to make a move (this is a simplified version for example)
@app.route('/move', methods=['POST'])
def make_move():
    direction = request.json.get('direction', '')  # Get the direction of the move
    if direction not in ['up', 'down', 'left', 'right']:
        return jsonify({"error": "Invalid move direction"}), 400
    
    # Here, you should implement the game logic (e.g., shifting and merging tiles)
    # For now, we're just returning the current state.
    
    return jsonify(game_state)

# API to get the current game state
@app.route('/2048.html', methods=['GET'])
def get_game_state():
    return jsonify(game_state)

if __name__ == '__main__':
    app.run(debug=True)
