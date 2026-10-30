import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _request():
    return {
        "scope_id": "room:rs-score",
        "snapshot_id": "snap:rs-score-1",
        "query_concept": "distributed robot coordination under disruption",
        "doc_concept": "networked robot coordination resilience",
        "query_vector": [1.0, 0.0, 0.0],
        "doc_vector": [0.8, 0.6, 0.0],
        "query_node_id": "claim:problem",
        "doc_node_id": "claim:method",
        "query_source_ids": ["source:problem-1"],
        "doc_source_ids": ["source:method-1"],
    }


def test_differential_score_cli_mcp_contract_lineage_and_classifier_handoff():
    request = _request()
    validate_request("research.score_rs_differential_pair", request)
    expected = HANDLERS["research.score_rs_differential_pair"](request)
    validate_result("research.score_rs_differential_pair", expected)
    assert scout_run_workflow("research.score_rs_differential_pair", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.score_rs_differential_pair", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(result.stdout) == expected
    pair = expected["scored_pair"]
    assert pair["lsa"] == pytest.approx(0.29121941856368966)
    assert pair["bert"] == pytest.approx(0.8)
    assert pair["diff"] == pytest.approx(0.5087805814363104)
    assert pair["passes"] is True
    assert pair["evidence"] == [
        {"source_id": "source:problem-1", "side": "problem"},
        {"source_id": "source:method-1", "side": "method"},
    ]

    classified = HANDLERS["research.classify_rs_pair"]({
        "scope_id": expected["scope_id"],
        "snapshot_id": expected["snapshot_id"],
        "scored_pair": pair,
    })
    assert classified["classified_pair"]["classification"] == "structural_transfer"
    assert classified["classified_pair"]["evidence"] == pair["evidence"]


def test_differential_score_rejects_incompatible_vector_shapes():
    request = _request()
    request["doc_vector"] = [0.8, 0.6]
    result = scout_run_workflow("research.score_rs_differential_pair", request)
    assert result["status"] == "invalid_input"
    assert "same non-zero dimension" in result["error"]
