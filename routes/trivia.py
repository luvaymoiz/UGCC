import logging
from flask import jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/trivia", methods=["GET"])
def trivia():
    answers = [1, 2, 3, 4]
    return jsonify({"answers": answers})


