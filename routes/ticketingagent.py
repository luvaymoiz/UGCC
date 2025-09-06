import logging
import json
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def euclidean_distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) ** 0.5

@app.route("/ticketing-agent", methods=["POST"])
def ticketing_agent():
    data = request.get_json()
    customers = data["customers"]
    concerts = data["concerts"]
    priority = data.get("priority", {})

    results = {}

    for customer in customers:
        name = customer["name"]
        vip_status = customer["vip_status"]
        location = customer["location"]
        credit_card = customer["credit_card"]

        best_concert = None
        best_score = float("-inf")

        for concert in concerts:
            score = 0

            # VIP points
            if vip_status:
                score += 100

            # Credit card priority
            if credit_card in priority and priority[credit_card] == concert["name"]:
                score += 50

            # Latency (closer = higher points, scale to 30)
            dist = euclidean_distance(location, concert["booking_center_location"])
            if dist == 0:
                latency_points = 30
            elif dist <= 10:
                latency_points = 20
            else:
                latency_points = 0
            score += latency_points

            if score > best_score:
                best_score = score
                best_concert = concert["name"]

        results[name] = best_concert

    return jsonify(results)
