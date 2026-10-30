"""RS-seeded downstream whitespace analysis over host-supplied projections."""

from __future__ import annotations

import hashlib
import json
import math
import re

import numpy as np

from .contracts import ContractError


_WORD = re.compile(r"(?u)\b\w\w+\b")
_SIGNAL_ORDER = {"strong": 0, "moderate": 1, "weak": 2}


def _rows(payload: dict, key: str, maximum: int) -> list[dict]:
    rows = payload.get(key)
    if not isinstance(rows, list) or len(rows) > maximum:
        raise ContractError(f"{key} must be an array with at most {maximum} records")
    return rows


def _vector(record: dict, label: str, dimension: int | None = None) -> np.ndarray:
    values = record.get("vector")
    if not isinstance(values, list) or not values or len(values) > 4096:
        raise ContractError(f"{label}.vector must be a non-empty array of at most 4096 numbers")
    if dimension is not None and len(values) != dimension:
        raise ContractError("artifact and baseline vectors must share one embedding dimension/model")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
           for value in values):
        raise ContractError(f"{label}.vector must contain finite numbers")
    return np.asarray(values, dtype=np.float64)


def _cosine(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = np.atleast_2d(np.asarray(left, dtype=np.float64))
    right = np.atleast_2d(np.asarray(right, dtype=np.float64))
    left_norm = np.linalg.norm(left, axis=1, keepdims=True)
    right_norm = np.linalg.norm(right, axis=1, keepdims=True)
    left_norm[left_norm < 1e-12] = 1.0
    right_norm[right_norm < 1e-12] = 1.0
    return (left / left_norm) @ (right / right_norm).T


def _section_coverage(section_vectors: np.ndarray, baseline_vectors: np.ndarray, k: int = 3):
    centroid = np.mean(section_vectors, axis=0).reshape(1, -1)
    similarities = _cosine(centroid, baseline_vectors)[0]
    indices = np.argsort(-similarities, kind="stable")[:min(k, len(baseline_vectors))]
    best_by_framework = _cosine(section_vectors, baseline_vectors[indices]).max(axis=0)
    return float(np.mean(best_by_framework)), indices, similarities[indices]


def _vocab_overlap(section_text: str, framework_name: str) -> float | None:
    framework_words = set(_WORD.findall(framework_name.lower()))
    if not framework_words:
        return None
    section_words = set(_WORD.findall(section_text.lower()))
    return len(framework_words & section_words) / len(framework_words)


def _classify(coverage: float, percentile: float | None) -> str:
    if percentile is not None:
        return "strong" if percentile <= .25 else "moderate" if percentile <= .5 else "weak"
    return "strong" if coverage < .3 else "moderate" if coverage < .5 else "weak"


def discover_rs_whitespace(payload: dict) -> dict:
    """Find low-framework-coverage sections downstream of RS bottlenecks."""
    artifacts = _rows(payload, "artifacts", 2500)
    frameworks = _rows(payload, "baseline_frameworks", 1000)
    salients = _rows(payload, "reverse_salients", 500)
    if not artifacts or not frameworks:
        raise ContractError("artifacts and baseline_frameworks must both be non-empty")
    artifact_ids, framework_ids = {}, {}
    for item in artifacts:
        item_id, section = item.get("id"), item.get("section")
        if not isinstance(item_id, str) or not item_id or item_id in artifact_ids:
            raise ContractError("artifact IDs must be unique non-empty strings")
        if not isinstance(section, str) or not section:
            raise ContractError(f"artifact {item_id!r} needs a non-empty section")
        artifact_ids[item_id] = item
    for item in frameworks:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in framework_ids:
            raise ContractError("baseline framework IDs must be unique non-empty strings")
        framework_ids[item_id] = item
    dimension = None
    artifact_vectors = []
    for item in artifacts:
        vec = _vector(item, f"artifact {item['id']}", dimension)
        dimension = len(vec)
        artifact_vectors.append(vec)
    baseline_vectors = []
    for item in frameworks:
        vec = _vector(item, f"baseline framework {item['id']}", dimension)
        baseline_vectors.append(vec)
    room_matrix, baseline_matrix = np.vstack(artifact_vectors), np.vstack(baseline_vectors)
    sections: dict[str, list[int]] = {}
    for index, item in enumerate(artifacts):
        sections.setdefault(item["section"], []).append(index)
    reference_coverage = {
        section: _section_coverage(room_matrix[indices], baseline_matrix)[0]
        for section, indices in sections.items()
    }
    signal_method = payload.get("signal_method", "percentile")
    use_percentile = signal_method == "percentile" and len(reference_coverage) >= 4
    reference_values = np.asarray(list(reference_coverage.values()), dtype=np.float64)
    seen_sections, zones = set(), []
    checked = 0
    for salient in salients:
        checked += 1
        target, source = salient.get("target_section", ""), salient.get("source_section", "")
        if not target or target in seen_sections:
            continue
        seen_sections.add(target)
        indices = sections.get(target, [])
        if not indices:
            continue
        coverage, nearest_indices, nearest_sims = _section_coverage(room_matrix[indices], baseline_matrix)
        nearest = [frameworks[int(index)] for index in nearest_indices]
        coverage_percentile = (float(np.mean(reference_values <= coverage)) if use_percentile else None)
        signal = _classify(coverage, coverage_percentile)
        section_text = " ".join(
            " ".join((str(artifacts[index].get("title") or ""), str(artifacts[index].get("text") or "")))
            for index in indices
        )
        overlap = _vocab_overlap(section_text, str(nearest[0].get("name") or nearest[0].get("label") or ""))
        opportunity_id = salient.get("opportunity_id") or salient.get("id", "")
        source_trail = [{"source": "host.reverse_salients", "source_id": opportunity_id,
                         "source_ref": salient.get("source_ref")}]
        source_trail.extend({"source": "host.room_artifact", "artifact_id": artifacts[index]["id"],
                             "source_ref": artifacts[index].get("source_ref")}
                            for index in indices[:3])
        source_trail.append({"source": "host.framework_baseline", "source_id": nearest[0]["id"],
                             "source_ref": nearest[0].get("source_ref")})
        zones.append({
            "zone_id": f"RS-WS-{len(zones)+1:03d}",
            "bottleneck": {"opportunity_id": opportunity_id, "source_section": source,
                           "target_section": target},
            "downstream_section": target,
            "nearest_brain_frameworks": [str(item.get("name") or item.get("label") or item["id"]) for item in nearest],
            "nearest_framework_refs": [{"id": item["id"], "name": item.get("name") or item.get("label") or item["id"],
                                         "cosine_similarity": round(float(sim), 4)}
                                        for item, sim in zip(nearest, nearest_sims)],
            "section_coverage": round(coverage, 4), "gap_signal": signal,
            "hypothesis": (f"Bottleneck in [{source}] blocks insight into "
                           f"{nearest[0].get('name') or nearest[0].get('label') or 'unknown'} for [{target}]"),
            "coverage_percentile": None if coverage_percentile is None else round(coverage_percentile, 4),
            "signal_method": "percentile_among_sections" if use_percentile else "fixed_cutoffs",
            "bottleneck_score": salient.get("differential_score", salient.get("score")),
            "second_signal": {"method": "framework_vocabulary_in_section_text",
                              "overlap": None if overlap is None else round(overlap, 4),
                              "confirmed": None if overlap is None else overlap < .5},
            "novelty_check": {"status": "in_room_check_only", "external_literature": "not_run"},
            "source_trail": source_trail,
        })
    zones.sort(key=lambda zone: (_SIGNAL_ORDER.get(zone["gap_signal"], 3), zone["section_coverage"], zone["zone_id"]))
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "eureka.hsi-rs-whitespace.v1", "capability_id": "portfolio.discover_rs_whitespace",
        "capability_version": "0.1.0", "status": "completed_rs_seeded_whitespace_scan",
        "scope": {"scope_id": payload.get("scope_id"), "snapshot_id": payload.get("snapshot_id")},
        "input_fingerprint": digest,
        "metadata": {"bottlenecks_checked": checked, "zones_found": len(zones),
                     "signal_method": "percentile" if use_percentile else "fixed",
                     "sections_in_reference": len(reference_coverage), "embedding_model": payload.get("embedding_model")},
        "zones": zones,
        "limitations": ["Uses only MindrianOS-supplied room artifacts, reverse salients, and framework vectors.",
                        "Low framework coverage and vocabulary overlap are room-relative signals, not validated bottlenecks or opportunities.",
                        "No external literature, demand, or novelty search is performed.",
                        "MindrianOS owns graph authorization, source resolution, Theo review, human qualification, and all writes."],
    }
