# routes/operationsafeguard.py
import logging
import re
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

# ----------------------------
# Challenge 1: reverse transforms
# ----------------------------
VOWELS = set("aeiouAEIOU")

def mirror_words(s: str) -> str:
    # inverse == forward
    return " ".join(w[::-1] for w in s.split(" "))

def encode_mirror_alphabet(s: str) -> str:
    # Atbash; inverse == forward
    def m(c):
        if "a" <= c <= "z":
            return chr(ord("z") - (ord(c) - ord("a")))
        if "A" <= c <= "Z":
            return chr(ord("Z") - (ord(c) - ord("A")))
        return c
    return "".join(m(c) for c in s)

def toggle_case(s: str) -> str:
    # inverse == forward
    return "".join(c.lower() if c.isupper() else c.upper() if c.islower() else c for c in s)

def swap_pairs_word(w: str) -> str:
    # inverse == forward
    a = list(w)
    for i in range(0, len(a) - 1, 2):
        a[i], a[i+1] = a[i+1], a[i]
    return "".join(a)

def swap_pairs(s: str) -> str:
    return " ".join(swap_pairs_word(w) for w in s.split(" "))

def encode_index_parity_word(w: str) -> str:
    # forward: even indices then odd indices (0-based)
    return w[::2] + w[1::2]

