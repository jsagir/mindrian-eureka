"""Temporal backtest: hide relationships created after a cutoff, run each method on the earlier graph, and see
how many of the hidden relationships the method ranks near the top. Compared against baselines.
Without this, a method has not earned a place in the agent."""
from __future__ import annotations

import heapq
from datetime import date, datetime, time, timezone

from .common import GraphInputError, MAX_BRIDGE_EDGES, MAX_BRIDGE_NODES, as_deadline, pair_key, require_size
from .gaps import ranked_pairs
from .bridging import communities, betweenness, participation, bridge_pairs
from .holes import induced_c4


def dated_edges(g):
    return [e for e in g.edges if e.get("created_at")]


def _parse_date(value, field="cutoff"):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min, tzinfo=timezone.utc)
    elif isinstance(value, str):
        raw = value.strip()
        try:
            parsed_date = date.fromisoformat(raw)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise GraphInputError(f"{field} must be an ISO date or date-time") from exc
        else:
            parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
    else:
        raise GraphInputError(f"{field} must be an ISO date or date-time")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def choose_cutoff(g, frac=0.7):
    ds = sorted(_parse_date(e["created_at"], "edge created_at") for e in dated_edges(g))
    return ds[int(len(ds) * frac)].isoformat() if ds else None


def split(g, cutoff):
    cutoff_date = _parse_date(cutoff)
    train = g.filtered(lambda e: not e.get("created_at") or _parse_date(e["created_at"], "edge created_at") < cutoff_date)
    future = {pair_key(e["s"], e["t"]) for e in g.edges
              if e.get("created_at") and _parse_date(e["created_at"], "edge created_at") >= cutoff_date}
    future = {p for p in future if not train.has_edge(*p)}
    return train, future


def methods(train, seed=7, budget_seconds=None, pref_limit=None):
    """Ranking methods. pref_limit keeps only the top pref_limit preferential-attachment pairs
    (streamed, so memory stays O(pref_limit) instead of O(n squared)); None keeps all of them."""
    deadline = as_deadline(budget_seconds)

    def holes():
        rows = induced_c4(train, budget_seconds=deadline)
        sc = {}
        for r in rows:
            for k in ("diagonal_1", "diagonal_2"):
                sc[r[k]] = sc.get(r[k], 0) + 1
        return [p for p, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]

    def bridge():
        comm = communities(train, seed)
        bc = betweenness(train, budget_seconds=deadline)
        pc = participation(train, comm)
        return [pair_key(r["u"], r["v"]) for r in bridge_pairs(train, comm, bc, pc, per_node=50)]

    def candidates():
        ids = sorted(train.nodes)
        for i in range(len(ids)):
            deadline.check("preferential-attachment ranking")
            for j in range(i + 1, len(ids)):
                if not train.has_edge(ids[i], ids[j]):
                    yield (-(train.deg(ids[i]) * train.deg(ids[j])), (ids[i], ids[j]))

    def pref():
        # Same order as sorting every pair by (-degree product, pair), without building the full list.
        ranked = sorted(candidates()) if pref_limit is None else heapq.nsmallest(pref_limit, candidates())
        return [p for _, p in ranked]

    return {"gaps": lambda: ranked_pairs(train, 1, budget_seconds=deadline), "holes": holes,
            "bridge": bridge, "pref_attachment": pref}


def evaluate(g, cutoff=None, ks=(10, 50, 200), seed=7, only_pairs=None, budget_seconds=None):
    require_size(g, MAX_BRIDGE_NODES, MAX_BRIDGE_EDGES, "relationship backtest (it runs exact betweenness)")
    deadline = as_deadline(budget_seconds)
    cutoff = cutoff or choose_cutoff(g)
    if not cutoff:
        return {"error": "no dated relationships; cannot backtest"}
    cutoff = _parse_date(cutoff).isoformat()
    train, future = split(g, cutoff)
    if only_pairs is not None:
        future = {p for p in future if p in only_pairs}
    if not future:
        return {"error": "no future relationships after cutoff", "cutoff": cutoff}
    ids = sorted(train.nodes)
    n_pairs = len(ids) * (len(ids) - 1) // 2 - len({pair_key(e["s"], e["t"]) for e in train.edges})
    res = {"cutoff": cutoff, "train_edges": len(train.edges), "future_edges": len(future), "candidate_pairs": n_pairs}
    for name, fn in methods(train, seed, deadline, pref_limit=max(ks, default=0)).items():
        deadline.check("relationship backtest")
        ranked = fn()
        # The preferential-attachment list is cut to the largest k; it proposes every non-adjacent pair.
        row = {"proposed": n_pairs if name == "pref_attachment" else len(ranked)}
        for k in ks:
            hits = sum(1 for p in ranked[:k] if p in future)
            exp = k * len(future) / n_pairs if n_pairs else 0.0
            row["hits@%d" % k] = hits
            row["lift@%d" % k] = (hits / exp) if exp > 0 else None
        res[name] = row
    return res
