from __future__ import annotations

import pytest

from mindrian_eureka.contracts import ContractError, validate_request, validate_result
from mindrian_eureka.workflow_handlers import (
    HANDLERS, evaluate_critic_rubric, inspect_candidate_grounding,
    prepare_critic_candidate, prepare_critic_rubric,
)


MECHANISM = "The COX enzyme inhibits Prostaglandin receptors in tissue"


def _payload():
    candidate = {"text": MECHANISM, "mechanismText": MECHANISM,
                 "sourceDomainTag": "medicine", "targetDomainTag": "biology"}
    prepared = prepare_critic_candidate({"candidate": candidate})
    return {
        "candidate_id": "candidate-01", "source_node_id": "node-7",
        "scope_id": "room-alpha", "snapshot_id": "snapshot-123", "candidate": candidate,
        "embedding": {"model": "mindrian-local-test-v1",
                      "vectors": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                      "text_sha256": prepared["mechanism_variant_sha256"]},
        "nearest_neighbors": [{"node_id": "node-8", "similarity": 0.2}],
        "source_refs": ["mindrian-graph://node/node-7"],
    }


def test_critic_prepare_and_inspect_are_shared_cli_mcp_capabilities():
    assert "portfolio.prepare_candidate_critic" in HANDLERS
    assert "portfolio.inspect_candidate_grounding" in HANDLERS
    request = {"candidate": {"mechanismText": MECHANISM}}
    validate_request("portfolio.prepare_candidate_critic", request)
    prepared = prepare_critic_candidate(request)
    validate_result("portfolio.prepare_candidate_critic", prepared)
    assert prepared["mechanism_variants"][0] == MECHANISM
    assert len(prepared["mechanism_variant_sha256"]) == 4


def test_critic_stage_a_pass_preserves_mindrian_graph_context_and_does_not_write():
    request = _payload()
    validate_request("portfolio.inspect_candidate_grounding", request)
    result = inspect_candidate_grounding(request)
    validate_result("portfolio.inspect_candidate_grounding", result)
    assert result["status"] == "passed_deterministic_gates"
    assert result["stage"] == "A"
    assert result["features"]["nn_delta"] == 0.8
    assert result["host_context"]["snapshot_id"] == "snapshot-123"
    assert result["host_context"]["nearest_neighbor_ids"] == ["node-8"]
    assert result["graph_write"] == "not_performed"
    assert "Stage B" in result["next_step"]


def test_critic_rejects_unsourced_quantity_before_embedding_gates():
    request = _payload()
    request["candidate"]["text"] += " with a $5M exit"
    request["candidate"]["mechanismText"] += " with a $5M exit"
    prepared = prepare_critic_candidate({"candidate": request["candidate"]})
    request["embedding"]["text_sha256"] = prepared["mechanism_variant_sha256"]
    request["embedding"]["vectors"] = [[1, 0, 0, 0]] * 4
    result = inspect_candidate_grounding(request)
    assert result["status"] == "gate_failed"
    assert result["tag"] == "unsourced_quantity"
    assert result["features"] == {}


def test_critic_requires_exact_source_variant_hashes_and_quantity_sources():
    request = _payload()
    request["embedding"]["text_sha256"][0] = "0" * 64
    with pytest.raises(ValueError, match="exact source-generated"):
        inspect_candidate_grounding(request)
    request = _payload()
    request["candidate"]["mechanismText"] += " $5M"
    request["sourced_quantities"] = True
    request["source_refs"] = []
    with pytest.raises(ValueError, match="source_refs"):
        inspect_candidate_grounding(request)


def test_critic_does_not_echo_local_source_paths():
    request = _payload()
    request["source_refs"] = [r"C:\Users\private\room\source.md"]
    with pytest.raises(ValueError, match="filesystem paths"):
        inspect_candidate_grounding(request)


