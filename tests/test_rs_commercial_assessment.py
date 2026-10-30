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
        "scope_id": "room:rs-commercial",
        "snapshot_id": "snapshot:rs-14",
        "discovery": {
            "query_concept": "distributed sensing",
            "doc_concept": "swarm coordination",
            "classification": "hybrid",
            "bridge_concept": "local consensus",
            "industry_signals_count": 4,
            "breakthrough_score": 7,
            "resolved_authors": [
                {"name": "Ada Lovelace", "source_ids": ["paper:1"]},
                {"name": "Grace Hopper", "source_ids": ["paper:2", "paper:3"]},
            ],
            "resolved_institutions": [{"name": "MIT", "source_ids": ["paper:1"]}],
        },
    }


def test_rs_commercial_case_cli_mcp_contract_and_lineage():
    request = _request()
    validate_request("research.assess_rs_commercial_case", request)
    expected = HANDLERS["research.assess_rs_commercial_case"](request)
    validate_result("research.assess_rs_commercial_case", expected)
    assert scout_run_workflow("research.assess_rs_commercial_case", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.assess_rs_commercial_case", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == expected
    assert expected["status"] == "commercial_hypothesis_ready"
    assert expected["market_size_estimate"].startswith("mid-market:")
    assert expected["value_proposition"] == (
        "Bridge distributed sensing and swarm coordination via local consensus "
        "to unlock a defensible cross-domain moat"
    )
    assert expected["partnership_targets"] == [
        {"name": "Ada Lovelace", "type": "author", "score": 1, "source_ids": ["paper:1"]},
        {"name": "Grace Hopper", "type": "author", "score": 0.5, "source_ids": ["paper:2", "paper:3"]},
        {"name": "MIT", "type": "institution", "score": 1, "source_ids": ["paper:1"]},
    ]
    assert expected["input_fingerprint"] == HANDLERS["research.assess_rs_commercial_case"](request)["input_fingerprint"]


def test_rs_commercial_case_preserves_unknown_market_signal():
    request = _request()
    request["discovery"].pop("breakthrough_score")
    result = HANDLERS["research.assess_rs_commercial_case"](request)
    assert result["market_size_estimate"] == "unknown-bucket: insufficient signal to estimate market size"
    assert "not a TAM/SAM estimate" in " ".join(result["limitations"])
