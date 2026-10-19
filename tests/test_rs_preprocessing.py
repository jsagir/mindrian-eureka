import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from mindrian_eureka.contracts import ContractError, validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _request():
    return {
        "scope_id": "room:rs-preprocess",
        "snapshot_id": "snapshot:papers-3",
        "domain_analysis": {
            "primary_domain": "distributed systems",
            "concepts": ["distributed sensing", "swarm coordination", "medical imaging"],
            "terminology": ["distributed systems"],
            "methods": ["local consensus"],
            "breakthroughs": ["fault-tolerant coordination"],
            "boundary_flag": False,
            "adjacent_domains": ["robotics"],
        },
        "documents": [
            {"id": "paper:1", "title": "Distributed sensing with local consensus", "abstract": "Researchers developed local consensus controls for swarm coordination. We measured system stability."},
            {"id": "paper:2", "title": "Quantum imaging"},
            {"id": "paper:3", "title": ""},
        ],
    }


def test_rs_preprocessing_cli_mcp_contract_and_boundary_features():
    request = _request()
    validate_request("research.preprocess_rs_documents", request)
    expected = HANDLERS["research.preprocess_rs_documents"](request)
    validate_result("research.preprocess_rs_documents", expected)
    assert scout_run_workflow("research.preprocess_rs_documents", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.preprocess_rs_documents", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == expected
    assert expected["scope_id"] == request["scope_id"]
    assert expected["counts"] == {
        "documents_received": 3, "documents_processed": 3,
        "documents_on_boundary": 2, "documents_missing_text": 1,
    }
    inside, outside, missing = expected["records"]
    assert inside["document_id"] == "paper:1"
    assert set(inside["concepts"]) == {"distributed sensing", "swarm coordination"}
    assert inside["relevance_score"] == 2 / 3
    assert inside["boundary_flag"] is False
    assert outside["boundary_flag"] is True
    assert missing["warning"] == "document_text_missing"


def test_rs_preprocessing_rejects_duplicate_ids_and_forbidden_domain_context():
    request = _request()
    request["documents"].append(dict(request["documents"][0]))
    with pytest.raises(ContractError, match="duplicate IDs"):
        HANDLERS["research.preprocess_rs_documents"](request)

    request = _request()
    request["domain_analysis"]["concepts"].append("SSN")
    result = scout_run_workflow("research.preprocess_rs_documents", request)
    assert result["status"] == "invalid_input"
    assert "forbidden_input" in result["error"]
