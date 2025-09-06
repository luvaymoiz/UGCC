import sys
import logging
from flask import Flask, request, jsonify
import json
import app
import sympy as sp


logger = logging.getLogger(__name__)

@app.route('/trading-formula', methods=['POST'])

def trading_formula():
    # Get JSON data from the request
    data = request.get_json()
    
    # Extract formula and variables from the data
    formula = data.get('formula')
    variables = data.get('variables')
    
    # Parse the formula (LaTeX format) and substitute variables
    try:
        # Create symbolic variables for each one
        sym_vars = {key: sp.symbols(key) for key in variables.keys()}
        
        # Convert LaTeX formula to a sympy expression
        expr = sp.sympify(formula, locals=sym_vars)
        
        # Substitute values from the variables and evaluate
        substituted_expr = expr.subs(variables)
        result = float(substituted_expr.evalf())
        
        # Return the result in the expected format
        return jsonify({'result': round(result, 4)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)