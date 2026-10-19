import json
import sys

import pytest

from mindrian_eureka.contracts import ContractError, validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    return {
        "scope_id": "room:baseline-whitespace",
        "snapshot_id": "snapshot-2026-10-19-a",
        "embedding_model": "test-shared-vectors-v1",
        "artifacts": [
            {"id": "a1", "title": "Current devices", "section": "devices", "source_ref": "mindrian-graph://node/a1", "text": "current device sensing and diagnostics", "vector": [1, 0, 0, 0]},
            {"id": "a2", "title": "Device signals", "section": "devices", "source_ref": "mindrian-graph://node/a2", "text": "diagnostic signals from current devices", "vector": [.98, .1, 0, 0]},
            {"id": "a3", "title": "Remote monitoring", "section": "care", "source_ref": "mindrian-graph://node/a3", "text": "remote monitoring for care teams", "vector": [.9, 0, .2, 0]},
            {"id": "a4", "title": "Workflow notes", "section": "care", "source_ref": "mindrian-graph://node/a4", "text": "workflow and care coordination", "vector": [.8, .1, .2, 0]},
            {"id": "a5", "title": "Device maintenance", "section": "devices", "source_ref": "mindrian-graph://node/a5", "text": "maintenance for medical devices", "vector": [.95, -.05, 0, 0]},
        ],
        "baseline_frameworks": [
            {"id": "b1", "name": "Device diagnostics", "description": "device diagnostic signals", "source_ref": "https://example.test/b1", "vector": [1, 0, 0, 0]},
            {"id": "b2", "name": "Remote care monitoring", "description": "remote care monitoring", "source_ref": "https://example.test/b2", "vector": [.8, 0, .2, 0]},
            {"id": "b3", "name": "Distributed governance systems", "description": "governance across distributed systems", "source_ref": "https://example.test/b3", "vector": [0, 0, 0, 1]},
            {"id": "b4", "name": "Adaptive learning models", "description": "adaptive learning models", "source_ref": "https://example.test/b4", "vector": [0, 1, 0, 0]},
        ],
        "gap_percentile": 0,
        "max_results": 20,
    }


def test_baseline_whitespace_outputs_traceable_ranked_room_relative_leads():
    payload = request()
    validate_request("portfolio.analyze_baseline_whitespace", payload)
    result = HANDLERS["portfolio.analyze_baseline_whitespace"](payload)
    validate_result("portfolio.analyze_baseline_whitespace", result)
    assert result["scope"] == {"scope_id": payload["scope_id"], "snapshot_id": payload["snapshot_id"]}
    assert result["method"]["reducer"] == "deterministic_pca_fallback"
    assert result["gaps"]
    assert result["gaps"][0]["gap_score"] >= result["gaps"][-1]["gap_score"]
    assert all(gap["nearest_room_artifacts"] for gap in result["gaps"])
    assert all(item.get("source_ref") for gap in result["gaps"] for item in gap["nearest_room_artifacts"])


def test_baseline_whitespace_cli_and_mcp_use_same_contract(tmp_path, capsys, monkeypatch):
    payload = request()
    expected = HANDLERS["portfolio.analyze_baseline_whitespace"](payload)
    assert mcp_server.scout_run_workflow("portfolio.analyze_baseline_whitespace", payload) == expected
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.analyze_baseline_whitespace", str(path)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected


def test_baseline_whitespace_rejects_mixed_embedding_spaces_and_bad_limits():
    payload = request()
    payload["baseline_frameworks"][0]["vector"] = [1, 2]
    with pytest.raises(ContractError, match="same embedding dimension/model"):
        HANDLERS["portfolio.analyze_baseline_whitespace"](payload)
    payload = request()
    payload["gap_percentile"] = 1.1
    with pytest.raises(ContractError, match="gap_percentile"):
        HANDLERS["portfolio.analyze_baseline_whitespace"](payload)
