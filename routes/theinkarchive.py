import json
import logging
import math
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def find_best_cycle(goods, rates_map):
    """
    Finds the most profitable trading cycle using a Bellman-Ford-like approach.
    This can find profitable cycles of any length.
    """
    num_goods = len(goods)
    max_gain = 1.0
    best_path_indices = []

    # We need to test for cycles starting from every node
    for start_node in range(num_goods):
        # Initialize distances and predecessors
        # We use negative log of rates to find the "shortest" path, which corresponds to the highest product of rates
        distance = [float('inf')] * num_goods
        predecessor = [-1] * num_goods
        distance[start_node] = 0

        # Relax edges repeatedly
        for i in range(num_goods): # n iterations for a graph with n nodes
            updated_in_iteration = False
            for (u, v), rate in rates_map.items():
                if rate <= 0: continue # Skip non-positive rates
                
                # Using negative log to convert multiplication to addition
                weight = -math.log(rate)
                
                if distance[u] + weight < distance[v]:
                    # Using a small epsilon to handle floating point inaccuracies
                    if abs(distance[u] + weight - distance[v]) > 1e-9:
                        distance[v] = distance[u] + weight
                        predecessor[v] = u
                        updated_in_iteration = True

            # If no updates in the (n-1)th iteration, no negative cycle from start_node
            if i == num_goods - 2 and not updated_in_iteration:
                break

        # In the nth iteration, check for nodes that are part of a profitable cycle
        if updated_in_iteration:
            for (u, v), rate in rates_map.items():
                if rate <= 0: continue
                weight = -math.log(rate)
                
                if distance[u] + weight < distance[v]:
                    if abs(distance[u] + weight - distance[v]) > 1e-9:
                        # Profitable cycle found. Reconstruct it.
                        path = []
                        current = v
                        # Backtrack to find the cycle
                        for _ in range(num_goods):
                            if current == -1: # Should not happen in a cycle
                                break
                            path.insert(0, current)
                            current = predecessor[current]
                        
                        # Find where the cycle actually starts
                        cycle_start_index = -1
                        for i in range(len(path) -1):
                            if path[i] == v:
                                cycle_start_index = i
                                break
                        
                        if cycle_start_index != -1:
                            cycle = path[cycle_start_index:]
                            # Ensure the path starts and ends at the same node
                            if cycle[0] != cycle[-1]:
                                cycle.append(cycle[0])

                            # Calculate gain for this cycle
                            current_gain = 1.0
                            for i in range(len(cycle) - 1):
                                from_node, to_node = cycle[i], cycle[i+1]
                                current_gain *= rates_map.get((from_node, to_node), 0)

                            if current_gain > max_gain:
                                max_gain = current_gain
                                best_path_indices = cycle

    best_path_names = [goods[i] for i in best_path_indices]
    return max_gain, best_path_names


@app.route("/The-Ink-Archive", methods=["POST"])
def solve_ink_archive():
    data = request.get_json(force=True, silent=False)
    results = []

    for test_case in data:
        goods = test_case.get("goods", [])
        ratios = test_case.get("ratios", [])
        
        rates_map = {}
        for r in ratios:
            # The problem statement implies indices are floats in JSON, but they represent integers.
            from_idx, to_idx = int(r[0]), int(r[1])
            rate = r[2]
            rates_map[(from_idx, to_idx)] = rate
        
        best_gain_ratio, best_path = find_best_cycle(goods, rates_map)
        
        if best_gain_ratio > 1.0:
            gain_percentage = (best_gain_ratio - 1) * 100
        else:
            # If no profitable cycle is found, gain is 0.
            gain_percentage = 0.0
        
        result = {
            "path": best_path,
            "gain": gain_percentage
        }
        
        results.append(result)

    return jsonify(results)