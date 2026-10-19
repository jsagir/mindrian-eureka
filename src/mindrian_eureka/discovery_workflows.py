"""Host-brokered discovery workflows for the remaining MindrianOS methods.

These functions operate only on caller-supplied, source-linked records. They do
not impersonate experts, fetch remote material, file room graph edges, or turn
heuristic signals into verified opportunities. The code provides explicit
workflow contracts around methods whose original packages depend on MindrianOS
services or remote model providers that are intentionally outside this repo.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


class WorkflowInputError(ValueError):
    """Invalid, incomplete, or untraceable workflow input."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 200_000) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise WorkflowInputError(f"{label} must be a string with {minimum}..{maximum} characters")
    return value.strip()


def _rows(value: Any, label: str, *, minimum: int = 1, maximum: int = 10_000) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise WorkflowInputError(f"{label} must contain {minimum}..{maximum} records")
    if any(not isinstance(row, dict) for row in value):
        raise WorkflowInputError(f"{label} entries must be objects")
    return value


def _unique_ids(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        item_id = row.get("id") or row.get("artifact_id") or row.get("source_id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise WorkflowInputError(f"{label}[{index}] needs a stable id")
        if item_id in result:
            raise WorkflowInputError(f"{label} contains duplicate id {item_id!r}")
        result[item_id] = row
    return result


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[\w'-]{3,}", text.casefold()) if token not in {
        "about", "after", "again", "against", "among", "because", "could", "their", "there", "these", "those", "through", "using", "which", "would", "with", "from", "into", "have", "this", "that", "they", "them", "were", "what", "when", "where", "will", "your", "than", "then", "also", "been", "being", "such", "more", "most", "some", "other", "only", "each", "both", "into", "over", "under", "very", "many", "much", "make", "made", "does", "doesn", "need", "needs", "used", "uses", "based", "result", "results", "study", "method", "methods", "system", "systems", "technology", "technology's", "research", "approach", "data", "using"
    }}


def _refs(row: dict[str, Any]) -> dict[str, Any]:
    source_ref = row.get("source_ref") or row.get("url") or row.get("path")
    return {key: row[key] for key in ("id", "artifact_id", "source_id", "title", "source_ref", "url", "path", "locator", "sha256") if key in row} | ({"source_ref": source_ref} if source_ref and "source_ref" not in row else {})


def portfolio_coverage(document: dict[str, Any]) -> dict[str, Any]:
    """Report represented and thin areas against an explicit supplied taxonomy.

    This is a coverage inventory. It does not infer market demand or assert
    commercial whitespace. Categories must be supplied by the host or user.
    """
    artifacts = _rows(document.get("artifacts"), "artifacts", maximum=25_000)
    taxonomy = document.get("taxonomy")
    if not isinstance(taxonomy, list) or not taxonomy:
        raise WorkflowInputError("taxonomy is required; a portfolio cannot establish market whitespace by itself")
    artifact_by_id = _unique_ids(artifacts, "artifacts")
    categories: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(taxonomy):
        if not isinstance(raw, dict):
            raise WorkflowInputError(f"taxonomy[{index}] must be an object")
        category_id = _text(raw.get("id"), f"taxonomy[{index}].id", maximum=256)
        if category_id in categories:
            raise WorkflowInputError(f"duplicate taxonomy id {category_id!r}")
        categories[category_id] = {**raw, "label": _text(raw.get("label", category_id), f"taxonomy[{index}].label", maximum=500)}
    membership: dict[str, set[str]] = defaultdict(set)
    for artifact_id, artifact in artifact_by_id.items():
        ids = artifact.get("category_ids", [])
        if not isinstance(ids, list) or any(not isinstance(cid, str) for cid in ids):
            raise WorkflowInputError(f"artifact {artifact_id!r}.category_ids must be an array of taxonomy ids")
        unknown = set(ids) - categories.keys()
        if unknown:
            raise WorkflowInputError(f"artifact {artifact_id!r} references unknown categories: {sorted(unknown)}")
        for category_id in set(ids):
            membership[category_id].add(artifact_id)
    counts = {category_id: len(membership[category_id]) for category_id in categories}
    total = len(artifact_by_id)
    ranked = sorted(categories, key=lambda cid: (counts[cid], str(categories[cid].get("label", "")).casefold(), cid))
    covered = [cid for cid in ranked if counts[cid] > 0]
    return {
        "schema_version": "eureka.portfolio-coverage-result.v1",
        "capability_id": "portfolio.inventory_taxonomy_coverage",
        "status": "completed_inventory",
        "scope_id": document.get("scope_id"),
        "snapshot_id": document.get("snapshot_id"),
        "input_counts": {"artifacts": total, "taxonomy_categories": len(categories)},
        "coverage": {"represented_categories": len(covered), "unrepresented_categories": len(ranked), "represented_fraction": len(covered) / len(ranked)},
        "areas": [{"category_id": cid, "label": categories[cid]["label"], "artifact_count": counts[cid], "artifact_refs": [_refs(artifact_by_id[aid]) for aid in sorted(membership[cid])]} for cid in ranked],
        "interpretation": "Unrepresented or thin categories are portfolio coverage observations only. They do not establish external demand, novelty, or commercial opportunity.",
        "provenance": {"method": "count supplied artifact-to-taxonomy assignments", "taxonomy_source": document.get("taxonomy_source"), "computed_at": _now()},
        "limitations": ["Taxonomy choice and category assignment quality govern the result.", "No embedding, PCA, UMAP, or market-demand inference was run.", "A category with few room artifacts may be intentional, irrelevant, or genuinely underexplored; this output cannot distinguish these cases."],
    }


def find_coverage_gaps(document: dict[str, Any]) -> dict[str, Any]:
    """Compose supplied-taxonomy inventory with an optional HSI-seeded room-relative scan."""
    coverage = portfolio_coverage(document)
    has_baselines = "baseline_frameworks" in document
    has_pairs = "hsi_pairs" in document
    if has_baselines != has_pairs:
        raise WorkflowInputError("baseline_frameworks and hsi_pairs must be supplied together")
    whitespace = discover_hsi_whitespace(document) if has_baselines else None
    return {
        "schema_version": "eureka.portfolio-coverage-gaps-result.v1",
        "capability_id": "portfolio.find_coverage_gaps",
        "status": "completed_coverage_and_whitespace_scan" if whitespace else "completed_taxonomy_coverage_scan",
        "scope_id": coverage.get("scope_id"), "snapshot_id": coverage.get("snapshot_id"),
        "coverage_inventory": coverage,
        "room_relative_whitespace": whitespace,
        "interpretation": "Coverage gaps and HSI regions are supplied-corpus observations. They do not prove demand, novelty, or commercial opportunity.",
        "limitations": [
            "Coverage depends on the user-supplied taxonomy and assignments.",
            "Optional whitespace results require host-generated HSI pairs and same-model artifact/baseline vectors.",
            "No embedding, external literature search, market-demand analysis, or graph write is performed by this workflow.",
        ],
    }


def discover_hsi_whitespace(document: dict[str, Any]) -> dict[str, Any]:
    """Find sparse room-relative regions between HSI-seeded artifact pairs.

    Vectors and baseline frameworks must be created/provided by the host using
    a shared embedding model. This function is deterministic and local; it does
    not embed content, search the literature, or establish market demand.
    """
    artifacts = _rows(document.get("artifacts"), "artifacts", maximum=25_000)
    by_id = _unique_ids(artifacts, "artifacts")
    baselines = _rows(document.get("baseline_frameworks"), "baseline_frameworks", maximum=5_000)
    pairs = _rows(document.get("hsi_pairs"), "hsi_pairs", maximum=50_000)
    baseline_ids = _unique_ids(baselines, "baseline_frameworks")

    import math
    import numpy as np

    def vector(row: dict[str, Any], label: str) -> list[float]:
        values = row.get("vector")
        if not isinstance(values, list) or not values or len(values) > 20_000:
            raise WorkflowInputError(f"{label}.vector must be a non-empty numeric array")
        out = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise WorkflowInputError(f"{label}.vector must contain finite numbers")
            out.append(float(value))
        return out

    av = {aid: vector(row, f"artifact {aid}") for aid, row in by_id.items()}
    bv = {bid: vector(row, f"baseline {bid}") for bid, row in baseline_ids.items()}
    dimensions = {len(v) for v in [*av.values(), *bv.values()]}
    if len(dimensions) != 1:
        raise WorkflowInputError("artifact and baseline vectors must share one embedding dimension/model")
    if len(av) < 2:
        raise WorkflowInputError("at least 2 artifacts are required to form an HSI seed pair")

    room_ids = list(av)
    artifact_matrix = np.asarray([av[aid] for aid in room_ids], dtype=np.float64)
    baseline_names = list(bv)
    baseline_matrix = np.asarray([bv[bid] for bid in baseline_names], dtype=np.float64)
    artifact_norms = np.linalg.norm(artifact_matrix, axis=1, keepdims=True)
    baseline_norms = np.linalg.norm(baseline_matrix, axis=1, keepdims=True)
    artifact_norms[artifact_norms < 1e-12] = 1.0
    baseline_norms[baseline_norms < 1e-12] = 1.0
    artifact_matrix /= artifact_norms
    baseline_matrix /= baseline_norms
    # Vectorized room-relative reference distributions; diagonal room matches are excluded.
    room_similarities = artifact_matrix @ artifact_matrix.T
    np.fill_diagonal(room_similarities, -np.inf)
    room_reference = np.sort(room_similarities, axis=1)[:, ::-1][:, :min(3, len(room_ids)-1)].mean(axis=1)
    baseline_similarities = baseline_matrix @ artifact_matrix.T
    baseline_reference = np.sort(baseline_similarities, axis=0)[-min(3, len(baseline_names)):].mean(axis=0)
    artifact_index = {aid: i for i, aid in enumerate(room_ids)}
    threshold = document.get("threshold")
    if threshold is not None:
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
            raise WorkflowInputError("threshold must be a finite number")
        selected_pairs = [pair for pair in pairs if pair.get("hsi_score", 0) > threshold]
        pair_selection = f"hsi_score > {threshold}"
    else:
        ranking = document.get("hsi_ranking", {}) or {}
        ranking_method = ranking if isinstance(ranking, str) else ranking.get("method") if isinstance(ranking, dict) else None
        if ranking_method == "percentile" or any(
        "hsi_percentile" in pair for pair in pairs
        ):
            selected_pairs, pair_selection = pairs, "as ranked by compute-hsi (percentile)"
        else:
            selected_pairs = [pair for pair in pairs if pair.get("hsi_score", 0) > 0.4]
            pair_selection = "hsi_score > 0.4 (legacy default)"
    signal_method = document.get("signal_method", "percentile")
    use_percentile = signal_method == "percentile" and len(room_ids) >= 4
    zones = []
    skipped = []
    for pair in selected_pairs:
        left_id, right_id = pair.get("left_id"), pair.get("right_id")
        if left_id not in av or right_id not in av or left_id == right_id:
            skipped.append({"left_id": left_id, "right_id": right_id, "reason": "seed artifact missing or duplicated"})
            continue
        score = pair.get("hsi_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            raise WorkflowInputError("each hsi_pair needs a finite hsi_score")
        centroid = (artifact_matrix[artifact_index[left_id]] + artifact_matrix[artifact_index[right_id]]) / 2
        centroid /= max(float(np.linalg.norm(centroid)), 1e-12)
        baseline_sims = baseline_matrix @ centroid
        baseline_order = np.argsort(-baseline_sims, kind="stable")
        room_sims = artifact_matrix @ centroid
        for seed_id in (left_id, right_id):
            room_sims[artifact_index[seed_id]] = -np.inf
        room_order = np.argsort(-room_sims, kind="stable")
        top_baseline = baseline_order[:min(3, len(baseline_names))]
        top_room = room_order[:min(3, len(room_ids)-2)]
        brain_sims = [(float(baseline_sims[i]), baseline_names[int(i)]) for i in top_baseline]
        room_candidates = [(float(room_sims[i]), room_ids[int(i)]) for i in top_room]
        brain_density = sum(x[0] for x in brain_sims) / len(brain_sims)
        room_density = sum(x[0] for x in room_candidates) / len(room_candidates) if room_candidates else 0.0
        if use_percentile:
            bp = float(np.mean(baseline_reference <= brain_density))
            rp = float(np.mean(room_reference <= room_density))
            signal = "strong" if bp >= .75 and rp <= .25 else "moderate" if bp >= .5 and rp <= .5 else "weak"
            signal_method_used = "percentile_vs_room_artifacts"
        else:
            bp = rp = None
            signal = "strong" if brain_density > .5 and room_density < .3 else "moderate" if brain_density > .3 and room_density < .5 else "weak"
            signal_method_used = "fixed_cutoffs"
        left, right = by_id[left_id], by_id[right_id]
        lexical_sim = pair.get("lexical_sim")
        zones.append({
            "zone_id": f"HSI-WS-{len(zones)+1:03d}",
            "seed_pair": {"left_id": left_id, "right_id": right_id, "hsi_score": float(score), "hsi_percentile": pair.get("hsi_percentile")},
            "centroid_description": f"Region between [{left.get('title', left_id)}] and [{right.get('title', right_id)}]",
            "nearest_baseline_frameworks": [{"id": bid, "label": baseline_ids[bid].get("label", bid), "cosine_similarity": round(sim, 4)} for sim, bid in brain_sims[:3]],
            "nearest_room_artifacts": [{"id": aid, "title": by_id[aid].get("title", aid), "cosine_similarity": round(sim, 4)} for sim, aid in room_candidates[:3]],
            "baseline_density": round(brain_density, 4), "room_density_excluding_seeds": round(room_density, 4),
            "baseline_density_percentile": None if bp is None else round(bp, 4),
            "room_density_percentile": None if rp is None else round(rp, 4),
            "signal_method": signal_method_used,
            "second_signal": {"method": "pair_lexical_similarity",
                              "lexical_sim": None if lexical_sim is None else round(float(lexical_sim), 4),
                              "confirmed": None if lexical_sim is None else bool(float(lexical_sim) < .5)},
            "gap_signal": signal,
            "hypothesis": f"The room may not articulate a connection between [{left.get('title', left_id)}] and [{right.get('title', right_id)}]; the nearby supplied framework is [{baseline_ids[brain_sims[0][1]].get('label', brain_sims[0][1])}].",
            "source_refs": [_refs(left), _refs(right), *[_refs(baseline_ids[bid]) for _, bid in brain_sims[:1]]],
            "novelty_check": {"status": "room-relative-only", "external_literature": "not_checked"},
        })
    zones.sort(key=lambda z: ({"strong": 0, "moderate": 1, "weak": 2}[z["gap_signal"]], -z["baseline_density"], z["zone_id"]))
    return {
        "schema_version": "eureka.hsi-whitespace-result.v1", "capability_id": "portfolio.discover_hsi_whitespace",
        "status": "completed_room_relative_scan", "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"),
        "input_counts": {"artifacts": len(av), "baseline_frameworks": len(bv), "hsi_pairs": len(pairs),
                         "qualifying_pairs": len(selected_pairs), "zones": len(zones), "skipped_pairs": len(skipped)},
        "pair_selection": pair_selection,
        "zones": zones, "skipped_pairs": skipped,
        "provenance": {"method": "HSI-seeded embedding centroid; top-3 cosine density; seed-excluded room density; percentile comparison against supplied room artifacts", "embedding_model": document.get("embedding_model"), "signal_method": "percentile" if use_percentile else "fixed", "computed_at": _now()},
        "interpretation": "A high signal is a hypothesis that a connection region is sparse in this supplied room while near supplied baseline frameworks. It is not proof of a literature gap, novelty, demand, or opportunity.",
        "limitations": ["All vectors and baseline frameworks must use the same embedding model and preprocessing.", "The result depends on HSI pair quality, baseline selection, and small-corpus percentile stability.", "No external literature or market search was performed; MindrianOS must broker any such research with user approval."],
    }


def retrieve_mechanisms(document: dict[str, Any]) -> dict[str, Any]:
    """Retrieve candidate source mechanisms from a caller-supplied corpus."""
    query = _text(document.get("problem"), "problem", maximum=12_000)
    records = _rows(document.get("mechanisms"), "mechanisms", maximum=20_000)
    ids = _unique_ids(records, "mechanisms")
    q_tokens = _tokens(query)
    if not q_tokens:
        raise WorkflowInputError("problem needs searchable content words")
    ranked = []
    for record_id, record in ids.items():
        mechanism = _text(record.get("mechanism"), f"mechanism {record_id}", maximum=20_000)
        domain = _text(record.get("domain"), f"mechanism {record_id}.domain", maximum=500)
        if not any(isinstance(record.get(key), str) and record[key].strip() for key in ("source_ref", "url", "path")):
            raise WorkflowInputError(f"mechanism {record_id!r} needs source_ref, url, or path")
        body = " ".join((str(record.get("title", "")), domain, mechanism, str(record.get("source_excerpt", ""))))
        terms = _tokens(body)
        overlap = q_tokens & terms
        union = q_tokens | terms
        # Transparent lexical recall only. It is deliberately not labeled a fit score.
        ranked.append({"id": record_id, "title": record.get("title", record_id), "domain": domain,
                       "mechanism": mechanism, "matched_terms": sorted(overlap),
                       "lexical_recall": len(overlap) / len(q_tokens),
                       "source": _refs(record)})
    ranked.sort(key=lambda row: (-row["lexical_recall"], row["id"]))
    limit = document.get("top_k", 20)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise WorkflowInputError("top_k must be an integer from 1 to 100")
    return {
        "schema_version": "eureka.mechanism-retrieval-result.v1",
        "capability_id": "analogy.retrieve_mechanism_candidates",
        "status": "completed_retrieval",
        "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"), "problem": query,
        "retrieval_source": document.get("corpus_id", "host-supplied mechanism corpus"),
        "retrieved": ranked[:limit],
        "candidate_count": len(ranked),
        "provenance": {"method": "case-insensitive lexical overlap recall", "computed_at": _now(), "external_research": "not_performed"},
        "limitations": ["Lexical recall finds records to inspect; it does not establish structural similarity or transferability.", "No external search was performed. Pass an approved, source-linked external bundle as records when remote research is authorized.", "Use structural mapping and evidence review before proposing an adaptation."],
    }


