"""Tests that keep the reproduction guide true.

The guide is docs/reproduce-the-jhtv-method.md. These tests pin its headings, its commands,
its numbers, its status, its reproducible and not-reproducible sections and its replay block.
They read repo files only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from guide_support import (
    BEGIN,
    CITED_CLAIMS,
    CITED_PAIRS,
    END,
    RECORD_SENTENCE,
    REPLAY_RECORD_PATH,
    read_replay_record,
    replay_block,
    replay_statement,
)
from mindrian_eureka.example.contracts import (
    EXAMPLE_COMMAND,
    EXAMPLE_DIR,
    EXPECTED_NAME,
    RESULT_MATCH,
    RESULT_NO_MATCH,
)
from test_release_gate_record import parse_front_matter

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "reproduce-the-jhtv-method.md"
README = ROOT / "README.md"
EXAMPLE_README = ROOT / EXAMPLE_DIR / "README.md"
EXPECTED = ROOT / EXAMPLE_DIR / EXPECTED_NAME
RELEASE_RECORD = ROOT / "docs" / "rs-release-gate.md"
PYPROJECT = ROOT / "pyproject.toml"

LABEL = "candidate, not verified"
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
SHORT_CODE = re.compile(r"\b(RS|HSI)\b")
LINK = re.compile(r"\]\(([^)\s]+)\)")

HEADINGS = [
    "# Reproduce the JHTV method",
    "## Status of this guide",
    "## What this guide is for",
    "## What you need",
    "## Step 1. Install",
    "## Step 2. Check the machine",
    "## Step 3. Run the public example",
    "## Step 4. Check the hashes",
    "## Step 5. Read the ranked pairs",
    "## Step 6. Open the hub (optional)",
    "## Step 7. Run the method on your own folder",
    "## How this maps to the JHTV run",
    "## What is reproducible",
    "## The graph-derive replay",
    "## What is not reproducible",
    "## If your hashes do not match",
    "## Words you will meet",
]

README_HEADING = "## Reproduce the method on public data"
README_AFTER = "## Open the results as one page"
README_BEFORE = "## Quick start"


# --- helpers -----------------------------------------------------------------


def _guide() -> str:
    assert GUIDE.exists(), "docs/reproduce-the-jhtv-method.md does not exist yet"
    return GUIDE.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Return the body of one `## ` section, up to the next `## ` heading."""
    marker = f"\n{heading}\n"
    assert marker in f"\n{text}", f"missing heading {heading}"
    body = f"\n{text}".split(marker, 1)[1]
    return body.split("\n## ", 1)[0]


def _bullets(section: str) -> list[str]:
    return [line for line in section.splitlines() if line.startswith("- ")]


