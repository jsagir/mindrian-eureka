"""Shared handlers for capability stages exposed by both workflow CLI and MCP."""

from __future__ import annotations

import json
import hashlib
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import discovery_workflows as workflows
from .analogy_fitness import assess_analogy_fitness
from .analogy_whitespace import analyze as discover_transfer_whitespace
from .contracts import ContractError
from .graph_relations.runner import explore as explore_graph_relationships, prepare_artifact_bundle as project_graph_artifacts
from .graph_relations.sme_bridge import analyze as map_graph_neighbourhoods
from .graph_relations.services import (assess_edge_atypicality, find_bridge_pairs, find_network_holes,
                                       find_semantic_gaps, find_structural_gaps)
from .graph_relations.tasks import (backtest_relationship_methods, compare_bidirectional_topics,
                                    rank_evidence_paths, score_bayesian_surprise)
from .hsi_engine import run_hsi
from .hsi_baseline_whitespace import analyze_baseline_whitespace
from .hsi_external_whitespace import analyze_external_whitespace
from .hsi_interpret_whitespace import interpret_whitespace
from .hsi_rs_whitespace import discover_rs_whitespace
from .pitch_analysis import analyze_corpus
from .structure_mapping import workflow as sme_workflow


class NodeRuntimeUnavailable(RuntimeError):
    """A packaged Node.js engine worker cannot run in this host environment."""


def compare_text_differences(payload: dict) -> dict:
    result = analyze_corpus(payload, legacy=bool(payload.get("legacy", False)),
                            input_bytes=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if result.get("errors"):
        result["status"] = "invalid_input"
    if payload.get("scope_id") is not None or payload.get("snapshot_id") is not None:
        result["scope"] = {"scope_id": payload.get("scope_id"), "snapshot_id": payload.get("snapshot_id")}
    return result


def generate_rs_thesis(payload: dict) -> dict:
    """Generate the LATEST RS deterministic thesis and evidence record."""
    pair = payload["classified_pair"]
    breakthrough = payload.get("breakthrough") or {}
    mechanisms = {
        "structural_transfer": "isomorphic structure transfers under",
        "semantic_implementation": "semantic embedding bridges",
        "hybrid": "both structural and semantic alignment supports",
    }


    dimensions = {
        "feasibility": "feasible novel transfer",
        "market": "market-ready innovation",
        "magnitude": "high-magnitude breakthrough",
        "advantage": "rare cross-domain advantage",
        "impact": "high-impact result",
    }
    classification = pair.get("classification")
    if classification not in mechanisms:
        raise ContractError("classified_pair.classification must be a supported RS classification")
    query = pair.get("query_concept")
    doc = pair.get("doc_concept")
    if not isinstance(query, str) or not query.strip() or not isinstance(doc, str) or not doc.strip():
        raise ContractError("classified_pair requires non-empty query_concept and doc_concept")
    dimension = breakthrough.get("dominant_dimension")
    bridge = pair.get("bridge_concept")
    fallbacks = []
    if dimension not in dimensions:
        fallbacks.append("dominant_dimension")
    if not isinstance(bridge, str) or not bridge:
        fallbacks.append("bridge_concept")
        bridge = "domain analogy"
    z = dimensions.get(dimension, "novel insight")
    thesis = f"By applying {query} to {doc}, achieve {z} because {mechanisms[classification]} {bridge}."
    evidence = []
    for item in pair.get("evidence", []):
        if not isinstance(item, dict):
            continue
        sentence = item.get("sentence")
        if not isinstance(sentence, str) or not sentence.strip():
            continue
        evidence.append({
            "source_id": item.get("source_id") if isinstance(item.get("source_id"), str) else None,
            "url": item.get("url") if isinstance(item.get("url"), str) else None,
            "retrieved_at": item.get("retrieved_at") if isinstance(item.get("retrieved_at"), str) else None,
            "side": item.get("side") if item.get("side") in {"problem", "method"} else "unspecified",
            "sentence": sentence.strip()[:400],
        })
        if len(evidence) == 8:
            break
    novelty = pair.get("novelty_check_status", "not_run")
    if novelty not in {"passed", "failed", "possible_prior_art", "not_run"}:
        novelty = "not_run"
    second_signal = pair.get("second_signal") if isinstance(pair.get("second_signal"), dict) else None
    sources = sorted({item["source_id"] for item in evidence if item["source_id"]})
    confidence = 0.20
    basis = ["template_fill_only"]
    if any(item["side"] == "problem" for item in evidence):
        confidence += 0.15
        basis.append("problem_sentence_sourced")
    if any(item["side"] == "method" for item in evidence):
        confidence += 0.15
        basis.append("method_sentence_sourced")
    if len(sources) >= 2:
        confidence += 0.10
        basis.append("two_or_more_sources")
    if second_signal and second_signal.get("confirmed") is True:
        confidence += 0.15
        basis.append("second_signal_confirmed")
    if novelty == "passed":
        confidence += 0.15
        basis.append("novelty_check_passed")
    elif novelty in {"failed", "possible_prior_art"}:
        confidence -= 0.15
        basis.append("novelty_check_" + novelty)
    if "bridge_concept" in fallbacks:
        confidence -= 0.10
        basis.append("bridge_concept_fallback")
    if "dominant_dimension" in fallbacks:
        confidence -= 0.05
        basis.append("dimension_fallback")
    if not evidence:
        confidence = min(confidence, 0.35)
        basis.append("no_evidence_cap_0.35")
    confidence = round(min(1.0, max(0.0, confidence)), 2)
    label = "unsupported" if confidence < 0.30 else "weak" if confidence < 0.50 else "moderate" if confidence < 0.75 else "strong"
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "schema_version": "eureka.rs-thesis-record.v1",
        "capability_id": "research.generate_rs_thesis",
        "capability_version": "0.1.0",
        "status": "hypothesis_recorded" if evidence else "unsupported_hypothesis",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "thesis": thesis,
        "components": {"X": query, "Y": doc, "Z": z, "mechanism": mechanisms[classification], "bridge_concept": bridge},
        "fallbacks_used": fallbacks,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "source_ids": sources,
        "second_signal": {"confirmed": second_signal.get("confirmed") is True, "method": second_signal.get("method")}
            if second_signal else {"confirmed": None, "method": None},
        "novelty_check_status": novelty,
        "confidence": confidence,
        "confidence_label": label,
        "confidence_basis": basis,
        "input_fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "limitations": [
            "The thesis is a deterministic template fill, not a generated or validated conclusion.",
            "Confidence is a fixed heuristic over supplied evidence metadata, not calibrated probability.",
            "Evidence, novelty status, and second-signal status are caller supplied and are not independently verified.",
            "This stage does not read or write a MindrianOS room or fetch external evidence.",
        ],
    }


