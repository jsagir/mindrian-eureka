import json
import sys

from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main


def _request():
    themes = [
        ("battery", "Battery chemistry stores renewable electricity for later grid use."),
        ("medical", "Clinical imaging sensors detect abnormalities in patient scans."),
        ("agriculture", "Irrigation systems distribute water to improve crop yields."),
        ("storage", "Electrochemical materials improve long duration energy storage."),
        ("diagnostics", "Medical diagnostic imaging uses sensors to detect disease."),
    ]
    return {
        "scope_id": "room:research",
        "snapshot_id": "mos-snapshot-29",
        "pairs": [
            {"id": f"pair-{index}", "a": text, "b": themes[(index + 1) % len(themes)][1],
             "source": f"mindrian-graph://node/{artifact_id}"}
            for index, (artifact_id, text) in enumerate(themes)
        ],
    }


def test_jason_cli_and_mcp_preserve_graph_projection_lineage(monkeypatch, tmp_path, capsys):
    request = _request()
    mcp_result = mcp_server.scout_run_workflow("analysis.compare_text_differences", request)
    assert mcp_result["scope"] == {"scope_id": "room:research", "snapshot_id": "mos-snapshot-29"}
    assert mcp_result["pairs"][0]["source_trail"]["source"].startswith("mindrian-graph://node/")

    input_file = tmp_path / "jason-input.json"
    input_file.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "analysis.compare_text_differences", str(input_file)])
    workflow_cli_main()
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result["scope"] == mcp_result["scope"]
    assert [row["id"] for row in cli_result["pairs"]] == [row["id"] for row in mcp_result["pairs"]]
    assert cli_result["provenance"]["input_sha256"] == mcp_result["provenance"]["input_sha256"]
