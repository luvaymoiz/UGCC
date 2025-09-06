# routes/princess_diaries.py
import logging
from heapq import heappush, heappop
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def build_graph(edges, id_of):
    g = {i: [] for i in id_of.values()}
    for e in edges:
        u, v = id_of[e["connection"][0]], id_of[e["connection"][1]]
        w = e["fee"]
        g[u].append((v, w))
        g[v].append((u, w))
    return g

def dijkstra(graph, src):
    INF = 10**18
    dist = {u: INF for u in graph}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heappop(pq)
        if d != dist[u]:
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heappush(pq, (nd, v))
    return dist  # dict node -> distance

@app.route('/princess-diaries', methods=['POST'])
def princess_diaries():
    """
    Input JSON:
    {
      "tasks": [{"name": "...","start": int,"end": int,"station": int,"score": int}, ...],
      "subway": [{"connection":[u,v], "fee": int}, ...],
      "starting_station": int
    }
    Output JSON:
    { "max_score": int, "min_fee": int, "schedule": [names...] }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    tasks = data.get("tasks", [])
    subway = data.get("subway", [])
    starting_station = data.get("starting_station", 0)

    if not isinstance(tasks, list) or not isinstance(subway, list):
        return jsonify({"error": "tasks and subway must be lists"}), 400

    if not tasks:
        return jsonify({"max_score": 0, "min_fee": 0, "schedule": []})

    # ---- Compact station IDs only for used stations ----
    stations = {starting_station}
    for t in tasks:
        stations.add(t["station"])
    for e in subway:
        stations.add(e["connection"][0]); stations.add(e["connection"][1])

    id_of = {s: i for i, s in enumerate(sorted(stations))}
    rid_of = {i: s for s, i in id_of.items()}  # (only needed for debugging)

    # Map tasks to compact ids
    T = []
    for t in tasks:
        T.append({
            "name": t["name"],
            "start": int(t["start"]),
            "end": int(t["end"]),
            "station": id_of[t["station"]],
            "score": int(t["score"])
        })
    T.sort(key=lambda x: x["start"])  # chronological

    start_id = id_of[starting_station]

    # ---- Build graph & run Dijkstra from only necessary sources ----
    graph = build_graph(subway, id_of)

    # Run Dijkstra from every station that’s an endpoint we need
    # We’ll need distances:
    # - start -> each task.station
    # - task_i.station -> task_j.station (for j>i and time-feasible)
    unique_sources = {start_id} | {t["station"] for t in T}
    dist_from = {}
    for s in unique_sources:
        dist_from[s] = dijkstra(graph, s)

    # Helper to get distance with INF fallback
    INF = 10**18
    def fee(a, b):
        return dist_from[a].get(b, INF)

    # ---- DP over tasks: maximize score, tie-break by min fee ----
    n = len(T)
    dp_score = [-10**9] * n
    dp_fee   = [10**18] * n
    parent   = [-1] * n

    for i in range(n):
        # option: start -> task i -> back to start later
        base_fee = fee(start_id, T[i]["station"])
        if base_fee < INF:
            dp_score[i] = T[i]["score"]
            dp_fee[i]   = base_fee

        # try chaining from a previous task j
        for j in range(i):
            if T[j]["end"] <= T[i]["start"]:
                # can move from j to i
                move_fee = fee(T[j]["station"], T[i]["station"])
                if move_fee == INF or dp_score[j] < 0:
                    continue
                cand_score = dp_score[j] + T[i]["score"]
                cand_fee   = dp_fee[j] + move_fee

                if (cand_score > dp_score[i]) or (cand_score == dp_score[i] and cand_fee < dp_fee[i]):
                    dp_score[i] = cand_score
                    dp_fee[i]   = cand_fee
                    parent[i]   = j

    # pick best end task (include return-to-start fee)
    best_i, best_score, best_total_fee = -1, -10**9, 10**18
    for i in range(n):
        if dp_score[i] < 0:
            continue
        ret_fee = fee(T[i]["station"], start_id)
        if ret_fee == INF:
            continue
        total_fee = dp_fee[i] + ret_fee
        if (dp_score[i] > best_score) or (dp_score[i] == best_score and total_fee < best_total_fee):
            best_i, best_score, best_total_fee = i, dp_score[i], total_fee

    if best_i == -1:
        # no feasible path (disconnected)
        return jsonify({"max_score": 0, "min_fee": 0, "schedule": []})

    # reconstruct schedule
    schedule = []
    i = best_i
    while i != -1:
        schedule.append(T[i]["name"])
        i = parent[i]
    schedule.reverse()

    return jsonify({
        "max_score": int(best_score),
        "min_fee": int(best_total_fee),
        "schedule": schedule
    })
