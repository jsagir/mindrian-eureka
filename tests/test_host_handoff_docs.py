"""Doc tests for the engine run hand-off contract and the places that link to it (Phase 3, plan 07).

The tests read repo files and the code that the doc describes. They pin the headings, the
required terms, the parity with the two published schemas, the parity with the refusal codes
and with the registered tool names, the house style and the links.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "mos-eureka-engine-run-contract.md"
README = ROOT / "README.md"
HOST = ROOT / "docs" / "integrations" / "mindrianos.md"
ENGINE_DOC = ROOT / "docs" / "engines" / "opportunity-pairs.md"
USAGE = ROOT / "docs" / "using-capabilities.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
SCHEMAS = ROOT / "src" / "mindrian_eureka" / "data" / "schemas"
INPUT_SCHEMA = SCHEMAS / "pair-screen-input.v1.json"
OUTPUT_SCHEMA = SCHEMAS / "pair-screen-output.v1.json"

HEADINGS = [
    "# MindrianOS engine run contract (opportunity.run_pair_screen)",
    "## What this page is for",
    "## What Eureka provides",
    "## The call order",
    "## The approval step",
    "## Request, key by key",
    "## Result, key by key",
    "## Refusals and errors",
    "## Room scope and what is never written",
    "## How MindrianOS should wire the command",
    "## The provenance gap marks",
    "## Rules for the consumer",
    "## Plugin facts checked on 2026-11-07",
    "## Open questions for the plugin phase",
]
LABEL = "candidate, not verified"
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
FENCE = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
SCOUT_TOKEN = re.compile(r"scout_[a-z_]+")
COMMIT = re.compile(r"\b[0-9a-f]{9,12}\b")

PLAN_TOOL = "scout_plan_pair_screen"
START_TOOL = "scout_start_pair_screen"
HOST_RUN_HEADING = "## The engine run: opportunity.run_pair_screen"
README_MCP_HEADING = "## Run the MCP server"


def _read(path: Path) -> str:
    assert path.exists(), f"missing file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _contract() -> str:
    return _read(CONTRACT)


def _section(text: str, heading: str) -> str:
    assert text.count(heading + "\n") == 1, f"heading not found once: {heading}"
    after = text.split(heading + "\n", 1)[1]
    return after.split("\n## ", 1)[0]


def _without_fences(text: str) -> str:
    return FENCE.sub("", text)


def _schema_names(node: Any, found: set[str]) -> None:
    """Collect every property name and every $defs name of a schema."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            found.update(properties)
        defs = node.get("$defs")
        if isinstance(defs, dict):
            found.update(defs)
        for value in node.values():
            _schema_names(value, found)
    elif isinstance(node, list):
        for value in node:
            _schema_names(value, found)


def _names_of(path: Path) -> set[str]:
    names: set[str] = set()
    _schema_names(json.loads(path.read_text(encoding="utf-8")), names)
    return names


def test_contract_headings_are_exact_and_in_order() -> None:
    lines = _without_fences(_contract()).splitlines()
    found = [line for line in lines if line.startswith("# ") or line.startswith("## ")]
    assert found == HEADINGS


def test_contract_names_the_surface() -> None:
    text = _contract()
    for term in (
        PLAN_TOOL,
        START_TOOL,
        "scout_status",
        "scout_result",
        "scout_cancel",
        "scout_delete_job",
        "scout_record_review",
        "opportunity.run_pair_screen",
        "/mos:eureka",
        "ALLOWED_MCP_ROUTES",
        "ASYNC_ROUTES",
        "plan_digest",
        "approval_ref",
        "verified_by_engine",
        "status: refused",
        "room_write",
        "MINDRIAN_EUREKA_RS_MODEL_PATH",
        "eureka run",
        "PROVEN",
        "ASSUMED",
    ):
        assert term in text, term
    facts = _section(text, "## Plugin facts checked on 2026-11-07")
    assert COMMIT.search(facts), "no commit hash in the plugin facts"
    assert "MindrianOS-Plugin" in facts


def test_contract_covers_every_input_schema_key() -> None:
    names = _names_of(INPUT_SCHEMA)
    assert {"objective", "scope_id", "snapshot_id", "artifacts", "approval"} <= names
    section = _section(_contract(), "## Request, key by key")
    missing = sorted(name for name in names if f"`{name}`" not in section)
    assert missing == []


def test_contract_covers_every_output_schema_key() -> None:
    names = _names_of(OUTPUT_SCHEMA)
    assert {"files", "id_map", "outputs", "payload", "host_handoff", "persistence"} <= names
    section = _section(_contract(), "## Result, key by key")
    missing = sorted(name for name in names if f"`{name}`" not in section)
    assert missing == []


