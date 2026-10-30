"""Tests for the console helper (plan 02-04, task 3)."""

from __future__ import annotations

import io
import re
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from mindrian_eureka.run import console
from mindrian_eureka.run.console import Console, use_color

ANSI = re.compile(r"\x1b\[")


class FakeTTY(io.StringIO):
    """A text stream that reports itself as a terminal."""

    def isatty(self) -> bool:
        return True


def _clock(values: list[float]) -> Callable[[], float]:
    iterator = iter(values)
    return lambda: next(iterator)


# --- use_color --------------------------------------------------------------


@pytest.mark.parametrize(
    ("tty", "flag", "env", "expected"),
    [
        (True, False, {"TERM": "xterm"}, True),
        (True, False, {}, True),
        (False, False, {"TERM": "xterm"}, False),
        (True, True, {"TERM": "xterm"}, False),
        (True, False, {"NO_COLOR": "1", "TERM": "xterm"}, False),
        (True, False, {"NO_COLOR": "", "TERM": "xterm"}, False),
        (True, False, {"TERM": "dumb"}, False),
    ],
)
def test_use_color(tty: bool, flag: bool, env: dict[str, str], expected: bool) -> None:
    stream = FakeTTY() if tty else io.StringIO()
    assert use_color(stream, flag, env) is expected


def test_use_color_defaults_to_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert use_color(FakeTTY(), False) is True
    monkeypatch.setenv("NO_COLOR", "1")
    assert use_color(FakeTTY(), False) is False


def test_use_color_closed_stream_is_false() -> None:
    stream = io.StringIO()
    stream.close()
    assert use_color(stream, False, {}) is False


# --- Console ----------------------------------------------------------------


def test_info_and_stage_go_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    ui = Console(clock=_clock([100.0, 112.34]))
    ui.info("loading")
    ui.stage("ranking")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "loading\n[12.3s] ranking\n"


def test_quiet_silences_info_and_stage_only(capsys: pytest.CaptureFixture[str]) -> None:
    ui = Console(quiet=True)
    ui.info("loading")
    ui.stage("ranking")
    ui.warn("careful")
    ui.error("broken", fix="repair it")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "warning: careful\neureka: broken\n  Fix: repair it\n"


def test_error_without_fix(capsys: pytest.CaptureFixture[str]) -> None:
    Console().error("broken")
    assert capsys.readouterr().err == "eureka: broken\n"


def test_out_goes_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    Console().out("result line")
    captured = capsys.readouterr()
    assert captured.out == "result line\n"
    assert captured.err == ""


def test_streams_are_looked_up_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ui = Console()
    first_out, first_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", first_out)
    monkeypatch.setattr(sys, "stderr", first_err)
    ui.out("a")
    ui.warn("b")
    second_out, second_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", second_out)
    monkeypatch.setattr(sys, "stderr", second_err)
    ui.out("c")
    assert first_out.getvalue() == "a\n"
    assert first_err.getvalue() == "warning: b\n"
    assert second_out.getvalue() == "c\n"
    assert second_err.getvalue() == ""


def test_injected_streams() -> None:
    out, err = io.StringIO(), io.StringIO()
    ui = Console(stdout=out, stderr=err)
    ui.out("x")
    ui.warn("y")
    assert out.getvalue() == "x\n"
    assert err.getvalue() == "warning: y\n"


def test_color_only_on_prefixes_for_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.delenv("NO_COLOR", raising=False)
    err = FakeTTY()
    ui = Console(stdout=io.StringIO(), stderr=err)
    ui.info("plain info")
    ui.stage("plain stage")
    ui.warn("w")
    ui.error("e", fix="f")
    lines = err.getvalue().splitlines()
    assert not ANSI.search(lines[0])
    assert not ANSI.search(lines[1])
    assert lines[2] == "\x1b[33mwarning:\x1b[0m w"
    assert lines[3] == "\x1b[31meureka:\x1b[0m e"
    assert lines[4] == "  Fix: f"


@pytest.mark.parametrize("variant", ["non_tty", "no_color_flag", "no_color_env", "dumb"])
def test_no_color_cases(monkeypatch: pytest.MonkeyPatch, variant: str) -> None:
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.delenv("NO_COLOR", raising=False)
    err: io.StringIO = io.StringIO() if variant == "non_tty" else FakeTTY()
    flag = variant == "no_color_flag"
    if variant == "no_color_env":
        monkeypatch.setenv("NO_COLOR", "1")
    if variant == "dumb":
        monkeypatch.setenv("TERM", "dumb")
    ui = Console(stderr=err, no_color=flag)
    ui.warn("w")
    ui.error("e")
    assert not ANSI.search(err.getvalue())


def test_control_characters_from_data_are_removed(capsys: pytest.CaptureFixture[str]) -> None:
    ui = Console()
    ui.warn("file \x1b[31mred\x1b[0m name\r")
    assert capsys.readouterr().err == "warning: file [31mred[0m name\n"


def test_console_never_reads_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    class Forbidden(io.StringIO):
        def read(self, *args: int) -> str:
            raise AssertionError("stdin was read")

        def readline(self, *args: int) -> str:
            raise AssertionError("stdin was read")

    monkeypatch.setattr(sys, "stdin", Forbidden())
    ui = Console(stdout=io.StringIO(), stderr=io.StringIO())
    ui.info("a")
    ui.stage("b")
    ui.warn("c")
    ui.error("d", fix="e")
    ui.out("f")


def test_source_has_no_input_calls_and_no_em_dash() -> None:
    text = Path(console.__file__).read_text(encoding="utf-8")
    assert "input(" not in text
    assert chr(0x2014) not in text
