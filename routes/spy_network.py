import json
import logging
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

@app.route("/investigate", methods=["POST"])
def investigate():
    try:
        payload = request.get_json(force=True, silent=False)

        # Accept both shapes:
        # 1) {"networks": [...]}  (spec)
        # 2) [...]                (top-level list, observed in logs)
        if isinstance(payload, dict):
            networks = payload.get("networks", [])
            if not isinstance(networks, list):
                return jsonify({"error": "'networks' must be a list"}), 400
        elif isinstance(payload, list):
            networks = payload
        else:
            return jsonify({"error": "JSON must be an object with 'networks' or a list"}), 400

        results = []

        for item in networks:
            if not isinstance(item, dict):
                return jsonify({"error": "each network must be an object"}), 400

            net_id = item.get("networkId")
            edges = item.get("network", [])
            if net_id is None or not isinstance(edges, list):
                return jsonify({"error": "network requires 'networkId' and 'network' list"}), 400

            # Map spy names to ids
            idx = {}
            def gid(name):
                if name not in idx:
                    idx[name] = len(idx)
                return idx[name]

            u, v = [], []
            for e in edges:
                if not isinstance(e, dict) or "spy1" not in e or "spy2" not in e:
                    return jsonify({"error": "edge must have spy1 and spy2"}), 400
                u.append(gid(e["spy1"]))
                v.append(gid(e["spy2"]))

            n = len(idx)
            adj = [[] for _ in range(n)]
            for i, (a, b) in enumerate(zip(u, v)):
                adj[a].append((b, i))
                adj[b].append((a, i))

            # Tarjan bridges
            disc = [-1]*n
            low  = [0]*n
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

            extra = []
            for i, e in enumerate(edges):
                if i not in bridges:
                    extra.append({"spy1": e["spy1"], "spy2": e["spy2"]})

            results.append({"networkId": net_id, "extraChannels": extra})

        return jsonify({"networks": results})

    except Exception:
        logger.exception("Error in /investigate")
        return jsonify({"error": "internal error"}), 500