def extract_rs_experts(payload: dict) -> dict:
    """Derive source-linked author candidates from a host-supplied paper bundle."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS expert extraction requires Node.js 22 or newer")
    if len(payload["papers"]) > 10000:
        raise ContractError("papers exceeds the 10000-record limit")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS expert input exceeds 20 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS expert Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS expert extraction requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "experts-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS expert extraction exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS expert worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS expert worker returned malformed JSON") from exc
    experts = worker_result["experts"]
    return {
        "schema_version": "eureka.rs-expert-extraction.v1",
        "capability_id": "research.extract_experts_from_papers",
        "capability_version": "0.1.0",
        "status": "experts_extracted" if experts else "no_authors_found",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "experts": experts,
        "counts": worker_result["counts"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "run_config": {
            "include_retracted": payload.get("include_retracted", False),
            "infer_first_author_institution": payload.get("infer_first_author_institution", False),
            "runtime": version.stdout.strip(),
        },
        "limitations": [
            "Records are author candidates derived only from the supplied papers; this does not resolve experts against a room directory.",
            "Citation count and h-index estimate cover only the supplied, deduplicated papers and do not represent career-wide influence.",
            "Identity confidence estimates record identity, not expertise or suitability.",
            "The capability performs no search, room read/write, Aura query, Brain call, or outreach.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def score_rs_breakthrough(payload: dict) -> dict:
    """Run the LATEST five-dimension RS breakthrough scoring heuristic."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS breakthrough scoring requires Node.js 22 or newer")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 1024 * 1024:
        raise ContractError("RS breakthrough request exceeds 1 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS breakthrough Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS breakthrough scoring requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "breakthrough-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=15, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS breakthrough scoring exceeded its 15 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS breakthrough worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS breakthrough worker returned malformed JSON") from exc
    source_result = worker_result["result"]
    classified_pair = {key: value for key, value in source_result.items() if key != "breakthrough"}
    for key in ("evidence", "second_signal", "novelty_check_status"):
        if key in payload["classified_pair"]:
            classified_pair[key] = payload["classified_pair"][key]
    return {
        "schema_version": "eureka.rs-breakthrough-score.v1",
        "capability_id": "research.score_rs_breakthrough",
        "capability_version": "0.1.0",
        "status": "score_ready",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "classified_pair": classified_pair,
        "breakthrough": source_result["breakthrough"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "run_config": payload.get("options", {}),
        "runtime": version.stdout.strip(),
        "limitations": [
            "The five dimensions are fixed heuristic transforms of caller-supplied signals, not calibrated probabilities.",
            "Industry signal counts, pair density, substrate tier, and percentile are host supplied and not verified here.",
            "This score does not establish that a pair is novel, useful, commercially viable, or worth solving.",
            "The capability performs no graph read/write, external search, or room lookup.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def classify_rs_pair(payload: dict) -> dict:
    """Apply the LATEST deterministic RS innovation classifier."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS innovation classification requires Node.js 22 or newer")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 1024 * 1024:
        raise ContractError("RS classifier request exceeds 1 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS classifier Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS innovation classification requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "classifier-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=15, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS innovation classification exceeded its 15 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS classifier worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS classifier worker returned malformed JSON") from exc
    source_result = worker_result["result"]
    if source_result.get("error") == "invalid_input":
        raise ContractError(source_result.get("reason", "invalid classifier input"))
    classified_pair = dict(source_result)
    for key in ("evidence", "second_signal", "novelty_check_status"):
        if key in payload["scored_pair"]:
            classified_pair[key] = payload["scored_pair"][key]
    return {
        "schema_version": "eureka.rs-classification.v1",
        "capability_id": "research.classify_rs_pair",
        "capability_version": "0.1.0",
        "status": "classification_ready",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "classified_pair": classified_pair,
        "classification": source_result["classification"],
        "bridge_concept": source_result["bridge_concept"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "run_config": payload.get("options", {}),
        "runtime": version.stdout.strip(),
        "limitations": [
            "Classification follows fixed LSA/BERT thresholds and is not a validated assessment of transfer value.",
            "The source direction-convention module is missing from LATEST; this adapter follows its documented Convention A rule from rs-math.cjs.",
            "A none result means neither axis cleared its floor; it must not be sent to the RS thesis generator.",
            "The capability uses host-supplied scored pairs and does no graph access, retrieval, room lookup, or persistence.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def assess_rs_commercial_case(payload: dict) -> dict:
    """Run the LATEST deterministic RS commercial-template assessor."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS commercial assessment requires Node.js 22 or newer")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 1024 * 1024:
        raise ContractError("RS commercial assessment request exceeds 1 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS commercial assessor Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS commercial assessment requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "commercial-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=15, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS commercial assessment exceeded its 15 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS commercial assessor worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS commercial assessor worker returned malformed JSON") from exc
    return {
        "schema_version": "eureka.rs-commercial-assessment.v1",
        "capability_id": "research.assess_rs_commercial_case",
        "capability_version": "0.1.0",
        "status": "commercial_hypothesis_ready",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        **worker_result["result"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "The market-size field is a fixed two-signal bucket label, not a TAM/SAM estimate or validated demand measure.",
            "Value propositions are deterministic templates, not customer-tested claims or business cases.",
            "Partnership targets are names supplied and resolved by MindrianOS; this stage does not verify identity, expertise, consent, or availability.",
            "Source references are carried through for review; the stage performs no research retrieval, room lookup, graph access, or persistence.",
            "The source egress helper is replaced by the local RS content-hygiene filter; host egress policy remains authoritative.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def preprocess_rs_documents(payload: dict) -> dict:
    """Run the LATEST local RS document preprocessor over a host bundle."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS document preprocessing requires Node.js 22 or newer")
    ids = [document["id"] for document in payload["documents"]]
    if len(ids) != len(set(ids)):
        raise ContractError("documents contains duplicate IDs")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS preprocessing request exceeds 20 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS preprocessor Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS document preprocessing requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "preprocessor-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS document preprocessing exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS preprocessor worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS preprocessor worker returned malformed JSON") from exc
    if isinstance(worker_result.get("result"), dict) and worker_result["result"].get("error"):
        raise ContractError(worker_result["result"].get("reason", "RS preprocessing rejected its input"))
    records = worker_result["result"]
    return {
        "schema_version": "eureka.rs-preprocessing.v1",
        "capability_id": "research.preprocess_rs_documents",
        "capability_version": "0.1.0",
        "status": "preprocessing_complete",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "records": records,
        "counts": {
            "documents_received": len(payload["documents"]),
            "documents_processed": len(records),
            "documents_on_boundary": sum(record["boundary_flag"] for record in records),
            "documents_missing_text": sum(record.get("warning") == "document_text_missing" for record in records),
        },
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "Concept extraction is a deterministic lexical overlap against host-supplied domain concepts, not semantic understanding.",
            "Document text is truncated to 100,000 characters per document by the source algorithm; output terms do not establish relevance or novelty.",
            "The source canonical cross-room egress-pattern module is absent from LATEST. This local worker uses the smaller RS hygiene filter; MindrianOS must run its authoritative egress guard before any external use.",
            "The capability receives text from MindrianOS and does no graph access, research retrieval, room lookup, or persistence.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def analyze_rs_domain_projection(payload: dict) -> dict:
    """Apply the LATEST RS domain ranker to a host-supplied graph projection."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS domain analysis requires Node.js 22 or newer")
    ids = [entry["id"] for entry in payload["substrate"]]
    if len(ids) != len(set(ids)):
        raise ContractError("substrate contains duplicate node IDs")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS domain-analysis request exceeds 20 MiB")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS domain-analysis Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS domain analysis requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "domain-analyzer-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS domain analysis exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS domain-analysis worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS domain-analysis worker returned malformed JSON") from exc
    analysis = worker_result["result"]["domain_analysis"]
    if analysis.get("ok") is False or analysis.get("error") == "invalid_topic":
        raise ContractError(analysis.get("reason", "invalid RS domain-analysis topic"))
    return {
        "schema_version": "eureka.rs-domain-analysis.v1",
        "capability_id": "research.analyze_rs_domain_projection",
        "capability_version": "0.1.0",
        "status": "domain_analysis_boundary" if analysis.get("boundary_flag", True) else "domain_analysis_ready",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "domain_analysis": analysis,
        "ranked_domains": worker_result["result"]["ranked_domains"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "This adapts the source's Brain-substrate ranking rules to a MindrianOS host-authorized projection; Eureka does not resolve or read the graph itself.",
            "Domain matching is lexical n-gram overlap weighted by host-supplied substrate scores, not semantic classification or a validated causal relationship.",
            "The source canonical cross-room egress-pattern source is absent from LATEST. This worker uses the smaller local hygiene filter; the host remains responsible for authorization and any outbound egress gate.",
            "Returned domains, concepts, terminology, and methods are investigation leads and do not establish evidence, opportunity, or novelty.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def score_rs_differential_pair(payload: dict) -> dict:
    """Score a host-embedded RS concept pair using the LATEST dual-floor method."""
    vectors = [payload["query_vector"], payload["doc_vector"]]
    if len(vectors[0]) != len(vectors[1]) or not vectors[0]:
        raise ContractError("query and document vectors must have the same non-zero dimension")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise ContractError("embedding vectors must contain only finite numbers")
    if any(not any(value != 0 for value in vector) for vector in vectors):
        raise ContractError("embedding vectors must be non-zero")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS differential-scoring request exceeds 20 MiB")
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS differential scoring requires Node.js 22 or newer")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS differential-scoring Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS differential scoring requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "differential-scorer-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS differential scoring exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS differential scorer failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS differential scorer returned malformed JSON") from exc
    return {
        "schema_version": "eureka.rs-differential-scoring.v1",
        "capability_id": "research.score_rs_differential_pair",
        "capability_version": "0.1.0",
        "status": "scored",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "scored_pair": worker_result["result"]["scored_pair"],
        "query_node_id": worker_result["result"].get("query_node_id"),
        "doc_node_id": worker_result["result"].get("doc_node_id"),
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "The LATEST pair-wise TF-IDF LSA and dual-floor rules run locally; semantic cosine uses the two embeddings MindrianOS supplies.",
            "The source's Pinecone/cache bridge and default embedding spine are not invoked. Host owns encoder choice, authorization, and model provenance.",
            "Legacy thresholds and the LSA leg are uncalibrated. A passing pair is a lead, not evidence of novelty, causality, or opportunity value.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def assess_rs_pair_set_quality(payload: dict) -> dict:
    """Run the fixed, offline LATEST RS corpus collapse detector."""
    pairs = payload["scored_pairs"]
    ids = [pair["pair_id"] for pair in pairs]
    if len(ids) != len(set(ids)):
        raise ContractError("scored_pairs contains duplicate pair IDs")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS pair-set quality request exceeds 20 MiB")
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS pair-set quality assessment requires Node.js 22 or newer")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS quality-gate Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS pair-set quality assessment requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "quality-gate-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS pair-set quality assessment exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS quality gate failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS quality gate returned malformed JSON") from exc
    quality = worker_result["result"]["quality"]
    return {
        "schema_version": "eureka.rs-pair-set-quality.v1",
        "capability_id": "research.assess_rs_pair_set_quality",
        "capability_version": "0.1.0",
        "status": "quality_gate_passed" if quality["ok"] else "quality_gate_flagged",
        "scope_id": payload.get("scope_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "quality": quality,
        "pair_lineage": worker_result["result"]["pair_lineage"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "This fixed deterministic gate detects the source-defined SEED-018 corner collapse, constant score columns, non-finite values, and cohorts too small for ranking.",
            "A pass indicates score-set variation only; it does not establish pair validity, ranking quality, novelty, or opportunity value.",
            "For score output produced by research.score_rs_differential_pair, signed_diff is reconstructed as semantic cosine minus lexical score.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }


def generate_rs_query_matrix(payload: dict) -> dict:
    """Generate the LATEST four-category RS query matrix from domain context."""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 20 * 1024 * 1024:
        raise ContractError("RS query-matrix request exceeds 20 MiB")
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("RS query generation requires Node.js 22 or newer")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the RS query-matrix Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("RS query generation requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "rs" / "query-matrix-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=raw, text=True, capture_output=True,
            timeout=15, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("RS query generation exceeded its 15 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "RS query-matrix worker failed without an error message"
        raise ValueError(detail)
    try:
        worker_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RS query-matrix worker returned malformed JSON") from exc
    if worker_result["result"].get("error"):
        raise ContractError(worker_result["result"].get("reason", "RS query-matrix input was invalid"))
    return {
        "schema_version": "eureka.rs-query-matrix.v1",
        "capability_id": "research.generate_rs_query_matrix",
        "capability_version": "0.1.0",
        "status": "query_matrix_ready",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "categories": worker_result["result"]["categories"],
        "query_count": worker_result["result"]["query_count"],
        "input_fingerprint": worker_result["input_fingerprint"],
        "runtime": version.stdout.strip(),
        "limitations": [
            "The 60 prompts are deterministic templates from domain context, not source-validated queries or evidence.",
            "Only the primary domain and first adjacent domain are used by the source method; supplied concepts and methods fill fixed template slots.",
            "MindrianOS must apply its canonical authorization and egress policy before sending any query to a research provider; this local hygiene filter is not the host egress boundary.",
            "Source carries Mindrian BSL 1.1; local evaluation only pending distribution review.",
        ],
    }
def find_mechanisms(payload: dict) -> dict:
    result = workflows.retrieve_mechanisms(payload)
    result["capability_id"] = "analogy.find_mechanisms"
    return result


def propose_relationships(payload: dict) -> dict:
    result = explore_graph_relationships(
        payload.get("snapshot", payload), top=payload.get("top", 100),
        seed=payload.get("seed", 7), attr=payload.get("attr", "problem_type"),
        text_label=payload.get("text_label"), min_common=payload.get("min_common", 2),
        null_rounds=payload.get("null_rounds", 8), focus_node_id=payload.get("focus_node_id"),
        focus_hops=payload.get("focus_hops", 2))
    result["capability_id"] = "graph.propose_relationships"
    return result


def prepare_graph_artifact_bundle(payload: dict) -> dict:
    return project_graph_artifacts(payload.get("snapshot", payload), payload.get("objective"),
                                   payload.get("scope_id"), payload.get("max_artifacts", 2500))


def cross_domain_research_stage(payload: dict) -> dict:
    """Run one local SME stage; MindrianOS owns research execution between stages."""
    stage = payload.get("stage")
    request = payload.get("request")
    if not isinstance(request, dict):
        raise sme_workflow.WorkflowError("request must be an object for the selected research stage")
    if stage == "prepare_research_plan":
        return sme_workflow.prepare_research_plan(**request)
    if stage == "validate_research_bundle":
        return sme_workflow.validate_research_bundle(request.get("plan"), request.get("bundle"))
    if stage == "map_structures":
        return sme_workflow.map_structures(request)
    if stage == "finalize_assessments":
        return sme_workflow.finalize_assessments(
            request.get("mapping_result"), request.get("verification_plan"),
            request.get("evidence_bundle"), request.get("assessments"))
    raise sme_workflow.WorkflowError("stage must be prepare_research_plan, validate_research_bundle, map_structures, or finalize_assessments")


def run_genesis_local_plan(payload: dict) -> dict:
    """Run the source Genesis planning pipeline over a MindrianOS-projected bundle."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Genesis runtime unavailable: install Node.js 22 or newer")
    if sum(len(item.get("text", "").encode("utf-8")) for item in payload["artifacts"]) > 20 * 1024 * 1024:
        raise ValueError("Genesis graph projection exceeds 20 MiB of artifact text; narrow the authorized snapshot")
    if len({item["id"] for item in payload["artifacts"]}) != len(payload["artifacts"]):
        raise ValueError("Genesis graph projection contains duplicate artifact IDs")
    payload.setdefault("research_year", datetime.now(timezone.utc).year)
    for item in payload["artifacts"]:
        digest = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
        if item.get("sha256") and item["sha256"].lower() != digest:
            raise ValueError(f"Genesis graph projection text hash does not match artifact {item['id']!r}")
        item["sha256"] = digest
    try:
        version_check = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version_check.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the Genesis Node.js runtime") from exc
    if version_check.returncode or major < 22:
        raise NodeRuntimeUnavailable("Genesis requires Node.js 22 or newer")
    input_fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                                  separators=(",", ":")).encode("utf-8")).hexdigest()
    runner = Path(__file__).resolve().parent / "data" / "genesis" / "runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Genesis planning exceeded its 30 second execution limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "Genesis worker exited without an error message"
        raise ValueError(detail)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Genesis worker returned malformed JSON") from exc
    result.update({
        "schema_version": "eureka.genesis-local-plan.v1",
        "capability_id": "research.run_genesis_local_plan",
        "capability_version": "0.1.0",
        "input_fingerprint": input_fingerprint,
        "run_config": {"max_analysis_context_chars": 200000, "research_year": payload.get("research_year"),
                       "runtime": version_check.stdout.strip()},
        "limitations": [
            "Domain identification is rule-based lexical evidence, not semantic classification or calibrated probability.",
            "Personas are simulated analytical lenses, not real experts or independent evidence.",
            "The research plan and search queries are prompts for MindrianOS's approved research broker; this capability performs no search or model call.",
            "The source handoff includes Tavily-shaped request fields; MindrianOS must translate them to its configured provider and apply its approval policy.",
            "All input graph records were supplied by MindrianOS. Eureka does not read or write the room graph.",
            "Source reuse rights are unresolved; this capability is experimental and local-evaluation-only.",
        ],
    })
    result.setdefault("status", "plan_ready_for_host_review")
    return result


def classify_weak_signal_tail(payload: dict) -> dict:
    """Apply the LATEST Eureka low-attention/high-growth cohort classifier."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Tail-quadrant runtime unavailable: install Node.js 22 or newer")
    ids = [item["id"] for item in payload["items"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Tail-quadrant input contains duplicate item IDs")
    for index, item in enumerate(payload["items"]):
        for axis in ("attention", "growth"):
            value = item[axis]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"items[{index}].{axis} must be finite and in [0, 1]")
    for option in ("attention_quantile", "growth_quantile", "max_tail_fraction"):
        value = payload.get(option)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError(f"{option} must be finite and in [0, 1]")
    brokerage = payload.get("brokerage") or {}
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
           for value in brokerage.values()):
        raise ValueError("brokerage values must be finite numbers")
    unknown_brokers = sorted(set(brokerage) - set(ids))
    if unknown_brokers:
        raise ValueError("brokerage contains IDs that are not in items: " + ", ".join(unknown_brokers[:10]))
    try:
        version_check = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version_check.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the tail-quadrant Node.js runtime") from exc
    if version_check.returncode or major < 22:
        raise NodeRuntimeUnavailable("Tail-quadrant requires Node.js 22 or newer")
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    runner = Path(__file__).resolve().parent / "data" / "eureka" / "tail-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Tail-quadrant analysis exceeded its 30 second execution limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "Tail-quadrant worker exited without an error message"
        raise ValueError(detail)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Tail-quadrant worker returned malformed JSON") from exc
    status = "insufficient_structure" if result.get("insufficient_structure") else (
        "suspect_noise" if result.get("suspect_noise") else "completed_analysis")
    return {
        "schema_version": "eureka.weak-signal-tail.v1",
        "capability_id": "portfolio.classify_weak_signal_tail",
        "capability_version": "0.1.0",
        "status": status,
        "snapshot_id": payload.get("snapshot_id"),
        "scope_id": payload["scope_id"],
        "input_fingerprint": fingerprint,
        "run_config": {
            "attention_quantile": payload.get("attention_quantile", 0.25),
            "growth_quantile": payload.get("growth_quantile", 0.75),
            "min_cohort": payload.get("min_cohort", 30),
            "max_tail_fraction": payload.get("max_tail_fraction", 0.25),
            "attention_proxy": payload["attention_proxy"],
            "growth_proxy": payload["growth_proxy"],
            "runtime": version_check.stdout.strip(),
        },
        "classification": result,
        "limitations": [
            "Attention and growth values are supplied by MindrianOS; their units and proxy definitions are recorded but not validated here.",
            "This classifies a low-attention/high-growth quadrant within the supplied cohort; it does not establish opportunity, causality, novelty, or evidence support.",
            "A suspect-noise result retains its candidate list and must be reviewed as such; insufficient structure returns no candidates.",
            "No graph reads or writes, retrieval, or external research occur in this capability.",
            "The source carries Mindrian BSL 1.1 headers; this integration is for local evaluation pending distribution review.",
        ],
    }


def assess_eureka_candidate_dimensions(payload: dict) -> dict:
    """Run the LATEST Eureka dimension map and AHP weighting over a host snapshot."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Eureka portfolio assessment requires Node.js 22 or newer")
    ids = [item["id"] for item in payload["items"]]
    if len(ids) != len(set(ids)):
        raise ContractError("items contains duplicate graph node IDs")
    by_id = {item["id"]: item for item in payload["items"]}
    endpoints = (payload["pair"]["a_id"], payload["pair"]["b_id"])
    if endpoints[0] == endpoints[1] or any(node_id not in by_id for node_id in endpoints):
        raise ContractError("pair endpoints must be distinct IDs present in items")
    for node_id in endpoints:
        if not by_id[node_id].get("source_refs"):
            raise ContractError(f"candidate {node_id!r} must include at least one source reference")
    rs_ref = payload["pair"].get("rs_source_ref")
    if not rs_ref:
        raise ContractError("pair.rs_source_ref is required to trace the supplied RS signal")
    for ref in [*by_id[endpoints[0]]["source_refs"], *by_id[endpoints[1]]["source_refs"], rs_ref]:
        parsed = urlsplit(ref)
        if ref.startswith(("/", "\\\\")) or (len(ref) >= 3 and ref[1] == ":" and ref[2] in "/\\"):
            raise ContractError("source references must not contain local filesystem paths")
        if parsed.scheme == "file" or (not parsed.scheme and ("/" in ref or "\\" in ref)):
            raise ContractError("source references must be opaque IDs or approved URIs, not filesystem paths")

    try:
        version_check = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version_check.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the Eureka portfolio Node.js runtime") from exc
    if version_check.returncode or major < 22:
        raise NodeRuntimeUnavailable("Eureka portfolio assessment requires Node.js 22 or newer")

    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    runner = Path(__file__).resolve().parent / "data" / "eureka" / "portfolio" / "assessment-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Eureka portfolio assessment exceeded its 30 second limit") from exc
    if completed.returncode:
        detail = completed.stderr.strip()[:1000] or "Eureka portfolio assessment worker failed"
        raise ContractError(detail)
    try:
        assessment = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Eureka portfolio worker returned malformed JSON") from exc
    return {
        "schema_version": "eureka.portfolio-dimension-assessment.v1",
        "capability_id": "portfolio.assess_candidate_dimensions",
        "capability_version": "0.1.0",
        "status": "completed_analysis",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "input_fingerprint": fingerprint,
        "run_config": {
            "runtime": version_check.stdout.strip(),
            "weak_dimension_floor": 0.4,
            "criteria": ["strategic_fit", "validated_demand", "tech_econ_feasibility"],
        },
        "assessment": assessment,
        "limitations": [
            "Inputs are MindrianOS-projected signals and provenance references; Eureka does not read or write the local graph.",
            "The dimensions and AHP-weighted result are source-defined portfolio heuristics, not calibrated probabilities, causal claims, or opportunity qualification.",
            "The RS direction/abs_diff signal is accepted as supplied and is not recomputed or independently verified here.",
            "A consistent AHP matrix only shows internal judgment consistency; it does not validate the judgments or scores.",
            "The source carries Mindrian BSL 1.1 headers; this integration is for local evaluation pending distribution review.",
        ],
    }


def prepare_eureka_opportunity_statement(payload: dict) -> dict:
    """Prepare a source-faithful, permanently unbanked statement draft for host review."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Eureka opportunity statement requires Node.js 22 or newer")
    candidate = payload["candidate"]
    if candidate["a"]["id"] == candidate["b"]["id"]:
        raise ContractError("candidate endpoints must have distinct graph node IDs")
    all_refs = [*candidate["a"]["source_refs"], *candidate["b"]["source_refs"],
                *candidate["shared_problem_source_refs"], candidate["priority_signal_source_ref"],
                candidate["rank_source_ref"]]
    for ref in all_refs:
        parsed = urlsplit(ref)
        if ref.startswith(("/", "\\\\")) or (len(ref) >= 3 and ref[1] == ":" and ref[2] in "/\\"):
            raise ContractError("source references must not contain local filesystem paths")
        if parsed.scheme == "file" or (not parsed.scheme and ("/" in ref or "\\" in ref)):
            raise ContractError("source references must be opaque IDs or approved URIs, not filesystem paths")
    if candidate["priority_signal_source_ref"] == candidate["rank_source_ref"]:
        raise ContractError("priority signal and host rank must have separately resolvable source references")

    try:
        version_check = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version_check.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the Eureka statement Node.js runtime") from exc
    if version_check.returncode or major < 22:
        raise NodeRuntimeUnavailable("Eureka opportunity statement requires Node.js 22 or newer")

    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    runner = Path(__file__).resolve().parent / "data" / "eureka" / "portfolio" / "opportunity-statement-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Eureka statement preparation exceeded its 30 second limit") from exc
    if completed.returncode:
        raise ContractError(completed.stderr.strip()[:1000] or "Eureka statement worker failed")
    try:
        draft = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Eureka statement worker returned malformed JSON") from exc
    if draft.get("critic") != "pending" or draft.get("banked") is not False:
        raise RuntimeError("Eureka statement worker violated the draft-only critic gate")
    return {
        "schema_version": "eureka.opportunity-statement-draft.v1",
        "capability_id": "opportunity.prepare_statement",
        "capability_version": "0.1.0",
        "status": "draft_pending_host_review",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "input_fingerprint": fingerprint,
        "run_config": {"runtime": version_check.stdout.strip(), "critic_invoked": False, "weak_dimension_floor": 0.4},
        "draft": draft,
        "limitations": [
            "This is a structured opportunity hypothesis draft, not a validated opportunity, market claim, or accepted graph fact.",
            "The priority signal and rank are supplied by MindrianOS and their provenance is echoed, not independently verified.",
            "The source's critic is deliberately not invoked; critic remains pending and banked remains false until MindrianOS runs its approved review process.",
            "MindrianOS owns authorization, source resolution, human review, persistence, and all graph writes.",
            "The source carries Mindrian BSL 1.1 headers; this integration is for local evaluation pending distribution review.",
        ],
    }


def harvest_eureka_graph_events(payload: dict) -> dict:
    """Run the LATEST Eureka graph-event harvest over a complete host projection."""
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Eureka graph-event harvest requires Node.js 22 or newer")
    snapshot = payload["snapshot"]
    nodes = snapshot["nodes"]
    edges = snapshot["edges"]
    node_ids = [item["id"] for item in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ContractError("snapshot contains duplicate graph node IDs")
    node_id_set = set(node_ids)
    for index, edge in enumerate(edges):
        if edge["source"] not in node_id_set or edge["target"] not in node_id_set:
            raise ContractError(f"snapshot edge {index} has an endpoint outside the complete node projection")
    edge_keys = [(edge["source"], edge["target"], edge["type"]) for edge in edges]
    if len(edge_keys) != len(set(edge_keys)):
        raise ContractError("snapshot contains duplicate directed graph edges")
    if payload["bank_dedup_complete"] is not True:
        raise ContractError("complete MindrianOS opportunity-bank dedup state is required")
    if len(snapshot["nodes"]) > 10000 or len(snapshot["edges"]) > 50000:
        raise ContractError("graph snapshot exceeds harvest limits (10,000 nodes; 50,000 edges)")

    try:
        version_check = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version_check.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the Eureka harvest Node.js runtime") from exc
    if version_check.returncode or major < 22:
        raise NodeRuntimeUnavailable("Eureka graph-event harvest requires Node.js 22 or newer")

    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    runner = Path(__file__).resolve().parent / "data" / "eureka" / "portfolio" / "opportunity-harvest-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=45, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Eureka graph-event harvest exceeded its 45 second limit") from exc
    if completed.returncode:
        raise ContractError(completed.stderr.strip()[:1000] or "Eureka graph-event harvest worker failed")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Eureka graph-event harvest worker returned malformed JSON") from exc
    if not result.get("ok"):
        raise ContractError(result.get("reason", "graph-event harvest failed"))
    return {
        "schema_version": "eureka.opportunity-harvest.v1",
        "capability_id": "opportunity.harvest_graph_events",
        "capability_version": "0.1.0",
        "status": "completed_analysis",
        "scope_id": payload["scope_id"],
        "snapshot_id": payload["snapshot_id"],
        "input_fingerprint": fingerprint,
        "run_config": {
            "runtime": version_check.stdout.strip(),
            "q2_link_gate": True,
            "hub_degree_ceiling": 6,
            "harvest_index_version": "HarvestIndex_v1",
            "harvest_index_status": "EXPERIMENTAL",
            "bank_dedup_complete": True,
            "graph_completeness": snapshot["completeness"],
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "harvest": {key: result[key] for key in ("count", "top_band", "top_candidate_id", "candidates", "warnings")},
        "limitations": [
            "The host must supply the complete authorized-scope graph projection and complete opportunity-bank names; partial graph or bank inputs are rejected.",
            "Results are unevidenced candidate handles. The method does not resolve sources, assess truth, or validate the underlying graph semantics.",
            "Q1 timing, Q5 actor fit, and Q8 desirability use the LATEST source defaults; these values are not independent measurements.",
            "HarvestIndex_v1 is explicitly experimental and advisory; its weights and ranking have not been calibrated against outcomes.",
            "Eureka reads only the request and never opens room.db, writes a side channel, or mutates MindrianOS state.",
            "MindrianOS owns authorization, evidence resolution, human review, persistence, and all graph writes.",
            "The source carries Mindrian BSL 1.1 headers; this integration is for local evaluation pending distribution review.",
        ],
    }


def prepare_critic_candidate(payload: dict) -> dict:
    """Return the exact source-defined mechanism perturbations to embed locally."""
    return _run_critic_worker({"action": "prepare", **payload}, "portfolio.prepare_candidate_critic")


def inspect_candidate_grounding(payload: dict) -> dict:
    """Run LATEST Eureka deterministic Stage A over MindrianOS-supplied vectors and neighbors."""
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        raise ContractError("candidate must be an object")
    if payload.get("sourced_quantities") and not payload.get("source_refs"):
        raise ContractError("source_refs are required when sourced_quantities is true")
    source_refs = payload.get("source_refs", [])
    if not isinstance(source_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in source_refs):
        raise ContractError("source_refs must be an array of non-empty opaque references")
    for ref in source_refs:
        parsed = urlsplit(ref)
        if ref.startswith(("/", "\\\\")) or (len(ref) >= 3 and ref[1] == ":" and ref[2] in "/\\"):
            raise ContractError("source_refs must not contain local filesystem paths")
        if parsed.scheme == "file" or (not parsed.scheme and ("/" in ref or "\\" in ref)):
            raise ContractError("source_refs must be resolvable opaque IDs or approved URIs, not filesystem paths")
    embedding = payload.get("embedding")
    vectors = embedding.get("vectors") if isinstance(embedding, dict) else None
    if not isinstance(vectors, list) or not vectors:
        raise ContractError("embedding.vectors must be a non-empty matrix prepared by MindrianOS")
    dim = len(vectors[0]) if isinstance(vectors[0], list) else 0
    if not 1 <= dim <= 4096 or len(vectors) > 32:
        raise ContractError("embedding vectors must have a shared dimension from 1 to 4096 and at most 32 rows")
    for row_index, row in enumerate(vectors):
        if not isinstance(row, list) or len(row) != dim:
            raise ContractError(f"embedding.vectors[{row_index}] has inconsistent dimensions")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in row):
            raise ContractError(f"embedding.vectors[{row_index}] must contain finite numbers")
        if not any(value != 0 for value in row):
            raise ContractError(f"embedding.vectors[{row_index}] cannot be zero")
    variant_hashes = embedding.get("text_sha256")
    expected = _run_critic_worker({"action": "prepare", "candidate": candidate}, "portfolio.prepare_candidate_critic")
    if variant_hashes != expected.get("mechanism_variant_sha256"):
        raise ContractError("embedding.text_sha256 must match the exact source-generated mechanism variants")
    if not isinstance(embedding.get("model"), str) or not embedding["model"].strip():
        raise ContractError("embedding.model must identify MindrianOS's configured local model")
    neighbors = payload.get("nearest_neighbors")
    if not isinstance(neighbors, list) or len(neighbors) > 1000:
        raise ContractError("nearest_neighbors must be a host-prepared array with at most 1000 records")
    for index, neighbor in enumerate(neighbors):
        if not isinstance(neighbor, dict) or not isinstance(neighbor.get("node_id"), str) or not neighbor["node_id"]:
            raise ContractError(f"nearest_neighbors[{index}] needs a stable node_id")
        score = neighbor.get("similarity")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not -1 <= score <= 1:
            raise ContractError(f"nearest_neighbors[{index}].similarity must be in [-1, 1]")
    return _run_critic_worker({"action": "evaluate", **payload}, "portfolio.inspect_candidate_grounding")


def prepare_critic_rubric(payload: dict) -> dict:
    """Prepare source-authored neutral/adversarial prompts for MindrianOS's local judge."""
    stage_a = payload.get("stage_a_result")
    context = stage_a.get("host_context", {}) if isinstance(stage_a, dict) else {}
    if not isinstance(stage_a, dict) or stage_a.get("pass") is not True or stage_a.get("status") != "passed_deterministic_gates":
        raise ContractError("a passing critic Stage A result is required before rubric preparation")
    for key in ("candidate_id", "source_node_id", "scope_id", "snapshot_id"):
        if context.get(key) != payload.get(key):
            raise ContractError(f"stage_a_result {key} does not match this rubric request")
    mechanism_hashes = _run_critic_worker(
        {"action": "prepare", "candidate": payload.get("candidate")}, "portfolio.prepare_candidate_critic"
    ).get("mechanism_variant_sha256")
    if context.get("embedding_variant_sha256") != mechanism_hashes:
        raise ContractError("candidate mechanismText does not match the Stage A embedded variants")
    return _run_critic_worker({"action": "prepare_rubric", **payload}, "portfolio.prepare_critic_rubric")


def evaluate_critic_rubric(payload: dict) -> dict:
    """Apply the source parser and code-derived two-pass rubric to host judge responses."""
    stage_a = payload.get("stage_a_result")
    stage_context = stage_a.get("host_context", {}) if isinstance(stage_a, dict) else {}
    if not isinstance(stage_a, dict) or stage_a.get("pass") is not True or stage_a.get("status") != "passed_deterministic_gates":
        raise ContractError("a passing critic Stage A result is required before rubric evaluation")
    for key in ("candidate_id", "snapshot_id", "source_node_id"):
        if stage_context.get(key) != payload.get(key):
            raise ContractError(f"stage_a_result {key} does not match this rubric request")
    responses = payload.get("judge_responses")
    if not isinstance(responses, dict) or not all(key in responses for key in ("neutral", "adversarial")):
        raise ContractError("judge_responses must include neutral and adversarial responses")
    return _run_critic_worker({"action": "evaluate_rubric", **payload}, "portfolio.evaluate_critic_rubric")


def _run_critic_worker(payload: dict, capability_id: str) -> dict:
    node = shutil.which("node")
    if not node:
        raise NodeRuntimeUnavailable("Eureka critic requires Node.js 22 or newer")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=2, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise NodeRuntimeUnavailable("Could not verify the Eureka critic Node.js runtime") from exc
    if version.returncode or major < 22:
        raise NodeRuntimeUnavailable("Eureka critic requires Node.js 22 or newer")
    runner = Path(__file__).resolve().parent / "data" / "eureka" / "critic" / "critic-runner.cjs"
    try:
        completed = subprocess.run(
            [node, str(runner)], input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Eureka critic stage exceeded its 30 second execution limit") from exc
    if completed.returncode:
        raise ContractError(completed.stderr.strip()[:1000] or "Eureka critic worker failed")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Eureka critic worker returned malformed JSON") from exc
    stage = "b" if payload["action"].endswith("rubric") else "a"
    result.update({"schema_version": f"eureka.critic-stage-{stage}.v1", "capability_id": capability_id,
                   "capability_version": "0.1.0", "runtime": version.stdout.strip()})
    if payload["action"] == "evaluate":
        fingerprint_payload = {key: value for key, value in payload.items() if key != "action"}
        result["input_fingerprint"] = hashlib.sha256(json.dumps(
            fingerprint_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        result["source_refs"] = payload.get("source_refs", [])
        result["host_context"]["sourced_quantities"] = bool(payload.get("sourced_quantities", False))
    elif payload["action"] == "evaluate_rubric":
        result["input_fingerprint"] = hashlib.sha256(json.dumps(
            {key: value for key, value in payload.items() if key != "action"},
            sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
    return result


HANDLERS = {
    "research.generate_rs_thesis": generate_rs_thesis,
    "research.extract_experts_from_papers": extract_rs_experts,
    "research.score_rs_breakthrough": score_rs_breakthrough,
    "research.classify_rs_pair": classify_rs_pair,
    "research.assess_rs_commercial_case": assess_rs_commercial_case,
    "research.preprocess_rs_documents": preprocess_rs_documents,
    "research.analyze_rs_domain_projection": analyze_rs_domain_projection,
    "research.score_rs_differential_pair": score_rs_differential_pair,
    "research.assess_rs_pair_set_quality": assess_rs_pair_set_quality,
    "research.generate_rs_query_matrix": generate_rs_query_matrix,
    "analysis.compare_text_differences": compare_text_differences,
    "portfolio.find_hybrid_similarity_pairs": run_hsi,
    "analogy.assess_structural_fitness": assess_analogy_fitness,
    "analogy.discover_transfer_whitespace": discover_transfer_whitespace,
    "portfolio.inventory_taxonomy_coverage": workflows.portfolio_coverage,
    "portfolio.find_coverage_gaps": workflows.find_coverage_gaps,
    "portfolio.discover_hsi_whitespace": workflows.discover_hsi_whitespace,
    "portfolio.analyze_external_whitespace": analyze_external_whitespace,
    "portfolio.interpret_whitespace": interpret_whitespace,
    "portfolio.discover_rs_whitespace": discover_rs_whitespace,
    "portfolio.analyze_baseline_whitespace": analyze_baseline_whitespace,
    "analogy.retrieve_mechanism_candidates": workflows.retrieve_mechanisms,
    "analogy.find_mechanisms": find_mechanisms,
    "analogy.cross_domain_research": cross_domain_research_stage,
    "research.prepare_multidomain_plan": workflows.plan_multidomain_research,
    "research.group_multidomain_findings": workflows.synthesize_research_findings,
    "research.run_genesis_local_plan": run_genesis_local_plan,
    "portfolio.classify_weak_signal_tail": classify_weak_signal_tail,
    "portfolio.assess_candidate_dimensions": assess_eureka_candidate_dimensions,
    "opportunity.prepare_statement": prepare_eureka_opportunity_statement,
    "opportunity.harvest_graph_events": harvest_eureka_graph_events,
    "portfolio.prepare_candidate_critic": prepare_critic_candidate,
    "portfolio.inspect_candidate_grounding": inspect_candidate_grounding,
    "portfolio.prepare_critic_rubric": prepare_critic_rubric,
    "portfolio.evaluate_critic_rubric": evaluate_critic_rubric,
    "analysis.audit_claim_traceability": workflows.critique_proposal,
    "analysis.critique_pitch": workflows.critique_pitch,
    "deliberation.prepare_six_hat_review": workflows.structure_debate,
    "graph.package_relationship_proposals": workflows.propose_graph_relationships,
    "graph.explore_local_relationships": lambda payload: explore_graph_relationships(
        payload.get("snapshot", payload), top=payload.get("top", 100),
        seed=payload.get("seed", 7), attr=payload.get("attr", "problem_type"),
        text_label=payload.get("text_label"), min_common=payload.get("min_common", 2),
        null_rounds=payload.get("null_rounds", 8), focus_node_id=payload.get("focus_node_id"),
        focus_hops=payload.get("focus_hops", 2)),
    "graph.propose_relationships": propose_relationships,
    "graph.prepare_artifact_bundle": prepare_graph_artifact_bundle,
    "graph.map_neighbourhoods": lambda payload: map_graph_neighbourhoods(
        payload.get("snapshot", payload), payload.get("base_node_id"), payload.get("target_node_id"),
        hops=payload.get("hops", 2), rules=payload.get("rules", "AN"), attr=payload.get("attr", "problem_type")),
    "graph.backtest_relationship_methods": backtest_relationship_methods,
    "graph.score_bayesian_surprise": score_bayesian_surprise,
    "graph.compare_bidirectional_topics": compare_bidirectional_topics,
    "graph.rank_evidence_paths": rank_evidence_paths,
    "graph.find_structural_gaps": find_structural_gaps,
    "graph.find_network_holes": find_network_holes,
    "graph.find_bridge_pairs": find_bridge_pairs,
    "graph.assess_edge_atypicality": assess_edge_atypicality,
    "graph.find_semantic_gaps": find_semantic_gaps,
    "discovery.plan_opportunity_scout": workflows.plan_opportunity_discovery,
}