def plan_multidomain_research(document: dict[str, Any]) -> dict[str, Any]:
    """Plan Genesis-style parallel inquiry from user-approved domains."""
    objective = _text(document.get("objective"), "objective", maximum=12_000)
    domains = document.get("approved_domains")
    if not isinstance(domains, list) or not 1 <= len(domains) <= 12:
        raise WorkflowInputError("approved_domains must contain 1..12 domains selected or confirmed by the user")
    normalized = []
    seen = set()
    for index, item in enumerate(domains):
        if isinstance(item, str):
            row = {"name": item, "rationale": "user-confirmed domain"}
        elif isinstance(item, dict):
            row = item
        else:
            raise WorkflowInputError(f"approved_domains[{index}] must be a name or object")
        name = _text(row.get("name"), f"approved_domains[{index}].name", maximum=300)
        if name.casefold() in seen:
            raise WorkflowInputError(f"duplicate domain {name!r}")
        seen.add(name.casefold())
        rationale = _text(row.get("rationale", "user-confirmed domain"), f"approved_domains[{index}].rationale", maximum=1000)
        normalized.append({"domain": name, "rationale": rationale})
    exclusions = document.get("constraints", [])
    if not isinstance(exclusions, list) or any(not isinstance(x, str) for x in exclusions):
        raise WorkflowInputError("constraints must be an array of strings")
    tasks = []
    for index, row in enumerate(normalized, 1):
        tasks.append({"task_id": f"research-{index:02d}", "domain": row["domain"],
                      "why_selected": row["rationale"],
                      "constraints_to_respect": list(exclusions),
                      "research_questions": [
                          f"What mechanisms in {row['domain']} address a function structurally relevant to: {objective}?",
                          f"What evidence, counterevidence, limitations, and boundary conditions apply to those mechanisms?",
                          "What would falsify the proposed transfer, and what source would establish that?",
                      ],
                      "analytical_lens_only": True, "remote_execution": "requires host research broker and approval"})
    return {
        "schema_version": "eureka.genesis-research-plan.v1", "capability_id": "research.prepare_multidomain_plan",
        "status": "plan_ready_for_host_review", "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"),
        "objective": objective, "approved_domains": normalized, "research_tasks": tasks,
        "cross_domain_synthesis_questions": ["Which mechanisms address the same underlying function?", "Where do source findings conflict or rely on different assumptions?", "Which proposed transfer has a specific falsifying test?"],
        "handoff": {"research_execution": "MindrianOS approved broker", "evidence_adjudication": "SME and human review", "portfolio_write": "MindrianOS only after user decision"},
        "provenance": {"method": "bounded task planning from user-confirmed domains", "computed_at": _now()},
        "limitations": ["This tool plans research; it does not perform searches or generate findings.", "Domains are user/host confirmed, not inferred as evidence-grounded classifications.", "Task wording is a scaffold, not a simulated expert opinion."],
    }


