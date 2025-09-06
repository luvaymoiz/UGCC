from routes import app
import json
import logging
from flask import request, jsonify
from routes import app
import sympy
import re

logger = logging.getLogger(__name__)

def preprocess_formula(formula_str: str) -> str:
    """
    Cleans and standardizes the LaTeX formula string for parsing.

    This function isolates the mathematical expression, removes LaTeX text formatting,
    and maps special LaTeX variable notations to plain text equivalents.
    """
    # 1. Isolate the expression on the right-hand side of the equation.
    if '=' in formula_str:
        formula_str = formula_str.split('=', 1)[1]

    # 2. Remove LaTeX math mode delimiters.
    formula_str = formula_str.replace('$$', '').strip()

    # 3. Replace '\\text{...}' with its content.
    formula_str = re.sub(r'\\text\{([^}]+)\}', r'\1', formula_str)

    # 4. Standardize multiplication and exponentiation operators.
    formula_str = formula_str.replace('\\times', '*')
    formula_str = formula_str.replace('\\cdot', '*')
    formula_str = formula_str.replace('^', '**')

    # 5. Map special LaTeX notations for variables to a consistent text format.
    #    This ensures variable names in the formula match the keys in the JSON input.
    replacements = {
        "E[R_m]": "E_R_m",
        "E[R_p]": "E_R_p",
        "E[R_i]": "E_R_i",
        "\\beta_i": "beta_i",
        "Z_\\alpha": "Z_alpha",
        "\\sigma_p": "sigma_p"
    }
    for latex, text in replacements.items():
        formula_str = formula_str.replace(latex, text)

    # Note: Standard LaTeX functions like \\frac, \\max, \\log are natively
    # handled by sympy's parser and do not need to be replaced.
    return formula_str

@app.route("/trading-formula", methods=["POST"])
def evaluate_formulas():
    """
    Flask endpoint to evaluate a list of financial formulas.

    Accepts a JSON array of test cases and returns a JSON array of results.
    """
    try:
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, list):
            return jsonify({"error": "Request body must be a JSON array of test cases"}), 400

        response_results = []
        for test_case in data:
            formula = test_case.get("formula")
            variables = test_case.get("variables")

            if not all([formula, isinstance(variables, dict)]):
                response_results.append({"name": test_case.get("name"), "error": "Invalid test case format"})
                continue
            
            # Step 1: Preprocess the LaTeX formula.
            processed_formula_str = preprocess_formula(formula)

            # Step 2: Parse the string into a symbolic expression using sympy.
            # We provide a dictionary of symbols to ensure variables are correctly identified.
            symbols = {k: sympy.Symbol(k) for k in variables.keys()}
            parsed_expression = sympy.parsing.latex.parse_latex(processed_formula_str, local_dict=symbols)

            # Step 3: Substitute the numerical values for the symbols.
            substituted_expression = parsed_expression.subs(variables)

            # Step 4: Evaluate the final expression to a floating-point number.
            numerical_result = float(substituted_expression.evalf())

            # Step 5: Round the result to four decimal places as required.
            final_result = round(numerical_result, 4)

            response_results.append({"result": final_result})

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500
    
    return jsonify(response_results)