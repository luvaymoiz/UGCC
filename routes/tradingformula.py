from flask import Flask, request, jsonify
import ast
import math
import re
import logging
from routes import app

logger = logging.getLogger(__name__)



# ---------- Helpers to sanitize & transform LaTeX-ish input ----------

GREEK = {
    "alpha","beta","gamma","delta","epsilon","zeta","eta","theta","iota","kappa",
    "lambda","mu","nu","xi","omicron","pi","rho","sigma","tau","upsilon",
    "phi","chi","psi","omega"
}


def strip_math_delims(s: str) -> str:
    s = s.strip()
    # remove $$...$$ or $...$
    if (s.startswith("$$") and s.endswith("$$")) or (s.startswith("$") and s.endswith("$")):
        s = s.strip("$")
    return s

def rhs_of_assignment(s: str) -> str:
    # allow "Fee = ..." or "SR = ..." → take right hand side
    if "=" in s:
        return s.split("=", 1)[1]
    return s

def replace_text_command(s: str) -> str:
    # \text{TradeAmount} → TradeAmount
    return re.sub(r"\\text\{([^}]+)\}", lambda m: m.group(1).replace(" ", ""), s)

def normalize_subscripts(s: str) -> str:
    # Z_\alpha -> Z_alpha ; sigma_p -> sigma_p ; X_{long} -> X_long
    s = re.sub(r"_\{([A-Za-z][A-Za-z0-9_]*)\}", r"_\1", s)   # _{p} -> _p
    s = re.sub(r"_\\([A-Za-z]+)", lambda m: "_" + m.group(1), s)  # _\alpha -> _alpha
    s = re.sub(r"\\([a-z]+)_", lambda m: (m.group(1) if m.group(1) in GREEK else "\\"+m.group(1)) + "_", s)
    # \sigma_p (var name) -> sigma_p (drop backslash when it's a symbol name)
    s = re.sub(r"\\([a-z]+)", lambda m: m.group(1) if m.group(1) in GREEK else "\\" + m.group(1), s)
    return s

def bracket_to_underscore(s: str) -> str:
    # E[R_p] -> E_R_p ; X[i] -> X_i
    return re.sub(r"([A-Za-z]+)\[([^\]]+)\]", r"\1_\2", s)

def replace_operators(s: str) -> str:
    # \cdot, \times -> *
    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    # \left( ... \right) -> ( ... )
    s = s.replace(r"\left", "").replace(r"\right", "")
    return s

def replace_frac(s: str) -> str:
    # Replace \frac{A}{B} with (A)/(B) using a stack to match nested braces
    def repl_frac(match):
        start = match.start()
        # we are at '\frac{'
        i = match.end()  # position after '\frac{'
        # find A
        a, i = read_braced(s, i-1)   # i-1 is at '{'
        # i now at char after A's closing brace, expect '/'
        if i >= len(s) or s[i] != '/':
            return s[match.start():i]
        i += 1  # skip '/'
        # next should be '{'
        b, j = read_braced(s, i)
        return f"(({a})/({b}))", match.start(), j

    def read_braced(text, pos_open_brace):
        # pos_open_brace points at '{'
        assert text[pos_open_brace] == '{'
        depth = 0
        i = pos_open_brace
        i += 1
        start = i
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                if depth == 0:
                    return text[start:i], i+1
                depth -= 1
            i += 1
        raise ValueError("Unbalanced braces in \\frac")

    # iterate and replace all \frac occurrences
    i = 0
    out = []
    while i < len(s):
        m = re.search(r"\\frac\{", s[i:])
        if not m:
            out.append(s[i:])
            break
        m_start = i + m.start()
        out.append(s[i:m_start])
        # perform replacement from m_start
        content, start, new_i = repl_frac(re.match(r"\\frac\{", s[m_start:]).re.match, )  # dummy to please linter
        # easier: call our own using string slice
        # Recompute using local slice
        local = s[m_start:]
        # read A and B using helpers
        a, idx = read_braced(local, local.find('{'))  # after \frac
        if local[idx] != '/':
            raise ValueError("Malformed \\frac")
        b, idx2 = read_braced(local, idx+1)
        out.append(f"(({a})/({b}))")
        i = m_start + idx2
    return "".join(out)

