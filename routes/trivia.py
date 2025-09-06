import logging
import json
from flask import jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/trivia", methods=["GET"])
def trivia():
    answers = [
    1,                  # Q1: "Trivia!"
    3,                  # Q2: "Ticketing Agent"
    2,                  # Q3: "Blankety Blanks"
    2,                  # Q4: "Princess Diaries"
    3,                  # Q5: "MST Calculation"
    4,                  # Q6: "Universal Bureau of Surveillance" (Amy Winehouse)
    1,                  # Q7: "Operation Safeguard"
    [1, 2, 3, 4, 5],    # Q8: "Capture The Flag" (all are anagrams)
    4                   # Q9: "Filler 1"
  ]
    result = answers
    logging.info("answers :{}".format(result))
    return json.dumps(result)


