import logging
import socket

from routes import app
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

def _linear_imputation(data):
    """
    Imputes missing 'null' values in a single list using piecewise linear interpolation.
    It finds the non-null points and interpolates between them.
    This method is robust for handling gaps of various sizes.
    """
    if not data:
        return []

    # Find the indices and values of non-null data points
    known_indices = [i for i, x in enumerate(data) if x is not None]
    known_values = [data[i] for i in known_indices]

    # If there are no known values, return the list as is (no imputation possible)
    if not known_values:
        return data

    # Create a copy of the list to perform imputation on
    imputed_data = list(data)

    # Handle leading nulls: use the first known value
    first_known_index = known_indices[0]
    for i in range(first_known_index):
        imputed_data[i] = known_values[0]

    # Handle trailing nulls: use the last known value
    last_known_index = known_indices[-1]
    for i in range(last_known_index + 1, len(data)):
        imputed_data[i] = known_values[-1]

    # Interpolate for nulls between known values
    for i in range(len(known_indices) - 1):
        start_idx = known_indices[i]
        end_idx = known_indices[i+1]
        start_val = known_values[i]
        end_val = known_values[i+1]

        # Calculate the number of steps and the step size
        num_steps = end_idx - start_idx
        if num_steps > 1:
            step_size = (end_val - start_val) / num_steps
            for j in range(1, num_steps):
                if imputed_data[start_idx + j] is None:
                    imputed_data[start_idx + j] = start_val + (j * step_size)
    
    return imputed_data

@app.route('/blanketyblanks', methods=['POST'])

def blankety_blanks():
    try:
        payload = request.get_json()
        series = payload.get("series", [])
        
        if not isinstance(series, list) or not all(isinstance(s, list) for s in series):
            return jsonify({"error": "Invalid input format. 'series' must be an array of lists."}), 400
        
        imputed_series = []
        for s in series:
            imputed_list = _linear_imputation(s)
            imputed_series.append(imputed_list)

        return jsonify({"answer": imputed_series}), 200

    except Exception as e:
        # Generic error handling for unexpected issues
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Running the Flask application
    # In a production environment, you would use a more robust server like Gunicorn or uWSGI
    app.run(debug=True, host='0.0.0.0', port=5000)