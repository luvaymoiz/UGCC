import logging
from flask import jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/trivia", methods=["GET"])
def trivia():
    answers = [
        1,               
        3,       
        2,       
        2,
        3,
        4,
        1,
        [1, 2, 3, 4],
        4 
    ]
    return jsonify({"answers": answers})


