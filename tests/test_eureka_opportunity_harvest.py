import json
import sys

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    nodes = [
        {"id": "a", "type": "technology", "properties": {"section": "market-analysis"}},
        {"id": "b", "type": "technology", "properties": {"section": "solution-design"}},
        {"id": "c", "type": "technology", "properties": {"section": "solution-design"}},
        {"id": "d", "type": "technology", "properties": {"section": "solution-design"}},
        {"id": "lonely", "type": "technology", "properties": {}},
        {"id": "ws1", "type": "WhitespaceZone", "properties": {}},
        {"id": "hub", "type": "technology", "properties": {"section": "hub-section"}},
    ]
    edges = [
        {"source": "a", "target": "b", "type": "RELATED_TO"},
        {"source": "c", "target": "d", "type": "COMPETES_WITH"},
        {"source": "b", "target": "c", "type": "CONTRADICTS"},
        {"source": "ws1", "target": "a", "type": "RELATED_TO"},
    ]
    for i in range(8):
        node_id = f"spoke-{i}"
        nodes.append({"id": node_id, "type": "technology", "properties": {}})
        edges.append({"source": "hub", "target": node_id, "type": "RELATED_TO"})
    return {
        "scope_id": "room:harvest-test",
        "snapshot_id": "graph-snapshot-harvest-01",
        "snapshot": {
            "completeness": "complete_authorized_scope",
            "omitted_nodes": 0,
            "omitted_edges": 0,
            "nodes": nodes,
            "edges": edges,
        },
        "bank_dedup_complete": True,
        "banked_opportunity_names": [],
    }


def test_graph_event_harvest_applies_source_lanes_gates_and_lineage():
    payload = request()
    validate_request("opportunity.harvest_graph_events", payload)
    result = HANDLERS["opportunity.harvest_graph_events"](payload)
    validate_result("opportunity.harvest_graph_events", result)

    assert (result["scope_id"], result["snapshot_id"]) == (payload["scope_id"], payload["snapshot_id"])
    candidates = result["harvest"]["candidates"]
    lanes = {candidate["source_event"] for candidate in candidates}
    assert {"bridge", "contradiction", "whitespace"} <= lanes
    assert not any("hub" in candidate["evidence_handles"] for candidate in candidates)
    assert not any("lonely" in candidate["evidence_handles"] for candidate in candidates)
    assert all(candidates[i - 1]["score"] >= candidates[i]["score"] for i in range(1, len(candidates)))
    cross = next(c for c in candidates if c["evidence_handles"] == ["a", "b"])
    within = next(c for c in candidates if c["evidence_handles"] == ["c", "d"])
    assert cross["score"] > within["score"]
    assert cross["harvest_index"]["value"] == "unknown"
    assert result["run_config"]["harvest_index_status"] == "EXPERIMENTAL"
    serialized = json.dumps(result)
    assert "market-analysis" not in serialized
    assert "solution-design" not in serialized


def test_harvest_cli_and_mcp_share_output_and_full_scope_gate(capsys, tmp_path, monkeypatch):
    payload = request()
    expected = HANDLERS["opportunity.harvest_graph_events"](payload)
    assert mcp_server.scout_run_workflow("opportunity.harvest_graph_events", payload) == expected

    input_file = tmp_path / "harvest.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "opportunity.harvest_graph_events", str(input_file)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected

    incomplete = request()
    incomplete["snapshot"]["completeness"] = "partial_projection"
    response = mcp_server.scout_run_workflow("opportunity.harvest_graph_events", incomplete)
    assert response["status"] == "invalid_input"


def test_harvest_rejects_dangling_or_duplicate_graph_records():
    dangling = request()
    dangling["snapshot"]["edges"].append({"source": "missing", "target": "a", "type": "RELATED_TO"})
    response = mcp_server.scout_run_workflow("opportunity.harvest_graph_events", dangling)
    assert response["status"] == "invalid_input"
    assert "complete node projection" in response["error"]

    duplicate = request()
    duplicate["snapshot"]["nodes"].append(duplicate["snapshot"]["nodes"][0])
    response = mcp_server.scout_run_workflow("opportunity.harvest_graph_events", duplicate)
    assert response["status"] == "invalid_input"
    assert "duplicate graph node IDs" in response["error"]
