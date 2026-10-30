"""Local SME mapping and two-pass, host-brokered external research workflow.

This module never performs network access or treats a grant identifier as
authorization. MindrianOS owns provider access and approval; this package
canonicalizes query plans, validates returned source lineage, runs SME locally,
and assembles evidence-linked review records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from . import CAPABILITY_ID, CAPABILITY_VERSION
from . import _sme_core as sme
from . import _ranking_reference as ranking


class WorkflowError(ValueError):
    """A typed input or lineage refusal suitable for a host-facing error."""


def canonical_query_hash(query: dict[str, Any]) -> str:
    """Hash provider, exact egress text, and provider restrictions."""
    canonical = {
        "provider": query["provider"],
        "query": query["query"],
        "include_domains": sorted(set(query.get("include_domains", []))),
        "intent": query.get("intent"),
        "source_refs": sorted(set(query.get("source_refs", []))),
        "inference_ids": sorted(set(query.get("inference_ids", []))),
    }
    blob = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def prepare_research_plan(*, run_id: str, stage: str, scope_id: str,
                          queries: list[dict[str, Any]], parent_result_id: str | None = None) -> dict[str, Any]:
    """Freeze exact proposed searches for host approval and provider execution."""
    if stage not in {"mechanism_discovery", "inference_verification"}:
        raise WorkflowError("stage must be mechanism_discovery or inference_verification")
    if not run_id or not scope_id or not queries:
        raise WorkflowError("run_id, scope_id and at least one exact query are required")
    if stage == "inference_verification" and not parent_result_id:
        raise WorkflowError("inference_verification requires the parent mapping result id")
    seen: set[str] = set()
    canonical_queries = []
    for raw in queries:
        query = dict(raw)
        query_id = query.get("query_id")
        text = query.get("query")
        provider = query.get("provider")
        if not isinstance(query_id, str) or not query_id:
            raise WorkflowError("every query needs a stable query_id")
        if query_id in seen:
            raise WorkflowError(f"duplicate query_id: {query_id}")
        seen.add(query_id)
        if not isinstance(text, str) or len(text.strip()) < 3:
            raise WorkflowError(f"query {query_id} has no usable exact search text")
        if provider not in {"openalex", "arxiv", "pubmed", "tavily"}:
            raise WorkflowError(f"query {query_id} uses an unsupported research provider")
        if not isinstance(query.get("why"), str) or len(query["why"].strip()) < 3:
            raise WorkflowError(f"query {query_id} needs a short explanation of its purpose")
        if not isinstance(query.get("source_refs", []), list):
            raise WorkflowError(f"query {query_id} source_refs must be a list")
        if any(not isinstance(ref, str) for ref in query.get("source_refs", [])):
            raise WorkflowError(f"query {query_id} source_refs must contain strings")
        if not isinstance(query.get("include_domains", []), list) or any(
            not isinstance(domain, str) for domain in query.get("include_domains", [])
        ):
            raise WorkflowError(f"query {query_id} include_domains must be a list of domains")
        if stage == "mechanism_discovery" and query.get("intent") != "find_mechanism":
            raise WorkflowError("mechanism_discovery plans may contain only find_mechanism queries")
        if stage == "inference_verification" and query.get("intent") not in {
            "find_support", "find_counterevidence", "check_novelty", "check_boundary"
        }:
            raise WorkflowError("inference_verification plans need support, counterevidence, novelty, or boundary queries")
        query["query_hash"] = canonical_query_hash(query)
        query["source_refs"] = sorted(set(query.get("source_refs", [])))
        if query.get("inference_ids") is not None:
            if not isinstance(query["inference_ids"], list) or not query["inference_ids"]:
                raise WorkflowError(f"query {query_id} inference_ids must be a non-empty list when supplied")
            if any(not isinstance(inference_id, str) or not inference_id for inference_id in query["inference_ids"]):
                raise WorkflowError(f"query {query_id} inference_ids must contain non-empty strings")
            query["inference_ids"] = sorted(set(query["inference_ids"]))
        canonical_queries.append(query)
    selected_inference_ids = sorted({inference_id for query in canonical_queries
                                     for inference_id in query.get("inference_ids", [])})
    if stage == "inference_verification":
        if not selected_inference_ids:
            raise WorkflowError("verification queries must target at least one selected inference")
        if len(selected_inference_ids) > 20:
            raise WorkflowError("verify at most twenty selected inferences in one research pass")
        required = {"find_support", "find_counterevidence", "check_novelty", "check_boundary"}
        missing = {
            inference_id: sorted(required - {query["intent"] for query in canonical_queries
                                            if inference_id in query.get("inference_ids", [])})
            for inference_id in selected_inference_ids
        }
        missing = {key: value for key, value in missing.items() if value}
        if missing:
            raise WorkflowError(f"every selected inference needs support, counterevidence, novelty, and boundary queries: {missing}")
    return {
        "schema_version": "eureka.external-research-plan.v1",
        "run_id": run_id,
        "stage": stage,
        "scope_id": scope_id,
        "parent_result_id": parent_result_id,
        "selected_inference_ids": selected_inference_ids if stage == "inference_verification" else [],
        "queries": canonical_queries,
        "approval": {
            "grant_id": None,
            "approved_query_hashes": [],
            "approved_at": None,
            "approved_via": None,
        },
        "egress": "none; host approval and provider execution are still required",
    }


def validate_research_bundle(plan: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Check lineage and exact-query coverage; host remains authoritative for approval."""
    for field in ("run_id", "stage", "scope_id"):
        if plan.get(field) != bundle.get(field):
            raise WorkflowError(f"research bundle {field} does not match its plan")
    if bundle.get("schema_version") != "eureka.external-research-bundle.v1":
        raise WorkflowError("unsupported external research bundle schema")
    if not bundle.get("grant_id"):
        raise WorkflowError("host-approved grant_id is required as lineage metadata")
    plan_queries = plan.get("queries", [])
    if not isinstance(plan_queries, list) or not plan_queries:
        raise WorkflowError("research plan must contain exact queries")
    planned: dict[str, str] = {}
    planned_query_rows: dict[str, dict[str, Any]] = {}
    for query in plan_queries:
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or not query_id or query_id in planned:
            raise WorkflowError("research plan contains an invalid or duplicate query_id")
        if query.get("query_hash") != canonical_query_hash(query):
            raise WorkflowError(f"prepared query {query_id} hash does not match its exact contents")
        planned[query_id] = query["query_hash"]
        planned_query_rows[query_id] = query
    if plan.get("stage") == "inference_verification":
        query_selection = sorted({inference_id for query in plan_queries
                                  for inference_id in query.get("inference_ids", [])})
        if query_selection != sorted(set(plan.get("selected_inference_ids", []))):
            raise WorkflowError("selected_inference_ids must exactly match the inference IDs bound to approved queries")
    approved = set(bundle.get("approved_query_hashes", []))
    if not approved or not approved.issubset(set(planned.values())):
        raise WorkflowError("bundle approval hashes do not match the prepared exact-query plan")
    outcomes = bundle.get("query_outcomes", [])
    source_rows = bundle.get("sources", [])
    if not isinstance(outcomes, list) or not isinstance(source_rows, list):
        raise WorkflowError("query_outcomes and sources must be arrays")
    outcome_by_id = {row.get("query_id"): row for row in outcomes}
    if len(outcome_by_id) != len(outcomes):
        raise WorkflowError("bundle contains duplicate query outcomes")
    approved_queries = {query_id: query_hash for query_id, query_hash in planned.items()
                        if query_hash in approved}
    if set(outcome_by_id) != set(approved_queries):
        raise WorkflowError("bundle needs one outcome for every approved query and no unapproved queries")
    for query_id, outcome in outcome_by_id.items():
        if outcome.get("status") not in {"results", "empty_valid", "failed", "blocked"}:
            raise WorkflowError(f"query outcome {query_id} has an unknown status")
        if outcome.get("query_hash") != approved_queries[query_id]:
            raise WorkflowError(f"query outcome {query_id} has a mismatched query hash")
        if outcome.get("status") == "results" and outcome.get("result_count", 0) < 1:
            raise WorkflowError(f"query outcome {query_id} says results but has zero results")
        if outcome.get("status") == "empty_valid" and outcome.get("result_count") != 0:
            raise WorkflowError(f"query outcome {query_id} says empty_valid but has results")
        if outcome.get("status") in {"failed", "blocked"} and not outcome.get("failure_code"):
            raise WorkflowError(f"query outcome {query_id} must preserve its failure_code")
    claim_ids: set[str] = set()
    source_ids: set[str] = set()
    for source in source_rows:
        query_id = source.get("query_id")
        if query_id not in planned:
            raise WorkflowError(f"source {source.get('source_id')} cites an unplanned query")
        expected_hash = planned[query_id]
        if source.get("query_hash") != expected_hash or expected_hash not in approved:
            raise WorkflowError(f"source {source.get('source_id')} is not linked to an approved exact query")
        if source.get("retrieval_status") not in {"full_text", "abstract_only", "metadata_only", "snippet_only"}:
            raise WorkflowError("source has an unknown retrieval_status")
        planned_provider = planned_query_rows[query_id]["provider"]
        allowed_source_providers = {planned_provider}
        if planned_provider == "tavily":
            allowed_source_providers.update({"tavily-extract", "webfetch"})
        if source.get("provider") not in allowed_source_providers:
            raise WorkflowError(f"source {source.get('source_id')} provider does not match its planned provider route")
        if outcome_by_id[query_id].get("status") != "results":
            raise WorkflowError(f"source {source.get('source_id')} is attached to a query without successful results")
        if not isinstance(source.get("source_id"), str) or not source["source_id"]:
            raise WorkflowError("every source needs a non-empty source_id")
        if source.get("source_id") in source_ids:
            raise WorkflowError(f"duplicate source_id: {source.get('source_id')}")
        source_ids.add(source["source_id"])
        claims = source.get("claims", [])
        if not isinstance(claims, list) or not claims:
            raise WorkflowError(f"source {source.get('source_id')} needs at least one traceable claim")
        for claim in claims:
            if not isinstance(claim.get("claim_id"), str) or not claim["claim_id"]:
                raise WorkflowError("every claim needs a non-empty claim_id")
            if claim.get("claim_id") in claim_ids:
                raise WorkflowError(f"duplicate claim_id: {claim.get('claim_id')}")
            claim_text = claim.get("text")
            if not isinstance(claim_text, str) or not claim_text:
                raise WorkflowError(f"claim {claim.get('claim_id')} must contain exact non-empty text")
            if not isinstance(claim.get("locator"), str) or not claim["locator"]:
                raise WorkflowError(f"claim {claim.get('claim_id')} needs a source locator")
            quote_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
            if quote_hash.lower() != claim.get("quote_sha256", "").lower():
                raise WorkflowError(f"claim {claim.get('claim_id')} quote_sha256 does not match its exact text")
            claim_ids.add(claim["claim_id"])
    for query_id, outcome in outcome_by_id.items():
        actual_count = sum(1 for source in source_rows if source.get("query_id") == query_id)
        if outcome.get("status") == "results" and outcome.get("result_count") < actual_count:
            raise WorkflowError(f"query outcome {query_id} reports fewer results than the bundle contains")
    return {
        "ok": True,
        "run_id": bundle["run_id"],
        "stage": bundle["stage"],
        "grant_id": bundle["grant_id"],
        "source_count": len(source_ids),
        "claim_count": len(claim_ids),
        "query_count": len(approved),
        "outcome_summary": {status: sum(1 for row in outcomes if row.get("status") == status)
                            for status in ("results", "empty_valid", "failed", "blocked")},
        "approval_verified_by": "host; Scout verified only query/source lineage",
    }


