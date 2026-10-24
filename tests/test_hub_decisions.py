"""Structure test for the hub design decisions file (plan 02.1-01, HUB-02)."""

import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "brand" / "hub-design-decisions.md"
INTAKE = ROOT / ".mindrian" / "intake.json"
GITIGNORE = ROOT / ".gitignore"
README_BRAND = ROOT / "docs" / "brand-application.md"

EM_DASH = "—"
EN_DASH = "–"


def _text() -> str:
    return DECISIONS.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    assert match, f"section missing: {heading}"
    rest = text[match.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _table_rows(section: str) -> list[str]:
    return [line for line in section.splitlines() if line.startswith("|")]


def _book_root() -> Path | None:
    env = os.environ.get("MOS_BRAND_BOOK")
    for candidate in (env, str(Path.home() / "mos-brand")):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return None


def test_decision_table_has_the_seven_areas():
    intake = json.loads(INTAKE.read_text(encoding="utf-8"))
    has_graph_surface = "graph-visualization" in intake["what"]["surfaces"]
    rows = _table_rows(_section(_text(), "Decision table"))
    areas = ["Colour", "Type", "Layout", "Motion", "Theo face", "Graph", "Copy"]
    for area in areas:
        matches = [r for r in rows if r.split("|")[1].strip().lower().startswith(area.lower())]
        assert matches, f"no table row for {area}"
        row = matches[0]
        ok = "segments/" in row or "rule set" in row
        if not has_graph_surface and area in ("Colour", "Graph"):
            ok = ok or "not in packet" in row
        assert ok, f"row for {area} has no segment path: {row}"


def test_silent_register_has_all_18_items():
    section = _section(_text(), "Book-silent register (D-03)")
    for n in range(1, 19):
        line = next((l for l in section.splitlines() if re.match(rf"^{n}\. ", l)), None)
        assert line, f"silent item {n} missing"
        assert "proposed segment" in line, f"item {n} lacks 'proposed segment'"
    item10 = next(l for l in section.splitlines() if l.startswith("10. "))
    assert "Stricter by choice, proposed segment." in item10
    assert "Hub applies 13 px at all widths." in item10


def test_deviations_section():
    section = _section(_text(), "Deviations from the book guide")
    for needle in [
        "Bridge links thick yellow with red particles",
        "no particles",
        "1.54:1",
        "deviation, not book-derived; proposed segment",
        "Camera moves are short (760 ms)",
        "no in-page motion setting",
        "Instant camera",
    ]:
        assert needle in section, f"deviations section lacks: {needle}"
    for col in ("Item", "Book guide", "Hub", "Reason", "Status"):
        assert col in section.splitlines()[2] or col in section


def test_owner_word_section():
    section = _section(_text(), "OWNER-WORD answers")
    assert "D-14" in section
    assert "D-17" in section
    assert "D-14 owner ruling 2026-10-24: keep, label Potential eureka." in section


def test_no_dashes_in_decisions_and_intake():
    for path in (DECISIONS, INTAKE):
        content = path.read_text(encoding="utf-8")
        assert EM_DASH not in content, path
        assert EN_DASH not in content, path


def test_superseded_block_in_readme_decisions():
    head = "\n".join(README_BRAND.read_text(encoding="utf-8").splitlines()[:5])
    assert "Superseded for the hub on 2026-10-24 by docs/brand/hub-design-decisions.md" in head


def test_gitignore_lists_machine_files():
    lines = {l.strip() for l in GITIGNORE.read_text(encoding="utf-8").splitlines()}
    for entry in (
        ".mindrian/brand.lock.json",
        ".mindrian/WORKFLOW.md",
        ".mindrian/memory.db*",
        ".mindrian/memory.json",
    ):
        assert entry in lines, entry


def test_cited_segment_paths_exist_in_book():
    book = _book_root()
    if book is None:
        pytest.skip("book checkout not found (set MOS_BRAND_BOOK)")
    paths = set(re.findall(r"`(segments/[A-Za-z0-9_./-]+)`", _text()))
    assert paths, "no segment path cited"
    for rel in sorted(paths):
        assert (book / rel).exists(), f"cited segment missing in book: {rel}"
