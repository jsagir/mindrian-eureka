"""W2 proof: the README shows the doctor and run commands before the quick start."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HEADING = "## Run Eureka on your own folder"
NEXT_HEADING = "## Quick start"
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
FENCE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _section() -> str:
    text = _text()
    assert text.count(HEADING) == 1
    after = text.split(HEADING, 1)[1]
    return after.split("\n## ", 1)[0]


def test_section_shows_the_doctor_and_run_commands() -> None:
    commands = [line for block in FENCE.findall(_section()) for line in block.splitlines()]
    assert "uv run eureka doctor" in commands
    assert "uv run eureka run ./my-sources --out ./eureka-run" in commands
    assert "uv sync --extra modern-encoder" in commands


def test_section_holds_the_label_and_the_offline_note() -> None:
    section = _section()
    assert "candidate, not verified" in section
    assert "Every result is a candidate, not verified. It is a lead for human review." in section
    assert "downloads nothing" in section
    assert "no network call" in section


def test_section_link_target_exists() -> None:
    section = _section()
    targets = re.findall(r"\]\(([^)#]+)\)", section)
    assert "docs/offline-install.md" in targets
    for target in targets:
        assert (ROOT / target).exists(), target


def test_section_has_no_short_engine_code_and_no_dash_characters() -> None:
    section = _section()
    assert SHORT_CODE.search(section) is None
    assert chr(0x2014) not in section
    assert chr(0x2013) not in section


def test_section_sits_before_the_quick_start() -> None:
    text = _text()
    assert text.index(HEADING) < text.index(NEXT_HEADING)
