import json
import sys

from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.opportunity_pairs.jobs import JobStore
from mindrian_eureka import scout_cli
from mindrian_eureka.workflow_cli import main as workflow_cli_main


def _request():
    artifacts = [
        ("a1", "battery storage grid energy resilience"),
        ("a2", "clinical imaging diagnostic medical sensors"),
        ("a3", "agricultural irrigation water crop yield"),
        ("a4", "electrochemical battery storage power system"),
        ("a5", "medical imaging sensors diagnostic equipment"),
    ]
    return {
        "scope_id": "room-demo",
        "snapshot_id": "mindrian-snapshot-17",
        "top_k": 5,
        "artifacts": [
            {"id": artifact_id, "source_ref": f"mindrian-graph://node/{artifact_id}", "text": text}
            for artifact_id, text in artifacts
        ],
        "dense_vectors": {
            "a1": [1, 0, 0], "a2": [0, 1, 0], "a3": [0, 0, 1],
            "a4": [0.9, 0.1, 0], "a5": [0.1, 0.9, 0],
        },
    }


def test_latest_hsi_bundle_runs_through_cli_and_mcp(monkeypatch, tmp_path, capsys):
    request = _request()
    mcp_result = mcp_server.scout_run_workflow("portfolio.find_hybrid_similarity_pairs", request)
    assert mcp_result["capability_id"] == "portfolio.find_hybrid_similarity_pairs"
    assert mcp_result["scope"] == {"scope_id": "room-demo", "snapshot_id": "mindrian-snapshot-17"}
    assert mcp_result["metadata"]["lexical_method"] == "hybrid"
    assert mcp_result["metadata"]["ranking"] == "percentile"
    assert mcp_result["artifacts"][0]["source_ref"].startswith("mindrian-graph://node/")

    input_file = tmp_path / "hsi-input.json"
    input_file.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.find_hybrid_similarity_pairs", str(input_file)])
    workflow_cli_main()
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result["scope"] == mcp_result["scope"]
    def stable_pairs(result):
        pairs = json.loads(json.dumps(result["hsi_pairs"]))
        for pair in pairs:
            for evidence in pair.get("source_trail", []):
                evidence.pop("retrieved_at", None)
        return pairs
    assert stable_pairs(cli_result) == stable_pairs(mcp_result)


def test_mindrian_graph_projection_flows_into_hsi_without_graph_access():
    graph_snapshot = {
        "nodes": [
            {"id": artifact_id, "labels": ["Research"], "name": text.split()[0].title(), "text": text}
            for artifact_id, text in [
                ("node-battery", "Battery storage grid energy resilience power research."),
                ("node-medical", "Clinical imaging diagnostic medical sensors patient research."),
                ("node-agriculture", "Agricultural irrigation water crop yield soil research."),
                ("node-electrochem", "Electrochemical battery storage power system research."),
                ("node-diagnostics", "Medical imaging sensors diagnostic equipment research."),
            ]
        ],
        "edges": [],
        "meta": {"scope_id": "room:graph-test", "snapshot_id": "mos-graph-snap-9"},
    }
    projection = mcp_server.scout_run_workflow("graph.prepare_artifact_bundle", {
        "snapshot": graph_snapshot, "objective": "Find surprising mechanisms", "scope_id": "room:graph-test",
    })
    request = {key: projection[key] for key in ("scope_id", "snapshot_id", "artifacts")}
    request["dense_vectors"] = {
        "node-battery": [1, 0, 0], "node-medical": [0, 1, 0], "node-agriculture": [0, 0, 1],
        "node-electrochem": [0.9, 0.1, 0], "node-diagnostics": [0.1, 0.9, 0],
    }
    result = mcp_server.scout_run_workflow("portfolio.find_hybrid_similarity_pairs", request)
    assert result["scope"] == {"scope_id": "room:graph-test", "snapshot_id": "mos-graph-snap-9"}
    assert {row["id"] for row in projection["artifacts"]} == {row["id"] for row in result["artifacts"]}
    assert all(row["source_ref"].startswith("mindrian-graph://node/") for row in result["artifacts"])


