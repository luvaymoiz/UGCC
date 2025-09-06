import json
import logging
from flask import request, jsonify
from routes import app

# Setup logger
logger = logging.getLogger(__name__)

@app.route("/The-Ink-Archive", methods=["POST"])
def inkarchive():
    # Get the JSON data from the request body
    data = request.get_json(force=True, silent=False)

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Check if 'data' is a list or dictionary and handle accordingly
    if isinstance(data, list):
        # If it's a list, we assume the format is already structured correctly
        goods = data[0].get("goods", [])  # Assuming the goods data is inside the first list item
        rates = data[0].get("rates", [])
    elif isinstance(data, dict):
        goods = data.get("goods", [])
        rates = data.get("rates", [])
    else:
        return jsonify({"error": "Invalid data format"}), 400

    if not goods or not rates:
        return jsonify({"error": "Invalid data: 'goods' and 'rates' are required."}), 400

    # Continue processing as usual
    # Number of goods
    n = len(goods)

    # Initialize graph
    graph = {good: [] for good in goods}

    # Build graph with trade rates
    for i in range(n):
        for j in range(n):
            if rates[i][j] > 0:  # If there's a trade rate
                graph[goods[i]].append((goods[j], rates[i][j]))

    # Bellman-Ford algorithm to detect arbitrage (profitable cycles)
    def bellman_ford(start):
        dist = {good: -float('inf') for good in goods}
        dist[start] = 1  # Starting with 1 unit of the start good

        # Relax edges n-1 times
        for _ in range(n - 1):
            for u in goods:
                for v, rate in graph[u]:
                    if dist[u] * rate > dist[v]:
                        dist[v] = dist[u] * rate

        # Check for profitable cycles (arbitrage)
        for u in goods:
            for v, rate in graph[u]:
                if dist[u] * rate > dist[v]:
                    return True  # Arbitrage found
        return False

    # Test all goods to see if we can find an arbitrage cycle
    for good in goods:
        if bellman_ford(good):
            logger.info(f"Profitable cycle exists, starting with {good}")
            return jsonify({"message": f"Profitable cycle exists, starting with {good}"})

    # If no profitable cycle is found
    return jsonify({"message": "No profitable cycle found."})

