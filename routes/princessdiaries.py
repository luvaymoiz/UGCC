import sys
import logging
from flask import Flask, request, jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route('/evaluate', methods=['POST'])


# --- Solution Code ---
# This is the solver function from the previous response.

def solve_princess_schedule(data):
    
    """
    Finds the optimal schedule for the princess to maximize score and minimize travel fees.
    """
    tasks = data['tasks']
    subway = data['subway']
    starting_station = data['starting_station']

    # 1. Pre-processing: Identify all unique stations and sort tasks
    stations = set([starting_station])
    for task in tasks:
        stations.add(task['station'])
    for route in subway:
        stations.add(route['connection'][0])
        stations.add(route['connection'][1])
    
    max_station_id = 0
    if stations:
        max_station_id = max(stations)
    
    num_stations = max_station_id + 1

    tasks.sort(key=lambda x: x['start'])
    num_tasks = len(tasks)

    if num_tasks == 0:
        return {"max_score": 0, "min_fee": 0, "schedule": []}

    # 2. All-Pairs Shortest Path (Floyd-Warshall Algorithm)
    dist = [[float('inf')] * num_stations for _ in range(num_stations)]
    for i in range(num_stations):
        dist[i][i] = 0

    for route in subway:
        u, v = route['connection']
        fee = route['fee']
        if u < num_stations and v < num_stations:
            dist[u][v] = min(dist[u][v], fee)
            dist[v][u] = min(dist[v][u], fee)

    for k in range(num_stations):
        for i in range(num_stations):
            for j in range(num_stations):
                if dist[i][k] != float('inf') and dist[k][j] != float('inf'):
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])

    # 3. Dynamic Programming
    dp = [(0, 0)] * num_tasks
    parent = [-1] * num_tasks

    for i in range(num_tasks):
        task_i = tasks[i]
        base_score = task_i['score']
        base_fee = dist[starting_station][task_i['station']]
        dp[i] = (base_score, base_fee)
        
        for j in range(i):
            task_j = tasks[j]
            if task_j['end'] <= task_i['start']:
                prev_score, prev_fee = dp[j]
                new_score = prev_score + task_i['score']
                new_fee = prev_fee + dist[task_j['station']][task_i['station']]
                
                current_best_score, current_best_fee = dp[i]
                if new_score > current_best_score or \
                   (new_score == current_best_score and new_fee < current_best_fee):
                    dp[i] = (new_score, new_fee)
                    parent[i] = j
    
    # 4. Find the best overall schedule
    max_score = -1
    min_fee = float('inf')
    best_end_index = -1

    for i in range(num_tasks):
        score, partial_fee = dp[i]
        total_fee = partial_fee + dist[tasks[i]['station']][starting_station]
        
        if score > max_score or (score == max_score and total_fee < min_fee):
            max_score = score
            min_fee = total_fee
            best_end_index = i

    if best_end_index == -1:
        # This handles the case where no tasks are possible, 
        # but given the problem, we can likely find at least one.
        # If the only possible schedule is one task, this logic still works.
        # To handle truly zero tasks, check the initial num_tasks.
        return {"max_score": 0, "min_fee": 0, "schedule": []}


    # 5. Reconstruct the schedule
    schedule_names = []
    curr_index = best_end_index
    while curr_index != -1:
        schedule_names.append(tasks[curr_index]['name'])
        curr_index = parent[curr_index]
    schedule_names.reverse()

    return {
        "max_score": max_score,
        "min_fee": min_fee,
        "schedule": schedule_names
    }



# --- API Endpoint ---
# This defines the URL and method for our API.
@app.route('/evaluate', methods=['POST'])
def evaluate_princessdiaries():
    # Get the JSON data sent in the request body
    input_data = request.get_json()
    logger.info(f"Received: {input_data}")
    
    # Call the solver function with the input data
    result = solve_princess_schedule(input_data)
    
    logger.info(f"Returned: {result}")
    
    # Return the result as a JSON response
    return jsonify(result)
