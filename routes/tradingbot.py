import json
import logging
import random
from flask import Flask, request, jsonify
from routes import app

# Set up logging for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/trading-bot", methods=["POST"])
def trading_bot():
    """
    This endpoint processes a list of news events and their associated candle
    data, and returns a list of 50 trading decisions.
    
    The decision-making logic is a placeholder as the "correct" decision
    relies on a future, hidden exit price. This simple logic randomly
    selects between 'LONG' and 'SHORT' for demonstration.
    
    The expected input is a JSON array of event objects.
    The expected output is a JSON array of decision objects.
    """
    
    try:
        # Get the JSON data from the POST request body
        data = request.get_json(force=True, silent=False)
        
        # Check if the data is a list and if it's not empty
        if not isinstance(data, list) or not data:
            logger.error("Invalid input: data is not a list or is empty")
            return jsonify({"error": "Invalid input, expected a list of events"}), 400
        
        # Select the first 50 news events from the input.
        # The challenge specifies the bot should output decisions for 50 events.
        # We assume the input list has at least 50 events as per the prompt.
        selected_events = data[:50]
        
        # Prepare the list to store the trading decisions
        decisions = []
        
        # Iterate over the selected events to make a trading decision for each
        for event in selected_events:
            event_id = event.get("id")
            
            # Placeholder logic for making a trading decision.
            # In a real-world scenario, this is where a predictive model
            # would analyze the news title and historical price data to
            # predict whether the price will go up or down.
            # Since the exit price is hidden, we'll use a random choice.
            decision = random.choice(["LONG", "SHORT"])
            
            # Append the decision to the decisions list
            decisions.append({
                "id": event_id,
                "decision": decision
            })
            
        # Log the number of decisions made
        logger.info(f"Generated {len(decisions)} trading decisions.")

        # Return the list of decisions as a JSON response with a 200 OK status
        return jsonify(decisions), 200
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
