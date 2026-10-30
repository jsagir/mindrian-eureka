import json
import sys

import pytest

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    return {
        "scope_id": "room:portfolio-test",
        "snapshot_id": "graph-snapshot-2026-10-19-01",
        "items": [
            {"id": "tech-a", "primary_tier": 1, "pair_count": 0, "degree": 2,
             "source_refs": ["mindrian-graph://node/tech-a"]},
            {"id": "tech-b", "primary_tier": 2, "pair_count": 4, "degree": 3,
             "source_refs": ["mindrian-graph://node/tech-b"]},
            {"id": "tech-c", "primary_tier": 3, "pair_count": 8, "degree": 1,
             "source_refs": ["mindrian-graph://node/tech-c"]},
        ],
        "pair": {
            "a_id": "tech-a",
            "b_id": "tech-b",
            "rs_source_ref": "mindrian-eureka://rs/run-1/pair-1",
            "rs": {"direction": "semantic_implementation", "abs_diff": 0.2, "passes": True},
        },
        "criteria_matrix": [[1, 0.5, 0.25], [2, 1, 0.5], [4, 2, 1]],
    }


def test_assessment_preserves_lineage_and_source_method_outputs():
    payload = request()
    validate_request("portfolio.assess_candidate_dimensions", payload)
    result = HANDLERS["portfolio.assess_candidate_dimensions"](payload)
    validate_result("portfolio.assess_candidate_dimensions", result)

    assessment = result["assessment"]
    assert (result["scope_id"], result["snapshot_id"]) == (payload["scope_id"], payload["snapshot_id"])
    assert assessment["candidate_ids"] == ["tech-a", "tech-b"]
    assert assessment["source_refs"]["tech-a"] == ["mindrian-graph://node/tech-a"]
    assert assessment["pair_dimensions"] == {
        "strategic_fit": 1,
        "validated_demand": 0.25,
        "tech_econ_feasibility": 1,
    }
    assert assessment["weighting"]["weights"] == pytest.approx([1 / 7, 2 / 7, 4 / 7])
    assert assessment["weighting"]["consistency_ratio"] == pytest.approx(0)
    assert assessment["portfolio_priority_signal"] == pytest.approx(11 / 14)


def test_cli_and_mcp_dispatch_share_the_same_contract_and_result(capsys, tmp_path, monkeypatch):
    payload = request()
    expected = HANDLERS["portfolio.assess_candidate_dimensions"](payload)
    assert mcp_server.scout_run_workflow("portfolio.assess_candidate_dimensions", payload) == expected

    input_file = tmp_path / "assessment.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.assess_candidate_dimensions", str(input_file)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected


def test_inconsistent_ahp_matrix_is_rejected_and_filesystem_sources_are_forbidden():
    bad_matrix = request()
    bad_matrix["criteria_matrix"] = [[1, 9, 1 / 9], [1 / 9, 1, 9], [9, 1 / 9, 1]]
    response = mcp_server.scout_run_workflow("portfolio.assess_candidate_dimensions", bad_matrix)
    assert response["status"] == "invalid_input"
    assert "AHP_INCONSISTENT" in response["error"]

    bad_source = request()
    bad_source["items"][0]["source_refs"] = ["/home/user/private.md"]
    response = mcp_server.scout_run_workflow("portfolio.assess_candidate_dimensions", bad_source)
    assert response["status"] == "invalid_input"
    assert "filesystem paths" in response["error"]