def test_contract_lists_every_refusal_code() -> None:
    from mindrian_eureka.host_run.contracts import REASONS

    section = _section(_contract(), "## Refusals and errors")
    missing = sorted(code for code in REASONS if f"`{code}`" not in section)
    assert missing == []


def test_tool_names_equal_the_registered_functions() -> None:
    from mindrian_eureka.opportunity_pairs import mcp_server

    text = _contract()
    for name in (PLAN_TOOL, START_TOOL):
        assert name in text
        assert callable(getattr(mcp_server, name, None)), name
    tokens = set(SCOUT_TOKEN.findall(text))
    unknown = sorted(token for token in tokens if not hasattr(mcp_server, token))
    assert unknown == []


def test_contract_states_the_approval_limits() -> None:
    text = _contract()
    approval = _section(text, "## The approval step")
    for term in ("cannot verify", "audit", "single use", "24 hours", "idempotency"):
        assert term in approval, term
    assert text.count(LABEL) >= 3
    assert "Eureka writes nothing to a room" in text


def test_contract_forbids_a_silent_retry_and_a_start_without_approval() -> None:
    text = _contract()
    wiring = _section(text, "## How MindrianOS should wire the command")
    assert "silently" in wiring
    assert "without approval" in wiring
    approval = _section(text, "## The approval step")
    assert "refus" in approval


def test_contract_carries_the_provenance_hand_off() -> None:
    text = _contract()
    marks = _section(text, "## The provenance gap marks")
    for term in (
        "docs/jhtv-replay-record.md",
        "scripts/emit-provenance-gap-list",
        "OPP-027",
        "OPP-031",
        "room_mark",
        "pending_approval",
        "host-owned write",
        "approval",
    ):
        assert term in marks, term
    assert re.search(r"only a later Eureka quick task\b[^.]*\bdone\b", marks)


def test_contract_carries_the_plugin_phase_facts() -> None:
    text = _contract()
    for term in ("387", "routeGate", "2,500", "100", "3,000", "200"):
        assert term in text, term


def test_contract_house_style() -> None:
    text = _contract()
    assert EN_DASH not in text
    assert EM_DASH not in text
    lowered = text.lower()
    assert "university" not in lowered
    assert "institute" not in lowered
    for name in ("Sagir", "Aronhime", "Jonathan", "Lawrence"):
        assert name not in text, name
    assert "/home/" not in text
    assert "/mnt/" not in text
    assert SHORT_CODE.search(text) is None


def test_contract_links_exist() -> None:
    targets = LINK.findall(_contract())
    for target in targets:
        if target.startswith(("http://", "https://")):
            continue
        assert (CONTRACT.parent / target).exists(), target


def test_host_doc_section_and_limits() -> None:
    text = _read(HOST)
    assert text.count(HOST_RUN_HEADING + "\n") == 1
    assert (
        text.index("## The reverse leg: a room seed")
        < text.index(HOST_RUN_HEADING)
        < text.index("## External research and confidentiality")
    )
    section = _section(text, HOST_RUN_HEADING)
    for term in (
        "docs/mos-eureka-engine-run-contract.md",
        PLAN_TOOL,
        "writes nothing to a room",
        LABEL,
    ):
        assert term in section, term
    for target in LINK.findall(section):
        if not target.startswith(("http://", "https://")):
            assert (HOST.parent / target).exists(), target
    assert EN_DASH not in section and EM_DASH not in section
    assert "Input is bounded at 2,500 artifacts and 20 MiB of UTF-8 artifact text" not in text
    assert re.search(r"3,000 artifacts[^.]*\b200\b[^.]*20 MiB", text)
    assert "2,500" in text


def test_engine_doc_limit_is_corrected() -> None:
    text = _read(ENGINE_DOC)
    assert "Input limit: 2,500 artifacts" not in text
    assert "3,000 artifacts" in text


def test_usage_and_architecture_docs_list_the_tools() -> None:
    for path in (USAGE, ARCHITECTURE):
        text = _read(path)
        assert PLAN_TOOL in text, path.name
        assert START_TOOL in text, path.name


def test_readme_points_to_the_contract() -> None:
    text = _read(README)
    section = _section(text, README_MCP_HEADING)
    assert PLAN_TOOL in section
    assert "docs/mos-eureka-engine-run-contract.md" in section
    for target in LINK.findall(section):
        if not target.startswith(("http://", "https://")):
            assert (README.parent / target).exists(), target
    assert EN_DASH not in section and EM_DASH not in section
    assert SHORT_CODE.search(section) is None
    order = [
        "## Run Eureka on your own folder",
        "## Open the results as one page",
        "## Start a room from one pair",
        "## Quick start",
    ]
    positions = [text.index(heading) for heading in order]
    assert positions == sorted(positions)
