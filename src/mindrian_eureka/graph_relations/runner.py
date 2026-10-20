"""Read-only local graph relationship discovery over a caller-authorized snapshot."""
from __future__ import annotations

import time
import hashlib
import json
from urllib.parse import quote
from typing import Any

from . import atypicality, bridging, gaps, holes, proposals, textsim
from .common import (MAX_BRIDGE_EDGES, MAX_BRIDGE_NODES, Graph, GraphBudgetError,  # noqa: F401  (re-exported)
                     GraphInputError, as_deadline, require_size)


def prepare_artifact_bundle(snapshot: dict[str, Any], objective: str, scope_id: str,
                            max_artifacts: int = 2500) -> dict[str, Any]:
    """Project graph nodes into the existing source-linked RS/HSI bundle contract."""
    validate_snapshot(snapshot)
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 5000:
        raise GraphInputError("objective must contain 1..5000 characters")
    if not isinstance(scope_id, str) or not scope_id.strip() or len(scope_id) > 256:
        raise GraphInputError("scope_id must contain 1..256 characters")
    host_scope_id = (snapshot.get("meta") or {}).get("scope_id")
    if host_scope_id is not None and host_scope_id != scope_id:
        raise GraphInputError("scope_id does not match the scope bound to the supplied graph snapshot")
    if not isinstance(max_artifacts, int) or isinstance(max_artifacts, bool) or not 2 <= max_artifacts <= 2500:
        raise GraphInputError("max_artifacts must be an integer from 2 to 2500")
    graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot.get("meta"))
    artifacts = []
    skipped_empty = 0
    text_bytes = 0
    for node_id, node in graph.nodes.items():
        name = graph.name(node_id)
        labels = node.get("labels") or []
        text_parts = [str(name), str(node.get("text") or "").strip()]
        if labels:
            text_parts.append("labels: " + ", ".join(str(label) for label in labels))
        for field in ("problem_type", "discipline", "domain", "jtbd_anchor"):
            value = graph.attr(node_id, field)
            if value:
                text_parts.append(f"{field.replace('_', ' ')}: {value}")
        content = "\n".join(part for part in text_parts if part).strip()
        if not content:
            skipped_empty += 1
            continue
        if len(content) > 1_000_000:
            raise GraphInputError(f"graph node {node_id!r} exceeds the 1,000,000-character artifact limit")
        attrs = node.get("attrs") or {}
        # Never turn a local filesystem path into an engine result. The host
        # owns source resolution and may supply an opaque, room-safe reference.
        source_ref = next((attrs.get(key) for key in ("source_ref", "url", "uri")
                           if isinstance(attrs.get(key), str) and attrs[key].strip()), None)
        source_ref = source_ref or f"mindrian-graph://node/{quote(str(node_id), safe='')}"
        if len(str(node_id)) > 256 or len(str(name)) > 2000 or len(source_ref) > 2048:
            raise GraphInputError(f"graph node {node_id!r} exceeds the RS/HSI artifact identity/title/source-ref limits")
        text_bytes += len(content.encode("utf-8"))
        if text_bytes > 20 * 1024 * 1024:
            raise GraphInputError("projected artifact text exceeds the RS/HSI 20 MiB bundle limit; narrow the authorized graph snapshot")
        artifacts.append({
            "id": str(node_id), "source_ref": source_ref, "title": str(name), "text": content,
            "corpus": "room", "media_type": "text/plain",
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        })
    if len(artifacts) < 2:
        raise GraphInputError("at least two graph nodes need usable text to prepare a discovery bundle")
    if len(artifacts) > max_artifacts:
        raise GraphInputError(f"eligible graph nodes exceed max_artifacts={max_artifacts}; narrow the authorized host snapshot")
    snapshot_id = (snapshot.get("meta") or {}).get("snapshot_id")
    digest_input = "\n".join(f"{row['id']}:{row['sha256']}" for row in sorted(artifacts, key=lambda row: row["id"]))
    bundle_id = snapshot_id or "sha256:" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    return {
        "schema_version": "eureka.graph-artifact-bundle.v1",
        "capability_id": "graph.prepare_artifact_bundle",
        "status": "completed_projection",
        "objective": objective.strip(), "scope_id": scope_id.strip(), "snapshot_id": bundle_id,
        "artifacts": artifacts,
        "projection": {"source_node_count": len(graph.nodes), "artifact_count": len(artifacts),
                       "skipped_empty_node_count": skipped_empty, "max_artifacts": max_artifacts,
                       "source_ref_policy": "preserve source_ref/url/uri node attribute; never expose path; otherwise emit mindrian-graph://node/{id}",
                       "corpus": "room"},
        "handoff": {"next_capability": "opportunity.synthesize_discovery_signals",
                    "instruction": "Pass this bundle to the RS/HSI local scout after host scope authorization and review."},
        "limitations": ["This is a projection of graph node text, not source evidence or a Holon boundary.",
                        "Fallback mindrian-graph references require a MindrianOS resolver to open the node and its provenance.",
                        "No graph query beyond the supplied snapshot and no graph or portfolio write was performed."],
    }


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("nodes"), list) or not isinstance(snapshot.get("edges"), list):
        raise GraphInputError("snapshot must contain nodes and edges arrays")
    if len(snapshot["nodes"]) > 10_000 or len(snapshot["edges"]) > 50_000:
        raise GraphInputError("snapshot exceeds the analysis limit of 10,000 nodes or 50,000 edges; narrow the authorized snapshot")
    if "meta" in snapshot and not isinstance(snapshot["meta"], dict):
        raise GraphInputError("snapshot.meta must be an object when provided")
    ids: set[str] = set()
    for index, node in enumerate(snapshot["nodes"]):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"].strip():
            raise GraphInputError(f"snapshot.nodes[{index}] needs a non-empty string id")
        if node["id"] in ids:
            raise GraphInputError(f"snapshot contains duplicate node id {node['id']!r}")
        ids.add(node["id"])
        if "labels" in node and (not isinstance(node["labels"], list) or any(not isinstance(label, str) for label in node["labels"])):
            raise GraphInputError(f"snapshot node {node['id']!r}.labels must be an array of strings")
        if "attrs" in node and not isinstance(node["attrs"], dict):
            raise GraphInputError(f"snapshot node {node['id']!r}.attrs must be an object")
    for index, edge in enumerate(snapshot["edges"]):
        if not isinstance(edge, dict) or not all(isinstance(edge.get(key), str) and edge[key] for key in ("s", "t", "type")):
            raise GraphInputError(f"snapshot.edges[{index}] needs string s, t, and type fields")
        if edge["s"] not in ids or edge["t"] not in ids:
            raise GraphInputError(f"snapshot.edges[{index}] references a node absent from the snapshot")


