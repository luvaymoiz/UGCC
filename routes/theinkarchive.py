import math
from flask import request, jsonify
from routes import app

def build_graph(goods, ratios):
    n = len(goods)
    # adjacency as edge list; also map (u,v)->rate for product
    edges = []
    rate_map = {}
    for u, v, r in ratios:
        u = int(u); v = int(v)
        r = float(r)
        if r <= 0.0:
            continue
        edges.append((u, v, -math.log(r)))  # weight = -ln(rate)
        rate_map[(u, v)] = r
    return n, edges, rate_map

def extract_cycle(start_v, pred, n):
    x = start_v
    for _ in range(n):  # move into the cycle
        x = pred[x]
    # collect cycle by walking until we repeat x
    cycle = [x]
    cur = pred[x]
    while cur != x and cur != -1 and len(cycle) <= n+1:
        cycle.append(cur)
        cur = pred[cur]
    cycle.reverse()  # order along edges (cycle[0] -> cycle[1] -> ...)
    return cycle

def rotate_cycle_canonical(cycle, goods, rate_map):
    """
    Rotate cycle so it starts at the node with the largest incoming edge rate.
    Ties broken by lexicographically smallest good name.
    cycle: [n0, n1, ..., nk-1] describing edges ni -> n(i+1 mod k)
    """
    k = len(cycle)
    if k == 0:
        return cycle[:]
    # compute incoming rate to each node
    scored = []
    for i in range(k):
        cur = cycle[i]
        prev = cycle[(i - 1) % k]
        r = rate_map.get((prev, cur), 0.0)
        scored.append((r, goods[cur], i))  # (incoming rate, name, index)
    # pick the node with max incoming rate; tie-break by name
    rmax, _, imax = max(scored, key=lambda t: (t[0], -ord(t[1][0]) if t[1] else 0, t[1]))
    # rotate
    rotated = cycle[imax:] + cycle[:imax]
    return rotated


def cycle_gain(cycle, rate_map):
    prod = 1.0
    for i in range(len(cycle)):
        a = cycle[i]
        b = cycle[(i + 1) % len(cycle)]
        r = rate_map.get((a, b))
        if r is None:
            return 1.0, False
        prod *= r
    return prod, True

def best_arbitrage(goods, ratios):
    n, edges, rate_map = build_graph(goods, ratios)
    if n == 0:
        return [], 0.0

    best_prod = 1.0
    best_cycle = None

    for src in range(n):
        dist = [0.0] * n
        pred = [-1] * n

        # Relax edges n-1 times
        for _ in range(n - 1):
            changed = False
            for u, v, w in edges:
                if dist[u] + w < dist[v] - 1e-18:
                    dist[v] = dist[u] + w
                    pred[v] = u
                    changed = True
            if not changed:
                break

        # Detect any negative cycle reachable from src
        changed_vertex = -1
        for u, v, w in edges:
            if dist[u] + w < dist[v] - 1e-18:
                pred[v] = u
                changed_vertex = v
                break

        if changed_vertex == -1:
            continue  # no cycle from this src

        cycle_nodes = extract_cycle(changed_vertex, pred, n)
        if len(cycle_nodes) >= 2:
            prod, ok = cycle_gain(cycle_nodes, rate_map)
            if ok and prod > best_prod + 1e-15:
                best_prod = prod
                best_cycle = cycle_nodes

    if not best_cycle:
        return [], 0.0

    
    best_cycle = rotate_cycle_canonical(best_cycle, goods, rate_map)

    names = [goods[i] for i in best_cycle]
    names.append(names[0])  
    gain_pct = (best_prod - 1.0) * 100.0
    return names, gain_pct


@app.route("/The-Ink-Archive", methods=["POST"])
def the_ink_archive():
    data = request.get_json(silent=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Expected a JSON array of challenge items"}), 400

    results = []
    for idx, item in enumerate(data):
        goods = item.get("goods", [])
        ratios = item.get("ratios", [])
        if not isinstance(goods, list) or not isinstance(ratios, list):
            return jsonify({"error": f"Item {idx}: invalid 'goods' or 'ratios'"}), 400
        path, gain = best_arbitrage(goods, ratios)
        results.append({"path": path, "gain": gain})

    return jsonify(results)
