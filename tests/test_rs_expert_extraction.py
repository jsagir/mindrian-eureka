import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def test_latest_rs_expert_extraction_cli_mcp_and_lineage_parity():
    request = {
        "scope_id": "room:rs-experts",
        "snapshot_id": "snapshot:papers-4",
        "papers": [
            {
                "id": "paper-a", "title": "Distributed sensing systems", "source": "openalex",
                "source_id": "openalex:paper-a", "source_url": "https://openalex.org/W1",
                "fetched_at": "2026-01-01T00:00:00Z", "cited_by_count": 30,
                "authors": [{"name": "Ada Lovelace", "orcid": "0000-0001-2345-6789", "institution": "MIT", "email": "ada@mit.edu"}],
            },
            {
                "id": "paper-b", "title": "Robust swarm control", "source": "arxiv",
                "source_id": "arxiv:paper-b", "source_url": "https://arxiv.org/abs/1234.5678",
                "retrieved_at": "2026-01-02T00:00:00Z", "cited_by_count": 4,
                "authors": ["ADA LOVELACE."],
            },
            {
                "id": "paper-c", "title": "Retracted study", "source": "openalex",
                "is_retracted": True, "cited_by_count": 100, "authors": ["Ada Lovelace"],
            },
        ],
    }
    validate_request("research.extract_experts_from_papers", request)
    expected = HANDLERS["research.extract_experts_from_papers"](request)
    validate_result("research.extract_experts_from_papers", expected)
    mcp_result = scout_run_workflow("research.extract_experts_from_papers", request)
    assert mcp_result == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "papers.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.extract_experts_from_papers", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == mcp_result

    ada = expected["experts"][0]
    assert ada["name"] == "Ada Lovelace"
    assert ada["paper_count"] == 2
    assert ada["h_index_estimate"] == 2
    assert ada["h_index_basis"] == "retrieved_papers_only"
    assert ada["identity_resolution"] == "name_merged_into_orcid"
    assert ada["confidence"] == 0.93
    assert ada["public_email_or_null"] == "ada@mit.edu"
    assert ada["evidence"][0]["url"] == "https://openalex.org/W1"
    assert expected["counts"]["excluded_retracted"] == 1
    assert expected["scope_id"] == request["scope_id"]
    assert expected["snapshot_id"] == request["snapshot_id"]
    assert "does not resolve experts against a room directory" in " ".join(expected["limitations"])


def test_rs_extraction_filters_local_content_and_returns_empty_state():
    result = HANDLERS["research.extract_experts_from_papers"]({
        "papers": [
            {"id": "p1", "title": "Paper with local content", "source": "openalex",
             "authors": ["Meeting_transcript Person", "Safe Author"]},
        ],
    })
    assert result["status"] == "experts_extracted"
    assert [expert["name"] for expert in result["experts"]] == ["Safe Author"]
    assert result["counts"]["skipped_authors"] == 1

    empty = HANDLERS["research.extract_experts_from_papers"]({"papers": []})
    assert empty["status"] == "no_authors_found"
    assert empty["experts"] == []