def project_focus(snapshot: dict[str, Any], focal_node_id: str, hops: int = 2, max_nodes: int = 10_000):
    """Build an explicit, undirected semantic-neighborhood projection of an authorized snapshot."""
    if not isinstance(focal_node_id, str) or not focal_node_id:
        raise GraphInputError("focal_node_id must be a non-empty stable node identifier")
    if not isinstance(hops, int) or isinstance(hops, bool) or not 0 <= hops <= 5:
        raise GraphInputError("focus_hops must be an integer from 0 to 5")
    validate_snapshot(snapshot)
    graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot.get("meta"))
    if focal_node_id not in graph.nodes:
        raise ValueError(f"focal node {focal_node_id!r} is not present in the authorized snapshot")
    included, frontier = {focal_node_id}, {focal_node_id}
    for _ in range(hops):
        next_frontier = set()
        for node_id in frontier:
            next_frontier.update(graph.adj[node_id] - included)
        included.update(next_frontier)
        if len(included) > max_nodes:
            raise GraphInputError(f"focus projection exceeds {max_nodes} nodes; narrow the host snapshot or focus_hops")
        frontier = next_frontier
        if not frontier:
            break
    nodes = [node for node_id, node in graph.nodes.items() if node_id in included]
    edges = [edge for edge in graph.edges if edge["s"] in included and edge["t"] in included]
    projection_meta = {
        "focus_node_id": focal_node_id,
        "focus_hops": hops,
        "included_node_ids": sorted(included),
        "included_node_count": len(included),
        "source_node_count": len(graph.nodes),
        "omitted_node_count": len(graph.nodes) - len(included),
        "included_edge_count": len(edges),
        "omitted_edge_count": len(graph.edges) - len(edges),
        "boundary_policy": "undirected semantic-edge neighborhood; host authorization must be applied before snapshot delivery",
    }
    meta = dict(graph.meta)
    meta["focus_projection"] = projection_meta
    return {"nodes": nodes, "edges": edges, "meta": meta}, projection_meta