def synthesize_research_findings(document: dict[str, Any]) -> dict[str, Any]:
    """Group exact source-linked host findings and preserve disagreement."""
    findings = _rows(document.get("findings"), "findings", maximum=5000)
    refs = _unique_ids(findings, "findings")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding_id, row in refs.items():
        claim = _text(row.get("claim"), f"finding {finding_id}.claim", maximum=12_000)
        source_ref = row.get("source_ref") or row.get("url") or row.get("path")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise WorkflowInputError(f"finding {finding_id!r} needs a source_ref, url, or path")
        position = row.get("position", "unspecified")
        if position not in {"supports", "contradicts", "context", "unspecified"}:
            raise WorkflowInputError(f"finding {finding_id!r}.position is invalid")
        # Group only exact normalized claim strings: no paraphrase equivalence is inferred.
        key = re.sub(r"\W+", " ", claim.casefold()).strip()
        if not key:
            raise WorkflowInputError(f"finding {finding_id!r}.claim has no searchable words")
        groups[key].append({"finding_id": finding_id, "claim": claim, "position": position,
                            "source": _refs(row), "locator": row.get("locator"),
                            "evidence_quote": row.get("evidence_quote")})
    clusters = []
    for index, (key, members) in enumerate(sorted(groups.items()), 1):
        positions = {member["position"] for member in members}
        clusters.append({"claim_group_id": f"claim-{index:03d}", "exact_normalized_claim": key,
                         "findings": members, "contains_disagreement": "supports" in positions and "contradicts" in positions,
                         "assessment": "unadjudicated"})
    return {"schema_version": "eureka.genesis-synthesis.v1", "capability_id": "research.group_multidomain_findings",
            "status": "completed_source_grouping", "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"),
            "finding_count": len(findings), "claim_groups": clusters,
            "unlinked_findings": [], "handoff": "SME/human adjudication; no consensus or truth verdict was generated",
            "provenance": {"method": "exact normalized claim grouping; source references retained", "computed_at": _now()},
            "limitations": ["Paraphrases are not merged.", "Support labels are supplied by the host and are not independently checked.", "This does not synthesize a causal narrative or validate claims."]}


