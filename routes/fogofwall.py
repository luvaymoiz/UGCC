from flask import Flask, request, jsonify
import json
from typing import Dict, List, Tuple, Set, Optional
import heapq
from collections import deque

app = Flask(__name__)

class FogOfWallSolver:
    def __init__(self):
        self.games: Dict[str, 'GameState'] = {}
    
    def get_or_create_game(self, game_id: str, test_case: dict = None) -> 'GameState':
        if game_id not in self.games:
            if test_case is None:
                raise ValueError(f"Game {game_id} not found and no test_case provided")
            self.games[game_id] = GameState(test_case)
        return self.games[game_id]

class GameState:
    def __init__(self, test_case: dict):
        self.game_id = test_case['game_id']
        self.length_of_grid = test_case['length_of_grid']
        self.num_of_walls = test_case['num_of_walls']
        
        # Initialize crows
        self.crows = {}
        for crow_data in test_case['crows']:
            self.crows[crow_data['id']] = {
                'x': crow_data['x'],
                'y': crow_data['y']
            }
        
        # Initialize knowledge maps
        self.known_cells: Set[Tuple[int, int]] = set()  # Cells we've scanned
        self.walls: Set[Tuple[int, int]] = set()  # Confirmed wall positions
        self.empty_cells: Set[Tuple[int, int]] = set()  # Confirmed empty positions
        
        # Track scan coverage
        self.scanned_areas: Set[Tuple[int, int]] = set()  # Center positions of 5x5 scans
        
        # Movement tracking
        self.move_count = 0
        self.max_moves = self.length_of_grid ** 2
        
        # Strategy state
        self.exploration_phase = True
        self.current_crow_index = 0
        self.crow_ids = list(self.crows.keys())
    
    def update_crow_position(self, crow_id: str, new_pos: List[int]):
        """Update crow position after a move"""
        self.crows[crow_id]['x'] = new_pos[0]
        self.crows[crow_id]['y'] = new_pos[1]
        self.move_count += 1
    
    def process_scan_result(self, crow_id: str, scan_result: List[List[str]]):
        """Process the 5x5 scan result and update our knowledge"""
        crow_x = self.crows[crow_id]['x']
        crow_y = self.crows[crow_id]['y']
        
        # Mark this position as scanned
        self.scanned_areas.add((crow_x, crow_y))
        
        # Process the 5x5 grid (centered on crow)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                grid_x = crow_x + dx
                grid_y = crow_y + dy
                scan_x = dx + 2
                scan_y = dy + 2
                
                cell_value = scan_result[scan_y][scan_x]
                
                if cell_value == 'X':  # Out of bounds
                    continue
                elif cell_value == 'W':  # Wall
                    self.walls.add((grid_x, grid_y))
                    self.known_cells.add((grid_x, grid_y))
                elif cell_value == '_' or cell_value == 'C':  # Empty or crow
                    self.empty_cells.add((grid_x, grid_y))
                    self.known_cells.add((grid_x, grid_y))
        
        self.move_count += 1
    
    def get_unexplored_cells(self) -> Set[Tuple[int, int]]:
        """Get cells that haven't been scanned yet"""
        all_cells = set()
        for x in range(self.length_of_grid):
            for y in range(self.length_of_grid):
                all_cells.add((x, y))
        
        explored_cells = set()
        for scan_center in self.scanned_areas:
            cx, cy = scan_center
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ex, ey = cx + dx, cy + dy
                    if 0 <= ex < self.length_of_grid and 0 <= ey < self.length_of_grid:
                        explored_cells.add((ex, ey))
        
        return all_cells - explored_cells
    
    def find_optimal_scan_position(self, crow_id: str) -> Optional[Tuple[int, int]]:
        """Find the best position to scan that covers the most unexplored cells"""
        crow_x = self.crows[crow_id]['x']
        crow_y = self.crows[crow_id]['y']
        unexplored = self.get_unexplored_cells()
        
        if not unexplored:
            return None
        
        best_pos = None
        best_score = -1
        
        # Consider positions within reasonable distance
        search_radius = 10
        for target_x in range(max(0, crow_x - search_radius), 
                            min(self.length_of_grid, crow_x + search_radius + 1)):
            for target_y in range(max(0, crow_y - search_radius), 
                                min(self.length_of_grid, crow_y + search_radius + 1)):
                
                # Skip if already scanned from this position
                if (target_x, target_y) in self.scanned_areas:
                    continue
                
                # Skip if this is a known wall
                if (target_x, target_y) in self.walls:
                    continue
                
                # Count how many unexplored cells this scan would cover
                coverage = 0
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        check_x, check_y = target_x + dx, target_y + dy
                        if (check_x, check_y) in unexplored:
                            coverage += 1
                
                if coverage > 0:
                    # Factor in distance (prefer closer positions)
                    distance = abs(target_x - crow_x) + abs(target_y - crow_y)
                    score = coverage * 10 - distance
                    
                    if score > best_score:
                        best_score = score
                        best_pos = (target_x, target_y)
        
        return best_pos
    
    def find_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[str]:
        """Find shortest path from start to end, avoiding known walls"""
        if start == end:
            return []
        
        # BFS pathfinding
        queue = deque([(start, [])])
        visited = {start}
        
        directions = [('N', 0, -1), ('S', 0, 1), ('E', 1, 0), ('W', -1, 0)]
        
        while queue:
            (x, y), path = queue.popleft()
            
            for dir_name, dx, dy in directions:
                nx, ny = x + dx, y + dy
                
                # Check bounds
                if not (0 <= nx < self.length_of_grid and 0 <= ny < self.length_of_grid):
                    continue
                
                # Skip known walls
                if (nx, ny) in self.walls:
                    continue
                
                # Skip visited
                if (nx, ny) in visited:
                    continue
                
                new_path = path + [dir_name]
                
                if (nx, ny) == end:
                    return new_path
                
                queue.append(((nx, ny), new_path))
                visited.add((nx, ny))
        
        return []  # No path found
    
    def get_next_action(self) -> dict:
        """Determine the next action to take"""
        # Check if we've found all walls
        if len(self.walls) >= self.num_of_walls:
            return {
                'action_type': 'submit',
                'submission': [f"{x}-{y}" for x, y in self.walls]
            }
        
        # Check if we're running out of moves
        if self.move_count >= self.max_moves - 1:
            return {
                'action_type': 'submit',
                'submission': [f"{x}-{y}" for x, y in self.walls]
            }
        
        # Round-robin between crows
        crow_id = self.crow_ids[self.current_crow_index]
        self.current_crow_index = (self.current_crow_index + 1) % len(self.crow_ids)
        
        crow_x = self.crows[crow_id]['x']
        crow_y = self.crows[crow_id]['y']
        
        # If we haven't scanned from current position, scan first
        if (crow_x, crow_y) not in self.scanned_areas:
            return {
                'action_type': 'scan',
                'crow_id': crow_id
            }
        
        # Find optimal position to move and scan
        target_pos = self.find_optimal_scan_position(crow_id)
        
        if target_pos is None:
            # No good scan positions found, submit what we have
            return {
                'action_type': 'submit',
                'submission': [f"{x}-{y}" for x, y in self.walls]
            }
        
        # Find path to target position
        path = self.find_path((crow_x, crow_y), target_pos)
        
        if not path:
            # Can't reach target, try to scan from current position anyway
            return {
                'action_type': 'scan',
                'crow_id': crow_id
            }
        
        # Move towards target
        return {
            'action_type': 'move',
            'crow_id': crow_id,
            'direction': path[0]
        }

solver = FogOfWallSolver()

@app.route('/fog-of-wall', methods=['POST'])
def fog_of_wall():
    try:
        data = request.json
        challenger_id = data['challenger_id']
        game_id = data['game_id']
        
        # Handle initial request
        if 'test_case' in data:
            game = solver.get_or_create_game(game_id, data['test_case'])
            action = game.get_next_action()
        else:
            # Handle subsequent requests with previous action results
            game = solver.get_or_create_game(game_id)
            
            if 'previous_action' in data:
                prev_action = data['previous_action']
                
                if prev_action['your_action'] == 'move':
                    game.update_crow_position(prev_action['crow_id'], prev_action['move_result'])
                elif prev_action['your_action'] == 'scan':
                    game.process_scan_result(prev_action['crow_id'], prev_action['scan_result'])
            
            action = game.get_next_action()
        
        # Prepare response
        response = {
            'challenger_id': challenger_id,
            'game_id': game_id,
            **action
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
