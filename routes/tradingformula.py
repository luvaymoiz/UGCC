import logging
import math
import re
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from routes import app


logger = logging.getLogger(__name__)

# 2. Core Evaluation Logic (from previous solution)
def solve_formula(formula_str: str, variables: dict) -> float:
    expression = formula_str
    while "\\\\" in expression:
        expression = expression.replace("\\\\", "\\")
    
    expression = re.sub(r"^(.*?=)", "", expression).strip().replace("$$", "")

    sorted_vars = sorted(variables.keys(), key=len, reverse=True)
    for var_name in sorted_vars:
        expression = expression.replace(f"\\text{{{var_name}}}", str(variables[var_name]))
        expression = expression.replace(var_name, str(variables[var_name]))

    replacements = {
        r"\times": "*", r"\cdot": "*", r"\frac{": "(", r"}{": ")/(",
        r"\max": "max", r"\min": "min", r"e^": "math.exp", r"\log": "math.log",
        r"\sum": "sum", r"{": "(", r"}": ")", r"[": "(", r"]": ")",
    }
    for latex, python_syntax in replacements.items():
        expression = expression.replace(latex, python_syntax)
    
    expression = expression.replace("\\", "")
    expression = "".join(expression.split())
    
    logger.info(f"Translated expression for evaluation: '{expression}'")
    
    safe_context = {
        "max": max, "min": min, "sum": sum, "math": math, "__builtins__": None
    }
    
    result = eval(expression, safe_context)
    return float(result)


# 3. Flask API Endpoint
@app.route("/trading-formula", methods=["POST"])
def evaluate_trading_formula():
    logger.info("Received request on /trading-formula endpoint.")
    
    try:
        # This is where the error from your screenshot occurs.
        # It fails if the request body is not valid JSON.
        test_cases = request.get_json()

        if not isinstance(test_cases, list):
            logger.error("Invalid JSON format: A JSON array was expected.")
            return jsonify({"error": "Input must be a JSON array"}), 400

        response_data = []
        for case in test_cases:
            name = case.get('name', 'Unnamed Case')
            try:
                formula = case.get("formula")
                variables = case.get("variables")
                
                if not all([formula, isinstance(variables, dict)]):
                    raise ValueError("'formula' and 'variables' are required fields.")

                numerical_result = solve_formula(formula, variables)
                rounded_result = round(numerical_result, 4)
                response_data.append({"result": rounded_result})
                logger.info(f"Successfully processed '{name}'. Result: {rounded_result}")

            except Exception as e:
                logger.error(f"Error processing case '{name}': {e}", exc_info=True)
                return jsonify({
                    "error": f"Failed to process case '{name}'",
                    "details": str(e)
                }), 400
        
        return jsonify(response_data)

    except BadRequest as e:
        # This specifically catches JSON decoding errors
        logger.error(f"Request body is not valid JSON. Details: {e.description}")
        return jsonify({"error": "Malformed JSON received.", "details": e.description}), 400
    except Exception as e:
        logger.critical(f"An unexpected internal server error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500


# Main execution block
if __name__ == '__main__':
    app.run(debug=True, port=5000)