def critique_proposal(document: dict[str, Any]) -> dict[str, Any]:
    """Audit a proposed solution's evidence completeness and falsifiability."""
    proposal = _text(document.get("proposal"), "proposal", maximum=20_000)
    claims = _rows(document.get("claims"), "claims", maximum=500)
    claim_rows = _unique_ids(claims, "claims")
    evidence_rows = document.get("evidence", [])
    if not isinstance(evidence_rows, list) or any(not isinstance(row, dict) for row in evidence_rows):
        raise WorkflowInputError("evidence must be an array of objects")
    evidence_by_id = _unique_ids(evidence_rows, "evidence") if evidence_rows else {}
    reviewed = []
    for claim_id, claim in claim_rows.items():
        text = _text(claim.get("text"), f"claim {claim_id}.text", maximum=10_000)
        ids = claim.get("evidence_ids", [])
        if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
            raise WorkflowInputError(f"claim {claim_id}.evidence_ids must be an array")
        unknown = set(ids) - evidence_by_id.keys()
        if unknown:
            raise WorkflowInputError(f"claim {claim_id} references unknown evidence ids: {sorted(unknown)}")
        counter_ids = claim.get("counterevidence_ids", [])
        if not isinstance(counter_ids, list) or any(item not in evidence_by_id for item in counter_ids):
            raise WorkflowInputError(f"claim {claim_id}.counterevidence_ids must reference supplied evidence")
        reviewed.append({"claim_id": claim_id, "text": text, "support_refs": [_refs(evidence_by_id[i]) for i in ids],
                         "counterevidence_refs": [_refs(evidence_by_id[i]) for i in counter_ids],
                         "review_flags": (["no_linked_evidence"] if not ids else []) + (["no_counterevidence_review_recorded"] if not counter_ids else []) + (["falsifying_observation_not_specified"] if not claim.get("falsifier") else []),
                         "falsifier": claim.get("falsifier")})
    return {"schema_version": "eureka.proposal-critique-result.v1", "capability_id": "analysis.audit_claim_traceability",
            "status": "completed_completeness_review", "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"), "proposal": proposal,
            "claims": reviewed, "decision": "not_assessed", "overall_flags": ["No independent factual verification or market assessment was performed."],
            "provenance": {"method": "claim/evidence/counterevidence/falsifier completeness audit", "computed_at": _now()},
            "limitations": ["This is a structural review, not a substantive critique from Jason's original model.", "No external sources or room graph were accessed.", "Missing counterevidence links indicate missing review data, not that counterevidence exists."]}


