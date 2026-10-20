"""Individually callable, read-only graph algorithms for CLI and MCP clients.

These services deliberately return candidate signals, not accepted knowledge. They
operate only on the graph snapshot supplied by the authorized host.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from . import atypicality, bridging, gaps, holes, textsim
from .common import MAX_BRIDGE_EDGES, MAX_BRIDGE_NODES, Graph, GraphInputError, as_deadline
from .runner import validate_snapshot


def _context(capability_id: str, snapshot: dict[str, Any], options: dict[str, Any]) -> tuple[Graph, dict[str, Any]]:
    validate_snapshot(snapshot)
    meta = snapshot.get("meta") or {}
    if not isinstance(meta, dict):
        raise GraphInputError("snapshot.meta must be an object")
    lineage_requested = "scope_id" in meta or "snapshot_id" in meta
    if lineage_requested and (
        not isinstance(meta.get("scope_id"), str) or not meta["scope_id"].strip() or
        not isinstance(meta.get("snapshot_id"), str) or not meta["snapshot_id"].strip()
    ):
        raise GraphInputError("lineage requires non-empty snapshot.meta.scope_id and snapshot.meta.snapshot_id")
    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    graph = Graph(snapshot["nodes"], snapshot["edges"], meta)
    if not graph.nodes:
        raise GraphInputError("snapshot must contain at least one node")
    return graph, {
        "schema_version": "eureka.graph-algorithm-result.v1",
        "capability_id": capability_id,
        "status": "completed_analysis",
        "graph_access": "read_only_snapshot",
        "scope_id": meta.get("scope_id"),
        "snapshot_id": meta.get("snapshot_id"),
        "input_fingerprint": fingerprint,
        "graph_summary": {"node_count": len(graph.nodes), "edge_count": len(graph.edges)},
        "run_config": options,
        "limitations": [
            "Results are algorithmic leads, not evidence-backed or accepted knowledge.",
            "Only the supplied snapshot was analyzed; this service does not authorize, fetch evidence, or write to a graph.",
        ],
    }


def find_structural_gaps(payload: dict[str, Any], *, budget_seconds: float | None = None) -> dict[str, Any]:
    deadline = as_deadline(budget_seconds)
    snapshot = payload["snapshot"]
    min_common, hub_cap, top = payload.get("min_common", 2), payload.get("hub_cap", 150), payload.get("top", 200)
    graph, result = _context("graph.find_structural_gaps", snapshot,
                             {"min_common": min_common, "hub_cap": hub_cap, "top": top})
    if not 1 <= min_common <= 100 or not 1 <= hub_cap <= 500 or not 1 <= top <= 1000:
        raise GraphInputError("min_common, hub_cap, or top is outside its allowed range")
    rows, skipped = gaps.open_triads(graph, min_common=min_common, hub_cap=hub_cap, budget_seconds=deadline)
    result.update({"method": "open_triads", "pairs": [
        {"source_node_id": row["u"], "target_node_id": row["v"], "common_neighbor_count": row["common"],
         "jaccard": row["jaccard"], "adamic_adar": row["adamic_adar"], "null_z": row["z"],
         "shared_neighbor_ids": row["via"]}
        for row in rows[:top]], "skipped_hub_node_ids": skipped,
        "limitations": result["limitations"] + [
            "Open-triad scores rank shared-neighbor structure; they do not establish that a missing edge should exist.",
        ]})
    return result


def find_network_holes(payload: dict[str, Any], *, budget_seconds: float | None = None) -> dict[str, Any]:
    deadline = as_deadline(budget_seconds)
    snapshot = payload["snapshot"]
    rounds, seed = payload.get("rounds", 4), payload.get("seed", 7)
    hub_cap, limit, top = payload.get("hub_cap", 120), payload.get("cycle_limit", 20000), payload.get("top", 200)
    include_persistence = payload.get("include_persistence", False)
    graph, result = _context("graph.find_network_holes", snapshot,
                             {"rounds": rounds, "seed": seed, "hub_cap": hub_cap, "cycle_limit": limit,
                              "top": top, "include_persistence": include_persistence})
    if len(graph.nodes) > 1200 or len(graph.edges) > 6000:
        raise GraphInputError("network-hole analysis is limited to 1,200 nodes and 6,000 edges; narrow the authorized snapshot")
    if not isinstance(rounds, int) or isinstance(rounds, bool) or not 1 <= rounds <= 10 or isinstance(seed, bool) or not isinstance(seed, int):
        raise GraphInputError("rounds must be an integer from 1..10 and seed must be an integer")
    if not isinstance(include_persistence, bool):
        raise GraphInputError("include_persistence must be boolean")
    if not 1 <= hub_cap <= 2500 or not 1 <= limit <= 20000 or not 1 <= top <= 1000:
        raise GraphInputError("hub_cap, cycle_limit, or top is outside its allowed range")
    cycles = holes.induced_c4(graph, hub_cap=hub_cap, limit=limit, budget_seconds=deadline)
    null_mean, null_sd = holes.swap_null(graph, rounds=rounds, seed=seed, hub_cap=hub_cap, budget_seconds=deadline)
    hole_z = (len(cycles) - null_mean) / null_sd if null_sd > 1e-9 else 0.0
    summary = {"holes": len(cycles), "null_mean": null_mean, "null_sd": null_sd, "z": hole_z}
    diagonal_counts: dict[tuple[str, str], int] = {}
    for cycle in cycles:
        for field in ("diagonal_1", "diagonal_2"):
            pair = tuple(cycle[field])
            diagonal_counts[pair] = diagonal_counts.get(pair, 0) + 1
    candidates = [{"node_ids": list(pair), "cycle_count": count}
                  for pair, count in sorted(diagonal_counts.items(), key=lambda item: (-item[1], item[0]))[:top]]
    persistence = holes.ripser_summary(graph) if include_persistence else None
    persistence_status = ("not_requested" if not include_persistence else
                          "completed" if persistence is not None else "unavailable")
    result.update({"method": "induced_c4_with_degree_preserving_swap_null", "summary": summary,
                   "candidate_diagonals": candidates, "cycles_examined": len(cycles),
                   "ripser_summary": persistence, "persistence_status": persistence_status,
                   "limitations": result["limitations"] + [
                       "A missing diagonal in an induced four-cycle is a structural lead, not evidence of a meaningful relationship.",
                       "The rewiring null and optional persistence summary are diagnostics whose interpretation depends on graph construction.",
                   ]})
    return result


def find_bridge_pairs(payload: dict[str, Any], *, budget_seconds: float | None = None) -> dict[str, Any]:
    deadline = as_deadline(budget_seconds)
    snapshot = payload["snapshot"]
    seed, top = payload.get("seed", 7), payload.get("top", 200)
    per_node, min_bc = payload.get("per_node", 20), payload.get("min_betweenness", 0.0)
    graph, result = _context("graph.find_bridge_pairs", snapshot,
                             {"seed": seed, "top": top, "per_node": per_node, "min_betweenness": min_bc})
    if len(graph.nodes) > MAX_BRIDGE_NODES or len(graph.edges) > MAX_BRIDGE_EDGES:
        raise GraphInputError("bridge analysis uses exact betweenness and is limited to 2,500 nodes and 12,000 edges")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 1 <= top <= 1000 or not 1 <= per_node <= 100:
        raise GraphInputError("seed, top, or per_node is outside its allowed range")
    if isinstance(min_bc, bool) or not isinstance(min_bc, (int, float)) or not math.isfinite(min_bc) or min_bc < 0:
        raise GraphInputError("min_betweenness must be a finite non-negative number")
    communities, betweenness, participation, bridge_nodes = bridging.bridge_report(graph, seed, budget_seconds=deadline)
    pairs = bridging.bridge_pairs(graph, communities, betweenness, participation,
                                  per_node=per_node, min_bc=min_bc)
    result.update({"method": "label_propagation_brandes_participation", "community_count": len(set(communities.values())),
                   "bridge_nodes": [{"node_id": row["id"], "community": row["community"],
                                     "betweenness": row["betweenness"], "participation": row["participation"]}
                                    for row in bridge_nodes[:top]],
                   "candidate_pairs": [{"source_node_id": row["u"], "target_node_id": row["v"],
                                        "bridge_node_id": row["via"], "score": row["score"]}
                                       for row in pairs[:top]],
                   "limitations": result["limitations"] + [
                       "Bridge candidates depend on label-propagation communities and exact betweenness in this snapshot; neither implies a useful cross-domain transfer.",
                   ]})
    return result


def assess_edge_atypicality(payload: dict[str, Any], *, budget_seconds: float | None = None) -> dict[str, Any]:
    deadline = as_deadline(budget_seconds)
    snapshot = payload["snapshot"]
    attr, shuffles, seed, use_label = payload.get("category_attribute", "problem_type"), payload.get("shuffles", 20), payload.get("seed", 7), payload.get("use_label", False)
    graph, result = _context("graph.assess_edge_atypicality", snapshot,
                             {"category_attribute": attr, "shuffles": shuffles, "seed": seed, "use_label": use_label})
    if len(graph.edges) > 20000:
        raise GraphInputError("edge atypicality is limited to 20,000 edges; narrow the authorized snapshot")
    if not isinstance(attr, str) or not attr or len(attr) > 128 or not isinstance(shuffles, int) or isinstance(shuffles, bool) or not 1 <= shuffles <= 50:
        raise GraphInputError("category_attribute or shuffles is outside its allowed range")
    if isinstance(seed, bool) or not isinstance(seed, int) or not isinstance(use_label, bool):
        raise GraphInputError("seed must be an integer and use_label must be boolean")
    zscores, categories, observed = atypicality.category_zscores(graph, attr, shuffles=shuffles,
                                                                  seed=seed, use_label=use_label,
                                                                  budget_seconds=deadline)
    result.update({"method": "degree_preserving_edge_rewiring_category_zscores",
                   "category_attribute": attr, "observed_category_pairs": [
                       {"categories": list(pair), "observed_edge_count": count,
                        "null_z": zscores.get(pair, 0.0)}
                       for pair, count in sorted(observed.items(), key=lambda item: (-item[1], item[0]))],
                   "edge_profile": atypicality.edge_profile(graph, zscores, categories),
                   "limitations": result["limitations"] + [
                       "This describes category combinations among existing edges; it does not identify missing edges or measure novelty, value, or quality.",
                       "Z-scores depend on the supplied categories, graph snapshot, rewiring procedure, and shuffle count.",
                   ]})
    return result


def find_semantic_gaps(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = payload["snapshot"]
    label, min_sim, top = payload.get("text_label"), payload.get("min_similarity", 0.25), payload.get("top", 200)
    graph, result = _context("graph.find_semantic_gaps", snapshot,
                             {"text_label": label, "min_similarity": min_sim, "top": top})
    if label is not None and (not isinstance(label, str) or not label):
        raise GraphInputError("text_label must be a non-empty string when provided")
    ids = [node_id for node_id, node in graph.nodes.items()
           if (label is None or label in node.get("labels", []))
           and (graph.name(node_id).strip() or str(node.get("text", "")).strip())]
    if len(ids) > 3000:
        raise GraphInputError("semantic-gap analysis is limited to 3,000 text-bearing nodes; select a text_label")
    if isinstance(min_sim, bool) or not isinstance(min_sim, (int, float)) or not math.isfinite(min_sim) or not 0 <= min_sim <= 1:
        raise GraphInputError("min_similarity must be a finite number in [0, 1]")
    if not 1 <= top <= 1000:
        raise GraphInputError("top must be an integer from 1 to 1,000")
    pairs = textsim.semantic_gaps(graph, ids, min_sim=min_sim, top=top)
    result.update({"method": "tfidf_cosine_similarity_without_graph_edge", "compared_node_count": len(ids),
                   "candidate_pairs": [{"source_node_id": row["u"], "target_node_id": row["v"],
                                        "similarity": row["sim"], "common_neighbor_count": row["common"]}
                                       for row in pairs],
                   "limitations": result["limitations"] + [
                       "The default similarity uses lightweight lexical TF-IDF, not a language-model embedding or causal relation test.",
                       "High text similarity without an edge is a retrieval lead; it does not establish a missing relationship.",
                   ]})
    return result
