import logging
import json
from flask import jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/trivia", methods=["GET"])
def trivia():
    answers = [
    4,                  # Q1: "Trivia!"
    1,                  # Q2: "Ticketing Agent"
    2,                  # Q3: "Blankety Blanks"
    2,                  # Q4: "Princess Diaries"
    3,                  # Q5: "MST Calculation"
    4,                  # Q6: "Universal Bureau of Surveillance" (Amy Winehouse)
    1,                  # Q7: "Operation Safeguard"
    5,    # Q8: "Capture The Flag" (all are anagrams)
    4,                   # Q9: "Filler 1"
    3,                     #10
    3,#11
    2,#12
    4,#12
    1,#12
    2,#12
    1,#12
    1,#12
    2,
    2,
    1,
    1,
    2,
    3,
    3,
    2
  ]
    logging.info("answers : %s", answers)
    return jsonify({"answers": answers})