def critique_pitch(document: dict[str, Any]) -> dict[str, Any]:
    """Compose local Jason text diagnostics with the existing claim-traceability audit."""
    from .pitch_analysis import analyze_corpus

    pitch = _text(document.get("pitch"), "pitch", maximum=200_000)
    comparisons = document.get("comparisons", [])
    if not isinstance(comparisons, list) or len(comparisons) > 5000 or any(not isinstance(pair, dict) for pair in comparisons):
        raise WorkflowInputError("comparisons must be an array of at most 5,000 text-pair records")
    text_request = {"pairs": comparisons, "texts": [{"id": "pitch", "text": pitch}],
                    "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id")}
    text_result = analyze_corpus(text_request, input_bytes=json.dumps(text_request, ensure_ascii=False).encode("utf-8"))
    audit_request = {"proposal": document.get("proposal"), "claims": document.get("claims"),
                     "evidence": document.get("evidence", []), "scope_id": document.get("scope_id"),
                     "snapshot_id": document.get("snapshot_id")}
    audit = critique_proposal(audit_request)
    return {
        "schema_version": "eureka.pitch-diagnostics-result.v1",
        "capability_id": "analysis.critique_pitch",
        "status": "completed_local_diagnostics",
        "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"),
        "pitch_diagnostics": text_result,
        "claim_traceability": audit,
        "decision": "not_assessed",
        "limitations": [
            "This combines text-difference diagnostics and claim/evidence completeness checks; it is not Jason's full generative critique workflow.",
            "No external evidence search, graph traversal, demand analysis, or substantive truth adjudication was performed.",
            "Text similarity and restatement flags are diagnostic leads, not novelty or quality scores.",
        ],
    }


