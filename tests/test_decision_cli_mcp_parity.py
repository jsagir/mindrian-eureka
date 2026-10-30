import contextlib
import copy
import io
import json
import sys

import pytest

from mindrian_eureka.decision_patterns.cli import main as omm_cli_main
from mindrian_eureka.contracts import ContractError, validate_request
from mindrian_eureka.opportunity_pairs.mcp_server import (
    DecisionSequenceInput,
    DecisionSequenceFitInput,
    decision_compare_sequence_patterns,
    decision_fit_sequence_patterns,
)


def _model(model_id, probability):
    return {
        "id": model_id,
        "label": model_id,
        "initial_distribution": [0.25, 0.25, 0.25, 0.25],
        "transition_matrix": [[0.25, 0.25, 0.25, 0.25] for _ in range(4)],
        "emission_probabilities": [[probability] * 4 for _ in range(4)],
    }


def test_omm_cli_and_mcp_return_the_same_real_hmm_result(tmp_path, monkeypatch):
    pytest.importorskip("pomegranate")
    request = {
        "scope_id": "room:omm-cli-mcp",
        "snapshot_id": "snapshot:omm-fixture-1",
        "sequence_id": "decision-trace-1",
        "observations": [
            {"step_id": "step-1", "features": {
                "complex_features": True,
                "multidirectional_causation": True,
                "holistic_view": False,
                "creative_synthesis": True,
            }},
            {"step_id": "step-2", "features": {
                "complex_features": False,
                "multidirectional_causation": True,
                "holistic_view": True,
                "creative_synthesis": False,
            }},
        ],
        "models": [_model("high-emission", 0.8), _model("low-emission", 0.3)],
    }
    input_path = tmp_path / "decision-sequence.json"
    input_path.write_text(json.dumps(request), encoding="utf-8")

    output = io.StringIO()
    monkeypatch.setattr(sys, "argv", ["eureka-omm", "analyze", str(input_path)])
    with contextlib.redirect_stdout(output):
        omm_cli_main()
    cli_result = json.loads(output.getvalue())

    mcp_result = decision_compare_sequence_patterns(DecisionSequenceInput(**request))
    assert cli_result == mcp_result
    assert cli_result["capability_id"] == "decision.compare_sequence_patterns"
    assert cli_result["status"] == "completed_unvalidated_model_comparison"
    assert cli_result["scope"] == {
        "scope_id": request["scope_id"],
        "snapshot_id": request["snapshot_id"],
        "sequence_id": request["sequence_id"],
    }
    assert len(cli_result["model_results"]) == 2
    assert cli_result["warnings"]


def test_omm_contract_rejects_malformed_features_and_hmm_matrices():
    request = {
        "scope_id": "room:omm-schema",
        "sequence_id": "decision-trace-schema",
        "observations": [{"step_id": "step-1", "features": {
            "complex_features": True,
            "multidirectional_causation": True,
            "holistic_view": False,
            "creative_synthesis": True,
        }}],
        "models": [_model("one", 0.8), _model("two", 0.3)],
    }
    validate_request("decision.compare_sequence_patterns", request)

    malformed_features = copy.deepcopy(request)
    malformed_features["observations"][0]["features"]["holistic_view"] = "false"
    with pytest.raises(ContractError):
        validate_request("decision.compare_sequence_patterns", malformed_features)

    malformed_matrix = copy.deepcopy(request)
    malformed_matrix["models"][0]["transition_matrix"] = [[1.0, 0.0]]
    with pytest.raises(ContractError):
        validate_request("decision.compare_sequence_patterns", malformed_matrix)


def test_omm_one_step_trace_uses_initial_and_emission_likelihoods():
    pytest.importorskip("pomegranate")
    request = {
        "scope_id": "room:omm-one-step",
        "sequence_id": "decision-trace-one-step",
        "observations": [{"step_id": "step-1", "features": {
            "complex_features": True,
            "multidirectional_causation": False,
            "holistic_view": True,
            "creative_synthesis": False,
        }}],
        "models": [_model("high-emission", 0.8), _model("low-emission", 0.3)],
    }
    validate_request("decision.compare_sequence_patterns", request)
    result = decision_compare_sequence_patterns(DecisionSequenceInput(**request))
    assert result["observation_count"] == 1
    assert len(result["model_results"]) == 2
    assert all(len(item["posterior_state_probabilities"]) == 1 for item in result["model_results"])
    assert all(sum(item.values()) == pytest.approx(1.0) for item in result["model_results"][0]["posterior_state_probabilities"])


def test_exploratory_fit_cli_and_mcp_share_the_published_contract(tmp_path, monkeypatch, capsys):
    pytest.importorskip("pomegranate")
    observations = lambda prefix: [
        {"step_id": f"{prefix}-{index + 1}", "features": {
            "complex_features": index % 2 == 0,
            "multidirectional_causation": index % 3 != 0,
            "holistic_view": index % 4 < 2,
            "creative_synthesis": index % 5 == 0,
        }}
        for index in range(16)
    ]
    request = {
        "training_mode": "exploratory_unlabeled_baum_welch",
        "seed_model": _model("seed", 0.5),
        "sequences": [
            {"observations": observations("trace-a")},
            {"observations": observations("trace-b")},
        ],
        "max_iterations": 1,
    }
    validate_request("decision.fit_sequence_patterns", request)
    input_path = tmp_path / "fit-bundle.json"
    input_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-decision-sequences", "fit", str(input_path)])
    omm_cli_main()
    cli_result = json.loads(capsys.readouterr().out)

    mcp_result = decision_fit_sequence_patterns(DecisionSequenceFitInput(**request))
    assert cli_result == mcp_result
    assert cli_result["capability_id"] == "decision.fit_sequence_patterns"
    assert cli_result["status"] == "exploratory_unvalidated_fit"
    assert cli_result["observation_count"] == 32
    assert cli_result["model"]["parameter_status"] == "exploratory_unvalidated"
