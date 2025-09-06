"""""
from routes import app
from routes import app
import json
import logging
from flask import request, jsonify
import re
from py_expression_eval import Parser
import math

logger = logging.getLogger(__name__)

def preprocess_formula(formula_str: str) -> str:
    
    # 1. Isolate the expression on the right-hand side of the equation.
    if '=' in formula_str:
        formula_str = formula_str.split('=', 1)[1]

    # 2. Remove LaTeX math mode delimiters.
    formula_str = formula_str.replace('$$', '').strip()

    # 3. Handle complex LaTeX structures first.
    # a. Fractional division: \frac{A}{B} becomes (A)/(B)
    formula_str = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', formula_str)
    
    # b. Maximum function: \max(...) becomes max(...)
    formula_str = re.sub(r'\\max\(([^)]+)\)', r'max(\1)', formula_str)
    
    # c. Minimum function: min(...) becomes min(...)
    formula_str = re.sub(r'min\(([^)]+)\)', r'min(\1)', formula_str)
    
    # d. Logarithm: log(...) becomes log(...)
    formula_str = re.sub(r'\\log\(([^)]+)\)', r'log(\1)', formula_str)
    
    # e. Exponential: e^x becomes exp(x)
    formula_str = re.sub(r'e\^\{?([^}]+)\}?', r'exp(\1)', formula_str)
    
    # 4. Replace simple LaTeX commands and notations.
    # a. Variable name replacements
    replacements = {
        "E [R_m]": "E_R_m",
        "E [R_p]": "E_R_p",
        "E [R_i]": "E_R_i",
        "\\beta_i": "beta_i",
        "Z_\\alpha": "Z_alpha",
        "\\sigma_p": "sigma_p"
    }
    for latex, text in replacements.items():
        formula_str = formula_str.replace(latex, text)

    # b. Operator replacements
    formula_str = formula_str.replace('\\times', '*')
    formula_str = formula_str.replace('\\cdot', '*')
    
    # c. Remove `\text{...}`
    formula_str = re.sub(r'\\text\{([^}]+)\}', r'\1', formula_str)
    
    return formula_str.strip()

@app.route("/trading-formula", methods=["POST"])
def evaluate_formulas():
    
    try:
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, list):
            return jsonify({"error": "Request body must be a JSON array of test cases"}), 400

        response_results = []
        parser = Parser()

        for test_case in data:
            formula = test_case.get("formula")
            variables = test_case.get("variables")

            if not all([formula, isinstance(variables, dict)]):
                response_results.append({"name": test_case.get("name"), "error": "Invalid test case format"})
                continue
            
            # Step 1: Preprocess the LaTeX formula.
            processed_formula_str = preprocess_formula(formula)

            try:
                # Step 2: Parse and evaluate the string expression.
                parsed_expression = parser.parse(processed_formula_str)
                numerical_result = parsed_expression.evaluate(variables)

                # Step 3: Round the result to four decimal places.
                final_result = round(numerical_result, 4)

                response_results.append({"result": final_result})

            except Exception as e:
                logger.error(f"Error evaluating formula '{formula}': {e}", exc_info=True)
                response_results.append({"name": test_case.get("name"), "error": f"Evaluation failed: {str(e)}"})
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500
    
    return jsonify(response_results)
"""