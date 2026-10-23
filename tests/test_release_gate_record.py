"""Presence and enum checks for the release-gate record of the unusual-pairs engine.

The record is docs/rs-release-gate.md. This test reads repo files only.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "rs-release-gate.md"
LICENSING = ROOT / "docs" / "licensing-and-provenance.md"

REQUIRED_KEYS = [
    "record",
    "version",
    "decision",
    "decision_scope",
    "decided_by",
    "decided_on",
    "status",
    "reopen_when",
    "evidence_checked_on",
]
HEADINGS = [
    "## 1. Summary",
    "## 2. Origin facts",
    "## 3. Author and citation facts",
    "## 4. License facts",
    "## 5. What the repo copied versus reimplemented",
    "## 6. Gap list",
    "## 7. Decision and conditions",
    "## 8. Effect on phases",
]


def _text() -> str:
    return RECORD.read_text(encoding="utf-8")


def parse_front_matter(text: str) -> dict:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "record must start with a front matter block"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    data: dict = {}
    current_list: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list is not None:
            data[current_list].append(line[4:].strip())
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            data[key] = []
            current_list = key
        else:
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            data[key] = value
            current_list = None
    return data


def _check_rules(fm: dict) -> list[str]:
    """Return rule violations for a parsed front matter block."""
    problems: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in fm:
            problems.append(f"missing key {key}")
    if problems:
        return problems
    if fm["record"] != "rs-source-release-gate":
        problems.append("record id wrong")
    if fm["decision"] not in {"go", "no-go", "internal-only"}:
        problems.append("decision not in enum")
    if fm["status"] not in {"draft", "decided"}:
        problems.append("status not in enum")
    if fm["status"] == "decided" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["decided_on"]):
        problems.append("decided record needs a YYYY-MM-DD date")
    if fm["status"] == "draft" and fm["decision"] != "no-go":
        problems.append("draft record must have decision no-go")
    if fm["decision"] == "go" and (fm["status"] != "decided" or fm["reopen_when"]):
        problems.append("go with open gaps is invalid")
    return problems


def test_front_matter_has_all_keys():
    fm = parse_front_matter(_text())
    for key in REQUIRED_KEYS:
        assert key in fm, key


def test_front_matter_rules_hold_for_the_record():
    assert _check_rules(parse_front_matter(_text())) == []


def test_record_id_and_enums():
    fm = parse_front_matter(_text())
    assert fm["record"] == "rs-source-release-gate"
    assert fm["decision"] in {"go", "no-go", "internal-only"}
    assert fm["status"] in {"draft", "decided"}


def test_decided_record_needs_a_date_and_draft_is_no_go():
    fm = parse_front_matter(_text())
    if fm["status"] == "decided":
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["decided_on"])
    else:
        assert fm["decision"] == "no-go"


def test_go_with_open_gaps_is_rejected():
    fm = parse_front_matter(_text())
    bad = dict(fm, decision="go", status="decided", decided_on="2026-01-01", reopen_when=["G1"])
    assert "go with open gaps is invalid" in _check_rules(bad)
    draft_go = dict(fm, decision="go", status="draft", reopen_when=[])
    assert _check_rules(draft_go)
    undated = dict(fm, decision="no-go", status="decided", decided_on="")
    assert "decided record needs a YYYY-MM-DD date" in _check_rules(undated)
    good = dict(fm, decision="go", status="decided", decided_on="2026-01-01", reopen_when=[])
    assert _check_rules(good) == []


def test_record_go_requires_no_open_gaps():
    fm = parse_front_matter(_text())
    if fm["decision"] == "go":
        assert fm["status"] == "decided"
        assert fm["reopen_when"] == []


def test_headings_exist_in_order():
    text = _text()
    positions = []
    for heading in HEADINGS:
        assert heading in text, heading
        positions.append(text.index(heading))
    assert positions == sorted(positions)


def test_gap_ids_in_gap_section():
    text = _text()
    start = text.index("## 6. Gap list")
    end = text.index("## 7. Decision and conditions")
    section = text[start:end]
    for gap in ("G1", "G2", "G3", "G4", "G5", "G6"):
        assert gap in section, gap
    assert "O1" in text


def test_author_name_is_held_privately():
    assert "name held privately" in _text()


def test_no_em_dash():
    dash = chr(8212)
    assert dash not in _text()
    assert dash not in LICENSING.read_text(encoding="utf-8")


def test_section_2_hashes_have_hex_format():
    text = _text()
    start = text.index("## 2. Origin facts")
    end = text.index("## 3. Author and citation facts")
    section = text[start:end]
    cells = [c.strip() for line in section.splitlines() if line.startswith("|") for c in line.split("|")]
    candidates = [c for c in cells if re.fullmatch(r"[0-9a-fA-F]{40,}", c)]
    assert len(candidates) >= 12
    for value in candidates:
        assert re.fullmatch(r"[0-9a-f]{64}", value), value


def test_licensing_note_links_to_record():
    assert "rs-release-gate.md" in LICENSING.read_text(encoding="utf-8")