def test_critic_stage_b_prepares_host_local_prompts_and_codes_the_verdict():
    request = _payload()
    request["candidate"]["mappingStatement"] = "The mechanism may transfer across these distinct systems."
    prepared_embeddings = prepare_critic_candidate({"candidate": request["candidate"]})
    request["embedding"]["text_sha256"] = prepared_embeddings["mechanism_variant_sha256"]
    stage_a = inspect_candidate_grounding(request)
    assert stage_a["pass"] is True
    prepare_input = {key: request[key] for key in ("candidate_id", "source_node_id", "scope_id", "snapshot_id", "candidate")}
    prepare_input["stage_a_result"] = stage_a
    rubric_prompts = prepare_critic_rubric(prepare_input)
    validate_result("portfolio.prepare_critic_rubric", rubric_prompts)
    assert "Argue this proposed analogy is generic filler" in rubric_prompts["adversarial_prompt"]
    assert rubric_prompts["prompt_sha256"]["neutral"] != rubric_prompts["prompt_sha256"]["adversarial"]
    evaluate_input = {
        **prepare_input,
        "source_node_id": request["source_node_id"],
        "prompt_sha256": rubric_prompts["prompt_sha256"],
        "judge_model": "mindrian-local-test-judge-v1",
        "judge_responses": {
            "neutral": {key: True for key in "abcdef"},
            "adversarial": {key: True for key in "abcdef"},
        },
    }
    validate_request("portfolio.evaluate_critic_rubric", evaluate_input)
    result = evaluate_critic_rubric(evaluate_input)
    validate_result("portfolio.evaluate_critic_rubric", result)
    assert result["verdict"] == "transferable"
    assert result["rubric_pattern"] == "111111"
    assert result["confidence"] == "not_calibrated"
    assert result["graph_write"] == "not_performed"
    assert "judge_responses" not in str(result)


def test_critic_stage_b_requires_matching_stage_a_candidate_and_prompt_hashes():
    request = _payload()
    request["candidate"]["mappingStatement"] = "Candidate mapping for review."
    prepared_embeddings = prepare_critic_candidate({"candidate": request["candidate"]})
    request["embedding"]["text_sha256"] = prepared_embeddings["mechanism_variant_sha256"]
    stage_a = inspect_candidate_grounding(request)
    prepare_input = {key: request[key] for key in ("candidate_id", "source_node_id", "scope_id", "snapshot_id", "candidate")}
    prepare_input["stage_a_result"] = stage_a
    rubric = prepare_critic_rubric(prepare_input)
    evaluate_input = {**prepare_input, "source_node_id": request["source_node_id"],
        "prompt_sha256": {**rubric["prompt_sha256"], "neutral": "0" * 64},
        "judge_model": "local-judge", "judge_responses": {"neutral": "a yes", "adversarial": "a yes"}}
    with pytest.raises(ValueError, match="prompt_sha256"):
        evaluate_critic_rubric(evaluate_input)
    evaluate_input["prompt_sha256"] = rubric["prompt_sha256"]
    evaluate_input["snapshot_id"] = "other-snapshot"
    with pytest.raises(ValueError, match="snapshot_id"):
        evaluate_critic_rubric(evaluate_input)


def test_critic_reports_low_novelty_against_host_graph_neighbors():
    request = _payload()
    request["nearest_neighbors"] = [{"node_id": "near-duplicate", "similarity": 0.97}]
    result = inspect_candidate_grounding(request)
    assert result["status"] == "gate_failed"
    assert result["route"] == "restatement"
    assert result["tag"] == "low_novelty_delta"
    assert result["host_context"]["nearest_neighbor_ids"] == ["near-duplicate"]


def test_critic_rejects_invalid_host_vectors():
    request = _payload()
    request["embedding"]["vectors"][1] = [float("nan"), 0, 0, 0]
    with pytest.raises(ValueError, match="finite numbers"):
        inspect_candidate_grounding(request)
