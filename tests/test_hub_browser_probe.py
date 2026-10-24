"""Self-tests of the browser harness, plus probes of file URL behavior.

The tests need Node and Playwright. When a tool or a browser is missing they skip with a
reason. Set EUREKA_REQUIRE_BROWSER=1 to turn the skip into a failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import hub_browser_support as support
import pytest
from hub_browser_support import BROWSERS, PROBES, file_url, require_browser, run_scenario

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def write_script(folder: Path, name: str, body: str) -> str:
    """Write the body of an async probe function and return its path."""
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def run_media(browser: str, **options: Any) -> dict[str, Any]:
    scenario = {"browser": browser, "url": file_url(PROBES / "media.html"), **options}
    result = run_scenario(scenario)
    assert result["ok"], result["stepErrors"]
    return result


def probe_value(tmp_path: Path, browser: str, **options: Any) -> dict[str, Any]:
    script = write_script(tmp_path, "probe.js", "return window.__probe;")
    steps = [{"kind": "eval", "file": script, "as": "probe"}]
    return run_media(browser, steps=steps, **options)["results"]["probe"]


# --- harness self-test ------------------------------------------------------


@pytest.mark.parametrize("browser", BROWSERS)
@pytest.mark.parametrize("reduced", [True, False])
def test_reduced_motion_is_emulated(browser: str, reduced: bool, tmp_path: Path) -> None:
    require_browser(browser)
    probe = probe_value(tmp_path, browser, reducedMotion=reduced)
    assert probe["prefersReducedMotion"] is reduced
    assert probe["js"] is True


@pytest.mark.parametrize("browser", BROWSERS)
def test_forced_colors_is_emulated(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    assert probe_value(tmp_path, browser, forcedColors="active")["forcedColors"] is True
    assert probe_value(tmp_path, browser, forcedColors="none")["forcedColors"] is False


@pytest.mark.parametrize("browser", BROWSERS)
def test_webgl_is_on_by_default_and_off_on_request(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    assert probe_value(tmp_path, browser)["webgl"] is True
    assert probe_value(tmp_path, browser, webgl=False)["webgl"] is False


@pytest.mark.parametrize("browser", BROWSERS)
def test_title_carries_the_probe_line(browser: str) -> None:
    require_browser(browser)
    result = run_media(browser, steps=[])
    assert result["browser"] == browser
    assert result["version"]
    assert result["cspViolations"] == []
    if browser == "chromium":
        # Firefox reports no request event for a file URL, so only Chromium lists them.
        assert any(name.endswith("media.html") for name in result["localRequests"])


@pytest.mark.parametrize("browser", BROWSERS)
def test_negative_control_reports_each_remote_attempt(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    wait = write_script(
        tmp_path,
        "settled.js",
        "return window.__probe.fetch !== 'pending' && window.__probe.socket !== 'pending';",
    )
    result = run_scenario(
        {
            "browser": browser,
            "url": file_url(PROBES / "negative-control.html"),
            "steps": [{"kind": "waitForFunction", "file": wait}],
        }
    )
    assert result["ok"], result["stepErrors"]
    blocked = {item["url"]: item["type"] for item in result["blockedRequests"]}
    assert "https://example.invalid/x" in blocked
    assert "http://example.invalid/i.png" in blocked
    assert "http://example.invalid/s.css" in blocked
    assert "wss://example.invalid/s" in blocked
    assert len(blocked) >= 4


@pytest.mark.parametrize("browser", BROWSERS)
def test_a_clean_page_reports_no_blocked_request(browser: str) -> None:
    require_browser(browser)
    assert run_media(browser, steps=[])["blockedRequests"] == []


@pytest.mark.parametrize("browser", BROWSERS)
def test_javascript_off_shows_the_noscript_text(browser: str) -> None:
    require_browser(browser)
    steps = [{"kind": "dom", "as": "dom"}]
    url = file_url(PROBES / "noscript.html")
    off = run_scenario({"browser": browser, "url": url, "javaScript": False, "steps": steps})
    on = run_scenario({"browser": browser, "url": url, "javaScript": True, "steps": steps})
    assert off["ok"] and on["ok"]
    assert "script is off" in off["results"]["dom"]
    assert "script is on" not in off["results"]["dom"]
    assert "script is on" in on["results"]["dom"]


@pytest.mark.parametrize("browser", BROWSERS)
def test_viewport_step_changes_the_inner_width(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    script = write_script(tmp_path, "width.js", "return window.innerWidth;")
    result = run_scenario(
        {
            "browser": browser,
            "url": file_url(PROBES / "media.html"),
            "viewport": {"width": 1000, "height": 700},
            "steps": [
                {"kind": "eval", "file": script, "as": "before"},
                {"kind": "setViewport", "width": 390, "height": 800},
                {"kind": "eval", "file": script, "as": "after"},
            ],
        }
    )
    assert result["ok"], result["stepErrors"]
    assert result["results"]["before"] == 1000
    assert result["results"]["after"] == 390


@pytest.mark.parametrize("browser", BROWSERS)
def test_eval_round_trips_an_args_object(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    script = write_script(tmp_path, "echo.js", "return { got: args, kind: typeof args.n };")
    args = {"n": 7, "text": "café", "list": [1, 2], "nested": {"ok": True}}
    result = run_media(
        browser, steps=[{"kind": "eval", "file": script, "as": "echo", "args": args}]
    )
    assert result["results"]["echo"] == {"got": args, "kind": "number"}


@pytest.mark.parametrize("browser", BROWSERS)
def test_screenshot_step_writes_a_png(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    shot = tmp_path / "shot.png"
    result = run_media(browser, steps=[{"kind": "screenshot", "path": str(shot)}])
    assert result["screenshots"] == [str(shot)]
    data = shot.read_bytes()
    assert data.startswith(PNG_MAGIC) and len(data) > 100


@pytest.mark.parametrize("browser", BROWSERS)
def test_a_page_script_error_is_data_not_a_crash(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    page = tmp_path / "broken.html"
    page.write_text(
        "<!doctype html><title>x</title><script>throw new Error('probe-boom')</script>",
        encoding="utf-8",
    )
    result = run_scenario({"browser": browser, "url": file_url(page), "steps": []})
    assert result["ok"] is True
    assert any("probe-boom" in text for text in result["pageErrors"])


@pytest.mark.parametrize("browser", BROWSERS)
def test_a_failed_step_is_reported_and_stops_the_run(browser: str) -> None:
    require_browser(browser)
    result = run_media(browser, steps=[])
    assert result["stepErrors"] == []
    failed = run_scenario(
        {
            "browser": browser,
            "url": file_url(PROBES / "media.html"),
            "timeoutMs": 1000,
            "steps": [{"kind": "click", "selector": "#does-not-exist"}],
        }
    )
    assert failed["ok"] is False
    assert failed["stepErrors"][0]["step"] == 1


def test_an_unknown_browser_raises_a_tool_error() -> None:
    if support.find_playwright() is None:
        pytest.skip("playwright is not installed")
    with pytest.raises(support.BrowserToolError):
        run_scenario({"browser": "netscape", "steps": []})


# --- unit tests of the wrapper ----------------------------------------------


def make_package(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "package.json").write_text("{}", encoding="utf-8")
    return folder


def test_find_playwright_prefers_the_environment_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dir = make_package(tmp_path / "env")
    npm_root = tmp_path / "root"
    make_package(npm_root / "playwright")
    monkeypatch.setenv(support.ENV_PLAYWRIGHT, str(env_dir))

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=f"{npm_root}\n", stderr="")

    monkeypatch.setattr(support.subprocess, "run", fake_run)
    assert support.find_playwright() == env_dir


def test_find_playwright_uses_the_npm_root_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    npm_root = tmp_path / "root"
    make_package(npm_root / "playwright")
    monkeypatch.setenv(support.ENV_PLAYWRIGHT, str(tmp_path / "missing"))
    calls: list[dict[str, Any]] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout=f"{npm_root}\n", stderr="")

    monkeypatch.setattr(support.subprocess, "run", fake_run)
    assert support.find_playwright() == npm_root / "playwright"
    assert calls[0]["timeout"] == 10


def test_find_playwright_falls_back_to_the_default_global_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    fallback = make_package(home / ".npm-global" / "lib" / "node_modules" / "playwright")
    monkeypatch.delenv(support.ENV_PLAYWRIGHT, raising=False)
    monkeypatch.setattr(support.Path, "home", classmethod(lambda cls: home))

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr(support.subprocess, "run", fake_run)
    assert support.find_playwright() == fallback


def test_find_playwright_returns_none_when_nothing_holds_a_package_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "empty").mkdir()
    monkeypatch.setenv(support.ENV_PLAYWRIGHT, str(tmp_path / "empty"))
    monkeypatch.setattr(support.Path, "home", classmethod(lambda cls: tmp_path / "nohome"))

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("npm")

    monkeypatch.setattr(support.subprocess, "run", fake_run)
    assert support.find_playwright() is None


def test_require_browser_skips_with_a_reason_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(support.ENV_REQUIRE, raising=False)
    monkeypatch.setattr(support, "_browser_state", lambda browser: "no tool here")
    with pytest.raises(pytest.skip.Exception) as caught:
        support.require_browser("chromium")
    assert "no tool here" in str(caught.value)


def test_require_browser_fails_when_the_variable_is_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(support.ENV_REQUIRE, "1")
    monkeypatch.setattr(support, "_browser_state", lambda browser: "no tool here")
    with pytest.raises(pytest.fail.Exception) as caught:
        support.require_browser("chromium")
    assert "no tool here" in str(caught.value)


def test_require_browser_passes_when_the_browser_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(support.ENV_REQUIRE, "1")
    monkeypatch.setattr(support, "_browser_state", lambda browser: "")
    support.require_browser("firefox")


def test_file_url_adds_the_fragment(tmp_path: Path) -> None:
    url = file_url(tmp_path / "a b.html", "view=map")
    assert url.startswith("file://")
    assert url.endswith("a%20b.html#view=map")
