"""Doc tests for the encoder profiles page (Phase 5, plan 06).

The tests read `docs/encoder-profiles.md` and the code that the page describes. They pin the
headings, the parity of the profile table with `encoder_spec.PROFILES`, the marks on claims,
the list of build sites that are not routed yet, the plugin hand-offs and the house style.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "encoder-profiles.md"

TITLE = "# Encoder profiles"
HEADINGS = [
    "## What this page is",
    "## The two profiles",
    "## The one rule: never mix",
    "## How a run records its encoder",
    "## How to pick a profile",
    "## How a non-exact run is checked",
    "## Install for the GPU profile",
    "## Build sites not routed yet",
    "## Hand-offs for the MindrianOS plugin session",
    "## Parked and later",
]
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
FENCE = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
NUMBERED = re.compile(r"^(\d+)\. ", re.MULTILINE)
MARKS = ("PROVEN", "INFERRED", "UNVERIFIED", "ASSUMED")
TABLE_COLUMNS = [
    "Profile",
    "Model id",
    "Dimension",
    "Device",
    "Dtype",
    "Maximum tokens",
    "Query prefix",
    "Document prefix",
    "Status",
    "Extra",
    "Source",
]


def _text() -> str:
    assert PAGE.exists(), "missing file: docs/encoder-profiles.md"
    return PAGE.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    assert text.count(heading + "\n") == 1, f"heading not found once: {heading}"
    after = text.split(heading + "\n", 1)[1]
    return after.split("\n## ", 1)[0]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _unquote(cell: str) -> str:
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`"):
        return cell[1:-1]
    return cell


def _profile_rows() -> dict[str, dict[str, str]]:
    section = _section(_text(), "## The two profiles")
    rows = [line for line in section.splitlines() if line.startswith("|")]
    assert len(rows) >= 3, "the profile table is missing"
    header = _cells(rows[0])
    assert header == TABLE_COLUMNS
    found: dict[str, dict[str, str]] = {}
    for line in rows[2:]:
        cells = _cells(line)
        assert len(cells) == len(header), line
        row = dict(zip(header, cells, strict=True))
        found[_unquote(row["Profile"])] = row
    return found


def test_document_exists_and_has_the_headings() -> None:
    lines = FENCE.sub("", _text()).splitlines()
    found = [line for line in lines if line.startswith("# ") or line.startswith("## ")]
    assert found == [TITLE, *HEADINGS]


def test_profile_table_equals_the_code() -> None:
    from mindrian_eureka.encoder_spec import PROFILE_EXTRA, PROFILE_STATUS, PROFILES

    rows = _profile_rows()
    assert sorted(rows) == sorted(PROFILES)
    for name, spec in PROFILES.items():
        row = rows[name]
        assert _unquote(row["Model id"]) == spec.model_id
        assert row["Dimension"] == str(spec.dimension)
        assert row["Device"] == spec.device
        assert row["Dtype"] == (spec.dtype if spec.dtype is not None else "none")
        cap = spec.max_seq_length
        expected_cap = str(cap) if cap is not None else "model default"
        assert row["Maximum tokens"] == expected_cap
        assert _unquote(row["Query prefix"]) == (spec.query_prefix or "(empty)")
        assert _unquote(row["Document prefix"]) == (spec.document_prefix or "(empty)")
        assert row["Status"] == PROFILE_STATUS[name]
        assert _unquote(row["Extra"]) == PROFILE_EXTRA[name]
        assert row["Source"], name


def test_claims_are_marked() -> None:
    text = _text()
    for word in ("PROVEN", "UNVERIFIED", "ASSUMED"):
        assert word in text, word
    section = _section(text, "## The two profiles")
    assert "docs/encoder-spike-results.md" in section
    assert "UNVERIFIED" in section
    for term in ("prefix whitespace", "attention setting", "revision pin"):
        assert term in section, term


def test_follow_up_sites_are_listed() -> None:
    section = _section(_text(), "## Build sites not routed yet")
    for site in (
        "hsi_engine.py",
        "analogy_fitness.py",
        "pitch_analysis/algorithm.py",
        "hsi_reference.py",
        "runner.py",
        "run/engines.py",
        "doctor.py",
    ):
        assert site in section, site
    assert "sha256" in section
    assert "not edited" in section
    rows = [line for line in section.splitlines() if line.startswith("|")][2:]
    assert len(rows) == 6
    assert "Six sites are not routed in this phase" in section
    assert "only for the `--encoder-profile` path" in section
    assert "_default_loader" in section
    assert "ReferenceBertEncoder" in section
    assert "identity=spec.identity()" in section
    for row in rows:
        cells = _cells(row)
        assert len(cells) == 4, row
        assert all(cells), row


def _hand_off_items() -> list[str]:
    section = _section(_text(), "## Hand-offs for the MindrianOS plugin session")
    marks = list(NUMBERED.finditer(section))
    items = []
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(section)
        items.append(section[mark.start() : end])
    return items


def test_hand_offs_are_numbered_and_sourced() -> None:
    items = _hand_off_items()
    assert len(items) == 10
    for index, item in enumerate(items, start=1):
        assert item.startswith(f"{index}. "), index
        assert "Source" in item, index
        assert any(mark in item for mark in MARKS), index
    joined = "\n".join(items).lower()
    for term in (
        "environment allowlist",
        "stderr",
        "doctor",
        "request field",
        "contract version marker",
        "vec0",
        "384",
        "2048",
        "0.55",
        "gpu-encoder",
        "local_model_unavailable",
    ):
        assert term.lower() in joined, term


def test_parked_items_have_no_work() -> None:
    section = _section(_text(), "## Parked and later")
    for term in ("local NIM", "topic taxonomy", "OpenAlex Topics", "JHTV", "default encoder"):
        assert term in section, term
    assert "- [ ]" not in section
    assert "- [x]" not in section
    assert "TODO" not in section


def test_check_section_matches_the_code() -> None:
    from mindrian_eureka.example import contracts as example_contracts

    section = _section(_text(), "## How a non-exact run is checked")
    for term in ("gpu-approx", "cpu-exact", "eureka check-example"):
        assert term in section, term
    threshold = example_contracts.GPU_APPROX_MIN_OVERLAP
    if threshold is None:
        assert "not measured yet" in section
    else:
        assert str(threshold) in section


def test_house_style() -> None:
    text = _text()
    assert EN_DASH not in text
    assert EM_DASH not in text
    assert not SHORT_CODE.search(text)
    assert "candidate, not verified" in text
    for number, line in enumerate(text.splitlines(), start=1):
        assert len(line) <= 400, f"line {number} is longer than 400 characters"
    for target in LINK.findall(text):
        if "://" in target:
            continue
        assert (PAGE.parent / target).resolve().exists(), target


def test_no_environment_variable_is_introduced() -> None:
    section = _section(_text(), "## How to pick a profile")
    assert "no environment variable" in section
    assert "--encoder-profile" in section
    assert not re.search(r"MINDRIAN_EUREKA_[A-Z_]*PROFILE", section)
    assert not re.search(r"MINDRIAN_EUREKA_[A-Z_]*PROFILE", _text())
