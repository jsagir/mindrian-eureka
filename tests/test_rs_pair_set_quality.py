import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _request():
    return {
        "scope_id": "room:rs-quality",
        "snapshot_id": "snapshot:rs-quality-1",
        "scored_pairs": [
            {"pair_id": f"pair:{i}", "lsa": 0.1 + i * 0.03, "bert": 0.3 + i * 0.02,
             "query_node_id": f"problem:{i}", "doc_node_id": f"method:{i}", "source_ids": [f"source:{i}"]}
            for i in range(12)
        ],
    }


def test_rs_pair_set_quality_cli_mcp_contract_and_lineage():
    request = _request()
    validate_request("research.assess_rs_pair_set_quality", request)
    expected = HANDLERS["research.assess_rs_pair_set_quality"](request)
    validate_result("research.assess_rs_pair_set_quality", expected)
    assert scout_run_workflow("research.assess_rs_pair_set_quality", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.assess_rs_pair_set_quality", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(result.stdout) == expected
    assert expected["status"] == "quality_gate_passed"
    assert expected["quality"]["ok"] is True
    assert expected["quality"]["stats"] == {"n": 12, "finite": 12, "corner_fraction": 0}
    assert expected["pair_lineage"][-1] == {
        "pair_id": "pair:11", "query_node_id": "problem:11", "doc_node_id": "method:11", "source_ids": ["source:11"]
    }


def test_rs_pair_set_quality_flags_seed018_corner_and_duplicate_ids():
    request = _request()
    request["scored_pairs"] = [
        {"pair_id": f"corner:{i}", "lsa": 0.98, "bert": 0.02, "source_ids": [f"source:{i}"]}
        for i in range(10)
    ]
    flagged = HANDLERS["research.assess_rs_pair_set_quality"](request)
    assert flagged["status"] == "quality_gate_flagged"
    assert flagged["quality"]["degenerate"] is True
    assert "seed018_corner_collapse" in flagged["quality"]["flags"]

    request["scored_pairs"][1]["pair_id"] = request["scored_pairs"][0]["pair_id"]
    rejected = scout_run_workflow("research.assess_rs_pair_set_quality", request)
    assert rejected["status"] == "invalid_input"
    assert "duplicate pair IDs" in rejected["error"]
