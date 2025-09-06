# routes/trading_formula.py
import re
import math
import logging
from decimal import Decimal, ROUND_HALF_UP
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

# ---------- formatting ----------
def _fmt4(x: float) -> str:
    return f"{Decimal(str(x)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}"

# ---------- LaTeX normalization ----------
def _strip_dollars_and_eq(s: str) -> str:
    s = s.strip().replace("$$", "").replace("$", "")
    if "=" in s:
        s = s.split("=", 1)[1]  # keep RHS only
    return s.strip()

def _strip_left_right(s: str) -> str:
    return s.replace(r"\left", "").replace(r"\right", "")

def _untex_text_macro(s: str) -> str:
    # \text{Trade Amount} -> Trade_Amount
    return re.sub(r"\\text\{([^}]*)\}", lambda m: re.sub(r"\s+", "_", m.group(1).strip()), s)

def _normalize_brackets_and_greek(s: str) -> str:
    # E[R_m] -> E_R_m ; Fee[USD] -> Fee_USD
    s = re.sub(r"([A-Za-z0-9]+)\[([A-Za-z0-9_]+)\]", r"\1_\2", s)
    # Z_{\alpha} -> Z_alpha ; Z_\alpha -> Z_alpha
    s = re.sub(r"_\{\\([A-Za-z]+)\}", r"_\1", s)
    s = re.sub(r"_\\([A-Za-z]+)", r"_\1", s)
    return s

# Greek token replacement in formulas (handles lower+upper)
_GREEK = [
    "alpha","beta","gamma","delta","epsilon","zeta","eta","theta","iota","kappa","lambda",
    "mu","nu","xi","omicron","pi","rho","sigma","tau","upsilon","phi","chi","psi","omega",
    "Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta","Iota","Kappa","Lambda",
    "Mu","Nu","Xi","Omicron","Pi","Rho","Sigma","Tau","Upsilon","Phi","Chi","Psi","Omega",
]
_GREEK_RE = re.compile(r"\\(" + "|".join(_GREEK) + r")\b")
def _replace_greek_in_formula(s: str) -> str:
    return _GREEK_RE.sub(lambda m: m.group(1), s)

def _replace_frac(expr: str) -> str:
    # Replace \frac{a}{b} -> ((a)/(b)), including nested cases
    pattern = re.compile(r"\\frac\s*\{([^{}]|{[^{}]*})+\}\s*\{([^{}]|{[^{}]*})+\}")
    while True:
        m = pattern.search(expr)
        if not m:
            break
        parts = re.findall(r"\{([^{}]*|[^{}]*\{[^{}]*\}[^{}]*)\}", m.group(0))
        if len(parts) >= 2:
            a, b = parts[0], parts[1]
            expr = expr[:m.start()] + f"(({a})/({b}))" + expr[m.end():]
        else:
            break
    return expr

def _replace_mul(expr: str) -> str:
    return expr.replace(r"\cdot", "*").replace(r"\times", "*")

def _replace_pow(expr: str) -> str:
    # a^{b} -> a**(b); a^b -> a**(b)
    expr = re.sub(r"\^\{([^}]*)\}", r"**(\1)", expr)
    expr = re.sub(r"\^([A-Za-z0-9_\.]+)", r"**(\1)", expr)
    return expr

def _replace_e_power(expr: str) -> str:
    # e^{x} / e^x -> exp(x)
    expr = re.sub(r"\be\^\{([^}]*)\}", r"exp(\1)", expr)
    expr = re.sub(r"\be\^([A-Za-z0-9_\.]+)", r"exp(\1)", expr)
    return expr

def _replace_max_min(expr: str) -> str:
    # \max{a,b} / \max(a,b) -> max(a,b); \min -> min
    expr = re.sub(r"\\max\s*\{", "max(", expr)
    expr = re.sub(r"\\max\s*\(", "max(", expr)
    expr = re.sub(r"\\min\s*\{", "min(", expr)
    expr = re.sub(r"\\min\s*\(", "min(", expr)
    return expr.replace("}", ")")

def _replace_logs(expr: str) -> str:
    expr = re.sub(r"\\log\s*\(", "log(", expr)
    expr = re.sub(r"\\ln\s*\(", "log(", expr)
    return expr

def _insert_implicit_multiplication(expr: str) -> str:
    """
    Insert * between a variable/number and following '(' when it's not a function call.
    E.g., 'beta_i (E_R_m - R_f)' -> 'beta_i*(E_R_m - R_f)'
    """
    pattern = re.compile(r'\b(?!(?:max|min|log|exp|sum|pow)\b)([A-Za-z_][A-Za-z0-9_]*|\d(?:\.\d+)?)\s*\(')
    return pattern.sub(lambda m: f"{m.group(1)}*(", expr)

def latex_to_python(formula_rhs: str) -> str:
    s = _strip_left_right(formula_rhs)
    s = _untex_text_macro(s)
    s = _normalize_brackets_and_greek(s)   # E[R_m] -> E_R_m, Z_\alpha -> Z_alpha
    s = _replace_frac(s)
    s = _replace_e_power(s)
    s = _replace_pow(s)
    s = _replace_mul(s)
    s = _replace_max_min(s)
    s = _replace_logs(s)
    s = _replace_greek_in_formula(s)       # \sigma -> sigma, etc.
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s) # remove any stray backslashes
    s = _insert_implicit_multiplication(s)
    s = s.replace("{", "(").replace("}", ")")
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ---------- variables normalization ----------
def normalize_var_name(name: str) -> str:
    n = str(name)
    n = _untex_text_macro(n)
    n = _normalize_brackets_and_greek(n)
    return n

def normalize_variables(vars_in: dict) -> dict:
    out = {}
    for k, v in vars_in.items():
        val = float(v)
        out[str(k)] = val                     # original
        out.setdefault(normalize_var_name(k), val)  # normalized alias
    return out

# ---------- safe eval ----------
ALLOWED = {
    "max": max, "min": min,
    "log": math.log, "exp": math.exp,
    "pow": pow, "sum": sum,
}

def evaluate_expr(py_expr: str, variables: dict) -> float:
    safe_env = dict(ALLOWED)
    # add variables but NEVER overwrite function names
    for k, v in normalize_variables(variables).items():
        if k in ALLOWED:
            continue
        safe_env[k] = v
    return float(eval(py_expr, {"__builtins__": {}}, safe_env))

def compute_one(formula: str, variables: dict) -> float:
    rhs = _strip_dollars_and_eq(formula)
    py_expr = latex_to_python(rhs)
    return evaluate_expr(py_expr, variables)

# ---------- Flask route ----------
@app.route("/trading-formula", methods=["POST"])
def trading_formula():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected JSON array"}), 400

    results = []
    for i, tc in enumerate(data):
        try:
            val = compute_one(tc.get("formula", ""), tc.get("variables", {}) or {})
            results.append({"result": _fmt4(val)})  # string with exactly 4 dp
        except Exception:
            logger.exception("TradingFormula error on test %d", i)
            results.append({"result": _fmt4(0.0)})
    return jsonify(results)
