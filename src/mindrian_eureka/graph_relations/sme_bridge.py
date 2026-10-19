"""Structure-map two neighbourhoods of the graph with the SME engine (engines/sme-agent/lib/sme.py).
A neighbourhood becomes a description group: nodes are entities, relationship types are predicates, 2-step
directed paths become second-order `then` relations (so systematicity has something to prefer), and node
categories become attributes. Candidate inferences that name two mapped target nodes become proposed edges;
those that need a node the target lacks are reported as `needs_new_node`."""
from __future__ import annotations

import re
import hashlib
import json
from typing import Any

from ..structure_mapping import _sme_core as sme
from .common import Graph
from .runner import GraphInputError, validate_snapshot

from .common import SEMANTIC_TYPES


_REL = re.compile(r"\(([a-z_]+) (n\d+|\(:skolem [^)]+\)) (n\d+|\(:skolem [^)]+\))\)")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:30] or "x"


def neighbourhood(g, center, hops=2, cap=60):
    if center not in g.nodes:
        raise GraphInputError(f"node {center!r} is not present in the supplied graph snapshot")
    if not isinstance(hops, int) or isinstance(hops, bool) or not 0 <= hops <= 4:
        raise GraphInputError("hops must be an integer from 0 to 4")
    seen, frontier = {center}, [center]
    for _ in range(hops):
        nxt = []
        for n in frontier:
            for m in sorted(g.adj[n], key=lambda x: -g.deg(x)):
                if m not in seen and len(seen) < cap:
                    seen.add(m); nxt.append(m)
        frontier = nxt
    return seen


def to_dgroup(sme, g, nodes, name, attr="problem_type", max_paths=200):
    d = sme.Dgroup(name)
    ent = {}
    for n in sorted(nodes):
        ent[n] = "n%d" % (len(ent) + 1)
        d.add_entity(ent[n])
    rel = {}
    for e in g.edges:
        if e["s"] in ent and e["t"] in ent and e["type"] in SEMANTIC_TYPES:
            k = (e["s"], e["t"], e["type"])
            if k not in rel:
                rel[k] = d.add_expr(e["type"].lower(), [ent[e["s"]], ent[e["t"]]], "r%d" % (len(rel) + 1))
    count = 0
    by_src = {}
    for (s, t, ty), nm in rel.items():
        by_src.setdefault(s, []).append((t, ty, nm))
    for (s, t, ty), nm in rel.items():
        for (t2, ty2, nm2) in by_src.get(t, []):
            if t2 != s and count < max_paths:
                d.add_expr("then", [nm, nm2])
                count += 1
    for n in sorted(nodes):
        v = g.attr(n, attr)
        if v:
            d.add_expr("is-" + slug(v), [ent[n]])
    d.finalize()
    return d, ent


def map_neighbourhoods(g, base_node, target_node, hops=2, rules="AN", attr="problem_type"):
    if base_node == target_node:
        raise GraphInputError("base_node and target_node must be different graph nodes")
    if rules not in sme.RULESETS:
        raise GraphInputError(f"rules must be one of {sme.RULESETS}")
    bn, tn = neighbourhood(g, base_node, hops), neighbourhood(g, target_node, hops)
    bn = bn - {target_node}
    tn = tn - {base_node}
    B, be = to_dgroup(sme, g, bn, "base", attr)
    T, te = to_dgroup(sme, g, tn, "target", attr)
    inv_t = {v: k for k, v in te.items()}
    res = sme.SME(rules=rules, max_gmaps=200).match(B, T)
    out = []
    for gm in res.gmaps[:3]:
        props = []
        seen = set()
        for ci in gm["candidate_inferences"]:
            for f, x, y in _REL.findall(ci["expression"]):
                ty = f.upper().replace("-", "_")
                if ty not in SEMANTIC_TYPES or (ty, x, y) in seen:
                    continue
                seen.add((ty, x, y))
                if x in inv_t and y in inv_t:
                    props.append({"kind": "edge", "type": ty, "s": inv_t[x], "t": inv_t[y], "expression": ci["expression"]})
                else:
                    props.append({"kind": "needs_new_node", "type": ty, "from": inv_t.get(x, x), "to": inv_t.get(y, y),
                                  "expression": ci["expression"]})
        out.append({"ses": gm["weight"], "n_mappings": len(gm["emaps"]),
                    "mapping": [(g.name({v: k for k, v in be.items()}[a]), g.name(inv_t[b])) for a, b in gm["emaps"]
                                if a in {v: k for k, v in be.items()} and b in inv_t],
                    "proposals": props})
    return {"matches": out, "truncated": res.truncated, "match_count": len(res.gmaps),
            "base_neighborhood_size": len(bn), "target_neighborhood_size": len(tn),
            "rules": rules, "hops": hops, "attribute": attr,
            "limitations": ["SME correspondence and SES are structural hypotheses, not proof of transfer.",
                            "Source evidence, target constraints, and empirical testing were not assessed."]}


def analyze(snapshot: dict[str, Any], base_node_id: str, target_node_id: str, *,
            hops: int = 2, rules: str = "AN", attr: str = "problem_type") -> dict[str, Any]:
    """Map two bounded neighborhoods using this package's bundled SME core."""
    validate_snapshot(snapshot)
    graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot.get("meta"))
    mapped = map_neighbourhoods(graph, base_node_id, target_node_id, hops=hops, rules=rules, attr=attr)
    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    for match in mapped["matches"]:
        for proposal in match["proposals"]:
            proposal["status"] = "proposed"
            proposal["evidence"] = []
    return {
        "schema_version": "eureka.graph-sme-bridge-result.v1",
        "capability_id": "graph.map_neighbourhoods",
        "capability_version": "0.1.0",
        "status": "completed_analysis",
        "scope_id": (snapshot.get("meta") or {}).get("scope_id"),
        "snapshot_id": (snapshot.get("meta") or {}).get("snapshot_id"),
        "input_fingerprint": fingerprint,
        "base_node_id": base_node_id,
        "target_node_id": target_node_id,
        "mapping": mapped,
        "limitations": mapped["limitations"] + [
            "The graph snapshot was read only; no graph, portfolio, or evidence record was written.",
            "Candidate inferences require source-backed validation and human review in MindrianOS.",
        ],
    }
