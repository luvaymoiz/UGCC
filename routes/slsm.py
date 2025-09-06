import json
import logging
import heapq
import math
from flask import request, jsonify
from flask import Flask
from routes import app


logger = logging.getLogger(__name__)


# --- Game Logic Helper Functions ---

def parse_jumps(jumps_raw):
    """Parses the raw jump strings from the input into structured data."""
    snakes, ladders = {}, {}
    smokes, mirrors = set(), set()
    for jump in jumps_raw:
        start_str, end_str = jump.split(':')
        start, end = int(start_str), int(end_str)
        if start == 0:
            mirrors.add(end)
        elif end == 0:
            smokes.add(start)
        elif start > end:
            snakes[start] = end
        else:
            ladders[start] = end
    return snakes, ladders, smokes, mirrors

def get_next_square(pos, roll, board_size, snakes, ladders):
    """
    Calculates the final square after a single roll, including overshoots
    and subsequent snake/ladder jumps.
    """
    if pos + roll > board_size:
        # Per the rules, overshoot means moving backwards from the end
        land_pos = board_size - ((pos + roll) - board_size)
    else:
        land_pos = pos + roll
    
    # Apply snake or ladder if the landing square has one
    return ladders.get(land_pos, snakes.get(land_pos, land_pos))

def find_shortest_path(board_size, snakes, ladders, smokes, mirrors):
    """
    Uses Dijkstra's algorithm to find the path with the minimum number of
    die rolls for a single player to get from square 1 to the final square.
    """
    # dist[square] stores the minimum number of rolls to reach it
    dist = {i: float('inf') for i in range(1, board_size + 2)}
    # parent[square] stores the previous square and the roll(s) to get there
    parent = {i: None for i in range(1, board_size + 2)}
    
    dist[1] = 0
    # Priority queue stores: (cost_in_rolls, square)
    pq = [(0, 1)]

    while pq:
        cost, current_square = heapq.heappop(pq)

        if cost > dist[current_square]:
            continue
        
        # Once we pull the final square, we have found the shortest path to it
        if current_square == board_size:
            break

        # Explore all 6 possible primary die rolls
        for d1 in range(1, 7):
            pos_after_d1 = get_next_square(current_square, d1, board_size, snakes, ladders)
            
            # Case 1: Landed on a Smoke square (2-roll move)
            if pos_after_d1 in smokes:
                for d2 in range(1, 7):
                    final_pos = max(1, pos_after_d1 - d2)
                    if cost + 2 < dist[final_pos]:
                        dist[final_pos] = cost + 2
                        parent[final_pos] = (current_square, [d1, d2])
                        heapq.heappush(pq, (dist[final_pos], final_pos))
            
            # Case 2: Landed on a Mirror square (2-roll move)
            elif pos_after_d1 in mirrors:
                for d2 in range(1, 7):
                    final_pos = get_next_square(pos_after_d1, d2, board_size, snakes, ladders)
                    if cost + 2 < dist[final_pos]:
                        dist[final_pos] = cost + 2
                        parent[final_pos] = (current_square, [d1, d2])
                        heapq.heappush(pq, (dist[final_pos], final_pos))
            
            # Case 3: Normal landing (1-roll move)
            else:
                final_pos = pos_after_d1
                if cost + 1 < dist[final_pos]:
                    dist[final_pos] = cost + 1
                    parent[final_pos] = (current_square, [d1])
                    heapq.heappush(pq, (dist[final_pos], final_pos))

    # Reconstruct the path by backtracking from the final square
    path = []
    curr = board_size
    if parent[curr] is None: # No path found
        return []
        
    while curr != 1:
        prev, rolls = parent[curr]
        path.insert(0, rolls)
        curr = prev
        
    return path

def find_worst_move(pos, board_size, snakes, ladders, smokes, mirrors):
    """
    For non-winning players, finds the move (1 or 2 rolls) that results
    in landing on the square with the lowest possible number.
    """
    worst_outcome = {'pos': float('inf'), 'rolls': []}

    for d1 in range(1, 7):
        pos_after_d1 = get_next_square(pos, d1, board_size, snakes, ladders)
        
        if pos_after_d1 in smokes:
            # To get the worst outcome, move backward the maximum amount (roll 6)
            final_pos = max(1, pos_after_d1 - 6)
            if final_pos < worst_outcome['pos']:
                worst_outcome = {'pos': final_pos, 'rolls': [d1, 6]}
        elif pos_after_d1 in mirrors:
            # Check all possible second rolls to find the one that lands lowest
            local_worst_pos_for_d1 = float('inf')
            best_d2_for_worst_pos = 0
            for d2 in range(1, 7):
                final_pos = get_next_square(pos_after_d1, d2, board_size, snakes, ladders)
                if final_pos < local_worst_pos_for_d1:
                    local_worst_pos_for_d1 = final_pos
                    best_d2_for_worst_pos = d2
            if local_worst_pos_for_d1 < worst_outcome['pos']:
                worst_outcome = {'pos': local_worst_pos_for_d1, 'rolls': [d1, best_d2_for_worst_pos]}
        else:
            if pos_after_d1 < worst_outcome['pos']:
                worst_outcome = {'pos': pos_after_d1, 'rolls': [d1]}
                
    return worst_outcome

# --- Flask Route ---

@app.route("/slsm", methods=["POST"])
def slsm_solver():
    """Main endpoint to solve the Snakes & Ladders puzzle."""
    try:
        data = request.get_json(force=True, silent=False)
        logger.info(f"Received data: {data}")

        board_size = data['boardSize']
        num_players = data['players']
        snakes, ladders, smokes, mirrors = parse_jumps(data['jumps'])

        # 1. Find the optimal sequence of moves for the last player to win.
        winning_moves = find_shortest_path(board_size, snakes, ladders, smokes, mirrors)

        if not winning_moves:
            logger.error("No winning path could be found.")
            return jsonify({"error": "No solution exists."}), 400

        # 2. Build the final list of rolls by interleaving player turns.
        final_rolls = []
        player_positions = {i: 1 for i in range(num_players)}
        last_player_idx = num_players - 1
        winning_move_idx = 0
        turn = 0
        
        while winning_move_idx < len(winning_moves):
            current_player_idx = turn % num_players

            if current_player_idx == last_player_idx:
                # It's the winning player's turn, use the pre-calculated move.
                move_rolls = winning_moves[winning_move_idx]
                final_rolls.extend(move_rolls)
                winning_move_idx += 1
                # We don't need to simulate the winning player's path as it's already determined.
            else:
                # It's another player's turn, give them a stalling move.
                current_pos = player_positions[current_player_idx]
                worst_move = find_worst_move(current_pos, board_size, snakes, ladders, smokes, mirrors)
                final_rolls.extend(worst_move['rolls'])
                # CRITICAL FIX: Update the player's position for their next turn.
                player_positions[current_player_idx] = worst_move['pos']
            
            turn += 1

        logger.info(f"Successful solution found with {len(final_rolls)} rolls.")
        return jsonify(final_rolls)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500