def _outside_fences(text: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return lines


def _release_front_matter() -> dict:
    return parse_front_matter(RELEASE_RECORD.read_text(encoding="utf-8"))


def _internal_only_required(front: dict) -> bool:
    """P-11: internal only unless the record has decision go and status decided."""
    return not (front["decision"] == "go" and front["status"] == "decided")


def _person_words(front: dict) -> list[str]:
    names: list[str] = []
    for key in ("decided_by", "partner_internal_decided_by"):
        value = front.get(key, "")
        value = re.sub(r"\(.*?\)", "", value).strip()
        if value:
            names.append(value)
            names.extend(value.split())
    return [name for name in names if len(name) >= 3]


def _table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def _links(text: str) -> list[str]:
    return LINK.findall(text)


def _link_exists(base: Path, target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return True
    path = target.split("#", 1)[0]
    return (base / path).exists()


# --- guide tests -------------------------------------------------------------


def test_headings_exact_and_in_order() -> None:
    found = [
        line
        for line in _outside_fences(_guide())
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert found == HEADINGS


def test_commands_are_the_contract_commands() -> None:
    text = _guide()
    example = EXAMPLE_COMMAND.replace("<run-folder>", "my-run")
    for command in (
        "uv sync --extra modern-encoder",
        "uv run eureka doctor",
        example,
        "uv run eureka check-example my-run",
        "uv run eureka hub my-run --out my-hub",
        "uv run eureka run ./my-sources --out ./eureka-run",
    ):
        assert command in text, command
    assert RESULT_MATCH in text
    assert RESULT_NO_MATCH in text


def test_example_numbers_come_from_the_expected_file() -> None:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    text = _guide()
    assert f"{expected['example']['records']} records" in text
    for output in expected["outputs"]:
        if "pairs" in output:
            assert f"{output['pairs']} pairs" in text, output["path"]


def test_links_resolve() -> None:
    text = _guide()
    targets = _links(text)
    assert targets, "the guide holds no link"
    for target in targets:
        assert _link_exists(GUIDE.parent, target), target


def test_wording_rules() -> None:
    text = _guide()
    assert EN_DASH not in text and EM_DASH not in text
    assert SHORT_CODE.search(text) is None
    assert text.count(LABEL) >= 6
    assert "not verified bit-for-bit" in text
    assert "It does not show novelty, evidence, demand or value." in text
    lowered = text.lower()
    for name in _person_words(_release_front_matter()):
        assert not re.search(rf"\b{re.escape(name.lower())}\b", lowered), name


def test_status_follows_the_release_record() -> None:
    front = _release_front_matter()
    guide_status = _section(_guide(), "## Status of this guide")
    readme_text = README.read_text(encoding="utf-8")
    assert readme_text.count(README_HEADING) == 1
    readme_status = _section(readme_text, README_HEADING)
    example_status = EXAMPLE_README.read_text(encoding="utf-8")
    if _internal_only_required(front):
        for name, text in (("guide", guide_status), ("readme", readme_status)):
            assert "internal only" in text.lower(), name
            assert "docs/rs-release-gate.md" in text or "rs-release-gate.md" in text, name
            if front["decision"] == "no-go":
                assert "no-go" in text, name
        assert "internal only" in example_status.lower()
        assert "rs-release-gate.md" in example_status
        if front["decision"] == "no-go":
            assert "no-go" in example_status
        assert "docs/rs-release-gate.md" in guide_status
        for gap in front["reopen_when"]:
            assert gap in guide_status, gap
    else:
        for name, text in (
            ("guide", guide_status),
            ("readme", readme_status),
            ("example", example_status),
        ):
            assert "internal only" not in text.lower(), name


def test_internal_only_is_enforced_by_exclusion() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"\[tool\.setuptools\.package-data\]\n(.*?)(?:\n\[|\Z)", text, re.DOTALL)
    assert match, "pyproject.toml has no package-data block"
    block = match.group(1)
    for word in ("examples", "docs", "reference-run"):
        assert word not in block, word


def test_reproducible_section() -> None:
    section = _section(_guide(), "## What is reproducible")
    assert len(_bullets(section)) >= 3
    for phrase in ("byte for byte", "manifest.json", "ENG-03"):
        assert phrase in section, phrase


def test_not_reproducible_section() -> None:
    section = _section(_guide(), "## What is not reproducible")
    assert len(_bullets(section)) >= 6
    for phrase in (
        "The JHTV collection is private.",
        "not verified bit-for-bit",
        "2026-10-29",
        "graph services",
        "another platform",
        "does not show novelty",
    ):
        assert phrase in section, phrase


def test_mapping_table() -> None:
    section = _section(_guide(), "## How this maps to the JHTV run")
    rows = _table_rows(section)
    assert rows, "no table"
    assert rows[0] == [
        "JHTV step",
        "What it was",
        "What Eureka does now",
        "Can you reproduce it",
    ]
    assert len(rows) - 1 >= 6
    assert all(len(row) == 4 for row in rows)


def test_replay_block_state() -> None:
    text = _guide()
    block = replay_block(text)
    assert text.count("Replay outcome") == 1
    assert "not recorded yet" not in text
    assert REPLAY_RECORD_PATH.exists()
    record = read_replay_record()
    assert record is not None
    assert block == replay_statement(record)


# --- replay statement unit cases (no file) -----------------------------------


def _check_statement(statement: str) -> None:
    assert LABEL in statement
    assert EN_DASH not in statement and EM_DASH not in statement
    assert "\n" not in statement
    assert statement.endswith(RECORD_SENTENCE)
    assert SHORT_CODE.search(statement) is None


def test_replay_statement_unit_cases() -> None:
    gap_done = replay_statement({"outcome": "provenance_gap", "room_mark": "done"})
    gap_wait = replay_statement({"outcome": "provenance_gap", "room_mark": "pending_approval"})
    for statement in (gap_done, gap_wait):
        _check_statement(statement)
        assert statement.startswith("Replay outcome: provenance gap.")
        assert "2,130 claims" in statement and "2,267,385 pairs" in statement
        assert "OPP-027 to OPP-031" in statement
        assert "Each of these candidates stays a candidate, not verified." in statement
    assert "is made in the room" in gap_done
    assert "waits for a host approval step" in gap_wait
    assert gap_done != gap_wait

    equal = replay_statement(
        {
            "outcome": "replayed",
            "claims": str(CITED_CLAIMS),
            "pairs": str(CITED_PAIRS),
            "two_run_hashes_equal": "true",
        }
    )
    _check_statement(equal)
    assert equal.startswith("Replay outcome: replayed.")
    assert "The counts are equal." in equal
    assert "The replay result is a candidate, not verified." in equal

    differ = replay_statement(
        {
            "outcome": "replayed",
            "claims": "2117",
            "pairs": "2239786",
            "two_run_hashes_equal": "true",
        }
    )
    _check_statement(differ)
    expected_counts = (
        "The counts differ: claims 2,117 against 2,130 and pairs 2,239,786 against 2,267,385."
    )
    assert expected_counts in differ

    with pytest.raises(ValueError):
        replay_statement({"outcome": "maybe"})
    with pytest.raises(ValueError):
        replay_statement({"outcome": "replayed", "pairs": "5", "two_run_hashes_equal": "true"})
    with pytest.raises(ValueError):
        replay_statement(
            {"outcome": "replayed", "claims": "5", "pairs": "5", "two_run_hashes_equal": "false"}
        )
    with pytest.raises(ValueError):
        replay_statement({"outcome": "provenance_gap"})


def test_statement_uses_only_listed_keys() -> None:
    """Text in a record key outside the listed keys must not reach the statement."""
    secret = "PRIVATE-ROOM-TEXT-9f3a"
    extra = {
        "label": secret,
        "note": secret,
        "title": secret,
        "checked_on": secret,
        "opportunity": secret,
    }
    gap = {"outcome": "provenance_gap", "room_mark": "pending_approval"}
    replayed = {
        "outcome": "replayed",
        "claims": str(CITED_CLAIMS),
        "pairs": str(CITED_PAIRS),
        "two_run_hashes_equal": "true",
    }
    for base in (gap, replayed):
        assert replay_statement({**base, **extra}) == replay_statement(base)
        assert secret not in replay_statement({**base, **extra})
    record = read_replay_record()
    assert record is not None
    statement = replay_statement(record)
    # `label` is excluded: the fixed label is constant text of the statement, not read from
    # the record, and the loop above proves a changed `label` value does not reach it.
    listed = {"outcome", "room_mark", "claims", "pairs", "two_run_hashes_equal", "label"}
    for key, value in record.items():
        if key not in listed and len(str(value)) > 12:
            assert str(value) not in statement


def test_replay_block_markers_unit_cases() -> None:
    assert replay_block(f"a\n{BEGIN}\n  x y  \n{END}\nb") == "x y"
    with pytest.raises(ValueError):
        replay_block(f"{BEGIN} x")
    with pytest.raises(ValueError):
        replay_block(f"{END} x {BEGIN}")
    with pytest.raises(ValueError):
        replay_block(f"{BEGIN} x {END} {BEGIN} y {END}")


def test_read_replay_record_unit_cases(tmp_path: Path) -> None:
    assert read_replay_record(tmp_path / "absent.md") is None
    good = tmp_path / "good.md"
    good.write_text("---\noutcome: provenance_gap\nroom_mark: done\n---\n\n# x\n", encoding="utf-8")
    record = read_replay_record(good)
    assert record is not None and record["outcome"] == "provenance_gap"
    bad = tmp_path / "bad.md"
    bad.write_text("---\noutcome: maybe\n---\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_replay_record(bad)
    none = tmp_path / "none.md"
    none.write_text("---\nlabel: x\n---\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_replay_record(none)


# --- README section ----------------------------------------------------------


def test_readme_section() -> None:
    text = README.read_text(encoding="utf-8")
    assert text.count(README_HEADING) == 1
    assert text.index(README_AFTER) < text.index(README_HEADING) < text.index(README_BEFORE)
    section = _section(text, README_HEADING)
    targets = _links(section)
    assert "docs/reproduce-the-jhtv-method.md" in targets
    assert "examples/public-example/README.md" in targets
    assert "uv run eureka check-example" in section
    assert LABEL in section
    assert EN_DASH not in section and EM_DASH not in section
    assert SHORT_CODE.search(section) is None
    for target in targets:
        assert _link_exists(ROOT, target), target