def structure_debate(document: dict[str, Any]) -> dict[str, Any]:
    """Check a source-linked six-perspective debate and leave ruling to a human."""
    topic = _text(document.get("topic"), "topic", maximum=5000)
    hypothesis = _text(document.get("hypothesis"), "hypothesis", maximum=5000)
    arguments = _rows(document.get("arguments"), "arguments", maximum=500)
    raw_evidence = document.get("evidence", [])
    if not isinstance(raw_evidence, list) or any(not isinstance(row, dict) for row in raw_evidence):
        raise WorkflowInputError("evidence must be an array of source records")
    evidence_by_id = _unique_ids(raw_evidence, "evidence") if raw_evidence else {}
    for evidence_id, evidence_row in evidence_by_id.items():
        if not (evidence_row.get("source_ref") or evidence_row.get("url") or evidence_row.get("path")):
            raise WorkflowInputError(f"evidence {evidence_id!r} needs a source_ref, url, or path")
    required = {"white", "red", "black", "yellow", "green", "blue"}
    by_hat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    argument_ids = set()
    for index, row in enumerate(arguments):
        arg_id = _text(row.get("id"), f"arguments[{index}].id", maximum=256)
        if arg_id in argument_ids:
            raise WorkflowInputError(f"duplicate argument id {arg_id!r}")
        argument_ids.add(arg_id)
        hat = row.get("hat")
        if hat not in required:
            raise WorkflowInputError(f"arguments[{index}].hat must be one of {sorted(required)}")
        text = _text(row.get("argument"), f"argument {arg_id}", maximum=10_000)
        evidence_ids = row.get("evidence_ids", [])
        if not isinstance(evidence_ids, list) or any(not isinstance(x, str) for x in evidence_ids):
            raise WorkflowInputError(f"argument {arg_id}.evidence_ids must be an array")
        unknown = set(evidence_ids) - evidence_by_id.keys()
        if unknown:
            raise WorkflowInputError(f"argument {arg_id} references unknown evidence ids: {sorted(unknown)}")
        by_hat[hat].append({"id": arg_id, "argument": text,
                            "evidence": [_refs(evidence_by_id[eid]) for eid in sorted(set(evidence_ids))],
                            "grounding": "source_linked" if evidence_ids else "no_sources_linked"})
    missing_hats = sorted(required - by_hat.keys())
    return {"schema_version": "eureka.bono-debate-review.v1", "capability_id": "deliberation.prepare_six_hat_review",
            "status": "partial_debate" if missing_hats else "ready_for_human_ruling", "scope_id": document.get("scope_id"),
            "snapshot_id": document.get("snapshot_id"),
            "topic": topic, "hypothesis": hypothesis,
            "perspectives": {hat: {"arguments": by_hat.get(hat, []), "present": bool(by_hat.get(hat))} for hat in ("white", "red", "black", "yellow", "green", "blue")},
            "missing_perspectives": missing_hats, "unresolved_questions": ["Which arguments are mutually inconsistent?", "What evidence would change the ruling?", "Are the perspectives grounded in independent sources or only different prompts?"],
            "ruling": {"required_from": "human navigator", "value": None},
            "provenance": {"method": "Six Thinking Hats argument organization and completeness checks", "computed_at": _now()},
            "limitations": ["Perspective labels do not create independent expertise or evidence.", "This does not execute research, simulate actual BONO debate behavior, or write to a room graph.", "The human navigator owns the ruling and any filing decision."]}


