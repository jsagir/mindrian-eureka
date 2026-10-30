import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _domain_analysis():
    source = HANDLERS["research.analyze_rs_domain_projection"]({
        "scope_id": "room:rs-query",
        "snapshot_id": "snapshot:rs-query-1",
        "topic": "wireless robot coordination under network disruption",
        "substrate": [
            {"id": "framework:distributed", "score": 0.9, "source_ids": ["source:ds"],
             "metadata": {"framework_name": "Distributed Systems", "title": "Network Coordination", "text": "Resilient communication for distributed robots facing network disruption", "tier": "core"}},
            {"id": "framework:control", "score": 0.85, "source_ids": ["source:control"],
             "metadata": {"framework_name": "Control Theory", "title": "Feedback Control", "text": "Robot feedback loops and coordination under communication disruption", "tier": "applied"}},
        ],
    })
    return {
        "scope_id": source["scope_id"],
        "snapshot_id": source["snapshot_id"],
        "domain_analysis": source["domain_analysis"],
    }


def test_rs_query_matrix_cli_mcp_contract_and_domain_stage_handoff():
    request = _domain_analysis()
    validate_request("research.generate_rs_query_matrix", request)
    expected = HANDLERS["research.generate_rs_query_matrix"](request)
    validate_result("research.generate_rs_query_matrix", expected)
    assert scout_run_workflow("research.generate_rs_query_matrix", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.generate_rs_query_matrix", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(result.stdout) == expected
    assert expected["status"] == "query_matrix_ready"
    assert expected["query_count"] == 60
    assert all(len(category) == 15 for category in expected["categories"].values())
    assert expected["categories"]["a_intersect_b"][0] == "Control Theory AND Distributed Systems"
    assert expected["scope_id"] == request["scope_id"]
    assert expected["snapshot_id"] == request["snapshot_id"]


def test_rs_query_matrix_rejects_source_hygiene_violations():
    request = _domain_analysis()
    request["domain_analysis"]["primary_domain"] = "SSN research"
    result = scout_run_workflow("research.generate_rs_query_matrix", request)
    assert result["status"] == "invalid_input"
