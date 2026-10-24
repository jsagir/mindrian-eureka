"""Helpers that run the Node browser driver from the Python tests.

The driver is `tests/hub_browser/driver.cjs`. It needs the Playwright module, which is not a
dependency of this repository. `find_playwright` looks for an installed copy. When no copy or
no browser exists, `require_browser` skips the test with a reason. Set `EUREKA_REQUIRE_BROWSER=1`
to turn the skip into a failure (use it in a release check).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import pytest

DRIVER = Path(__file__).resolve().parent / "hub_browser" / "driver.cjs"
PROBES = Path(__file__).resolve().parent / "hub_browser" / "probes"
ENV_PLAYWRIGHT = "EUREKA_PLAYWRIGHT_DIR"
ENV_REQUIRE = "EUREKA_REQUIRE_BROWSER"
BROWSERS = ("chromium", "firefox")


class BrowserToolError(RuntimeError):
    """The driver could not run, or it returned text that is not JSON."""


def _holds_package(path: Path) -> bool:
    return (path / "package.json").is_file()


def find_playwright() -> Path | None:
    """Return the folder of the Playwright package, or None.

    Order: the environment variable, the global npm root, the default global folder.
    A folder counts only when it holds a package.json.
    """
    env = os.environ.get(ENV_PLAYWRIGHT)
    if env and _holds_package(Path(env)):
        return Path(env)
    try:
        completed = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        root = completed.stdout.strip()
        if completed.returncode == 0 and root and _holds_package(Path(root) / "playwright"):
            return Path(root) / "playwright"
    except (OSError, subprocess.SubprocessError):
        pass
    fallback = Path.home() / ".npm-global" / "lib" / "node_modules" / "playwright"
    if _holds_package(fallback):
        return fallback
    return None


def file_url(path: str | Path, fragment: str = "") -> str:
    """Return the file URL of an existing or future local path, with an optional fragment."""
    url = Path(path).resolve().as_uri()
    return f"{url}#{fragment}" if fragment else url


def run_scenario(scenario: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    """Run one scenario in the driver and return the parsed JSON result.

    Raises:
        BrowserToolError: Node or Playwright is missing, the browser cannot start, the
            driver exits with code 2, the run times out, or the output is not JSON.
    """
    playwright = find_playwright()
    node = shutil.which("node")
    if playwright is None or node is None:
        raise BrowserToolError("node or the playwright package was not found")
    with tempfile.TemporaryDirectory(prefix="eureka-scenario-") as folder:
        scenario_file = Path(folder) / "scenario.json"
        scenario_file.write_text(json.dumps(scenario), encoding="utf-8")
        try:
            completed = subprocess.run(
                [
                    node,
                    str(DRIVER),
                    "--playwright",
                    str(playwright),
                    "--scenario",
                    str(scenario_file),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise BrowserToolError(f"driver timed out after {timeout} seconds") from error
    if completed.returncode == 2:
        raise BrowserToolError(completed.stderr.strip() or "driver exit code 2")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = (completed.stderr or completed.stdout).strip()[:300]
        raise BrowserToolError(f"driver output is not JSON: {detail}") from error


@cache
def _browser_state(browser: str) -> str:
    """Return an empty string when the browser starts, else the reason it does not."""
    if find_playwright() is None or shutil.which("node") is None:
        return "node or the playwright package is not installed"
    try:
        run_scenario({"browser": browser, "steps": [], "timeoutMs": 20000}, timeout=60)
    except BrowserToolError as error:
        return str(error).splitlines()[0] if str(error) else "browser cannot start"
    return ""


def require_browser(browser: str = "chromium") -> None:
    """Skip the test when the browser tools are missing. Fail instead when required.

    Set EUREKA_REQUIRE_BROWSER=1 to make a missing tool a failure.
    """
    reason = _browser_state(browser)
    if not reason:
        return
    message = f"browser tool not available for {browser}: {reason}"
    if os.environ.get(ENV_REQUIRE) == "1":
        pytest.fail(message)
    pytest.skip(message)
