"""Tests for the command line of `eureka run` and `eureka doctor` (cli.py, command.py)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import CORPUS_FIXTURE, InputSet
from mindrian_eureka import doctor
from mindrian_eureka.cli import main
from mindrian_eureka.run import pipeline
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE
from mindrian_eureka.run.manifest import tool_version

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
CATALOG = SRC / "mindrian_eureka" / "data" / "capability-catalog.v1.json"
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
ANSI = re.compile(r"\x1b\[")
ENGINE_NAMES = (
    "Find Unusual Pairs Across a Research Collection",
    "Rank Unusual Pairs by Wording and Meaning",
)
HEAVY = ("numpy", "sklearn", "scipy", "torch", "sentence_transformers")


def help_text(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    with pytest.raises(SystemExit) as caught:
        main([*argv, "--help"])
    assert caught.value.code == 0
    return capsys.readouterr().out


def run_args(inputs: InputSet, out: Path, model: Path, *extra: str) -> list[str]:
    return [
        "run",
        str(inputs.folder),
        "--out",
        str(out),
        "--model-path",
        str(model),
        *inputs.mapping_flags,
        *extra,
    ]


# --- Help and version -------------------------------------------------------


@pytest.mark.parametrize("command", [(), ("run",), ("doctor",)])
def test_help_texts(capsys: pytest.CaptureFixture[str], command: tuple[str, ...]) -> None:
    text = help_text(capsys, *command)
    for name in ENGINE_NAMES:
        assert name in text
    assert "Exit codes:" in text
    assert "130" in text
    assert SHORT_CODE.search(text) is None
    assert ANSI.search(text) is None
    assert LABEL in text


def test_run_help_states_the_rules(capsys: pytest.CaptureFixture[str]) -> None:
    text = " ".join(help_text(capsys, "run").split())
    assert "offline and non-interactive" in text
    assert "made only of non-ASCII letters sanitizes to underscores and collides" in text
    assert "omit it to get hash ids" in text
    for flag in (
        "--out",
        "--mapping",
        "--id-column",
        "--title-column",
        "--text-column",
        "--source-column",
        "--delimiter",
        "--model-path",
        "--max-artifacts",
        "--top-k",
        "--objective",
        "--threads",
        "--no-cache",
        "--dry-run",
        "--json",
        "--quiet",
        "--no-color",
        "--debug",
    ):
        assert flag in text


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0
    assert capsys.readouterr().out == f"eureka {tool_version()}\n"


def test_no_argument_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


@pytest.mark.parametrize(
    "flags",
    [
        ["--top-k", "0"],
        ["--top-k", "201"],
        ["--max-artifacts", "1"],
        ["--max-artifacts", "5001"],
        ["--threads", "0"],
        ["--threads", "many"],
    ],
)
def test_range_violation_is_usage_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, flags: list[str]
) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["run", str(tmp_path), *flags])
    assert caught.value.code == 2
    assert "must be" in capsys.readouterr().err


# --- Usage errors returned as codes -----------------------------------------


def test_mapping_with_column_flag_returns_2(
    isolated_env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("csv")
    assert inputs.mapping_file is not None
    code = main(
        [
            "run",
            str(inputs.folder),
            "--out",
            str(tmp_path / "out"),
            "--model-path",
            str(fake_model_dir),
            "--mapping",
            str(inputs.mapping_file),
            "--id-column",
            "case_id",
        ]
    )
    assert code == 2
    assert "Use either --mapping or the column flags, not both." in capsys.readouterr().err


def test_unmapped_csv_lists_headers(
    isolated_env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("csv")
    code = main(
        [
            "run",
            str(inputs.folder),
            "--out",
            str(tmp_path / "out"),
            "--model-path",
            str(fake_model_dir),
        ]
    )
    err = capsys.readouterr().err
    assert code == 2
    for header in ("case_id", "title", "description", "state_code"):
        assert header in err
    assert not (tmp_path / "out").exists()


def test_out_inside_input_returns_2(
    isolated_env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    code = main(run_args(inputs, inputs.folder / "result", fake_model_dir))
    assert code == 2
    assert "inside" in capsys.readouterr().err


# --- Successful run ---------------------------------------------------------


def test_successful_run_streams(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    assert main(run_args(inputs, out, fake_model_dir)) == 0
    captured = capsys.readouterr()
    assert captured.out.rstrip("\n").splitlines()[-1] == SUMMARY_LINE
    assert "Reading sources" not in captured.out
    assert re.search(r"^\[\d+\.\ds\]", captured.out, re.MULTILINE) is None
    assert "Reading sources" in captured.err
    assert SUMMARY_LINE not in captured.err
    assert ANSI.search(captured.err) is None
    assert ANSI.search(captured.out) is None
    assert (out / "manifest.json").is_file()
    info = json.loads((out / "run-info.json").read_text(encoding="utf-8"))
    assert info["argv"][0] == "run"
    assert str(inputs.folder) in info["argv"]


def test_csv_run_with_flags(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
) -> None:
    inputs = tmp_inputs("csv")
    assert main(run_args(inputs, tmp_path / "out", fake_model_dir)) == 0


def test_input_text_never_reaches_the_terminal(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    assert main(run_args(inputs, tmp_path / "out", fake_model_dir)) == 0
    captured = capsys.readouterr()
    data = json.loads(CORPUS_FIXTURE.read_text(encoding="utf-8"))
    for item in data["artifacts"][:5]:
        sentence = item["text"].split(".")[0].strip()
        assert sentence not in captured.out
        assert sentence not in captured.err


def test_quiet_hides_progress_but_not_warnings(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown", count=4)
    assert main(run_args(inputs, tmp_path / "out", fake_model_dir, "--quiet")) == 0
    captured = capsys.readouterr()
    assert "Reading sources" not in captured.err
    assert "Ranking with" not in captured.err
    assert "warning:" in captured.err
    assert captured.out.rstrip("\n").splitlines()[-1] == SUMMARY_LINE


def test_json_summary(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    assert main(run_args(inputs, tmp_path / "out", fake_model_dir, "--json")) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["schema"] == "eureka.run-summary.v1"
    assert document["label"] == LABEL
    assert document["summary_line"] == SUMMARY_LINE
    assert document["counts"]["records_used"] == 32


def test_dry_run_through_cli(
    isolated_env: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    code = main(["run", str(inputs.folder), "--out", str(out), "--dry-run"])
    assert code == 0
    assert "No model was loaded and nothing was written." in capsys.readouterr().out
    assert not out.exists()


# --- Failures ---------------------------------------------------------------


def test_keyboard_interrupt_returns_130(
    isolated_env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def stop(*args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "run_pipeline", stop)
    code = main(run_args(tmp_inputs("markdown"), tmp_path / "out", fake_model_dir))
    assert code == 130
    err = capsys.readouterr().err
    assert "eureka: Interrupted. No output was written." in err
    assert "Traceback" not in err


def test_unexpected_error_returns_1_without_traceback(
    isolated_env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("odd failure")

    monkeypatch.setattr(pipeline, "run_pipeline", boom)
    inputs = tmp_inputs("markdown")
    code = main(run_args(inputs, tmp_path / "out", fake_model_dir))
    err = capsys.readouterr().err
    assert code == 1
    assert "eureka: unexpected error (RuntimeError): odd failure" in err
    assert "Traceback" not in err
    with pytest.raises(RuntimeError):
        main(run_args(inputs, tmp_path / "out", fake_model_dir, "--debug"))


def test_missing_model_returns_1(
    isolated_env: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    code = main(["run", str(inputs.folder), "--out", str(out)])
    err = capsys.readouterr().err
    assert code == 1
    assert "No local model found." in err
    assert "Fix:" in err
    assert "MINDRIAN_EUREKA_RS_MODEL_PATH" in err
    assert "Traceback" not in err
    assert not out.exists()


# --- Doctor -----------------------------------------------------------------


def _results(status: doctor.Status) -> list[doctor.CheckResult]:
    return [
        doctor.CheckResult("D1", "Python", doctor.Status.PASS, "Python is fine.", None),
        doctor.CheckResult("D4", "Local model", status, "The model check.", "Fix it."),
    ]


@pytest.mark.parametrize(
    ("status", "expected"), [(doctor.Status.FAIL, 1), (doctor.Status.PASS, 0)]
)
def test_doctor_wiring(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: doctor.Status,
    expected: int,
) -> None:
    seen: dict[str, Any] = {}

    def fake_checks(**kwargs: Any) -> list[doctor.CheckResult]:
        seen.update(kwargs)
        return _results(status)

    monkeypatch.setattr(doctor, "run_checks", fake_checks)
    assert main(["doctor", "--load-model", "--model-path", "/some/folder"]) == expected
    assert seen["load_model"] is True
    assert seen["model_path"] == Path("/some/folder")
    assert "Eureka doctor" in capsys.readouterr().out


def test_doctor_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(doctor, "run_checks", lambda **kwargs: _results(doctor.Status.PASS))
    assert main(["doctor", "--json", "--no-color"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["schema_version"] == "eureka.doctor.v1"
    assert document["ok"] is True


# --- Old subcommands --------------------------------------------------------


def test_old_subcommands_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert main(["capabilities", "--summary"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["count"] == len(source["capabilities"])
    counts: dict[str, int] = {}
    for item in source["capabilities"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    assert summary["counts_by_status"] == counts
    assert main(["workflow"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), dict)
    first = source["capabilities"][0]["id"]
    assert main(["capability", first]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == first


# --- Import cost ------------------------------------------------------------


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    return env


def test_importing_cli_loads_no_heavy_library() -> None:
    code = (
        "import sys; import mindrian_eureka.cli; "
        f"bad = [m for m in {HEAVY!r} if m in sys.modules]; assert not bad, bad"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=_clean_env(), timeout=120
    )
    assert done.returncode == 0, done.stderr


def test_help_through_module_loads_no_heavy_library() -> None:
    code = (
        "import sys\n"
        "from mindrian_eureka.cli import main\n"
        "try:\n"
        "    main(['--help'])\n"
        "except SystemExit as exit_info:\n"
        "    assert exit_info.code == 0\n"
        f"bad = [m for m in {HEAVY!r} if m in sys.modules]\n"
        "assert not bad, bad\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=_clean_env(), timeout=120
    )
    assert done.returncode == 0, done.stderr
    module = subprocess.run(
        [sys.executable, "-m", "mindrian_eureka.cli", "--help"],
        capture_output=True,
        text=True,
        env=_clean_env(),
        timeout=120,
    )
    assert module.returncode == 0
    assert "usage: eureka" in module.stdout
