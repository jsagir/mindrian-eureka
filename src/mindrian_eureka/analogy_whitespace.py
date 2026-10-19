"""Analogy-seeded whitespace analysis over a host-supplied vector snapshot.

This is a read-only, source-derived local evaluation of the LATEST analogy
whitespace routine. It accepts data, not a MindrianOS room path.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import numpy as np


class WhitespaceInputError(ValueError):
    pass


FIXED_GAP_STRONG = 0.6
FIXED_GAP_MODERATE = 0.4
FIXED_BRAIN_SUPPORT = 0.3


def _percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    less = sum(item < value for item in values)
    equal = sum(item == value for item in values)
    return (less + 0.5 * equal) / len(values)


def _zscore(values: list[float], value: float) -> float:
    if len(values) < 2:
        return 0.0
    mean = float(np.mean(values))
    std = float(np.std(values))
    return (value - mean) / std if std else 0.0


def _finite_vector(value: Any, label: str) -> np.ndarray:
    if not isinstance(value, list) or not value or len(value) > 20_000:
        raise WhitespaceInputError(f"{label} must be a non-empty numeric vector")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not np.isfinite(x) for x in value):
        raise WhitespaceInputError(f"{label} must contain finite numbers")
    return np.asarray(value, dtype=np.float64)


def _hsi_candidates(hsi_pairs: list[dict], artifacts: list[dict], requested_mode: str) -> tuple[list[dict], dict]:
    sections = {row["id"]: row.get("section", "") for row in artifacts}
    cross = []
    for pair in hsi_pairs:
        left, right = pair.get("left_id"), pair.get("right_id")
        semantic, lexical = pair.get("semantic_sim"), pair.get("lsa_sim")
        if left not in sections or right not in sections or left == right or sections[left] == sections[right]:
            continue
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) for v in (semantic, lexical)):
            continue
        cross.append((left, right, sections[left], sections[right], float(semantic), float(lexical)))
    use_percentile = requested_mode == "percentile" and len(cross) >= 8
    if use_percentile:
        semantic_cut = float(np.quantile([row[4] for row in cross], .75))
        lexical_cut = float(np.quantile([row[5] for row in cross], .25))
    else:
        semantic_cut, lexical_cut = .6, .3
    candidates = []
    for left, right, left_section, right_section, semantic, lexical in cross:
        hit = semantic >= semantic_cut and lexical <= lexical_cut if use_percentile else semantic > semantic_cut and lexical < lexical_cut
        if hit:
            candidates.append({"source_id": left, "target_id": right,
                               "source_section": left_section, "target_section": right_section,
                               "analogy_distance": "cross-domain", "semantic_sim": semantic, "lsa_sim": lexical})
    return candidates, {"hsi_mode": "percentile" if use_percentile else "fixed",
                        "hsi_semantic_cut": semantic_cut, "hsi_lsa_cut": lexical_cut,
                        "hsi_cross_section_pairs": len(cross)}


def analyze(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise WhitespaceInputError("input must be an object")
    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    snapshot_id = document.get("snapshot_id")
    scope_id = document.get("scope_id")
    mode = document.get("mode", "percentile")
    min_corpus = document.get("min_corpus", 5)
    if mode not in {"percentile", "fixed"}:
        raise WhitespaceInputError("mode must be percentile or fixed")
    if isinstance(min_corpus, bool) or not isinstance(min_corpus, int) or not 2 <= min_corpus <= 10_000:
        raise WhitespaceInputError("min_corpus must be an integer from 2 to 10,000")
    artifacts = document.get("artifacts")
    baselines = document.get("baselines")
    edges = document.get("analogy_edges", [])
    hsi_pairs = document.get("hsi_pairs", [])
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 25_000:
        raise WhitespaceInputError("artifacts must contain 1..25,000 embedding records")
    if not isinstance(baselines, list) or not 1 <= len(baselines) <= 5_000:
        raise WhitespaceInputError("baselines must contain 1..5,000 framework vectors")
    if not isinstance(edges, list) or not isinstance(hsi_pairs, list):
        raise WhitespaceInputError("analogy_edges and hsi_pairs must be arrays")
    if len(edges) > 5_000 or len(hsi_pairs) > 50_000:
        raise WhitespaceInputError("input exceeds the 5,000 edge or 50,000 HSI pair limit")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] for row in artifacts):
        raise WhitespaceInputError("each artifact needs a stable id")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] for row in baselines):
        raise WhitespaceInputError("each baseline needs a stable id")
    artifact_ids = [row["id"] for row in artifacts]
    baseline_ids = [row["id"] for row in baselines]
    if len(set(artifact_ids)) != len(artifact_ids) or len(set(baseline_ids)) != len(baseline_ids):
        raise WhitespaceInputError("artifact and baseline IDs must be unique within their collections")
    room = [_finite_vector(row.get("vector"), f"artifact {row['id']}.vector") for row in artifacts]
    brain = [_finite_vector(row.get("vector"), f"baseline {row['id']}.vector") for row in baselines]
    dimensions = {len(row) for row in room + brain}
    if len(dimensions) != 1:
        raise WhitespaceInputError("artifact and baseline vectors must have one shared dimension/model")
    if not edges:
        edges, hsi_info = _hsi_candidates(hsi_pairs, artifacts, mode)
        source = "hsi-fallback"
    else:
        hsi_info, source = None, "host-analogy-edges"
    if len(artifacts) < 3 or not edges:
        return {"schema_version":"eureka.analogy-whitespace-result.v1",
                "capability_id":"analogy.discover_transfer_whitespace","status":"insufficient_input",
                "capability_version":"0.1.0","scope_id":scope_id,"snapshot_id":snapshot_id,"input_fingerprint":fingerprint,
                "run_config":{"mode":mode,"min_corpus":min_corpus},
                "metadata":{"source":source,"analogies_checked":len(edges),"zones_found":0,
                            "note":"No qualifying analogy edges or fewer than three artifact embeddings."},"zones":[],
                "limitations":["Whitespace is a room-relative lead, not evidence of novelty or a validated opportunity."]}

    room_matrix, brain_matrix = np.vstack(room), np.vstack(brain)
    exclude_endpoints = mode == "percentile"
    if exclude_endpoints:
        room_norm = np.linalg.norm(room_matrix, axis=1, keepdims=True); room_norm[room_norm == 0] = 1
        brain_norm = np.linalg.norm(brain_matrix, axis=1, keepdims=True); brain_norm[brain_norm == 0] = 1
        room_matrix, brain_matrix = room_matrix / room_norm, brain_matrix / brain_norm
    room_cosine, brain_cosine = room_matrix, brain_matrix
    if not exclude_endpoints:
        room_norm = np.linalg.norm(room_matrix, axis=1, keepdims=True); room_norm[room_norm == 0] = 1
        brain_norm = np.linalg.norm(brain_matrix, axis=1, keepdims=True); brain_norm[brain_norm == 0] = 1
        room_cosine, brain_cosine = room_matrix / room_norm, brain_matrix / brain_norm
    index = {artifact_id:i for i, artifact_id in enumerate(artifact_ids)}
    records, skipped, seen = [], {"missing_embedding":0,"self_edge":0,"duplicate":0,"over_cap":0}, set()
    for edge in edges:
        if len(records) >= 5000:
            skipped["over_cap"] += 1; continue
        if not isinstance(edge, dict):
            continue
        source_id, target_id = edge.get("source_id"), edge.get("target_id")
        if source_id not in index or target_id not in index:
            skipped["missing_embedding"] += 1; continue
        si, ti = index[source_id], index[target_id]
        if exclude_endpoints:
            if si == ti:
                skipped["self_edge"] += 1; continue
            key = tuple(sorted((si,ti)))
            if key in seen:
                skipped["duplicate"] += 1; continue
            seen.add(key)
        centroid = (room_matrix[si] + room_matrix[ti]) / 2
        centroid_norm = float(np.linalg.norm(centroid))
        if centroid_norm: centroid /= centroid_norm
        brain_sims = brain_cosine @ centroid
        nearest_idx = np.argsort(-brain_sims, kind="stable")[:min(3,len(brain_sims))]
        room_sims = room_cosine @ centroid
        nearest_other = None
        if exclude_endpoints and len(room_sims) > 2:
            room_sims[si] = room_sims[ti] = -np.inf
            best = int(np.argmax(room_sims)); max_room = float(room_sims[best])
            nearest_other = {"artifact":artifact_ids[best],"title":artifacts[best].get("title",artifact_ids[best]),
                             "similarity_to_centroid":round(max_room,4)}
        else:
            max_room = float(np.max(room_sims))
        records.append({"edge":edge,"source_id":source_id,"target_id":target_id,"source_idx":si,"target_idx":ti,
                        "nearest_brain":[baselines[int(i)].get("name",baselines[int(i)].get("title",baseline_ids[int(i)])) for i in nearest_idx],
                        "brain_sims":[float(brain_sims[i]) for i in nearest_idx],
                        "brain_mean":float(np.mean(brain_sims[nearest_idx])),"gap":1-max_room,"nearest_other":nearest_other})
    gaps=[row["gap"] for row in records]; brain_means=[row["brain_mean"] for row in records]
    percentile_mode = mode=="percentile" and len(records)>=min_corpus
    zones=[]
    for n,row in enumerate(records,1):
        gap_pct=_percentile(gaps,row["gap"]); brain_pct=_percentile(brain_means,row["brain_mean"])
        if percentile_mode:
            signal="strong" if gap_pct>=.80 and brain_pct>=.50 else "moderate" if gap_pct>=.50 else "weak"
        else:
            signal="strong" if row["gap"]>.60 and row["brain_mean"]>.30 else "moderate" if row["gap"]>.40 else "weak"
        edge=row["edge"]; source_id=row["source_id"]; target_id=row["target_id"]
        transfer=edge.get("analogy_distance","cross-domain")
        if source=="hsi-fallback":
            diff=float(edge.get("semantic_sim",0))-float(edge.get("lsa_sim",0))
            transfer="cross-domain" if diff>.5 else "semantic" if diff>.3 else "structural"
        else:
            transfer={"near":"structural","far":"semantic"}.get(transfer,"cross-domain")
        src=artifacts[row["source_idx"]]; tgt=artifacts[row["target_idx"]]
        nearest=row["nearest_brain"]
        zones.append({"zone_id":f"ANA-WS-{n:03d}","source_artifact":source_id,"target_artifact":target_id,
                      "source_section":edge.get("source_section",src.get("section","")),"target_section":edge.get("target_section",tgt.get("section","")),
                      "transfer_type":transfer,"nearest_brain_frameworks":nearest,"articulation_gap":round(row["gap"],4),
                      "gap_signal":signal,"hypothesis":f"The analogy between [{src.get('title',source_id)}] and [{tgt.get('title',target_id)}] may use [{nearest[0] if nearest else 'unknown'}], but the transfer mechanism is not articulated in this snapshot.",
                      "articulation_gap_percentile":round(gap_pct,4),"articulation_gap_z":round(_zscore(gaps,row["gap"]),4),
                      "brain_mean_similarity":round(row["brain_mean"],4),"nearest_brain_similarities":[round(x,4) for x in row["brain_sims"]],
                      "endpoints_excluded_from_gap":bool(exclude_endpoints and row["nearest_other"] is not None),
                      "nearest_other_artifact":row["nearest_other"],"structural_fitness":edge.get("structural_fitness"),
                      "verification":{"novelty_check":"not_checked","second_signal":"brain_nearest_neighbour_only"}})
    order={"strong":0,"moderate":1,"weak":2}
    zones.sort(key=lambda z:(order[z["gap_signal"]],-z["articulation_gap"],z["source_artifact"],z["target_artifact"]))
    return {"schema_version":"eureka.analogy-whitespace-result.v1","capability_id":"analogy.discover_transfer_whitespace",
            "capability_version":"0.1.0","status":"completed_analysis","scope_id":scope_id,"snapshot_id":snapshot_id,
            "input_fingerprint":fingerprint,"run_config":{"mode":mode,"min_corpus":min_corpus},"zones":zones,
            "metadata":{"timestamp":datetime.now(timezone.utc).isoformat(),"analogies_checked":len(edges),"pairs_scored":len(records),
                        "zones_found":len(zones),"source":source,"mode":"percentile" if percentile_mode else "fixed",
                        "requested_mode":mode,"pairs_skipped":skipped,"embedding_dim":int(room_matrix.shape[1]),
                        "room_artifacts_embedded":len(room),"brain_baselines":len(brain),"endpoints_excluded_from_gap":exclude_endpoints,
                        "hsi_thresholds":hsi_info,"parameters":{"min_corpus":min_corpus,"gap_strong_percentile":.80,
                        "gap_moderate_percentile":.50,"brain_support_percentile":.50,"fixed_gap_strong":FIXED_GAP_STRONG,
                        "fixed_gap_moderate":FIXED_GAP_MODERATE,"fixed_brain_support":FIXED_BRAIN_SUPPORT},
                        "note_fallback":"fewer than min_corpus pairs scored; fixed cut-offs used" if mode=="percentile" and not percentile_mode else None},
            "limitations":["The source algorithm is an experimental local evaluation port; source ownership and redistribution rights remain unresolved.",
                           "A sparse room-space articulation signal plus a nearby supplied baseline is not external novelty evidence.",
                           "Analogy edges and vectors are caller supplied; no graph, room path, literature, or market service was queried."]}
