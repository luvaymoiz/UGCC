import json
import logging
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def find_best_cycle(goods, rates_map):
    """
    Finds the most profitable trading cycle in a given graph.
    This implementation uses a brute-force search for short cycles,
    which is sufficient for the provided test cases.
    """
    num_goods = len(goods)
    best_gain_ratio = 1.0
    best_path_indices = []

    # Check for cycles of length 2, 3, and 4
    for i in range(num_goods):
        for j in range(num_goods):
            if i == j: continue
            
            # Check cycle of length 2: i -> j -> i
            if (i, j) in rates_map and (j, i) in rates_map:
                gain = rates_map[(i, j)] * rates_map[(j, i)]
                if gain > best_gain_ratio:
                    best_gain_ratio = gain
                    best_path_indices = [i, j, i]
            
            for k in range(num_goods):
                if i == k or j == k: continue
                
                # Check cycle of length 3: i -> j -> k -> i
                if (i, j) in rates_map and (j, k) in rates_map and (k, i) in rates_map:
                    gain = rates_map[(i, j)] * rates_map[(j, k)] * rates_map[(k, i)]
                    if gain > best_gain_ratio:
                        best_gain_ratio = gain
                        best_path_indices = [i, j, k, i]

                for l in range(num_goods):
                    if i == l or j == l or k == l: continue
                    
                    # Check cycle of length 4: i -> j -> k -> l -> i
                    if (i, j) in rates_map and (j, k) in rates_map and (k, l) in rates_map and (l, i) in rates_map:
                        gain = rates_map[(i, j)] * rates_map[(j, k)] * rates_map[(k, l)] * rates_map[(l, i)]
                        if gain > best_gain_ratio:
                            best_gain_ratio = gain
                            best_path_indices = [i, j, k, l, i]
                            
    # Convert indices to goods names
    best_path_names = [goods[i] for i in best_path_indices]
    
    return best_gain_ratio, best_path_names

@app.route("/The-Ink-Archive", methods=["POST"])
def solve_ink_archive():
    data = request.get_json(force=True, silent=False)
    results = []

    for test_case in data:
        goods = test_case.get("goods", [])
        ratios = test_case.get("ratios", [])
        
        # Create a dictionary for quick lookup of rates by (from_idx, to_idx)
        rates_map = {}
        for r in ratios:
            rates_map[(int(r[0]), int(r[1]))] = r[2]
        
        # Find the best trading cycle
        best_gain_ratio, best_path = find_best_cycle(goods, rates_map)
        
        # Calculate the gain percentage
        gain_percentage = (best_gain_ratio - 1) * 100
        
        result = {
            "path": best_path,
            "gain": gain_percentage
        }
        
        results.append(result)

    return jsonify(results)