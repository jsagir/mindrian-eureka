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
        "scope_id": "room:rs-domain",
        "snapshot_id": "snapshot:frameworks-8",
        "topic": "wireless robot coordination under network disruption",
        "substrate": [
            {"id": "framework:distributed", "score": 0.9, "source_ids": ["claim:ds-1"],
             "metadata": {"framework_name": "Distributed Systems", "title": "Network Coordination", "text": "Resilient communication for distributed robots facing network disruption", "tier": "core"}},
            {"id": "framework:control", "score": 0.85, "source_ids": ["claim:control-2"],
             "metadata": {"framework_name": "Control Theory", "title": "Feedback Control", "text": "Robot feedback loops and coordination under communication disruption", "tier": "applied"}},
            {"id": "framework:oncology", "score": 0.8, "source_ids": ["claim:oncology-3"],
             "metadata": {"framework_name": "Oncology", "title": "Tumor Response", "text": "Cancer pathways and cell growth", "tier": "core"}},
        ],
    }


def test_rs_domain_projection_cli_mcp_contract_lineage_and_preprocessor_handoff():
    request = _request()
    validate_request("research.analyze_rs_domain_projection", request)
    expected = HANDLERS["research.analyze_rs_domain_projection"](request)
    validate_result("research.analyze_rs_domain_projection", expected)
    assert scout_run_workflow("research.analyze_rs_domain_projection", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.analyze_rs_domain_projection", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == expected
    assert expected["status"] == "domain_analysis_ready"
    assert expected["domain_analysis"]["primary_domain"] == "Control Theory"
    assert expected["ranked_domains"][0]["source_ids"] == ["claim:control-2"]
    assert expected["ranked_domains"][0]["node_id"] == "framework:control"

    downstream = HANDLERS["research.preprocess_rs_documents"]({
        "scope_id": expected["scope_id"],
        "snapshot_id": expected["snapshot_id"],
        "domain_analysis": expected["domain_analysis"],
        "documents": [{"id": "paper:robotics", "abstract": "Control Theory and Distributed Systems address wireless robot coordination under network disruption."}],
    })
    assert downstream["records"][0]["concepts"]
    assert downstream["scope_id"] == expected["scope_id"]


def test_rs_domain_projection_empty_context_and_forbidden_topic():
    request = _request()
    request["substrate"] = []
    empty = HANDLERS["research.analyze_rs_domain_projection"](request)
    assert empty["status"] == "domain_analysis_boundary"
    assert empty["domain_analysis"]["warning"] == "substrate_empty_tier0"
    assert empty["domain_analysis"]["boundary_flag"] is True

    request = _request()
    request["topic"] = "SSN in wireless systems"
    rejected = scout_run_workflow("research.analyze_rs_domain_projection", request)
    assert rejected["status"] == "invalid_input"
