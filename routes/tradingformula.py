import sys
from flask import Flask, request, jsonify
import ast
import math
import re
import logging
from routes import app

logger = logging.getLogger(__name__)

# --- 1. LaTeX to Python Translation ---
LATEX_REPLACEMENTS = {
    "=": "",
    "$$": "",
    "$": "",
    "\\text": "",
    "\\{": "(",
    "\\}": ")",
    "{": "(",
    "}": ")",
    "\\left(": "(",
    "\\right)": ")",
    "\\times": "*",
    "\\cdot": "*",
    "\\frac": "",  # Handled by regex
    "e^": "math.exp",
    "^": "**",
    "\\log": "math.log",
    "\\max": "max",
    "\\min": "min",
    "\\sum": "sum",
    "\\alpha": "alpha", "\\beta": "beta", "\\gamma": "gamma", "\\delta": "delta",
    "\\epsilon": "epsilon", "\\zeta": "zeta", "\\eta": "eta", "\\theta": "theta",
    "\\iota": "iota", "\\kappa": "kappa", "\\lambda": "lambda", "\\mu": "mu",
    "\\nu": "nu", "\\xi": "xi", "\\omicron": "omicron", "\\pi": "pi",
    "\\rho": "rho", "\\sigma": "sigma", "\\tau": "tau", "\\upsilon": "upsilon",
    "\\phi": "phi", "\\chi": "chi", "\\psi": "psi", "\\omega": "omega"
}

def latex_to_python_safe(expr: str) -> str:
    """
    A robust function to translate LaTeX to a Python expression.
    """
    # Use re.sub to handle fractions like \frac{num}{den} -> (num)/(den)
    expr = re.sub(r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}', r'(\1)/(\2)', expr)
    
    # Use re.sub for cleaner variable name replacement
    expr = re.sub(r'\\([A-Za-z]+)', r'\1', expr)  # Replace Greek letters
    expr = re.sub(r'([A-Za-z0-9_]+)\[([^\]]+)\]', r'\1_\2', expr) # E[R_p] -> E_R_p
    
    # Apply all other simple string replacements
    for latex, python in LATEX_REPLACEMENTS.items():
        expr = expr.replace(latex, python)
        
    return expr.strip()

# --- 2. Safe Expression Evaluation ---
ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
    ast.Call, ast.Name, ast.Attribute, ast.Tuple, ast.Compare, ast.BoolOp, ast.And, ast.Or,
    ast.Gt, ast.Lt, ast.Eq, ast.NotEq, ast.GtE, ast.LtE
}

ALLOWED_NAMES = {
    "math": math,
    "max": max,
    "min": min,
    "sum": sum,
    "abs": abs,
}

def _check_ast_nodes(node):
    if type(node) not in ALLOWED_NODES:
        raise ValueError(f"Disallowed expression syntax: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _check_ast_nodes(child)

def safe_eval(expr: str, variables: dict) -> float:
    """
    Safely evaluates a Python expression string using an AST whitelist.
    """
    if not expr.strip():
        raise ValueError("Expression is empty.")

    # The evaluation environment, including allowed functions and variables
    env = {**ALLOWED_NAMES, **variables}
    
    # Parse the expression into an AST
    node = ast.parse(expr, mode="eval")

    # Check the AST against the whitelist
    _check_ast_nodes(node)
    
    # If checks pass, compile and evaluate the expression in the safe environment
    return float(eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, env))

# --- 3. API Endpoint ---
@app.route("/trading-formula", methods=["POST"])
def trading_formula_endpoint():
    try:
        test_cases = request.get_json()
        if not isinstance(test_cases, list):
            return jsonify({"error": "Input must be a JSON array"}), 400

        results = []
        for case in test_cases:
            try:
                formula = case.get("formula", "")
                variables = {k: float(v) for k, v in case.get("variables", {}).items()}
                
                logger.info(f"Processing formula: {formula} with variables: {variables}")

                # Translate and evaluate
                python_expr = latex_to_python_safe(formula)
                value = safe_eval(python_expr, variables)
                
                # Format and append result
                results.append({"result": f"{value:.4f}"})

            except Exception as e:
                logger.error(f"Error evaluating case: {e}. Original formula: '{case.get('formula')}'")
                results.append({"result": f"Error: {e}"})

        return jsonify(results)

    except Exception as e:
        logger.error(f"A server error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# --- 4. Main execution block for local testing ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)