def test_graph_projection_is_directly_accepted_by_combined_scout_mcp_and_cli(monkeypatch, tmp_path, capsys):
    from mindrian_eureka.contracts import validate_request

    graph_snapshot = {
        "nodes": [
            {"id": f"node-{index}", "name": f"Research {index}", "text": f"Source mechanism and finding {index} with supporting evidence."}
            for index in range(5)
        ],
        "edges": [],
        "meta": {"scope_id": "room:combined", "snapshot_id": "mos-graph-snap-31"},
    }
    projection = mcp_server.scout_run_workflow("graph.prepare_artifact_bundle", {
        "snapshot": graph_snapshot, "objective": "Find mechanisms across research", "scope_id": "room:combined",
    })
    validate_request("opportunity.synthesize_discovery_signals", projection)
    request = mcp_server.OpportunityScoutInput.model_validate(projection)
    captured = {}
    monkeypatch.setattr(mcp_server.manager, "start", lambda payload, key=None: captured.update(payload=payload, key=key) or {"job_id": "test-job"})
    response = mcp_server.scout_start_opportunity_signal_scout(request)
    assert response["job_id"] == "test-job"
    assert captured["payload"]["scope_id"] == "room:combined"
    assert captured["payload"]["snapshot_id"] == "mos-graph-snap-31"
    assert [row["id"] for row in captured["payload"]["artifacts"]] == [row["id"] for row in projection["artifacts"]]

    cli_capture = {}
    class FakeManager:
        def __init__(self, _data_dir):
            pass
        def start(self, payload):
            cli_capture.update(payload)
            return {"job_id": "cli-test-job"}
        def status(self, _job_id):
            return {"status": "completed"}
        def result(self, _job_id):
            return {"scope": {"scope_id": cli_capture["scope_id"], "snapshot_id": cli_capture["snapshot_id"]}}

    input_file = tmp_path / "graph-projection.json"
    input_file.write_text(json.dumps(projection), encoding="utf-8")
    monkeypatch.setattr(scout_cli, "JobManager", FakeManager)
    monkeypatch.setattr(sys, "argv", ["eureka-scout", str(input_file), "--data-dir", str(tmp_path / "data")])
    scout_cli.main()
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result["scope"] == {"scope_id": "room:combined", "snapshot_id": "mos-graph-snap-31"}
    assert cli_capture["snapshot_id"] == "mos-graph-snap-31"

    store = JobStore(tmp_path / "store")
    job_id, created = store.create({**projection, "mode": "local", "capability_id": "opportunity.synthesize_discovery_signals"}, None)
    assert created is True
    with store._connect() as db:
        persisted_snapshot = db.execute("SELECT snapshot_id FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0]
    assert persisted_snapshot == "mos-graph-snap-31"


def test_combined_scout_result_matches_published_output_contract(monkeypatch, tmp_path):
    from mindrian_eureka import opportunity_discovery
    from mindrian_eureka.contracts import validate_result

    artifacts = [
        {"id": "a", "source_ref": "mindrian-graph://node/a", "title": "A", "text": "alpha mechanism"},
        {"id": "b", "source_ref": "mindrian-graph://node/b", "title": "B", "text": "beta mechanism"},
    ]
    monkeypatch.setattr(opportunity_discovery, "run_document", lambda *args, **kwargs: {
        "status": "completed", "scope": {"scope_id": "room:test", "snapshot_id": "snap-1"},
        "outputs": [{"rank": 1, "payload": {"left": {"artifact_id": "a"}, "right": {"artifact_id": "b"},
                                               "structural_similarity": 0.4, "semantic_similarity": 0.8,
                                               "disagreement": "semantic_above_structural", "direction": "a_to_b"},
                      "review_context": "Source-linked review context."}],
        "method_details": {"encoder": {"name": "fixture"}}, "warnings": [],
    })
    monkeypatch.setattr(opportunity_discovery, "run_hsi", lambda request: {
        "status": "completed_experimental", "hsi_pairs": [{"left_id": "a", "right_id": "b", "rank": 1,
            "hsi_score": 0.7, "hsi_percentile": 0.95, "surprise_type": "cross_domain",
            "source_trail": [{"artifact_id": "a"}, {"artifact_id": "b"}]}],
        "metadata": {"ranking": "percentile"}, "warnings": [],
    })

    result = opportunity_discovery.run_signal_synthesis(
        {"objective": "Explore links", "scope_id": "room:test", "snapshot_id": "snap-1",
         "artifacts": artifacts, "encoder": "fixture", "model_path": "unused"},
        data_dir=tmp_path, job_id="contract-test",
    )

    validate_result("opportunity.synthesize_discovery_signals", result)
    assert result["status"] == "completed"
    assert result["outputs"][0]["payload"]["signals"]["method_signal_count"] == 2
    assert result["outputs"][0]["payload"]["signals"]["rs"]["direction"] == "a_to_b"
