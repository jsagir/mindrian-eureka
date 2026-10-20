"""Holes in the clique complex, found as induced 4-cycles: u-w1-v-w2-u with u,v not adjacent and w1,w2
not adjacent. Each is a one-dimensional hole at the smallest scale. The two diagonals (u-v, w1-w2) are the
candidate edges that would close it. A degree-preserving rewiring null says whether the graph has more
holes than chance. Optional: ripser gives the persistence summary of the whole graph if installed."""
from __future__ import annotations

from collections import defaultdict

from .common import distinct_pairs, pair_key, require_rewirable


def induced_c4(g, hub_cap=120, limit=20000):
    cyc, seen = [], set()
    for u in g.adj:
        if len(g.adj[u]) > hub_cap:
            continue
        two = defaultdict(list)
        for w in g.adj[u]:
            if len(g.adj[w]) > hub_cap:
                continue
            for v in g.adj[w]:
                if v != u and not g.has_edge(u, v) and u < v:
                    two[v].append(w)
        for v, ws in two.items():
            ws = sorted(ws)
            for i in range(len(ws)):
                for j in range(i + 1, len(ws)):
                    a, b = ws[i], ws[j]
                    if g.has_edge(a, b):
                        continue
                    key = tuple(sorted([tuple(sorted((u, v))), tuple(sorted((a, b)))]))
                    if key in seen:
                        continue
                    seen.add(key)
                    cyc.append({"diagonal_1": pair_key(u, v), "diagonal_2": pair_key(a, b), "cycle": [u, a, v, b]})
                    if len(cyc) >= limit:
                        return cyc
    return cyc


def swap_null(g, rounds=10, seed=7, hub_cap=120):
    """Hole counts in degree-preserving rewired copies (double edge swaps on undirected pairs)."""
    import random

    r = random.Random(seed)
    base = distinct_pairs(g)
    require_rewirable(base, "the hole swap null")
    counts = []
    from .common import Graph

    for _ in range(rounds):
        es = set(base)
        el = list(es)
        for _ in range(len(el) * 5):
            i, j = r.sample(range(len(el)), 2)
            (a, b), (c, d) = el[i], el[j]
            if len({a, b, c, d}) < 4:
                continue
            # Pick the rewiring orientation at random: (a,d),(c,b) or (a,c),(d,b). A fixed orientation
            # on sorted pairs is not uniform and biases the null.
            e, f = (d, c) if r.random() < 0.5 else (c, d)
            n1, n2 = pair_key(a, f), pair_key(e, b)
            if n1 in es or n2 in es:
                continue
            es.discard((a, b)); es.discard((c, d)); es.add(n1); es.add(n2)
            el[i], el[j] = n1, n2
        ng = Graph(list(g.nodes.values()), [{"s": a, "t": b, "type": "X"} for a, b in es])
        counts.append(len(induced_c4(ng, hub_cap)))
    mean = sum(counts) / len(counts)
    sd = (sum((c - mean) ** 2 for c in counts) / max(1, len(counts) - 1)) ** 0.5
    return mean, sd


def hole_summary(g, rounds=10, seed=7):
    cyc = induced_c4(g)
    mean, sd = swap_null(g, rounds, seed)
    z = (len(cyc) - mean) / sd if sd > 1e-9 else 0.0
    return {"holes": len(cyc), "null_mean": mean, "null_sd": sd, "z": z}


def ripser_summary(g, maxdim=1):
    """Persistence of the whole graph (shortest-path metric). None if ripser/numpy are missing."""
    try:
        import numpy as np
        from ripser import ripser
    except Exception:
        return None
    ids = sorted(g.nodes)
    ix = {n: i for i, n in enumerate(ids)}
    big = len(ids) + 1
    D = np.full((len(ids), len(ids)), float(big))
    for s in ids:
        dist, q = {s: 0}, [s]
        for x in q:
            for y in g.adj[x]:
                if y not in dist:
                    dist[y] = dist[x] + 1
                    q.append(y)
        for t, d in dist.items():
            D[ix[s], ix[t]] = d
    dg = ripser(D, distance_matrix=True, maxdim=maxdim)["dgms"]
    h1 = [(float(b), float(d)) for b, d in dg[1] if d < float("inf")]
    return {"h1_count": len(h1), "h1_longest": max((d - b for b, d in h1), default=0.0)}
