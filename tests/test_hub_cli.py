"""Check hub help, streams, exit codes and lightweight imports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from hub_support import make_run_folder
from mindrian_eureka.cli import main
from mindrian_eureka.hub import writer
from mindrian_eureka.hub.contracts import HUB_SUMMARY_SCHEMA
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE
from test_run_cli import ANSI, ENGINE_NAMES, HEAVY, SHORT_CODE, help_text


def test_help(capsys) -> None:
    text = help_text(capsys, "hub")
    for word in (*ENGINE_NAMES, "Exit codes:", "130", "--out", "--source-dir", "--json",
                 "--quiet", "--no-color", "--debug", "makes no network call"):
        assert word in text
    assert SHORT_CODE.search(text) is None and ANSI.search(text) is None


@pytest.mark.parametrize("as_json", [False, True])
def test_success(tmp_path: Path, capsys, no_network: list[object], as_json: bool) -> None:
    run = make_run_folder(tmp_path)
    args = ["hub", str(run), "--out", str(tmp_path / "hub")]
    assert main([*args, *(["--json"] if as_json else [])]) == 0
    captured = capsys.readouterr()
    if as_json:
        summary = json.loads(captured.out)
        assert summary["schema_version"] == HUB_SUMMARY_SCHEMA
        assert summary["label"] == LABEL
    else:
        assert captured.out.splitlines()[-1] == SUMMARY_LINE
    assert no_network == []


@pytest.mark.parametrize("kind,code", [("missing", 2), ("foreign-run", 2),
                                        ("damaged", 1), ("foreign-out", 2)])
def test_errors(tmp_path: Path, capsys, kind: str, code: int) -> None:
    run = make_run_folder(tmp_path)
    out = tmp_path / "hub"
    if kind == "missing":
        run = tmp_path / "absent"
    elif kind == "foreign-run":
        run = tmp_path / "foreign"
        run.mkdir()
    elif kind == "damaged":
        with (run / "corpus/records.jsonl").open("ab") as stream:
            stream.write(b" ")
    else:
        out.mkdir()
        (out / "keep.txt").write_text("keep")
    assert main(["hub", str(run), "--out", str(out)]) == code
    captured = capsys.readouterr()
    assert not captured.out and "Fix:" in captured.err


def test_quiet_keeps_warnings(tmp_path: Path, capsys) -> None:
    run = make_run_folder(tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    assert main(["hub", str(run), "--out", str(tmp_path / "hub"),
                 "--source-dir", str(sources), "-q"]) == 0
    captured = capsys.readouterr()
    assert "warning:" in captured.err and "[" not in captured.err
    assert captured.out.splitlines()[-1] == SUMMARY_LINE


@pytest.mark.parametrize("mode", ["import", "top-help", "hub-help"])
def test_light_import(mode: str) -> None:
    script = "import sys; from mindrian_eureka.cli import main; "
    if mode != "import":
        args = ["--help"] if mode == "top-help" else ["hub", "--help"]
        script += f"\ntry: main({args!r})\nexcept SystemExit: pass\n"
    script += f"\nassert not set({HEAVY!r}) & set(sys.modules)"
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True)


@pytest.mark.parametrize("error,debug,expected", [(KeyboardInterrupt, False, 130),
                                                (RuntimeError, False, 1),
                                                (RuntimeError, True, None)])
def test_exception_mapping(tmp_path: Path, monkeypatch, error, debug: bool, expected) -> None:
    def fail(*args, **kwargs):
        raise error("test")
    monkeypatch.setattr(writer, "build_hub", fail)
    args = ["hub", str(tmp_path / "run"), "--out", str(tmp_path / "hub")]
    if debug:
        with pytest.raises(error):
            main([*args, "--debug"])
    else:
        assert main(args) == expected
