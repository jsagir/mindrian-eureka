"""A healthy start of the stdio server writes nothing to stderr.

The MindrianOS plugin shows the first stderr line as the cause of a failed
start. The harmless import-time note of the reference script would hide the
real cause, so the server captures it instead of printing it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")

START_CODE = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "from mindrian_eureka.opportunity_pairs import mcp_server;"
    "mcp_server.main()"
)


def _clean_env(tmp_path: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("MINDRIAN_EUREKA_", "HSI_"))
    }
    env["MINDRIAN_EUREKA_DATA_DIR"] = str(tmp_path / "data")
    env["MINDRIAN_EUREKA_CACHE_DIR"] = str(tmp_path / "cache")
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    return env


def test_healthy_start_writes_nothing_to_stderr(tmp_path: Path) -> None:
    done = subprocess.run(
        [sys.executable, "-E", "-c", START_CODE, SRC_DIR],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        timeout=120,
    )
    assert done.stderr == ""
    assert done.returncode == 0


def test_import_time_text_is_kept_in_a_constant(tmp_path: Path) -> None:
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from mindrian_eureka.opportunity_pairs import mcp_server;"
        "sys.stdout.write(type(mcp_server.IMPORT_NOTES).__name__)"
    )
    done = subprocess.run(
        [sys.executable, "-E", "-c", code, SRC_DIR],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == "str"
    assert done.stderr == ""


def test_import_failure_still_reaches_stderr_with_its_message() -> None:
    from mindrian_eureka.opportunity_pairs import quiet_import

    def failing() -> None:
        print("a note before the failure", file=sys.stderr)
        raise ImportError("deliberate import failure")

    with pytest.raises(ImportError, match="deliberate import failure"):
        quiet_import.import_quietly(failing)


def test_quiet_import_returns_the_captured_text(capsys: pytest.CaptureFixture[str]) -> None:
    from mindrian_eureka.opportunity_pairs import quiet_import

    def noisy() -> None:
        print("captured note", file=sys.stderr)

    text = quiet_import.import_quietly(noisy)
    assert text == "captured note\n"
    assert capsys.readouterr().err == ""


def test_failure_replays_the_captured_note_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    from mindrian_eureka.opportunity_pairs import quiet_import

    def failing() -> None:
        print("a note before the failure", file=sys.stderr)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        quiet_import.import_quietly(failing)
    assert "a note before the failure" in capsys.readouterr().err

