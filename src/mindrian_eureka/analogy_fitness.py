"""Local SAPPhIRE-layer fitness assessment for selected analogy candidates.

This is a standalone implementation of the reviewed Analogies fitness rubric.
It uses an operator-supplied local encoder, keeps structure separate from
evidence validation, and does not retrieve remote analogies.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any

import numpy as np

from .opportunity_pairs.encoders import SentenceTransformerEncoder

LAYERS = ("state_change", "action", "parts", "phenomenon", "input", "real_effect", "effect")
BAND_RANK = {"none": 0, "surface": 1, "behavioral": 2, "structural": 3, "deep": 4}
BANDS = {"none": (0.0, 0.0), "surface": (0.1, 0.2), "behavioral": (0.3, 0.5), "structural": (0.6, 0.8), "deep": (0.8, 1.0)}
BEHAVIORAL = ("state_change", "action", "phenomenon")
STRUCTURAL = ("state_change", "action", "phenomenon", "real_effect")


class AnalogyInputError(ValueError):
    pass


class AnalogyUnavailable(RuntimeError):
    pass


def _group(item: Any, label: str) -> dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("structure"), dict):
        raise AnalogyInputError(f"{label} needs a structure object")
    structure = item["structure"]
    if set(structure) != set(LAYERS):
        raise AnalogyInputError(f"{label}.structure must contain exactly: {', '.join(LAYERS)}")
    for layer, value in structure.items():
        if not isinstance(value, str) or len(value) > 5000:
            raise AnalogyInputError(f"{label}.structure.{layer} must be text no longer than 5000 characters")
    if not any(structure.values()):
        raise AnalogyInputError(f"{label}.structure cannot be entirely empty")
    evidence_refs = item.get("evidence_refs")
    if not isinstance(evidence_refs, dict) or set(evidence_refs) != set(LAYERS):
        raise AnalogyInputError(f"{label}.evidence_refs must contain one array for every structural layer")
    for layer, refs in evidence_refs.items():
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise AnalogyInputError(f"{label}.evidence_refs.{layer} must be an array of non-empty claim/source IDs")
        if structure[layer].strip() and not refs:
            raise AnalogyInputError(f"{label}.structure.{layer} needs at least one evidence_refs entry")
    if not isinstance(item.get("id"), str) or not item["id"].strip():
        raise AnalogyInputError(f"{label}.id is required")
    if not isinstance(item.get("source_ref"), str) or not item["source_ref"].strip():
        raise AnalogyInputError(f"{label}.source_ref is required")
    description = item.get("description", "")
    if not isinstance(description, str) or len(description) > 20_000:
        raise AnalogyInputError(f"{label}.description must be text no longer than 20000 characters")
    if not any(structure.values()) and not description:
        raise AnalogyInputError(f"{label} needs a source description")
    return item


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))


def _quantile(values: list[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q, method="linear"))


def _empirical_percentile(values: list[float], value: float) -> float:
    """Empirical mid-rank percentile, matching the reviewed batch rubric."""
    if not values:
        return 0.0
    less = sum(candidate < value for candidate in values)
    equal = sum(candidate == value for candidate in values)
    return (less + 0.5 * equal) / len(values)


def _bounded_env_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if not math.isfinite(value):
        value = default
    return float(np.clip(value, 0.0, 1.0))


def _band(corresponding: set[str]) -> str:
    if "state_change" not in corresponding:
        return "none"
    if set(LAYERS).issubset(corresponding):
        return "deep"
    if set(STRUCTURAL).issubset(corresponding):
        return "structural"
    if set(BEHAVIORAL).issubset(corresponding):
        return "behavioral"
    return "surface"


def assess_analogy_fitness(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise AnalogyInputError("input must be an object")
    target = _group(document.get("target"), "target")
    candidates = document.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 100:
        raise AnalogyInputError("candidates must contain 1..100 source-linked structures")
    candidates = [_group(row, f"candidates[{i}]") for i, row in enumerate(candidates)]
    ids = [row["id"] for row in candidates]
    if len(set(ids)) != len(ids) or target["id"] in ids:
        raise AnalogyInputError("candidate IDs must be unique and must differ from target.id")
    model_path = os.environ.get("MINDRIAN_EUREKA_ANALOGY_MODEL_PATH") or os.environ.get("MINDRIAN_EUREKA_RS_MODEL_PATH")
    if not model_path:
        raise AnalogyUnavailable("A local sentence-transformer model is required; set MINDRIAN_EUREKA_ANALOGY_MODEL_PATH or MINDRIAN_EUREKA_RS_MODEL_PATH")

    text_pairs = []
    for row in [target, *candidates]:
        text_pairs.append(row.get("description", "") or " ".join(v for v in row["structure"].values() if v.strip()))
    layer_texts = [target["structure"][layer] for layer in LAYERS]
    for candidate in candidates:
        layer_texts.extend(candidate["structure"][layer] for layer in LAYERS)
    encoder = SentenceTransformerEncoder(model_path, allow_download=False)
    vectors = encoder.encode([*text_pairs, *layer_texts])
    text_vectors = vectors[:len(text_pairs)]
    layer_vectors = vectors[len(text_pairs):]
    target_layers = layer_vectors[:len(LAYERS)]
    raw_candidates = []
    offset = len(LAYERS)
    for index, candidate in enumerate(candidates):
        candidate_layers = layer_vectors[offset:offset + len(LAYERS)]
        offset += len(LAYERS)
        cosines = {}
        for i, layer in enumerate(LAYERS):
            a, b = target["structure"][layer].strip(), candidate["structure"][layer].strip()
            cosines[layer] = _cos(target_layers[i], candidate_layers[i]) if a and b else None
        raw_candidates.append({"candidate": candidate, "layer_cosines": cosines,
                               "text_similarity": _cos(text_vectors[0], text_vectors[index + 1])})

    fixed_threshold = _bounded_env_float("MINDRIAN_ANALOGY_LAYER_THRESHOLD", 0.5)
    text_weight = _bounded_env_float("MINDRIAN_ANALOGY_TEXT_WEIGHT", 0.5)
    restatement_floor = _bounded_env_float("MINDRIAN_ANALOGY_RESTATEMENT_FLOOR", 0.8)
    restatement_min_text = 0.5
    restatement_percentile = 0.9
    abs_floor = _bounded_env_float("MINDRIAN_ANALOGY_ABS_FLOOR", 0.3)
    thresholds: dict[str, float] = {}
    mode = "fixed_small_pool"
    if len(candidates) >= 5:
        mode = "corpus_relative_p75"
        for layer in LAYERS:
            values = [row["layer_cosines"][layer] for row in raw_candidates if row["layer_cosines"][layer] is not None]
            thresholds[layer] = (max(abs_floor, min(0.9, _quantile(values, 0.75)))
                                 if len(values) >= 5 else fixed_threshold)
    else:
        thresholds = {layer: fixed_threshold for layer in LAYERS}

    text_scores = [row["text_similarity"] for row in raw_candidates]
    output = []
    for row in raw_candidates:
        corresponding = {layer for layer, score in row["layer_cosines"].items()
                         if score is not None and score >= thresholds[layer]}
        band = _band(corresponding)
        corresponding_scores = [row["layer_cosines"][layer] for layer in corresponding]
        band_low, band_high = BANDS[band]
        structural_score = band_low + (band_high - band_low) * (sum(corresponding_scores) / len(corresponding_scores) if corresponding_scores else 0.0)
        text_pct = _empirical_percentile(text_scores, row["text_similarity"])
        thin_band = band_rank(band) <= BAND_RANK["behavioral"]
        restatement = (thin_band and row["text_similarity"] >= restatement_min_text and text_pct >= restatement_percentile
                       if mode == "corpus_relative_p75"
                       else thin_band and row["text_similarity"] >= restatement_floor)
        fused_score = text_weight * row["text_similarity"] + (1.0 - text_weight) * structural_score
        candidate = row["candidate"]
        output.append({"candidate_id": candidate["id"], "source": {"id": candidate["id"], "source_ref": candidate["source_ref"]},
                       "target": {"id": target["id"], "source_ref": target["source_ref"]},
                       "band": band, "structural_fitness": round(structural_score, 4),
                       "fused_fitness": round(fused_score, 4),
                       "corresponding_layers": [layer for layer in LAYERS if layer in corresponding],
                       "layer_cosines": row["layer_cosines"], "derived_layer_thresholds": thresholds,
                       "layer_source_evidence": {layer: {"target_expression": target["structure"][layer], "target_refs": target["evidence_refs"][layer], "candidate_expression": candidate["structure"][layer], "candidate_refs": candidate["evidence_refs"][layer]} for layer in LAYERS if target["structure"][layer].strip() or candidate["structure"][layer].strip()},
                       "text_similarity": round(row["text_similarity"], 4), "text_similarity_percentile": round(text_pct, 4),
                       "restatement_warning": bool(restatement),
                       "interpretation": "Candidate structural fit for review; not evidence that the source mechanism will transfer."})
    _rank_candidates(output)
    return {"schema_version": "eureka.analogy-fitness-result.v1", "capability_id": "analogy.assess_structural_fitness",
            "status": "completed_experimental", "scope_id": document.get("scope_id"),
            "snapshot_id": document.get("snapshot_id"),
            "target": {"id": target["id"], "source_ref": target["source_ref"]}, "candidate_count": len(output), "candidates": output,
            "provenance": {"method": "two-leg text/structural fitness; seven-layer SAPPhIRE cosine correspondence; fixed threshold for <5 candidates, per-layer P75 thresholds otherwise; band-first, fused-score ranking with restatement lift", "encoder": "local sentence-transformer", "model_path": model_path, "threshold_mode": mode, "scoring_parameters": {"text_weight": text_weight, "fixed_layer_threshold": fixed_threshold, "absolute_threshold_floor": abs_floor, "layer_quantile": 0.75, "restatement_percentile": restatement_percentile, "restatement_min_text": restatement_min_text, "fixed_restatement_threshold": restatement_floor}, "computed_at": datetime.now(timezone.utc).isoformat()},
            "limitations": ["Embedding similarities and layer bands are heuristics; thresholds are not calibrated against human-rated transfer cases.", "A structural match generates a candidate inference; use SME mapping plus source evidence, counterevidence, and boundary checks before acting.", "Restatement warning is a within-pool text-similarity heuristic, not novelty detection.", "Only supplied descriptions and structures were analyzed; no external research was fetched."]}


def band_rank(band: str) -> int:
    return BAND_RANK[band]


def _rank_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Band-first ranking with the source restatement-lift rule."""
    rows.sort(key=lambda row: (-BAND_RANK[row["band"]], -row["fused_fitness"], row["candidate_id"]))
    if len(rows) > 1 and rows[0]["restatement_warning"]:
        alternative = next((i for i, row in enumerate(rows) if not row["restatement_warning"]), None)
        if alternative is not None:
            rows.insert(0, rows.pop(alternative))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows
