"""Console output rules for `eureka run` and `eureka doctor`.

Progress, warnings and errors go to stderr. Results go to stdout. Color shows only on a
terminal, when NO_COLOR is unset and TERM is not "dumb". The console never prompts and
never reads stdin. Ctrl+C handling and exit codes live in the command layer.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Callable, Mapping
from typing import TextIO

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_RESET = "\x1b[0m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"


def use_color(stream: TextIO, no_color_flag: bool, env: Mapping[str, str] | None = None) -> bool:
    """Decide whether to write ANSI color to a stream.

    Args:
        stream: The stream that gets the text.
        no_color_flag: True when the user passed --no-color.
        env: The environment. It defaults to `os.environ`.

    Returns:
        True only for a terminal, with NO_COLOR unset, TERM not "dumb" and no flag.
    """
    variables = os.environ if env is None else env
    if no_color_flag or "NO_COLOR" in variables or variables.get("TERM") == "dumb":
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def _clean(text: str) -> str:
    """Remove control characters (such as escape codes) that came in with file data."""
    return _CONTROL.sub("", text)


class Console:
    """Write messages to stderr and results to stdout.

    Streams are looked up when a message is written, so test capture works.
    """

    def __init__(
        self,
        *,
        quiet: bool = False,
        no_color: bool = False,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.quiet = quiet
        self.no_color = no_color
        self._stdout = stdout
        self._stderr = stderr
        self._clock = clock
        self._start = clock()

    @property
    def _err(self) -> TextIO:
        return self._stderr if self._stderr is not None else sys.stderr

    @property
    def _out(self) -> TextIO:
        return self._stdout if self._stdout is not None else sys.stdout

    def _write_err(self, line: str) -> None:
        stream = self._err
        stream.write(line + "\n")
        stream.flush()

    def _prefix(self, text: str, color: str) -> str:
        if use_color(self._err, self.no_color):
            return f"{color}{text}{_RESET}"
        return text

    def info(self, message: str) -> None:
        """Write a progress message to stderr. Silent when quiet."""
        if not self.quiet:
            self._write_err(_clean(message))

    def stage(self, name: str) -> None:
        """Write a stage line with the elapsed seconds to stderr. Silent when quiet."""
        if not self.quiet:
            elapsed = self._clock() - self._start
            self._write_err(f"[{elapsed:.1f}s] {_clean(name)}")

    def warn(self, message: str) -> None:
        """Write a warning to stderr. A warning is never silent."""
        self._write_err(f"{self._prefix('warning:', _YELLOW)} {_clean(message)}")

    def error(self, message: str, fix: str | None = None) -> None:
        """Write an error and an optional fix to stderr. An error is never silent."""
        self._write_err(f"{self._prefix('eureka:', _RED)} {_clean(message)}")
        if fix:
            self._write_err(f"  Fix: {_clean(fix)}")

    def out(self, text: str) -> None:
        """Write a result to stdout, followed by a newline."""
        stream = self._out
        stream.write(text + "\n")
        stream.flush()