def explore(snapshot: dict[str, Any], *, top: int = 100, seed: int = 7,
            attr: str = "problem_type", text_label: str | None = None,
            min_common: int = 2, null_rounds: int = 8, focus_node_id: str | None = None,
            focus_hops: int = 2, budget_seconds: float | None = None) -> dict[str, Any]:
    """Analyze supplied graph records only; never connects to or mutates a graph store.

    The analysis stops with GraphBudgetError (a GraphInputError) when the analysed graph has more than
    2,500 nodes or 12,000 edges, or when the wall-clock budget runs out (120 seconds by default;
    budget_seconds overrides it for tests)."""
    deadline = as_deadline(budget_seconds)
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("nodes"), list) or not isinstance(snapshot.get("edges"), list):
        raise GraphInputError("snapshot must contain nodes and edges arrays")
    validate_snapshot(snapshot)
    # Bind the result to the exact host projection, including its snapshot
    # metadata. This remains useful when a caller has not assigned snapshot_id.
    snapshot_fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 1000:
        raise GraphInputError("top must be an integer between 1 and 1000")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise GraphInputError("seed must be an integer")
    if not isinstance(null_rounds, int) or isinstance(null_rounds, bool) or not 1 <= null_rounds <= 20:
        raise GraphInputError("null_rounds must be an integer between 1 and 20")
    if not isinstance(min_common, int) or isinstance(min_common, bool) or min_common < 1:
        raise GraphInputError("min_common must be a positive integer")
    focus_projection = None
    if focus_node_id is not None:
        snapshot, focus_projection = project_focus(snapshot, focus_node_id, focus_hops)
    graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot.get("meta"))
    if not graph.nodes:
        raise GraphInputError("snapshot has no valid nodes")
    # Checked after the optional focus projection, so a narrow focus can analyse part of a large snapshot.
    require_size(graph, MAX_BRIDGE_NODES, MAX_BRIDGE_EDGES, "local relationship exploration (it runs exact betweenness)")
    started = time.monotonic()
    signals: dict[str, list[dict[str, Any]]] = {}
    info: dict[str, Any] = {"nodes": len(graph.nodes), "edges": len(graph.edges), "source_meta": graph.meta}
    rows, skipped = gaps.open_triads(graph, min_common, budget_seconds=deadline)
    signals["gaps"] = [{"u": r["u"], "v": r["v"], "score": r["adamic_adar"] + max(0.0, r["z"]) * .1,
                        "common": r["common"], "z": round(r["z"], 3), "via": [graph.name(w) for w in r["via"][:4]]}
                       for r in rows[:top * 3]]
    info["hub_nodes_skipped"] = len(skipped)
    info["holes"] = holes.hole_summary(graph, rounds=null_rounds, seed=seed, budget_seconds=deadline)
    deadline.check("local relationship exploration")
    info["ripser"] = holes.ripser_summary(graph)
    cycle_scores: dict[tuple[str, str], list[list[str]]] = {}
    for cycle in holes.induced_c4(graph, budget_seconds=deadline):
        for key in ("diagonal_1", "diagonal_2"):
            cycle_scores.setdefault(cycle[key], []).append([graph.name(x) for x in cycle["cycle"]])
    signals["holes"] = [{"u": pair[0], "v": pair[1], "score": float(len(cycles)), "cycles": cycles[:2]}
                         for pair, cycles in sorted(cycle_scores.items(), key=lambda x: (-len(x[1]), x[0]))[:top * 3]]
    communities, betweenness, participation, bridge_rows = bridging.bridge_report(graph, seed, budget_seconds=deadline)
    signals["bridge"] = [{"u": r["u"], "v": r["v"], "score": r["score"], "via": graph.name(r["via"])}
                          for r in bridging.bridge_pairs(graph, communities, betweenness, participation)[:top * 3]]
    info["communities"] = len(set(communities.values()))
    info["top_bridges"] = [{"name": graph.name(r["id"]), "betweenness": round(r["betweenness"], 5),
                            "participation": round(r["participation"], 3)} for r in bridge_rows[:10]]
    deadline.check("local relationship exploration")
    text_ids = [n for n in graph.nodes if text_label is None or text_label in graph.nodes[n].get("labels", [])]
    if len(text_ids) <= 3000:
        signals["semantic"] = [{"u": r["u"], "v": r["v"], "score": r["sim"], "common": r["common"]}
                               for r in textsim.semantic_gaps(graph, text_ids, top=top * 3)]
    else:
        info["semantic"] = "skipped: more than 3000 text nodes; select a label"
    zscores, categories, _ = atypicality.category_zscores(graph, attr, shuffles=20, seed=seed, budget_seconds=deadline)
    info["atypicality"] = atypicality.edge_profile(graph, zscores, categories)
    ranked, dropped = proposals.merge(graph, signals)
    for row in ranked:
        score = atypicality.annotate([{"u": row["s"], "v": row["t"]}], graph, zscores, categories)[0]["atypicality_z"]
        row["atypicality_z"] = None if score is None else round(score, 3)
    ranked, issues = proposals.split_issues(ranked)
    info.update({"name_issues": len(issues), "dropped_existing": dropped,
                 "runtime_seconds": round(time.monotonic() - started, 3)})
    return {
        "schema_version": "eureka.graph-relationship-result.v1",
        "capability_id": "graph.explore_local_relationships",
        "capability_version": "0.1.0",
        "status": "completed_analysis",
        "graph_access": "read_only_snapshot",
        "scope_id": (snapshot.get("meta") or {}).get("scope_id"),
        "snapshot_id": snapshot.get("meta", {}).get("snapshot_id"),
        "input_fingerprint": snapshot_fingerprint,
        "run_config": {"top": top, "seed": seed, "attr": attr, "text_label": text_label,
                       "min_common": min_common, "null_rounds": null_rounds,
                       "focus_node_id": focus_node_id, "focus_hops": focus_hops},
        "summary": info, "focus_projection": focus_projection,
        "proposals": ranked[:top], "name_issues": issues[:100],
        "limitations": [
            "All relationship candidates are unevidenced hypotheses; suggested type and direction are not validated.",
            "The historical backtest in the source research found zero of 30 later edges in the top 200, including the baseline; discovery quality is unvalidated.",
            "This run analyzes only the supplied graph snapshot and performs no evidence retrieval, authorization, or graph writes.",
            "Neo4j elementId fallback identifiers are snapshot-local and may not remain stable after graph migration or recreation.",
            "Human review and source-backed validation are required before any candidate can be accepted.",
        ],
    }
