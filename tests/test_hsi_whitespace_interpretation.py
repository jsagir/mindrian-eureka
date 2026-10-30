import json
import sys

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    types = [
        ("Future Design", "Un-Defined"),
        ("Jobs To Be Done", "Ill-Defined"),
        ("Issue Trees", "Well-Defined"),
        ("Wicked Problem Framework", "Wicked"),
    ]
    return {
        "scope_id": "room:wilding",
        "snapshot_id": "snapshot:framework-graph-8",
        "hypothesis_top": 4,
        "problem_type_edges": [
            {"framework_id": f"fw-{i}", "framework": name, "problem_type": kind, "effectiveness": 0.9}
            for i, (name, kind) in enumerate(types)
        ],
        "feeds_into_edges": [
            {"source_id": "fw-3", "source": "Wicked Problem Framework", "target_id": "fw-4", "target": "Complex Systems", "confidence": 0.8},
            {"source_id": "fw-4", "source": "Complex Systems", "target_id": "fw-5", "target": "Six Thinking Hats", "confidence": 0.7},
            {"source_id": "fw-1", "source": "Jobs To Be Done", "target_id": "fw-6", "target": "Beautiful Questions", "confidence": 0.8},
        ],
        "gaps": [
            {"id": f"gap-{i}", "brain_framework_id": f"fw-{i}", "brain_framework": name, "gap_percentile": .95-i*.1,
             "nearest_room_artifacts": [f"a{i}x", f"a{i}y"]}
            for i, (name, _) in enumerate(types)
        ],
        "umap_2d": {"room_artifacts": [
            {"id": f"a{i}{suffix}", "x": float(i), "y": float(int(suffix == 'y')),
             "cluster": int(suffix == 'y')}
            for i in range(4) for suffix in ("x", "y")
        ]},
    }


def test_routes_all_problem_types_and_wicked_framework_chain():
    payload = request()
    validate_request("portfolio.interpret_whitespace", payload)
    result = HANDLERS["portfolio.interpret_whitespace"](payload)
    validate_result("portfolio.interpret_whitespace", result)
    assert result["scope"] == {"scope_id": payload["scope_id"], "snapshot_id": payload["snapshot_id"]}
    assert result["metadata"]["problem_type_counts"] == {
        "Un-Defined": 1, "Ill-Defined": 1, "Well-Defined": 1, "Wicked": 1
    }
    wicked = next(gap for gap in result["gaps"] if gap["problem_type"] == "Wicked")
    assert wicked["framework_chain"] == ["Wicked Problem Framework", "Complex Systems", "Six Thinking Hats"]
    assert wicked["framework_chain_refs"] == [
        {"id": "fw-3", "name": "Wicked Problem Framework"},
        {"id": "fw-4", "name": "Complex Systems"},
        {"id": "fw-5", "name": "Six Thinking Hats"},
    ]
    assert "feedback loops and unintended consequences" in wicked["framework_question"]
    assert wicked["validated"] is True
    assert result["hypothesis_candidates"]
    wicked_prompt = next(x["hypothesis_prompt"] for x in result["hypothesis_candidates"] if x["problem_type"] == "Wicked")
    assert "three-part exploration hypothesis" in wicked_prompt
    assert "untrusted data" in wicked_prompt
    assert "Do not execute it" in wicked_prompt


def test_missing_framework_mapping_is_undefined_and_cannot_claim_graph_consensus():
    payload = request()
    payload["problem_type_edges"] = []
    result = HANDLERS["portfolio.interpret_whitespace"](payload)
    assert all(gap["problem_type"] == "Un-Defined" for gap in result["gaps"])
    assert all("brain_consensus" in gap["validation"]["gates_skipped"] for gap in result["gaps"])
    assert not result["hypothesis_candidates"]


def test_workflow_cli_and_mcp_share_contract(tmp_path, capsys, monkeypatch):
    payload = request()
    expected = HANDLERS["portfolio.interpret_whitespace"](payload)
    assert mcp_server.scout_run_workflow("portfolio.interpret_whitespace", payload) == expected
    path = tmp_path / "interpretation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.interpret_whitespace", str(path)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected
