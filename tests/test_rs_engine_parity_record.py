"""Structure and number-drift checks for the canonical-path record.

The record is docs/rs-engine-parity.md. The numbers in its section 3 must equal
the committed baseline report. This test reads repo files only and runs no engine.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "rs-engine-parity.md"
REPRODUCTION = ROOT / "docs" / "hsi-rs-jhtv-reproduction.md"
BASELINE = ROOT / "tests" / "fixtures" / "rs_parity" / "baseline_report_pre_fix.json"
AFTER_FIX = ROOT / "tests" / "fixtures" / "rs_parity" / "report_after_tie_break_fix.json"
LSA_TIGHT_LIMIT = 1e-6

REQUIRED_KEYS = [
    "record",
    "version",
    "canonical_rs_path",
    "decided_by",
    "decided_on",
    "status",
    "evidence_report",
]
HEADINGS = [
    "## 1. Decision",
    "## 2. The three code paths",
    "## 3. Parity result",
    "## 4. JHTV smoke figures",
    "## 5. Known differences",
    "## 6. How the JHTV results relate",
    "## 7. Open fix list for path C",
    "## 8. How to run the parity test",
    "## 9. Scope",
]
SHA_PATH_A = "57c18df558d83fbffc8e9f7fda905729d0c0fbfe18a1c370b1db816efa3937f1"
SHA_PATH_B = "044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45"
REQUIRED_METRIC_KEYS = [
    "layers.layer1_ranker.max_abs_gap_delta",
    "layers.layer2_bm25.max_abs_delta",
    "layers.layer2_lsa.max_abs_delta",
    "layers.layer2_lsa.spearman",
    "layers.layer3_end_to_end.overlap_at_10",
    "layers.layer3_end_to_end.overlap_at_20",
    "layers.layer3_end_to_end.overlap_at_full",
    "layers.layer3_end_to_end.spearman_rank",
    "layers.layer3_end_to_end.sign_agreement",
    "layers.plugin_legacy_leg.overlap_at_full",
]
LAYER4_METRIC_KEYS = [
    "layers.layer4_real_model.overlap_at_10",
    "layers.layer4_real_model.overlap_at_20",
    "layers.layer4_real_model.overlap_at_full",
    "layers.layer4_real_model.spearman_rank",
    "layers.layer4_real_model.spearman_signed_gap",
    "layers.layer4_real_model.sign_agreement",
]
EM_DASH = chr(8212)


def _text() -> str:
    return RECORD.read_text(encoding="utf-8")


def parse_front_matter(text: str) -> dict:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "record must start with a front matter block"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    data: dict = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def section_three(text: str) -> str:
    """Text between the '## 3.' heading and the first '### ' or '## 4.' heading after it."""
    start = text.index("## 3. Parity result")
    body = text[start + len("## 3. Parity result"):]
    stops = [body.index(marker) for marker in ("\n### ", "\n## 4.") if marker in body]
    assert stops, "section 3 has no end marker"
    return body[: min(stops)]


def section_three_one(text: str) -> str:
    """Text between the '### 3.1' heading and the '## 4.' heading."""
    start = text.index("### 3.1")
    end = text.index("\n## 4.", start)
    return text[start:end]


def baseline_value(report: dict, dotted: str):
    node = report
    for part in dotted.split("."):
        node = node[part]
    return node


def metric_line(section: str, key: str) -> str:
    # The key is wrapped in backticks in the table, so match the quoted form.
    for line in section.splitlines():
        if f"`{key}`" in line:
            return line
    raise AssertionError(f"no metric row for {key} in section 3")


def check_drift(section: str, report: dict, keys: list[str]) -> list[str]:
    problems = []
    for key in keys:
        expected = format(baseline_value(report, key), ".4g")
        line = metric_line(section, key)
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if expected not in cells[1:2]:
            problems.append(f"{key}: expected {expected} in the value column, line is: {line}")
    return problems


def test_front_matter_keys_and_values():
    data = parse_front_matter(_text())
    for key in REQUIRED_KEYS:
        assert key in data and data[key] != "", f"missing front matter key: {key}"
    assert data["status"] == "decided"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["decided_on"])
    assert data["canonical_rs_path"].startswith("eureka-pair-scout")


def test_headings_exist_in_order():
    text = _text()
    position = -1
    for heading in HEADINGS:
        found = text.find("\n" + heading, position + 1)
        assert found > position, f"heading missing or out of order: {heading}"
        position = found


def test_script_hashes_for_path_a_and_b_present_in_full():
    text = _text()
    assert SHA_PATH_A in text
    assert SHA_PATH_B in text


def test_section_three_numbers_equal_baseline_report():
    report = json.loads(BASELINE.read_text(encoding="utf-8"))
    section = section_three(_text())
    keys = list(REQUIRED_METRIC_KEYS)
    if report["layers"].get("layer4_real_model") is not None:
        keys += LAYER4_METRIC_KEYS
    problems = check_drift(section, report, keys)
    assert not problems, "\n".join(problems)


def test_drift_check_detects_a_changed_number():
    # Guard for the guard: a changed number in a copy of section 3 must be reported.
    report = json.loads(BASELINE.read_text(encoding="utf-8"))
    section = section_three(_text())
    key = "layers.layer2_lsa.max_abs_delta"
    expected = format(baseline_value(report, key), ".4g")
    tampered = section.replace(f"| {expected} |", "| 9.999 |", 1)
    assert tampered != section
    assert check_drift(tampered, report, [key]), "drift check did not notice a changed number"


def test_section_seven_has_the_four_open_items():
    text = _text()
    start = text.index("## 7. Open fix list for path C")
    end = text.index("\n## 8.", start)
    section = text[start:end].lower()
    for word in ("tie-break", "clip", "dense-input", "top_k"):
        assert word in section, f"section 7 lacks a row for: {word}"
    assert "pending, scheduled" not in section, "the tie-break row must have a final status"


def test_known_difference_wording_and_smoke_figure_present():
    text = _text()
    assert "known difference" in text.lower()
    assert "0.423" in text


def test_no_em_dash():
    assert EM_DASH not in _text()


def test_links_to_reproduction_record_and_quotes_outcome_lines():
    text = _text()
    assert "hsi-rs-jhtv-reproduction.md" in text
    outcome_lines = [
        line for line in REPRODUCTION.read_text(encoding="utf-8").splitlines() if line.startswith("Outcome: reproduced")
    ]
    assert len(outcome_lines) == 2
    for line in outcome_lines:
        assert line in text, f"outcome line not quoted exactly: {line[:60]}"


def test_section_three_one_numbers_equal_after_fix_report():
    report = json.loads(AFTER_FIX.read_text(encoding="utf-8"))
    section = section_three_one(_text())
    keys = list(REQUIRED_METRIC_KEYS)
    if report["layers"].get("layer4_real_model") is not None:
        keys += LAYER4_METRIC_KEYS
    problems = check_drift(section, report, keys)
    assert not problems, "\n".join(problems)


def test_section_three_one_drift_check_detects_a_changed_number():
    report = json.loads(AFTER_FIX.read_text(encoding="utf-8"))
    section = section_three_one(_text())
    key = "layers.layer2_lsa.max_abs_delta"
    expected = format(baseline_value(report, key), ".4g")
    tampered = section.replace(f"| {expected} |", "| 9.999 |", 1)
    assert tampered != section
    assert check_drift(tampered, report, [key])


def test_tie_break_row_says_fixed_exactly_when_after_fix_lsa_delta_is_tight():
    report = json.loads(AFTER_FIX.read_text(encoding="utf-8"))
    text = _text()
    start = text.index("## 7. Open fix list for path C")
    end = text.index("\n## 8.", start)
    row = next(line for line in text[start:end].splitlines() if "tie-break" in line.lower() and line.startswith("|"))
    is_fixed = report["layers"]["layer2_lsa"]["max_abs_delta"] <= LSA_TIGHT_LIMIT
    assert ("fixed" in row.lower()) == is_fixed, row
