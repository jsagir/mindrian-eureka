"""Doc tests for the room seed contract and the three places that link to it (Phase 2.3, SEED-06).

The tests read repo files only. They pin the headings, the required terms, the model boundary
sentence, the parity with the closed schema, the commands, the house style and the links.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "room-seed-contract.md"
README = ROOT / "README.md"
GUIDE = ROOT / "docs" / "partner-run-guide.md"
HOST = ROOT / "docs" / "integrations" / "mindrianos.md"
SCHEMA = ROOT / "src" / "mindrian_eureka" / "data" / "schemas" / "room-seed.v1.json"

HEADINGS = [
    "# Room seed contract (eureka.room-seed.v1)",
    "## What this page is for",
    "## Where a seed comes from",
    "## The seed folder",
    "## seed.json, key by key",
    "## Known and feed next",
    "## The evidence files",
    "## How MindrianOS should open a seed",
    "## The first step in the new room",
    "## The model boundary",
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

README_HEADING = "## Start a room from one pair"
GUIDE_HEADING = "## 8. Start a room from one pair"
HOST_HEADING = "## The reverse leg: a room seed"


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
    """Collect every property name and every $defs name of the schema."""
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


def test_contract_headings_are_exact_and_in_order() -> None:
    lines = _without_fences(_contract()).splitlines()
    found = [line for line in lines if line.startswith("# ") or line.startswith("## ")]
    assert found == HEADINGS


def test_contract_names_the_plugin_surface() -> None:
    text = _contract()
    for term in (
        "/mos:ignite --from-seed",
        "/mos:rooms new",
        "opportunity-bank",
        "review_status: proposed",
        "F.1",
        "BRIEF",
        "feed_next",
        "known",
        "suggested_sections",
        "eureka.room-seed.v1",
        "critic: pending",
        "banked: false",
        "ASSUMED",
        "PROVEN",
    ):
        assert term in text, term
    facts = _section(text, "## Plugin facts checked on 2026-11-07")
    assert "fe9ee3511" in facts


def test_contract_states_the_model_boundary() -> None:
    from mindrian_eureka.seed.contracts import MODEL_BOUNDARY

    text = _contract()
    boundary = _section(text, "## The model boundary")
    assert MODEL_BOUNDARY in boundary
    for word in ("offline", "partner", "model provider"):
        assert word in boundary, word
    assert text.count(LABEL) >= 3


def test_contract_covers_every_schema_key() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    names: set[str] = set()
    _schema_names(schema, names)
    assert {"scope_id", "snapshot_id", "feed_next", "model_boundary", "sha256"} <= names
    text = _contract()
    missing = sorted(name for name in names if f"`{name}`" not in text)
    assert missing == []


def test_contract_flags_the_derived_ids_and_the_statement_basis() -> None:
    text = _contract()
    for name in ("scope_id", "snapshot_id"):
        spots = [m.start() for m in re.finditer(re.escape(name), text)]
        assert any("derived" in text[max(0, s - 200) : s + 200] for s in spots), name
    assert "not MindrianOS ids" in text
    assert "opportunity.prepare_statement" in text
    assert "was not called" in text
    assert "untrusted" in text


def _seed_parser() -> argparse.ArgumentParser:
    from mindrian_eureka.seed.command import register_seed

    parser = argparse.ArgumentParser(prog="eureka")
    register_seed(parser.add_subparsers(dest="command"))
    return parser


def _command_lines(text: str) -> list[str]:
    lines: list[str] = []
    for block in FENCE.findall(text):
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith(("eureka seed", "uv run eureka seed")):
                lines.append(stripped)
    return lines


def _parse_command(line: str, parser: argparse.ArgumentParser) -> argparse.Namespace:
    line = re.sub(r"<[^>]*>", "1", line)
    tokens = shlex.split(line)
    start = tokens.index("seed")
    return parser.parse_args(["seed", *tokens[start + 1 :]])


def test_contract_commands_parse_with_the_real_parser() -> None:
    parser = _seed_parser()
    lines = _command_lines(_contract())
    assert len(lines) >= 3
    for line in lines:
        namespace = _parse_command(line, parser)
        assert namespace.command == "seed", line
    flags = " ".join(lines)
    for flag in ("--pair", "--cluster", "--list", "--min-degree"):
        assert flag in flags, flag


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


def _links_exist(path: Path, section: str) -> None:
    targets = LINK.findall(section)
    assert targets, "no link in the section"
    for target in targets:
        if target.startswith(("http://", "https://")):
            continue
        assert (path.parent / target).exists(), target


def test_readme_section() -> None:
    text = _read(README)
    assert text.count(README_HEADING + "\n") == 1
    assert (
        text.index("## Open the results as one page")
        < text.index(README_HEADING)
        < text.index("## Quick start")
    )
    section = _section(text, README_HEADING)
    for term in (
        "uv run eureka seed ./eureka-run --list",
        "--pair",
        "--cluster",
        "docs/room-seed-contract.md",
        LABEL,
    ):
        assert term in section, term
    _links_exist(README, section)
    assert EN_DASH not in section and EM_DASH not in section
    assert SHORT_CODE.search(section) is None


def test_guide_section() -> None:
    text = _read(GUIDE)
    assert text.count(GUIDE_HEADING + "\n") == 1
    assert (
        text.index("## 7. MindrianOS on the same machine")
        < text.index(GUIDE_HEADING)
        < text.index("## How the bundle is built")
    )
    section = _section(text, GUIDE_HEADING)
    for term in ("eureka seed", "room_sections", "docs/room-seed-contract.md", LABEL):
        assert term in section, term
    _links_exist(GUIDE, section)
    assert EN_DASH not in section and EM_DASH not in section
    lowered = section.lower()
    assert "university" not in lowered and "institute" not in lowered


def test_host_doc_section() -> None:
    text = _read(HOST)
    assert text.count(HOST_HEADING + "\n") == 1
    assert (
        text.index("## Tool contract")
        < text.index(HOST_HEADING)
        < text.index("## External research and confidentiality")
    )
    section = _section(text, HOST_HEADING)
    for term in ("docs/room-seed-contract.md", "eureka seed", "writes nothing to a room"):
        assert term in section, term
    _links_exist(HOST, section)
    assert EN_DASH not in section and EM_DASH not in section

