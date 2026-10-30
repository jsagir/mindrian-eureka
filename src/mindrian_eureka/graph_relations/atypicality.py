"""Uzzi-style atypicality on graph edges, by node category pair.
z < 0 means the pair is rarer than a degree-preserving rewiring predicts (an unusual combination).
Best profile per the source work: a conventional core with a minority of unusual links."""
from __future__ import annotations

import random
from collections import Counter

from .common import as_deadline, distinct_pairs, pair_key, require_rewirable


def _count(edges, cat):
    c = Counter()
    for s, t in edges:
        a, b = cat.get(s), cat.get(t)
        if a is not None and b is not None:
            c[pair_key(a, b)] += 1
    return c


def category_zscores(g, attr="problem_type", shuffles=30, seed=7, use_label=False, budget_seconds=None):
    deadline = as_deadline(budget_seconds)
    cat = {n: (g.label(n) if use_label else g.attr(n, attr)) for n in g.nodes}
    base = distinct_pairs(g)
    require_rewirable(base, "the edge atypicality rewiring null")
    obs = _count(base, cat)
    r = random.Random(seed)
    sums, sq = Counter(), Counter()
    keys = set(obs)
    runs = []
    for _ in range(shuffles):
        deadline.check("the edge atypicality rewiring null")
        es = set(base); el = list(es)
        for step in range(len(el) * 3):
            if not step & 1023:
                deadline.check("the edge atypicality rewiring null")
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
        cc = _count(es, cat)
        runs.append(cc); keys |= set(cc)
    z = {}
    for k in keys:
        vals = [cc.get(k, 0) for cc in runs]
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / max(1, len(vals) - 1)) ** 0.5
        z[k] = (obs.get(k, 0) - m) / sd if sd > 1e-9 else 0.0
    return z, cat, obs


def edge_profile(g, z, cat):
    """Per-edge z, global 10th percentile (Uzzi's novelty tail) and median (conventional core)."""
    zs = []
    for e in g.edges:
        a, b = cat.get(e["s"]), cat.get(e["t"])
        if a is not None and b is not None:
            zs.append(z.get(pair_key(a, b), 0.0))
    if not zs:
        return {"n": 0, "p10": None, "median": None}
    zs.sort()
    return {"n": len(zs), "p10": zs[max(0, int(0.1 * len(zs)) - 1)], "median": zs[len(zs) // 2]}


def annotate(rows, g, z, cat):
    """Attach the category-pair z to proposal rows (u, v keys)."""
    for r in rows:
        a, b = cat.get(r["u"]), cat.get(r["v"])
        r["atypicality_z"] = z.get(pair_key(a, b)) if a is not None and b is not None else None
    return rows
