"""CLI tests for `eureka check-example` and the maker script (Phase 4, plan 01)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mindrian_eureka.cli import main
from mindrian_eureka.example import build as build_module
from mindrian_eureka.example import command as command_module
from mindrian_eureka.example.check import load_expected
from mindrian_eureka.example.contracts import (
    EXAMPLE_DIR,
    EXPECTED_NAME,
    REPORT_SCHEMA,
    RESULT_MATCH,
    RESULT_NO_MATCH,
)
from mindrian_eureka.run.contracts import LABEL
from mindrian_eureka.run.output import canonical_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RUN = ROOT / "tests/fixtures/hub_public/run"
HEAVY = ("numpy", "torch", "sklearn", "sentence_transformers")


@pytest.fixture()
def expected_file(tmp_path: Path) -> Path:
    path = tmp_path / "expected.json"
    code = build_module.main([str(FIXTURE_RUN), "--out", str(path), "--repo-root", str(ROOT)])
    assert code == 0
    return path


def copy_run(tmp_path: Path) -> Path:
    target = tmp_path / "run"
    shutil.copytree(FIXTURE_RUN, target)
    return target


def help_text(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    with pytest.raises(SystemExit) as caught:
        main([*argv, "--help"])
    assert caught.value.code == 0
    return capsys.readouterr().out


def test_exit_0_on_match(expected_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["check-example", str(FIXTURE_RUN), "--expected", str(expected_file)])
    out = capsys.readouterr().out
    assert code == 0
    assert RESULT_MATCH in out
    assert out.count("PASS X") == 7


def test_exit_1_on_mismatch(
    tmp_path: Path, expected_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = copy_run(tmp_path)
    target = run / "ranked-pairs.md"
    data = bytearray(target.read_bytes())
    data[-1] = ord("Z") if data[-1] != ord("Z") else ord("Y")
    target.write_bytes(bytes(data))
    code = main(["check-example", str(run), "--expected", str(expected_file)])
    out = capsys.readouterr().out
    assert code == 1
    assert RESULT_NO_MATCH in out
    assert "FAIL X6" in out
    assert "ranked-pairs.md" in out


def test_exit_2_on_usage_errors(
    tmp_path: Path,
    expected_file: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(command_module, "REPO_ROOT", tmp_path / "no-repo")
    monkeypatch.chdir(tmp_path)
    cases = [
        ["check-example", str(tmp_path / "missing"), "--expected", str(expected_file)],
        ["check-example", str(FIXTURE_RUN), "--expected", str(tmp_path / "missing.json")],
        ["check-example", str(FIXTURE_RUN)],
        ["check-example", str(empty), "--expected", str(expected_file)],
    ]
    for argv in cases:
        capsys.readouterr()
        assert main(argv) == 2
        err = capsys.readouterr().err
        assert "eureka:" in err
        assert "Fix:" in err


def test_json_output(expected_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["check-example", str(FIXTURE_RUN), "--expected", str(expected_file), "--json"])
    document = json.loads(capsys.readouterr().out)
    assert code == 0
    assert document["schema"] == REPORT_SCHEMA
    assert document["result"] == "match"
    assert len(document["checks"]) == 7
    assert document["label"] == LABEL


def test_default_expected_location(
    tmp_path: Path,
    expected_file: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work = tmp_path / "work"
    place = work / EXAMPLE_DIR
    place.mkdir(parents=True)
    shutil.copy(expected_file, place / EXPECTED_NAME)
    monkeypatch.setattr(command_module, "REPO_ROOT", tmp_path / "no-repo")
    monkeypatch.chdir(work)
    assert main(["check-example", str(FIXTURE_RUN)]) == 0
    capsys.readouterr()
    # Next to the package: the repo root is used when the working folder has no file.
    repo = tmp_path / "repo"
    (repo / EXAMPLE_DIR).mkdir(parents=True)
    shutil.copy(expected_file, repo / EXAMPLE_DIR / EXPECTED_NAME)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(command_module, "REPO_ROOT", repo)
    monkeypatch.chdir(elsewhere)
    assert main(["check-example", str(FIXTURE_RUN)]) == 0
    capsys.readouterr()
    monkeypatch.setattr(command_module, "REPO_ROOT", tmp_path / "no-repo")
    assert main(["check-example", str(FIXTURE_RUN)]) == 2
    assert "Give --expected FILE" in capsys.readouterr().err


def test_help_and_listing(capsys: pytest.CaptureFixture[str]) -> None:
    assert "check-example" in help_text(capsys)
    text = help_text(capsys, "check-example")
    assert LABEL in text
    for needle in ("  0 ", "  1 ", "  2 ", "  130 "):
        assert needle in text
    assert "makes no network call" in text
    assert "loads no model" in text


def test_import_weight() -> None:
    code = (
        "import sys\n"
        "import mindrian_eureka.example.command\n"
        "import mindrian_eureka.example.check\n"
        f"heavy = {HEAVY!r}\n"
        "print([name for name in heavy if name in sys.modules])\n"
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
    )
    assert done.stdout.strip() == "[]"


def test_maker_script_and_module(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "made.json"
    assert build_module.main([str(FIXTURE_RUN), "--out", str(out)]) == 0
    line = capsys.readouterr().out.strip()
    assert line.endswith(" " + __import__("hashlib").sha256(out.read_bytes()).hexdigest())
    assert load_expected(out)["outputs"]
    assert out.read_bytes() == canonical_json(json.loads(out.read_text()), digits=None)
    inside = FIXTURE_RUN / "x-expected.json"
    assert build_module.main([str(FIXTURE_RUN), "--out", str(inside)]) == 2
    assert not inside.exists()
    script = ROOT / "scripts/make-example-hashes"
    assert script.is_file()
    assert os.access(script, os.X_OK)
    assert "uv run --offline python -m mindrian_eureka.example.build" in script.read_text()


@pytest.mark.parametrize("name", ["doctor", "run", "hub", "seed"])
def test_existing_commands_unchanged(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert help_text(capsys, name)
