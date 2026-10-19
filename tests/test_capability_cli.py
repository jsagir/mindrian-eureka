import json
import sys
from pathlib import Path

from mindrian_eureka.cli import main


CATALOG = Path(__file__).parents[1] / "src/mindrian_eureka/data/capability-catalog.v1.json"


def invoke(monkeypatch, capsys, *arguments):
    monkeypatch.setattr(sys, "argv", ["eureka", "capabilities", *arguments])
    main()
    return json.loads(capsys.readouterr().out)


def test_compact_capability_catalog_preserves_all_jobs_and_readiness(monkeypatch, capsys):
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    result = invoke(monkeypatch, capsys, "--summary")

    assert result["schema_version"] == source["schema_version"]
    assert result["catalog_version"] == source["catalog_version"]
    assert result["count"] == len(source["capabilities"]) == 66
    assert {item["id"] for item in result["capabilities"]} == {item["id"] for item in source["capabilities"]}
    assert result["counts_by_status"] == {
        "experimental": 53,
        "host_brokered": 5,
        "blocked": 4,
        "planned": 4,
    }
    for item in result["capabilities"]:
        assert item["name"]
        assert item["jtbd"]
        assert item["status"]
        assert "cli" in item
        assert "mcp" in item
        assert "input_schema" not in item
        assert "output_schema" not in item


def test_capability_catalog_can_filter_by_readiness_and_jtbd(monkeypatch, capsys):
    blocked = invoke(monkeypatch, capsys, "--summary", "--status", "blocked")
    assert blocked["count"] == 4
    assert all(item["status"] == "blocked" for item in blocked["capabilities"])
    assert all(item["cli"] is None and item["mcp"] is None for item in blocked["capabilities"])

    selected = invoke(monkeypatch, capsys, "--summary", "--search", "wicked")
    assert selected["count"] > 0
    assert all("wicked" in json.dumps(item).casefold() for item in selected["capabilities"])


def test_default_capabilities_output_remains_full_catalog(monkeypatch, capsys):
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    result = invoke(monkeypatch, capsys)
    assert result == source
