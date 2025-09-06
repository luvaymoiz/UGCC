import json
import logging
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/investigate", methods=["POST"])
def investigate():
    payload = request.get_json()
    networks = payload.get("networks", [])
    results = []

    for item in networks:
        net_id = item["networkId"]
        edges = item.get("network", [])

        # Map spy names to integer ids
        idx = {}
        def get_id(name):
            if name not in idx:
                idx[name] = len(idx)
            return idx[name]

        # Build adjacency (undirected) with edge indices
        n_edges = len(edges)
        u = [0]*n_edges
        v = [0]*n_edges
        for i, e in enumerate(edges):
            u[i] = get_id(e["spy1"])
            v[i] = get_id(e["spy2"])

        n = len(idx)
        adj = [[] for _ in range(n)]
        for i in range(n_edges):
            a, b = u[i], v[i]
            adj[a].append((b, i))
            adj[b].append((a, i))

        # Tarjan to find bridges
        disc = [-1]*n
        low = [0]*n
        time = 0
        bridges = set()

        def dfs(x, pe):
            nonlocal time
            disc[x] = low[x] = time
            time += 1
            for y, ei in adj[x]:
                if ei == pe:
                    continue
                if disc[y] == -1:
                    dfs(y, ei)
                    low[x] = min(low[x], low[y])
                    if low[y] > disc[x]:
                        bridges.add(ei)
                else:
                    low[x] = min(low[x], disc[y])

        for s in range(n):
            if disc[s] == -1:
                dfs(s, -1)

        # Non-bridges are extra channels (they lie on cycles)
        extra = []
        for i, e in enumerate(edges):
            if i not in bridges:
                extra.append({"spy1": e["spy1"], "spy2": e["spy2"]})

        results.append({"networkId": net_id, "extraChannels": extra})

    return jsonify({"networks": results})