def propose_graph_relationships(document: dict[str, Any]) -> dict[str, Any]:
    """Package caller-declared candidate links with explicit evidence and rationale."""
    nodes = _rows(document.get("nodes"), "nodes", maximum=25_000)
    node_map = _unique_ids(nodes, "nodes")
    evidence = document.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(row, dict) for row in evidence):
        raise WorkflowInputError("evidence must be an array")
    evidence_map = _unique_ids(evidence, "evidence") if evidence else {}
    candidates = _rows(document.get("relationships"), "relationships", maximum=50_000)
    output = []
    for index, row in enumerate(candidates):
        source, target = row.get("source_id"), row.get("target_id")
        if source not in node_map or target not in node_map or source == target:
            raise WorkflowInputError(f"relationships[{index}] must connect two distinct supplied node ids")
        relation = _text(row.get("relation"), f"relationships[{index}].relation", maximum=100)
        rationale = _text(row.get("rationale"), f"relationships[{index}].rationale", maximum=5000)
        evidence_ids = row.get("evidence_ids", [])
        if not isinstance(evidence_ids, list) or not evidence_ids or any(eid not in evidence_map for eid in evidence_ids):
            raise WorkflowInputError(f"relationships[{index}] must cite one or more supplied evidence ids")
        output.append({"candidate_id": f"relationship-{index + 1:04d}", "source": _refs(node_map[source]), "target": _refs(node_map[target]),
                       "relation": relation, "rationale": rationale, "evidence": [_refs(evidence_map[eid]) for eid in sorted(set(evidence_ids))],
                       "status": "proposed_for_human_review", "score": None})
    return {"schema_version": "eureka.relationship-proposals.v1", "capability_id": "graph.package_relationship_proposals",
            "status": "completed_proposal_packaging", "scope_id": document.get("scope_id"),
            "snapshot_id": document.get("snapshot_id"), "proposals": output,
            "graph_write": "not_performed", "provenance": {"method": "validation and packaging of caller-supplied candidate links", "computed_at": _now()},
            "limitations": ["No relationship discovery or ranking was performed.", "No graph write was performed.", "Evidence relevance and relation semantics require human review."]}