def frac_pass(s: str) -> str:
    # simpler robust pass: repeatedly replace first \frac{...}{...} using regex that matches balanced braces shallowly
    # This approximate works for your given tests.
    pattern = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
    while True:
        new_s, n = pattern.subn(r"((\1)/(\2))", s)
        if n == 0:
            return s
        s = new_s

def replace_pow_and_exp(s: str) -> str:
    # ^ -> **  (both ^{...} and ^x)
    s = re.sub(r"\^\{([^}]+)\}", r"**(\1)", s)
    s = re.sub(r"\^([A-Za-z0-9_\.]+)", r"**(\1)", s)
    # e**(something) -> math.exp(something)
    s = re.sub(r"\be\*\*\(([^)]+)\)", r"math.exp(\1)", s)
    return s

def replace_funcs(s: str) -> str:
    # \max(,) and \min(,) -> max/min
    s = s.replace(r"\max", "max").replace(r"\min", "min")
    # log(x) -> math.log(x)  (both \log and log)
    s = s.replace(r"\log", "log")
    s = re.sub(r"\blog\s*\(", "math.log(", s)
    return s

def latex_to_python(expr: str) -> str:
    expr = strip_math_delims(expr)
    expr = rhs_of_assignment(expr)
    expr = replace_text_command(expr)
    expr = replace_operators(expr)
    expr = normalize_subscripts(expr)
    expr = bracket_to_underscore(expr)
    expr = frac_pass(expr)
    expr = replace_pow_and_exp(expr)
    expr = replace_funcs(expr)
    # remove stray braces that sometimes remain around groups
    expr = expr.replace("{", "(").replace("}", ")")
    return expr.strip()

# ---------- Safe evaluator using ast ----------

ALLOWED_NAMES = {
    "math": math,
    "max": max,
    "min": min,
}

ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
    ast.Call, ast.Name, ast.Attribute, ast.Tuple
}

def safe_eval(expr: str, variables: dict) -> float:
    # build a safe environment: variables + allowed names
    env = {**ALLOWED_NAMES}
    # expose variables as plain names
    env.update(variables)

    node = ast.parse(expr, mode="eval")

    def _check(n):
        if type(n) not in ALLOWED_NODES:
            raise ValueError(f"Disallowed expression: {type(n).__name__}")
        for child in ast.iter_child_nodes(n):
            _check(child)
    _check(node)

    return float(eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, env))

# ---------- API ----------

def normalize_vars(vars_in: dict) -> dict:
    """Accepts keys like Z_alpha, sigma_p, E_R_p (your JSON) and exposes them
    to the evaluator exactly with those names."""
    norm = {}
    for k, v in vars_in.items():
        norm[k] = float(v)
        # also expose versions that might appear after transformations:
        # e.g., if someone wrote Z_\alpha and it became Z_alpha, we already have that
    return norm

def evaluate_case(case: dict) -> dict:
    formula = case.get("formula", "")
    variables = case.get("variables", {})
    if not isinstance(variables, dict):
        raise ValueError("`variables` must be an object/dict")
    expr = latex_to_python(formula)
    val = safe_eval(expr, normalize_vars(variables))
    return {"result": round(val, 4)}

@app.route("/trading-formula", methods=["POST"])
def trading_formula():
    data = request.get_json(force=True)
    try:
        if isinstance(data, list):
            return jsonify([evaluate_case(c) for c in data])
        elif isinstance(data, dict):
            return jsonify(evaluate_case(data))
        else:
            return jsonify({"error": "JSON must be an object or an array"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

