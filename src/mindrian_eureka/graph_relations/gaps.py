"""Structural gaps: unconnected pairs that share many neighbours (open triads).
Scores: common neighbours, Jaccard, Adamic-Adar, and a z-score against a random-neighbourhood null.
This is the cheap, fast cousin of the persistent-homology signal and doubles as the backtest baseline."""
from __future__ import annotations

import math
from collections import defaultdict

from .common import MAX_TRIAD_PAIRS, GraphBudgetError, as_deadline, hypergeom_z, pair_key


def open_triads(g, min_common=2, hub_cap=150, budget_seconds=None, max_pairs=MAX_TRIAD_PAIRS):
    deadline = as_deadline(budget_seconds)
    # Enumerating the neighbour pairs of a node costs degree squared. Count them first and refuse an
    # input that would enumerate more than max_pairs in total, before doing any of the work.
    total_pairs = sum(len(nb) * (len(nb) - 1) // 2 for nb in g.adj.values() if len(nb) <= hub_cap)
    if total_pairs > max_pairs:
        raise GraphBudgetError(
            f"open-triad analysis would enumerate {total_pairs:,} neighbour pairs, above the limit of "
            f"{max_pairs:,}; lower hub_cap or narrow the authorized snapshot")
    common = defaultdict(list)
    skipped = []
    for w, nb in g.adj.items():
        deadline.check("open-triad analysis")
        if len(nb) > hub_cap:
            skipped.append(w)
            continue
        nb = sorted(nb)
        for i in range(len(nb)):
            if not i & 63:
                deadline.check("open-triad analysis")
            for j in range(i + 1, len(nb)):
                u, v = nb[i], nb[j]
                if not g.has_edge(u, v):
                    common[(u, v)].append(w)
    n = len(g)
    out = []
    for n_seen, ((u, v), ws) in enumerate(common.items()):
        if not n_seen & 1023:
            deadline.check("open-triad scoring")
        if len(ws) < min_common:
            continue
        k = len(ws)
        union = len(g.adj[u] | g.adj[v])
        aa = sum(1.0 / math.log(max(2, g.deg(w))) for w in ws)
        z = hypergeom_z(k, g.deg(u), g.deg(v), n)
        out.append({"u": u, "v": v, "common": k, "jaccard": k / union if union else 0.0, "adamic_adar": aa,
                    "z": z, "via": ws[:8]})
    out.sort(key=lambda r: (-r["adamic_adar"], -r["z"], r["u"], r["v"]))
    return out, skipped


def ranked_pairs(g, min_common=1, hub_cap=150, budget_seconds=None):
    """Ranked list of (u, v) for the backtest."""
    rows, _ = open_triads(g, min_common, hub_cap, budget_seconds=budget_seconds)
    return [pair_key(r["u"], r["v"]) for r in rows]