def plan_opportunity_discovery(document: dict[str, Any]) -> dict[str, Any]:
    """Build a dependency-aware engine plan; execution remains explicitly selected."""
    objective = _text(document.get("objective"), "objective", maximum=12_000)
    requested = document.get("capability_ids")
    known = {"opportunity.find_cross_domain_pairs", "opportunity.synthesize_discovery_signals", "portfolio.find_hybrid_similarity_pairs", "portfolio.inventory_taxonomy_coverage", "portfolio.find_coverage_gaps", "portfolio.classify_weak_signal_tail", "portfolio.prepare_candidate_critic", "portfolio.inspect_candidate_grounding", "portfolio.prepare_critic_rubric", "portfolio.evaluate_critic_rubric", "analogy.retrieve_mechanism_candidates", "analogy.find_mechanisms", "analogy.assess_structural_fitness", "analogy.map_structure", "analogy.cross_domain_research", "research.prepare_multidomain_plan", "research.run_genesis_local_plan", "research.group_multidomain_findings", "analysis.compare_text_differences", "analysis.audit_claim_traceability", "analysis.critique_pitch", "deliberation.prepare_six_hat_review", "decision.compare_sequence_patterns", "graph.package_relationship_proposals", "graph.explore_local_relationships", "graph.propose_relationships", "graph.prepare_artifact_bundle", "graph.map_neighbourhoods", "graph.backtest_relationship_methods", "graph.score_bayesian_surprise", "graph.compare_bidirectional_topics", "graph.rank_evidence_paths"}
    if not isinstance(requested, list) or not requested or any(item not in known for item in requested):
        raise WorkflowInputError("capability_ids must name one or more known capability IDs")
    requested = list(dict.fromkeys(requested))
    dependencies = {
        "analogy.map_structure": ["analogy.retrieve_mechanism_candidates"],
        "analogy.cross_domain_research": ["analogy.retrieve_mechanism_candidates", "analogy.map_structure"],
        "deliberation.structure": ["evidence.fetch_for_question"],
        "graph.propose_relationships": ["human review of source-linked evidence"],
        "graph.prepare_artifact_bundle": ["MindrianOS-authorized graph snapshot"],
        "research.run_genesis_local_plan": ["graph.prepare_artifact_bundle", "Theo review before approved research execution"],
        "portfolio.classify_weak_signal_tail": ["MindrianOS-authorized cohort with precomputed, labeled attention and growth signals"],
        "portfolio.prepare_candidate_critic": ["Candidate with a mechanismText field"],
        "portfolio.inspect_candidate_grounding": ["portfolio.prepare_candidate_critic", "MindrianOS local embeddings and graph neighbors from the same authorized snapshot"],
        "portfolio.prepare_critic_rubric": ["portfolio.inspect_candidate_grounding passed for the same candidate/snapshot", "MindrianOS local judge"],
        "portfolio.evaluate_critic_rubric": ["portfolio.prepare_critic_rubric", "MindrianOS local neutral and adversarial judge responses"],
        "graph.map_neighbourhoods": ["MindrianOS-authorized graph snapshot", "distinct source and target node IDs"],
    }
    steps = []
    for index, capability_id in enumerate(requested, 1):
        steps.append({"step": index, "capability_id": capability_id, "status": "selected_for_plan", "depends_on": dependencies.get(capability_id, []), "egress": "host approval required for any external research", "stop_condition": "stop or mark blocked when required inputs, consent, or source lineage are missing"})
    return {"schema_version": "eureka.discovery-plan.v1", "status": "plan_ready_for_user_and_theo_review", "objective": objective,
            "scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"), "steps": steps,
            "principles": ["Run only selected capabilities; no automatic run-all.", "A plan is not a completed run.", "Local material stays inside the host-approved scope.", "External research runs through MindrianOS's approved broker.", "Candidate generation can increase review workload; cap output and preserve stop points."],
            "portfolio_write": "MindrianOS human-approved action only", "provenance": {"method": "explicit dependency-aware plan; no engine execution", "computed_at": _now()}}
