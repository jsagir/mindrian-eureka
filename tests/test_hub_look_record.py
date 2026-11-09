"""Evidence, status form, open items and hygiene of the Phase 2.3.1 look record (plan 09).

The record is `docs/brand/hub-review-result.md`, section "Phase 2.3.1 look". The evidence is the
phase folder of Phase 2.3.1. The Phase 2.1 evidence stays pinned by its own inventory, and this
file repeats that pin so a run of the new capture script cannot damage it (T-02.3.1-29).

No test here treats anything as owner approval. The status line of the new section must take
one of three exact forms, and "Approved by" needs a dated Brand stop block in the decisions
file (T-02.3.1-28). The book CLI may be called by the capture script with the read-only
`doctor` argument only (T-02.3.1-30, owner ruling R-01).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE = (ROOT / ".planning/phases"
         / "02.3.1-hub-look-matches-the-live-jhtv-site-cobalt-red-and-yellow-ac")
EVIDENCE = PHASE / "evidence"
OLD_PHASE = ROOT / ".planning/phases/02.1-opportunity-hub-in-the-mos-brand-format"
OLD_EVIDENCE = OLD_PHASE / "evidence"
RECORD = ROOT / "docs/brand/hub-review-result.md"
DECISIONS = ROOT / "docs/brand/hub-design-decisions.md"
SCRIPT = ROOT / "scripts/hub_look_capture.py"
BRAND = ROOT / "docs/brand"
SECTION = "## Phase 2.3.1 look"
WIDTHS = (320, 390, 768, 1280, 1600)
# The Phase 2.1 budget is 6,000,000 bytes for 37 screens. Scaled to 44 screens that is
# 7,135,135 bytes, rounded up to the next million.
BUDGET = 8_000_000
REVIEW_SENTENCE = "book review: not run, lock not reconciled, by owner ruling R-01; advisory"
WRITE_VERB = re.compile(
    r"mos-brand(?:\.cjs)?(?:\s+\S+)*?\s+"
    r"(?:asset\s+--replace|refresh\s+--apply|adopt\s+--apply|init|configure|run\s+approve)\b"
)
PLAN_WRITE_VERB = re.compile(
    r"mos-brand(?:\.cjs)?\s+(?:asset|refresh|adopt|init|configure|run\s+approve)\b"
)
DASH = re.compile("[–—]")
RULES_FILES = ("hub-model-rules.md", "hub-figure-rules.md", "hub-terms-rules.md",
               "hub-theme-rules.md", "hub-site-rules.md")


def planned_names() -> set[str]:
    names = {f"{part}-{w}" for w in WIDTHS
             for part in ("bank", "graph", "catalogue", "top", "pair", "record")}
    names |= {"locked-390", "locked-1280", "panel-pair-1280", "panel-record-390",
              "empty-1280", "diagram-1280"}
    names |= {"dark-top-1280", "dark-bank-390", "dark-bank-1280", "dark-graph-1280",
              "dark-catalogue-1280", "dark-panel-pair-1280", "dark-pair-1280",
              "dark-record-390"}
    assert len(names) == 44
    return names


def section_text() -> str:
    text = RECORD.read_text(encoding="utf-8")
    assert SECTION + "\n" in text, "the record lacks the section Phase 2.3.1 look"
    return text.split(SECTION + "\n", 1)[1]


def sub_section(name: str) -> str:
    body = section_text()
    match = re.search(rf"^### {re.escape(name)}\s*$", body, re.M)
    assert match, f"sub heading missing: {name}"
    rest = body[match.end():]
    nxt = re.search(r"^###? ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_inventory_matches_the_stored_screens() -> None:
    inventory = json.loads((EVIDENCE / "data/files.json").read_text(encoding="utf-8"))
    for key in ("capture_command", "screens_total_bytes", "files"):
        assert key in inventory, key
    screens = sorted((EVIDENCE / "screens").glob("*.jpg"))
    assert len(screens) == 44
    total = sum(path.stat().st_size for path in screens)
    assert total == inventory["screens_total_bytes"]
    assert total < BUDGET
    listed = {entry["path"] for entry in inventory["files"]}
    for path in screens:
        assert path.relative_to(ROOT).as_posix() in listed, path.name
        assert path.read_bytes()[:2] == b"\xff\xd8", path.name
    for entry in inventory["files"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        assert sha(path) == entry["sha256"], entry["path"]


def test_screen_names_are_the_planned_set() -> None:
    stored = {path.stem for path in (EVIDENCE / "screens").glob("*.jpg")}
    assert stored == planned_names()


def test_record_section() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert not DASH.search(text), "a dash character is in the record"
    body = section_text()
    for heading in ("Status", "Commands run", "Review results", "Measurements",
                    "Screenshot inspection", "Browser results", "Not verified here",
                    "Open items for the owner"):
        assert f"### {heading}\n" in body, heading
    for name in sorted(planned_names()):
        links = re.findall(rf"\[{re.escape(name)}\.jpg\]\(([^)]+)\)", body)
        assert links, f"no link for {name}.jpg"
        for target in links:
            assert (RECORD.parent / target).is_file(), target


def test_status_line_has_one_of_three_forms() -> None:
    lines = [line for line in sub_section("Status").splitlines() if line.strip()]
    assert lines, "the Status sub section is empty"
    status = lines[0].strip()
    pending = status.startswith("Implementation complete; visual verification pending the owner.")
    approved = re.match(r"^Approved by (\S.*?) on (\d{4}-\d{2}-\d{2})\.", status)
    rejected = re.match(r"^Not approved on (\d{4}-\d{2}-\d{2})", status)
    assert pending or approved or rejected, status
    if approved:
        date = approved.group(2)
        decisions = DECISIONS.read_text(encoding="utf-8")
        match = re.search(r"^## Brand stop\s*$", decisions, re.M)
        assert match, "the decisions file has no Brand stop section"
        block = decisions[match.end():]
        nxt = re.search(r"^## ", block, re.M)
        block = block[: nxt.start()] if nxt else block
        assert f"{date}, Phase 2.3.1 look" in block, "no dated Brand stop block for the new look"
        assert "Reviewer label" in block or "reviewer label" in block
        assert "owner's words" in block or "In the owner's words" in block or '"' in block


def test_open_items_are_listed() -> None:
    items = sub_section("Open items for the owner")
    expected = {
        "R-01": "IN FORCE", "O-01": "NOT APPROVED",
        "O-02": "ACCEPTED 2026-11-08", "O-04": "ACCEPTED 2026-11-08",
        "O-05": "ACCEPTED 2026-11-08", "O-06": "ACCEPTED 2026-11-08",
        "O-07": "ACCEPTED 2026-11-08", "O-08": "ACCEPTED 2026-11-08",
        "O-03": "DEFAULT IN FORCE", "O-09": "DEFAULT IN FORCE",
        "O-10": "DEFAULT IN FORCE", "O-11": "DEFAULT IN FORCE",
        "O-12": "OPEN", "O-13": "APPROVED", "O-14": "ADVISORY",
    }
    open_lines = []
    for ident, state in expected.items():
        matches = [line for line in items.splitlines() if re.match(rf"^- {ident}\b", line)]
        assert len(matches) == 1, f"{ident} must be on exactly one line"
        assert state in matches[0], f"{ident} lacks the state {state}"
        if "OPEN" in matches[0]:
            open_lines.append(ident)
    o12 = next(line for line in items.splitlines() if line.startswith("- O-12"))
    assert "Refero" in o12 and "not connected" in o12
    final = [line for line in items.splitlines() if line.startswith("- Final brand stop:")]
    assert len(final) == 1
    if "OPEN" in final[0]:
        open_lines.append("Final")
    assert set(open_lines) <= {"O-12", "Final"}, open_lines


def test_review_status_is_honest() -> None:
    status = json.loads((EVIDENCE / "data/review-status.json").read_text(encoding="utf-8"))
    assert status["review"] == REVIEW_SENTENCE
    assert "doctor_status" in status and "problems" in status
    assert "findings" not in status and "results" not in status
    assert REVIEW_SENTENCE.lower() in sub_section("Review results").lower()


def test_capture_script_runs_no_book_write_command() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert not WRITE_VERB.search(text), "the capture script names a book write verb"
    calls = re.findall(r"\[\s*\"node\"\s*,\s*str\(CLI\)\s*,([^\]]*)\]", text)
    assert calls, "the script has no book CLI call list"
    assert all(call.strip() == '"doctor"' for call in calls), calls
    assert len(calls) == 1, "every book CLI call goes through one helper"
    control = text + "\nsubprocess.run(['node', 'mos-brand.cjs', 'asset', '--replace'])\n"
    assert WRITE_VERB.search(control), "the negative control did not trip the check"


def test_no_plan_holds_a_book_write_command() -> None:
    plans = sorted(PHASE.glob("02.3.1-0?-PLAN.md"))
    if not plans:
        pytest.skip("no plan file present")
    for plan in plans:
        for number, line in enumerate(plan.read_text(encoding="utf-8").splitlines(), 1):
            assert not PLAN_WRITE_VERB.search(line), f"{plan.name}:{number}: {line}"


def test_phase_2_1_evidence_is_untouched() -> None:
    inventory = json.loads((OLD_EVIDENCE / "data/files.json").read_text(encoding="utf-8"))
    screens = list((OLD_EVIDENCE / "screens").glob("*.jpg"))
    reviews = list((OLD_EVIDENCE / "review").glob("*.json"))
    assert len(screens) == 37 and len(reviews) == 7
    total = sum(path.stat().st_size for path in screens)
    assert total == inventory["screens_total_bytes"] < 6_000_000
    for entry in inventory["files"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        assert sha(path) == entry["sha256"], entry["path"]


def test_public_only_and_provenance() -> None:
    digest = sha(ROOT / "tests/fixtures/hub_public/run/manifest.json")
    files = sorted((EVIDENCE / "data").glob("public-subset-*.json"))
    assert len(files) == 2, files
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["source_manifest_sha256"] == digest
        assert data["scores_recomputed"] is False and data["cutoffs_changed"] is False


def test_rules_files_are_linked_from_the_decisions_record() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    for name in RULES_FILES:
        links = re.findall(rf"\]\(({re.escape(name)})\)", text)
        assert links, f"the decisions record does not link {name}"
        assert (BRAND / name).is_file(), name
        assert not DASH.search((BRAND / name).read_text(encoding="utf-8")), name


def test_no_target_names() -> None:
    path = os.environ.get("EUREKA_NAME_DENYLIST")
    if not path or not Path(path).is_file():
        pytest.skip("no denylist supplied")
    terms = [line.strip().lower() for line in Path(path).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    assert terms
    files = [p for p in PHASE.rglob("*") if p.is_file() and p.suffix in {".md", ".json", ".css"}]
    files += [p for p in BRAND.rglob("*") if p.is_file()]
    files += [ROOT / "README.md", ROOT / "src/README.md",
              ROOT / "examples/public-example/README.md", SCRIPT, Path(__file__),
              ROOT / "tests/test_hub_readme_claims.py"]
    for file in files:
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="replace").lower()
        for term in terms:
            assert term not in text, f"a denylisted term is in {file.relative_to(ROOT)}"