def decode_index_parity_word(w: str) -> str:
    # inverse of encode_index_parity_word
    n = len(w)
    k = (n + 1) // 2  # number of evens
    evens, odds = w[:k], w[k:]
    out = []
    for i in range(n):
        out.append(evens[i//2] if i % 2 == 0 else odds[i//2])
    return "".join(out)

def encode_index_parity(s: str) -> str:
    return " ".join(encode_index_parity_word(w) for w in s.split(" "))

def decode_index_parity(s: str) -> str:
    return " ".join(decode_index_parity_word(w) for w in s.split(" "))

def double_consonants_encode(s: str) -> str:
    out = []
    for c in s:
        if c.isalpha() and c not in VOWELS:
            out.append(c + c)
        else:
            out.append(c)
    return "".join(out)

def double_consonants_decode(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isalpha() and c not in VOWELS and i + 1 < len(s) and s[i+1] == c:
            out.append(c)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)

# map forward transform name -> inverse function
INVERSE = {
    "mirror_words": mirror_words,
    "encode_mirror_alphabet": encode_mirror_alphabet,
    "toggle_case": toggle_case,
    "swap_pairs": swap_pairs,
    "encode_index_parity": decode_index_parity,
    "double_consonants": double_consonants_decode,
}

def _parse_transformation_names(tfs):
    """
    Accepts:
      - string: "[encode_mirror_alphabet(x), double_consonants(x), ...]"
      - list of names: ["encode_mirror_alphabet", "double_consonants", ...]
      - list with parens: ["encode_mirror_alphabet(x)", "double_consonants(x)"]
    Returns: list[str] of names
    """
    if isinstance(tfs, str):
        return re.findall(r'([a-zA-Z_]+)\s*\(x\)', tfs)
    if isinstance(tfs, list):
        names = []
        for item in tfs:
            if isinstance(item, str):
                m = re.match(r'^\s*([a-zA-Z_]+)\s*(?:\(\s*x\s*\))?\s*$', item)
                if m:
                    names.append(m.group(1))
        return names
    return []

def decode_challenge_one(transformed_word: str, transformations) -> str:
    names = _parse_transformation_names(transformations)
    s = transformed_word
    for name in reversed(names):  # reverse order
        inv = INVERSE.get(name)
        if not inv:
            logger.warning("Unknown transform: %s", name)
            continue
        s = inv(s)
    return s

# ----------------------------
# Challenge 2: coordinates → number (placeholder; returns size of filtered cluster)
# ----------------------------
def extract_number_from_coordinates(coords):
    """
    coords: list of [lat, lng] (strings or numbers)
    Strategy:
      - Parse to floats
      - Filter out far outliers via simple MAD rule
      - Return the count of the filtered set (deterministic integer)
    Replace with the real intended logic once you infer the pattern.
    """
    try:
        pts = []
        for a, b in coords:
            pts.append((float(a), float(b)))
        if not pts:
            return 0
        import statistics as st
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        mx, my = st.median(xs), st.median(ys)
        madx = st.median([abs(x - mx) for x in xs]) or 1.0
        mady = st.median([abs(y - my) for y in ys]) or 1.0
        filt = [(x, y) for (x, y) in pts if abs(x - mx)/madx <= 3 and abs(y - my)/mady <= 3]
        return len(filt)
    except Exception:
        return len(coords or [])

# ----------------------------
# Challenge 3: ciphers
# ----------------------------
def railfence3_decrypt(ct: str) -> str:
    n = len(ct)
    # rail index pattern 0..1..2..1..0..
    rail_idx = []
    r, dr = 0, 1
    for _ in range(n):
        rail_idx.append(r)
        if r == 0: dr = 1
        elif r == 2: dr = -1
        r += dr
    # count per rail
    counts = [rail_idx.count(i) for i in (0,1,2)]
    rails, p = [], 0
    for c in counts:
        rails.append(list(ct[p:p+c])); p += c
    pos = [0,0,0]
    out = []
    for r in rail_idx:
        out.append(rails[r][pos[r]])
        pos[r] += 1
    return "".join(out)

def keyword_substitution_decode_map(keyword: str):
    kw = []
    seen = set()
    for c in keyword.upper():
        if c.isalpha() and c not in seen:
            seen.add(c); kw.append(c)
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if c not in seen:
            seen.add(c); kw.append(c)
    enc = "".join(kw)  # cipher alphabet
    plain = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return {enc[i]: plain[i] for i in range(26)}

def keyword_decrypt(ct: str, keyword: str = "SHADOW") -> str:
    dec = keyword_substitution_decode_map(keyword)
    out = []
    for c in ct.upper():
        if c.isalpha():
            out.append(dec.get(c, c))
        else:
            out.append(c)
    return "".join(out)

def polybius_decrypt(ct: str) -> str:
    square = [
        "A","B","C","D","E",
        "F","G","H","I","K",
        "L","M","N","O","P",
        "Q","R","S","T","U",
        "V","W","X","Y","Z"
    ]
    digits = re.findall(r'\d{2}', ct)
    if not digits:
        return ct.replace("J","I").replace("j","i")
    out = []
    for d in digits:
        r = int(d[0]) - 1
        c = int(d[1]) - 1
        out.append(square[r*5 + c])
    return "".join(out)

def rot13(s: str) -> str:
    def tr(c):
        if 'a' <= c <= 'z': return chr((ord(c)-97+13)%26 + 97)
        if 'A' <= c <= 'Z': return chr((ord(c)-65+13)%26 + 65)
        return c
    return "".join(tr(c) for c in s)

def parse_log_entry(entry: str):
    fields = {}
    for part in entry.split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            fields[k.strip().upper()] = v.strip()
    return fields

def decode_challenge_three(entry: str) -> str:
    f = parse_log_entry(entry)
    ctype = (f.get("CIPHER_TYPE", "")).upper().replace(" ", "_")
    payload = f.get("ENCRYPTED_PAYLOAD", "")
    if ctype == "RAILFENCE":
        return railfence3_decrypt(payload)
    elif ctype == "KEYWORD":
        return keyword_decrypt(payload, "SHADOW")
    elif ctype == "POLYBIUS":
        return polybius_decrypt(payload)
    elif ctype in ("ROTATION_CIPHER", "ROT13", "CAESAR_13"):
        return rot13(payload)  # e.g., SVERJNYY -> FIREWALL
    else:
        return payload

# ----------------------------
# Challenge 4: Final synthesis (adjust to spec when known)
# ----------------------------
def final_synthesis(c1: str, c2: str, c3: str) -> str:
    # placeholder joiner; tweak once you know the exact rule
    return f"{c1}|{c2}|{c3}"

# ----------------------------
# Endpoint
# ----------------------------
@app.route("/operation-safeguard", methods=["POST"])
def operation_safeguard():
    data = request.get_json(force=True, silent=False)

    # Challenge 1
    c1_in = data.get("challenge_one", {}) or {}
    tfs = c1_in.get("transformations")
    transformed = c1_in.get("transformed_encrypted_word", "") or ""
    try:
        c1 = decode_challenge_one(transformed, tfs) if transformed else ""
    except Exception:
        logger.exception("Challenge 1 decode failed")
        c1 = ""

    # Challenge 2
    coords = data.get("challenge_two", []) or []
    try:
        c2 = extract_number_from_coordinates(coords)
    except Exception:
        logger.exception("Challenge 2 analysis failed")
        c2 = 0

    # Challenge 3
    entry = data.get("challenge_three", "") or ""
    try:
        c3 = decode_challenge_three(entry) if entry else ""
    except Exception:
        logger.exception("Challenge 3 decrypt failed")
        c3 = ""

    # Challenge 4
    c4 = final_synthesis(str(c1), str(c2), str(c3))

    # Grader requires strings for all values
    return jsonify({
        "challenge_one":   "" if c1 is None else str(c1),
        "challenge_two":   "" if c2 is None else str(c2),
        "challenge_three": "" if c3 is None else str(c3),
        "challenge_four":  "" if c4 is None else str(c4),
    })