def _description_group(raw: dict[str, Any], label: str):
    if not isinstance(raw, dict) or not isinstance(raw.get("expressions"), list):
        raise WorkflowError(f"{label} must be a description group with expressions")
    return sme.dgroup_from_dict(raw)


def _evidence_ids_for(expressions: list[str], evidence_map: dict[str, list[str]]) -> list[str]:
    found: set[str] = set()
    for expression in expressions:
        found.update(evidence_map.get(expression, []))
    return sorted(found)


def _canonical_evidence_map(raw: dict[str, list[str]], label: str) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        raise WorkflowError(f"{label} evidence must be an expression-to-claim object")
    out: dict[str, list[str]] = {}
    for expression, refs in raw.items():
        key = str(expression).strip().lower()
        if key in out:
            raise WorkflowError(f"{label} has duplicate expression evidence after normalization: {key}")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            raise WorkflowError(f"{label} expression {expression} needs a non-empty list of claim IDs")
        out[key] = sorted(set(refs))
    return out


def map_structures(document: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic mapping and return provenance-linked hypotheses."""
    if not document.get("run_id") or not document.get("scope_id"):
        raise WorkflowError("run_id and scope_id are required")
    target = _description_group(document["target"], "target")
    target_evidence = _canonical_evidence_map(document.get("target_evidence", {}), "target")
    evidence_catalog = document.get("evidence_catalog", [])
    catalog = {row["claim_id"]: row for row in evidence_catalog}
    if len(catalog) != len(evidence_catalog):
        raise WorkflowError("evidence_catalog contains duplicate claim_id values")
    if not isinstance(document.get("bases"), list) or not 1 <= len(document["bases"]) <= 10:
        raise WorkflowError("SME mapping requires between one and ten sourced mechanism bases")
    base_ids = [base.get("base_id") for base in document["bases"]]
    if any(not isinstance(base_id, str) or not base_id for base_id in base_ids) or len(set(base_ids)) != len(base_ids):
        raise WorkflowError("each mechanism base needs a unique, non-empty base_id")
    normalized_base_evidence = {
        str(base.get("base_id", "base")): _canonical_evidence_map(base.get("evidence", {}), str(base.get("base_id", "base")))
        for base in document.get("bases", [])
    }
    for label, evidence_map in [("target", target_evidence)] + list(normalized_base_evidence.items()):
        for expression_id, refs in evidence_map.items():
            if not refs:
                raise WorkflowError(f"{label} expression {expression_id} has an empty evidence list")
            missing = set(refs) - set(catalog)
            if missing:
                raise WorkflowError(f"{label} expression {expression_id} references unknown claims: {sorted(missing)}")
    absent_target = set(target.exprs) - set(target_evidence)
    if absent_target:
        raise WorkflowError(f"target has expressions without traceable room claims: {sorted(absent_target)}")
    for base in document.get("bases", []):
        base_id = base.get("base_id", "base")
        described = _description_group(base.get("description", {}), f"base {base_id}")
        absent = set(described.exprs) - set(normalized_base_evidence[base_id])
        if absent:
            raise WorkflowError(f"base {base_id} has expressions without traceable claims: {sorted(absent)}")
    rules = document.get("rules", ["AN", "MA"])
    if (not isinstance(rules, list) or not 1 <= len(rules) <= 2
            or any(not isinstance(rule, str) for rule in rules)
            or len(set(rules)) != len(rules)
            or any(rule not in sme.RULESETS for rule in rules)):
        raise WorkflowError("select one or two unique rules from AN, LS, MA")
    max_maps = int(document.get("max_maps_per_base", 5))
    if not 1 <= max_maps <= 10:
        raise WorkflowError("max_maps_per_base must be between 1 and 10")
    output_maps: list[dict[str, Any]] = []
    verification_targets: list[dict[str, Any]] = []
    for base_record in document.get("bases", []):
        base_id = base_record["base_id"]
        base = _description_group(base_record["description"], f"base {base_id}")
        base_evidence = normalized_base_evidence[base_id]
        for rule in rules:
            ranked = ranking.assess(base, target, rules=rule,
                                    known=document.get("known_claims", []), top=max_maps)
            for item in ranked:
                pairs = [tuple(pair) for pair in item.get("correspondences", [])]
                target_exprs = [right for left, right in pairs]
                target_context_refs = _evidence_ids_for(target_exprs, target_evidence)
                correspondence_rows = []
                for left, right in pairs:
                    correspondence_rows.append({
                        "base_item": left,
                        "target_item": right,
                        "base_claim_ids": base_evidence.get(left, []),
                        "target_claim_ids": target_evidence.get(right, []),
                    })
                inferences = []
                for ci in item.get("candidate_inferences", []):
                    base_expression = ci.get("base_expression", "")
                    raw_id = "\0".join([document["run_id"], base_id, rule, base_expression, ci["expression"]])
                    inference_id = "sme-ci-" + hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:20]
                    source_claim_ids = list(base_evidence.get(base_expression, []))
                    if not source_claim_ids:
                        raise WorkflowError(f"candidate inference {inference_id} has no source claims")
                    inference = {
                        "inference_id": inference_id,
                        "base_expression": base_expression,
                        "expression": ci["expression"],
                        "source_claim_ids": source_claim_ids,
                        "target_context_claim_ids": target_context_refs,
                        "status": "hypothesis_unverified",
                        "next_step": "Search for support, counterevidence, novelty, and analogy boundaries.",
                    }
                    inferences.append(inference)
                    verification_targets.append({
                        "inference_id": inference_id,
                        "hypothesis": ci["expression"],
                        "base_claim_ids": source_claim_ids,
                        "target_context_claim_ids": target_context_refs,
                        "required_checks": ["find_support", "find_counterevidence", "check_novelty", "check_boundary"],
                    })
                output_maps.append({
                    "map_id": "sme-map-" + hashlib.sha256(
                        f"{document['run_id']}\0{base_id}\0{rule}\0{item['rank_ses']}".encode("utf-8")
                    ).hexdigest()[:20],
                    "base_id": base_id,
                    "base_domain": base_record["domain"],
                    "rules": rule,
                    "ses": item["ses"],
                    "fit": item["fit"],
                    "surface_distance": item["surface_distance"],
                    "novelty": item["novelty"],
                    "triage_score": item["breakthrough"],
                    "rank": item["rank_ses"],
                    "correspondences": correspondence_rows,
                    "candidate_inferences": inferences,
                    "skolem_entities": item.get("skolem_entities", []),
                    "interpretation": "The score orders mappings for review. It is not evidence that the analogy or any inference is true.",
                })
            if ranked and ranked[0].get("search_truncated"):
                output_maps.append({
                    "map_id": f"sme-map-search-truncated-{base_id}-{rule}",
                    "base_id": base_id,
                    "base_domain": base_record["domain"],
                    "rules": rule,
                    "status": "partial",
                    "warning": "Global map search reached max_gmaps; results are not exhaustive.",
                    "candidate_inferences": [],
                })
    output_maps.sort(key=lambda row: (row.get("status") == "partial", -float(row.get("triage_score", 0.0))))
    used_ids = {claim_id for row in output_maps for mapping in row.get("correspondences", [])
                for claim_id in mapping.get("base_claim_ids", []) + mapping.get("target_claim_ids", [])}
    used_ids.update(claim_id for row in verification_targets
                    for claim_id in row["base_claim_ids"] + row["target_context_claim_ids"])
    return {
        "schema_version": "eureka.structure-mapping-result.v1",
        "result_id": "sme-map-result-" + hashlib.sha256(
            json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20],
        "run_id": document["run_id"],
        "scope_id": document["scope_id"],
        "capability_id": CAPABILITY_ID,
        "capability_version": CAPABILITY_VERSION,
        "status": "partial" if any(row.get("status") == "partial" for row in output_maps)
                  else ("completed" if output_maps else "completed_empty"),
        "network": "denied",
        "maps": output_maps,
        "verification_targets": verification_targets,
        "evidence_catalog": [catalog[key] for key in sorted(used_ids) if key in catalog],
        "warnings": [
            "Candidate inferences are hypotheses until evidence review.",
            "Encoding choices affect mapping; rerun leading candidates with an alternative encoding.",
        ],
    }


def finalize_assessments(mapping_result: dict[str, Any], verification_plan: dict[str, Any],
                         evidence_bundle: dict[str, Any], assessments: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach reviewed evidence outcomes without inventing an automatic truth judgment."""
    validate_research_bundle(verification_plan, evidence_bundle)
    for field in ("run_id", "scope_id"):
        if mapping_result.get(field) != evidence_bundle.get(field):
            raise WorkflowError(f"verification evidence {field} does not match the mapping run")
    if evidence_bundle.get("stage") != "inference_verification":
        raise WorkflowError("final evidence bundle must be an inference_verification bundle")
    if verification_plan.get("parent_result_id") != mapping_result.get("result_id"):
        raise WorkflowError("verification plan must name this mapping result as its parent")
    all_targets = {row["inference_id"]: row for row in mapping_result.get("verification_targets", [])}
    selected = set(verification_plan.get("selected_inference_ids", []))
    query_selection = {inference_id for q in verification_plan.get("queries", [])
                       for inference_id in q.get("inference_ids", [])}
    if selected != query_selection:
        raise WorkflowError("selected inference IDs do not match the inference IDs bound to verification queries")
    if not selected:
        selected = {inference_id for q in verification_plan.get("queries", [])
                    for inference_id in q.get("inference_ids", [])}
    unknown_refs = selected - set(all_targets)
    if unknown_refs:
        raise WorkflowError(f"verification plan selects unknown inference IDs: {sorted(unknown_refs)}")
    expected = {inference_id: all_targets[inference_id] for inference_id in selected}
    planned_checks = {inference_id: {q["intent"] for q in verification_plan.get("queries", [])
                                     if inference_id in q.get("inference_ids", [])}
                      for inference_id in expected}
    required_checks = {"find_support", "find_counterevidence", "check_novelty", "check_boundary"}
    missing_checks = {inference_id: sorted(required_checks - planned_checks[inference_id])
                      for inference_id in expected if required_checks - planned_checks[inference_id]}
    if missing_checks:
        raise WorkflowError(f"verification plan lacks required checks per inference: {missing_checks}")
    query_to_inferences = {q["query_id"]: set(q.get("inference_ids", []))
                           for q in verification_plan.get("queries", [])}
    claims_by_inference: dict[str, set[str]] = {inference_id: set() for inference_id in expected}
    for source in evidence_bundle.get("sources", []):
        for inference_id in query_to_inferences.get(source.get("query_id"), set()):
            if inference_id in claims_by_inference:
                claims_by_inference[inference_id].update(claim["claim_id"] for claim in source.get("claims", []))
    by_id = {row.get("inference_id"): row for row in assessments}
    if len(by_id) != len(assessments) or set(by_id) != set(expected):
        raise WorkflowError("provide exactly one assessment for every candidate inference")
    finalized = []
    for inference_id, target in expected.items():
        assessment = by_id[inference_id]
        status = assessment.get("status")
        if status not in {"supported", "contradicted", "untested"}:
            raise WorkflowError(f"assessment {inference_id} has an invalid status")
        if not assessment.get("reviewed_by"):
            raise WorkflowError(f"assessment {inference_id} must identify its model or human reviewer")
        refs = assessment.get("evidence_claim_ids", [])
        if set(refs) - claims_by_inference[inference_id]:
            raise WorkflowError(f"assessment {inference_id} references claims not returned for its own verification queries")
        if status in {"supported", "contradicted"} and not refs:
            raise WorkflowError(f"assessment {inference_id} needs cited evidence for status {status}")
        if status == "untested" and not assessment.get("falsifier"):
            raise WorkflowError(f"untested assessment {inference_id} needs a concrete falsifier")
        finalized.append({
            **target,
            "status": status,
            "assessment": assessment.get("rationale", ""),
            "evidence_claim_ids": sorted(set(refs)),
            "analogy_mismatch": assessment.get("analogy_mismatch", ""),
            "falsifier": assessment.get("falsifier"),
            "reviewed_by": assessment["reviewed_by"],
            "reviewed_at": assessment.get("reviewed_at") or datetime.now(timezone.utc).isoformat(),
        })
    return {
        "schema_version": "eureka.cross-domain-research-result.v1",
        "run_id": mapping_result["run_id"],
        "scope_id": mapping_result["scope_id"],
        "mapping_result_id": mapping_result.get("result_id"),
        "verification_grant_id": evidence_bundle["grant_id"],
        "status": "completed",
        "inferences": finalized,
        "decision_boundary": "Research status is a cited review outcome, not a truth guarantee or portfolio filing decision.",
        "filing_authority": "MindrianOS host and user only",
    }
