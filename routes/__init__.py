from flask import Flask

app = Flask(__name__)
import routes.square
import routes.trivia    
import routes.ticketingagent
import routes.princessdiaries
import routes.trivia
import os



# Your live server's URL. We'll get this from an environment variable in the GitHub Action.
# Fallback to your URL for local testing.
API_URL = os.getenv("API_URL", "https://ugcc.onrender.com/evaluate")

# The test case: the data to send.
test_input_data = {
  "tasks": [
    {"name": "A", "start": 480, "end": 540, "station": 1, "score": 2},
    {"name": "B", "start": 600, "end": 660, "station": 2, "score": 1},
    {"name": "C", "start": 720, "end": 780, "station": 3, "score": 3},
    {"name": "D", "start": 840, "end": 900, "station": 4, "score": 1},
    {"name": "E", "start": 960, "end": 1020, "station": 1, "score": 4},
    {"name": "F", "start": 530, "end": 590, "station": 2, "score": 1}
  ],
  "subway": [
    {"connection": [0, 1], "fee": 10},
    {"connection": [1, 2], "fee": 10},
    {"connection": [2, 3], "fee": 20},
    {"connection": [3, 4], "fee": 30}
  ],
  "starting_station": 0
}

# The expected result from the server.
expected_output = {
    "max_score": 11,
    "min_fee": 140,
    "schedule": ["A", "B", "C", "D", "E"]
}

print(f"▶️  Testing API endpoint: {API_URL}")
main
