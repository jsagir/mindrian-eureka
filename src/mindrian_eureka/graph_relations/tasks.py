"""Shared handlers for graph-relation tasks exposed through CLI and MCP."""
from __future__ import annotations

import math
from typing import Any

from .backtest import evaluate
from .common import Graph, GraphInputError
from .runner import validate_snapshot
from .surprise import score
from .textsim import btm_unique
from .traversal import rank_paths


def _scope(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    meta = payload.get("snapshot", {}).get("meta", {}) if isinstance(payload.get("snapshot"), dict) else {}
    scope_id = payload.get("scope_id") or meta.get("scope_id")
    snapshot_id = payload.get("snapshot_id") or meta.get("snapshot_id")
    if scope_id is not None and (not isinstance(scope_id, str) or not scope_id.strip()):
        raise GraphInputError("scope_id must be a non-empty string when provided")
    if snapshot_id is not None and (not isinstance(snapshot_id, str) or not snapshot_id.strip()):
        raise GraphInputError("snapshot_id must be a non-empty string when provided")
    if meta.get("scope_id") and payload.get("scope_id") and meta["scope_id"] != payload["scope_id"]:
        raise GraphInputError("scope_id does not match the scope bound to the supplied graph snapshot")
    if meta.get("snapshot_id") and payload.get("snapshot_id") and meta["snapshot_id"] != payload["snapshot_id"]:
        raise GraphInputError("snapshot_id does not match the supplied graph snapshot")
    return scope_id, snapshot_id


def backtest_relationship_methods(payload: dict[str, Any], *, budget_seconds: float | None = None) -> dict[str, Any]:
    snapshot = payload.get("snapshot")
    validate_snapshot(snapshot)
    scope_id, snapshot_id = _scope(payload)
    evaluation = evaluate(Graph(snapshot["nodes"], snapshot["edges"], snapshot.get("meta")),
                          payload.get("cutoff"), seed=payload.get("seed", 7), budget_seconds=budget_seconds)
    return {"schema_version": "eureka.graph-backtest-result.v1",
            "capability_id": "graph.backtest_relationship_methods",
            "status": "insufficient_data" if evaluation.get("error") else "completed_evaluation",
            "scope_id": scope_id, "snapshot_id": snapshot_id, "evaluation": evaluation}


def score_bayesian_surprise(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GraphInputError("request must be an object")
    scope_id, snapshot_id = _scope(payload)
    claims = payload.get("claims") if isinstance(payload, dict) else None
    if not isinstance(claims, list) or not 1 <= len(claims) <= 1000:
        raise GraphInputError("claims must contain 1..1,000 probability records")
    scores = []
    for index, row in enumerate(claims):
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
                or len(row["id"]) > 256 or not isinstance(row.get("claim"), str) or len(row["claim"]) > 20_000):
            raise GraphInputError(f"claims[{index}] needs string id and claim fields")
        for key in ("prior", "posterior"):
            values = row.get(key)
            if not isinstance(values, list) or not 1 <= len(values) <= 100:
                raise GraphInputError(f"claims[{index}].{key} must contain 1..100 probabilities")
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) or not 0 <= value <= 1 for value in values):
                raise GraphInputError(f"claims[{index}].{key} values must be finite probabilities in [0, 1]")
        scores.append({"id": row["id"], "claim": row["claim"], **score(row["prior"], row["posterior"])})
    return {"schema_version": "eureka.graph-surprise-result.v1",
            "capability_id": "graph.score_bayesian_surprise", "status": "completed_analysis",
            "scope_id": scope_id, "snapshot_id": snapshot_id, "scores": scores,
            "limitations": ["Probabilities are supplied by the caller; this task does not query a model or retrieve evidence.",
                            "Surprise and entropy prioritize review; neither establishes truth."]}


def compare_bidirectional_topics(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GraphInputError("request must be an object")
    scope_id, snapshot_id = _scope(payload)
    texts_a, texts_b = payload.get("texts_a"), payload.get("texts_b")
    if not isinstance(texts_a, list) or not isinstance(texts_b, list):
        raise GraphInputError("texts_a and texts_b must be arrays")
    if not texts_a or not texts_b or len(texts_a) > 2500 or len(texts_b) > 2500:
        raise GraphInputError("each BTM corpus must contain 1..2,500 documents")
    if any(not isinstance(text, str) or not text.strip() or len(text) > 200_000 for text in texts_a + texts_b):
        raise GraphInputError("BTM documents must be non-empty strings no longer than 200,000 characters")
    k, tau, seeds = payload.get("k", 6), payload.get("tau", .18), payload.get("seeds", [1, 2, 3])
    if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 100:
        raise GraphInputError("k must be an integer from 1 to 100")
    if isinstance(tau, bool) or not isinstance(tau, (int, float)) or not math.isfinite(tau) or not 0 <= tau <= 1:
        raise GraphInputError("tau must be a finite number in [0, 1]")
    if not isinstance(seeds, list) or not 1 <= len(seeds) <= 50 or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds):
        raise GraphInputError("seeds must contain 1..50 integer random seeds")
    unique, topics = btm_unique(texts_a, texts_b, k=k, tau=tau, seeds=tuple(seeds))
    return {"schema_version": "eureka.graph-btm-result.v1",
            "capability_id": "graph.compare_bidirectional_topics", "status": "completed_analysis",
            "scope_id": scope_id, "snapshot_id": snapshot_id,
            "unique_document_indexes": unique, "unique_topics": topics,
            "limitations": ["Topic outliers depend on corpus, tokenization, clustering seeds, k, and tau; they are not validated opportunities."]}


def rank_evidence_paths(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GraphInputError("request must be an object")
    scope_id, snapshot_id = _scope(payload)
    paths = payload.get("paths") if isinstance(payload, dict) else None
    if not isinstance(paths, list) or len(paths) > 5000:
        raise GraphInputError("paths must contain at most 5,000 host-retrieved path records")
    for index, row in enumerate(paths):
        if not isinstance(row, dict) or not isinstance(row.get("nodes"), list) or not isinstance(row.get("edges"), list):
            raise GraphInputError(f"paths[{index}] must contain node and edge arrays")
        if any(not isinstance(node, dict) or not isinstance(node.get("name"), str) for node in row["nodes"]):
            raise GraphInputError(f"paths[{index}].nodes need string name fields")
        if any(not isinstance(edge, dict) for edge in row["edges"]):
            raise GraphInputError(f"paths[{index}].edges must contain objects")
    return {"schema_version": "eureka.graph-traversal-result.v1",
            "capability_id": "graph.rank_evidence_paths", "status": "completed_analysis",
            "scope_id": scope_id, "snapshot_id": snapshot_id,
            "paths": rank_paths(paths),
            "limitations": ["This task ranks host-supplied paths; it does not query the graph or infer missing evidence."]}
