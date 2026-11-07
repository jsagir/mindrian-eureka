"""Tests that tie the GPU spike results page, the profile pin and the threshold to the log.

The page may show a GPU value only when the log file from the owner's run sits next to it. The
log is `docs/encoder-evidence/gpu-spike-log.json`. While it does not exist, every value on the
page is `NOT RUN`, and the profile revision and the overlap threshold stay unset.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from mindrian_eureka.encoder_spec import PROFILES
from mindrian_eureka.example import contracts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "encoder-spike.py"
PAGE = ROOT / "docs" / "encoder-spike-results.md"
LOG = ROOT / "docs" / "encoder-evidence" / "gpu-spike-log.json"
START = "<!-- spike-table:start -->"
END = "<!-- spike-table:end -->"
TITLE = "# GPU encoder spike: Nemotron-3-Embed-1B-BF16 on the RTX 3060"
HEADINGS = [
    "## Status",
    "## What this proves and what it does not",
    "## How to run",
    "## Results",
    "## Decisions that follow from the numbers",
    "## Next step",
]
PACKAGES = ("torch", "transformers", "sentence-transformers", "numpy", "huggingface-hub")


@pytest.fixture(scope="module")
def spike() -> ModuleType:
    spec = importlib.util.spec_from_file_location("encoder_spike_record", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["encoder_spike_record"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def block_of(text: str) -> str:
    assert text.count(START) == 1 and text.count(END) == 1
    return text.split(START, 1)[1].split(END, 1)[0].strip()


def front_status(text: str) -> str:
    lines = text.splitlines()
    assert lines[0] == "---"
    closing = lines.index("---", 1)
    status = [line for line in lines[1:closing] if line.startswith("status:")]
    assert len(status) == 1
    return status[0]


def value_cells(block: str) -> list[str]:
    cells = []
    for line in block.splitlines()[2:]:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        cells.append(parts[1])
    return cells


def read_log() -> dict[str, Any]:
    return json.loads(LOG.read_text(encoding="utf-8"))


def test_page_state_follows_the_log(spike: ModuleType, page_text: str) -> None:
    if not LOG.exists():
        assert front_status(page_text) == "status: not_run"
        block = block_of(page_text)
        assert block == spike.render_table(spike.skeleton_log()).strip()
        cells = value_cells(block)
        assert cells and all(cell == "NOT RUN" for cell in cells)
        assert not any(char.isdigit() for cell in cells for char in cell)
    else:
        log = read_log()
        assert log["schema_version"] == spike.SCHEMA
        expected = "status: not_run" if log["status"] == "not_run" else "status: recorded"
        assert front_status(page_text) == expected
        assert block_of(page_text) == spike.render_table(log).strip()


def test_profile_pin_comes_from_the_log(spike: ModuleType) -> None:
    revision = PROFILES["gpu-nemotron"].revision
    if revision is None:
        return
    assert LOG.exists(), "the profile revision is set but no spike log exists"
    log = read_log()
    assert spike.lookup(log, "model.revision") == revision
    assert spike.lookup(log, "load.bf16.ok") is True


def test_threshold_comes_from_the_page_and_the_log(page_text: str) -> None:
    threshold = contracts.GPU_APPROX_MIN_OVERLAP
    lines = page_text.splitlines()
    if threshold is None:
        assert "Threshold: not set" in lines
        return
    assert LOG.exists(), "a threshold is set but no spike log exists"
    assert f"Threshold: {threshold}" in lines
    assert any("owner" in line.lower() and "decid" in line.lower() for line in lines)


def test_page_headings_and_style(page_text: str) -> None:
    lines = page_text.splitlines()
    assert TITLE in lines
    assert [line for line in lines if line.startswith("## ")] == HEADINGS
    assert "—" not in page_text and "–" not in page_text
    assert re.search(r"\b(RS|HSI)\b", page_text) is None
    assert "candidate, not verified" in page_text
    how = page_text.split("## How to run", 1)[1].split("\n## ", 1)[0]
    for needle in ("python3 -m venv", "outside the repository", "--allow-download", "--render-doc"):
        assert needle in how, needle
    for name in PACKAGES:
        assert f"https://pypi.org/project/{name}/" in how, name


def test_page_makes_no_claim_about_results_without_a_log(page_text: str) -> None:
    if LOG.exists():
        return
    outside = page_text.replace(
        page_text.split("## How to run", 1)[1].split("\n## ", 1)[0], ""
    ).lower()
    for phrase in ("loaded successfully", "fits", "fast", "works on"):
        assert phrase not in outside, phrase
