import json
import sys

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    return {
        "scope_id": "room:statement-test",
        "snapshot_id": "graph-snapshot-statement-01",
        "candidate": {
            "a": {
                "id": "tech-a", "title": "Alpha", "primary_problem": "pa", "section": "sa",
                "dimensions": {"strategic_fit": 1, "validated_demand": 0.1, "tech_econ_feasibility": 0.9},
                "source_refs": ["mindrian-graph://node/tech-a"],
            },
            "b": {
                "id": "tech-b", "title": "Beta", "primary_problem": "pb", "section": "sb",
                "dimensions": {"strategic_fit": 0.1, "validated_demand": 0.2, "tech_econ_feasibility": 0.8},
                "source_refs": ["mindrian-graph://node/tech-b"],
            },
            "shared_problems": ["cold chain"],
            "shared_problem_source_refs": ["mindrian-research://finding/cold-chain"],
            "priority_signal": 0.8,
            "priority_signal_source_ref": "mindrian-eureka://assessment/assess-01",
            "rank": 3,
            "rank_source_ref": "mindrian-portfolio://ranking/run-02",
            "tail": True,
        },
    }


def test_statement_is_source_shaped_sanitized_and_never_banked():
    payload = request()
    payload["candidate"]["a"]["title"] = "Alpha\nSecond \u2014 line"
    validate_request("opportunity.prepare_statement", payload)
    result = HANDLERS["opportunity.prepare_statement"](payload)
    validate_result("opportunity.prepare_statement", result)

    draft = result["draft"]
    assert result["status"] == "draft_pending_host_review"
    assert (result["scope_id"], result["snapshot_id"]) == (payload["scope_id"], payload["snapshot_id"])
    assert draft["critic"] == "pending" and draft["banked"] is False
    assert "Alpha Second - line" in draft["text"]
    assert "both sides unvalidated on demand" in draft["text"]
    assert draft["text"].endswith(". Rank: 3")
    assert draft["fields"]["composite"] == 0.8
    assert draft["weak_dimensions"] == {
        "a": ["validated_demand"],
        "b": ["strategic_fit", "validated_demand"],
    }
    assert draft["node_source_refs"]["tech-a"] == ["mindrian-graph://node/tech-a"]
    assert draft["rank_source_ref"] == "mindrian-portfolio://ranking/run-02"


def test_statement_cli_and_mcp_share_the_same_draft(capsys, tmp_path, monkeypatch):
    payload = request()
    expected = HANDLERS["opportunity.prepare_statement"](payload)
    assert mcp_server.scout_run_workflow("opportunity.prepare_statement", payload) == expected

    input_file = tmp_path / "statement.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "opportunity.prepare_statement", str(input_file)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected


def test_statement_rejects_local_paths_and_same_endpoint():
    bad_path = request()
    bad_path["candidate"]["shared_problem_source_refs"] = ["/private/source.md"]
    response = mcp_server.scout_run_workflow("opportunity.prepare_statement", bad_path)
    assert response["status"] == "invalid_input"
    assert "filesystem paths" in response["error"]

    same_endpoint = request()
    same_endpoint["candidate"]["b"]["id"] = "tech-a"
    response = mcp_server.scout_run_workflow("opportunity.prepare_statement", same_endpoint)
    assert response["status"] == "invalid_input"
    assert "distinct graph node IDs" in response["error"]
