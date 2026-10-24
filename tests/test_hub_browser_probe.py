"""Self-tests of the browser harness, plus probes of file URL behavior.

The tests need Node and Playwright. When a tool or a browser is missing they skip with a
reason. Set EUREKA_REQUIRE_BROWSER=1 to turn the skip into a failure.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
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


# --- WebCrypto interop on a file URL (D-17) ---------------------------------

ITERATIONS = 600000
AAD = f"eureka.hub-envelope.v1|{ITERATIONS}"
PASSPHRASE = "pässword-for-the-probe"
PLAIN_TEXT = json.dumps({"hub": "probe", "n": 1, "text": "café"}, sort_keys=True)

DECRYPT_JS = """
window.hubDecrypt = async function (a) {
  const bytes = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
  const enc = new TextEncoder();
  try {
    const base = await crypto.subtle.importKey(
      "raw", enc.encode(a.passphrase), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: bytes(a.salt), iterations: a.iterations, hash: "SHA-256" },
      base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    const plain = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: bytes(a.nonce), additionalData: enc.encode(a.aad) },
      key, bytes(a.ciphertext));
    return { ok: true, text: new TextDecoder().decode(plain) };
  } catch (error) {
    return { ok: false, error: error.name };
  }
};
"""

DECRYPT_EVAL = """
const env = JSON.parse(document.getElementById("env").textContent);
return await window.hubDecrypt({ ...env, ...args });
"""


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def build_crypto_page(folder: Path) -> tuple[Path, dict[str, Any]]:
    """Encrypt a known text in Python and write a probe page that holds the values."""
    aesgcm = pytest.importorskip("cryptography.hazmat.primitives.ciphers.aead").AESGCM
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", PASSPHRASE.encode("utf-8"), salt, ITERATIONS, dklen=32)
    sealed = aesgcm(key).encrypt(nonce, PLAIN_TEXT.encode("utf-8"), AAD.encode("ascii"))
    env = {
        "passphrase": PASSPHRASE,
        "salt": b64(salt),
        "nonce": b64(nonce),
        "ciphertext": b64(sealed),
        "iterations": ITERATIONS,
        "aad": AAD,
    }
    (folder / "decrypt.js").write_text(DECRYPT_JS, encoding="utf-8")
    page = folder / "crypto.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><title>crypto probe</title></head>'
        '<body><script type="application/json" id="env">'
        + json.dumps(env)
        + '</script><script src="decrypt.js"></script></body></html>',
        encoding="utf-8",
    )
    return page, env


def crypto_steps(folder: Path, env: dict[str, Any]) -> list[dict[str, Any]]:
    script = write_script(folder, "decrypt-eval.js", DECRYPT_EVAL)
    sealed = bytearray(base64.b64decode(env["ciphertext"]))
    sealed[3] ^= 0x01
    return [
        {"kind": "eval", "file": script, "as": "good"},
        {"kind": "eval", "file": script, "as": "wrong_pass", "args": {"passphrase": "nope"}},
        {
            "kind": "eval",
            "file": script,
            "as": "tampered",
            "args": {"ciphertext": b64(bytes(sealed))},
        },
        {"kind": "eval", "file": script, "as": "wrong_aad", "args": {"aad": AAD + "x"}},
    ]


@pytest.mark.parametrize("browser", BROWSERS)
def test_webcrypto_opens_a_python_made_envelope_on_a_file_url(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    page, env = build_crypto_page(tmp_path)
    result = run_scenario(
        {"browser": browser, "url": file_url(page), "steps": crypto_steps(tmp_path, env)}
    )
    assert result["ok"], result["stepErrors"]
    found = result["results"]
    assert found["good"] == {"ok": True, "text": PLAIN_TEXT}
    for name in ("wrong_pass", "tampered", "wrong_aad"):
        assert found[name]["ok"] is False, name
        assert "text" not in found[name], name
        assert found[name]["error"] == "OperationError", (name, found[name])
    print(f"\nWEBCRYPTO {browser} {result['version']}: {found}")


def test_webkit_outcome_is_recorded_but_not_asserted(tmp_path: Path) -> None:
    if support.find_playwright() is None:
        pytest.skip("playwright is not installed")
    page, env = build_crypto_page(tmp_path)
    try:
        result = run_scenario(
            {
                "browser": "webkit",
                "url": file_url(page),
                "timeoutMs": 20000,
                "steps": crypto_steps(tmp_path, env),
            },
            timeout=90,
        )
    except support.BrowserToolError as error:
        print(f"\nWEBKIT launch error: {error}")
        return
    print(f"\nWEBKIT result: {result['version']} {result['results']}")


# --- Content-Security-Policy on a file URL (UI-SPEC section 12) --------------

SRC_LISTS = ("script-src", "style-src", "img-src", "font-src")
CSP_1 = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'none'"
)
CSP_2 = CSP_1.replace("'self'", "file:")
CSP_3 = CSP_1.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
CSP_CANDIDATES: tuple[tuple[str, str | None], ...] = (
    ("1", CSP_1),
    ("2", CSP_2),
    ("3", CSP_3),
    ("4", None),
)
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
CSP_PAGE = (
    '<!doctype html><html><head><meta charset="utf-8">{meta}<title>csp</title>'
    '<link rel="stylesheet" href="probe.css"></head><body><p id="t">text</p>'
    '<span id="s" style="display:block;width:77px">inline style</span>'
    '<img id="img" src="dot.png" alt="">'
    f'<img id="data" src="{DATA_GIF}" alt="">'
    '<img id="remote" src="http://example.invalid/i.png" alt="">'
    "<script>window.__inline = true;</script>"
    '<script src="probe.js"></script></body></html>'
)
CSP_CSS = (
    '@font-face{font-family:probefont;src:url("probe.woff2") format("woff2")}'
    "#t{font-family:probefont,sans-serif;display:block;width:123px}"
)
CSP_JS = (
    "window.__probe = { script: true };"
    "fetch('https://example.invalid/x').then("
    "function () { window.__probe.fetch = 'answered'; },"
    "function () { window.__probe.fetch = 'failed'; });"
)
CSP_EVAL = """
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
try { await document.fonts.load("16px probefont"); } catch (error) { /* font may fail */ }
for (let i = 0; i < 40 && !(window.__probe && window.__probe.fetch); i += 1) await wait(50);
const box = document.getElementById("t");
const img = document.getElementById("img");
return {
  script: Boolean(window.__probe && window.__probe.script),
  style: getComputedStyle(box).width === "123px",
  image: img.complete && img.naturalWidth > 0,
  dataImage: document.getElementById("data").naturalWidth > 0,
  inlineScript: window.__inline === true,
  cssomStyle: (() => {
    const el = document.createElement("div");
    document.body.appendChild(el);
    el.style.width = "99px";
    el.style.display = "block";
    return getComputedStyle(el).width === "99px";
  })(),
  inlineStyle: getComputedStyle(document.getElementById("s")).width === "77px",
  fontStatus: Array.from(document.fonts).map((face) => face.status),
};
"""


def write_csp_page(folder: Path, meta: str | None) -> Path:
    folder.mkdir()
    tag = f'<meta http-equiv="Content-Security-Policy" content="{meta}">' if meta else ""
    (folder / "index.html").write_text(CSP_PAGE.format(meta=tag), encoding="utf-8")
    (folder / "probe.css").write_text(CSP_CSS, encoding="utf-8")
    (folder / "probe.js").write_text(CSP_JS, encoding="utf-8")
    (folder / "dot.png").write_bytes(PNG_1X1)
    (folder / "probe.woff2").write_bytes(b"wOF2\x00\x01\x00\x00not-a-real-font")
    return folder / "index.html"


def probe_csp(browser: str, folder: Path, meta: str | None) -> dict[str, Any]:
    page = write_csp_page(folder, meta)
    script = write_script(folder.parent, f"csp-eval-{folder.name}.js", CSP_EVAL)
    result = run_scenario(
        {
            "browser": browser,
            "url": file_url(page),
            "steps": [{"kind": "eval", "file": script, "as": "state"}],
        }
    )
    assert result["ok"], result["stepErrors"]
    state = result["results"]["state"]
    directives = sorted({item["directive"] for item in result["cspViolations"]})
    font_blocked = "font-src" in directives
    font_requested = (not font_blocked) and any(
        s in ("loaded", "error") for s in state["fontStatus"]
    )
    violations = result["cspViolations"]
    return {
        "script": state["script"],
        "style": state["style"],
        "image": state["image"],
        "font": font_requested,
        "inline_script_ran": state["inlineScript"],
        "inline_style_applied": state["inlineStyle"],
        "cssom_style_works": state["cssomStyle"],
        "data_image_loaded": state["dataImage"],
        "violations": directives,
        "fetch_violation": "connect-src" in directives,
        "remote_image_violation": any(
            item["directive"] == "img-src" and item["blocked"].startswith("http")
            for item in violations
        ),
        "fetch_reached_harness": any(
            item["url"] == "https://example.invalid/x" for item in result["blockedRequests"]
        ),
    }


def loads_everything(row: dict[str, Any]) -> bool:
    return bool(row["script"] and row["style"] and row["image"] and row["font"])


def enforces(row: dict[str, Any]) -> bool:
    """A policy counts as enforced when it stops code, data URLs, remote loads and fetch."""
    return bool(
        not row["inline_script_ran"]
        and not row["data_image_loaded"]
        and row["remote_image_violation"]
        and row["fetch_violation"]
    )


def decide(table: dict[str, dict[str, dict[str, Any]]]) -> str:
    """Return the strictest candidate that loads all four types and is enforced."""
    for name, meta in CSP_CANDIDATES:
        if meta is None:
            continue
        rows = table[name].values()
        if all(loads_everything(row) and enforces(row) for row in rows):
            return meta
    return "none"


@pytest.fixture(scope="module")
def csp_table(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, dict[str, Any]]]:
    base = tmp_path_factory.mktemp("csp")
    table: dict[str, dict[str, dict[str, Any]]] = {}
    for browser in BROWSERS:
        require_browser(browser)
    for name, meta in CSP_CANDIDATES:
        table[name] = {
            browser: probe_csp(browser, base / f"{name}-{browser}", meta) for browser in BROWSERS
        }
    print("\nCSP table (candidate, browser: script style image font | violations | fetch):")
    for name, _meta in CSP_CANDIDATES:
        for browser, row in table[name].items():
            flags = " ".join(
                f"{key}={'yes' if row[key] else 'NO'}"
                for key in ("script", "style", "image", "font")
            )
            print(
                f"  {name} {browser:8} {flags} | {row['violations']} | "
                f"inline_script_ran={row['inline_script_ran']} "
                f"inline_style={row['inline_style_applied']} "
                f"cssom_style={row['cssom_style_works']} "
                f"data_image={row['data_image_loaded']} "
                f"remote_image_violation={row['remote_image_violation']} "
                f"fetch_violation={row['fetch_violation']} "
                f"reached_harness={row['fetch_reached_harness']} "
                f"enforced={enforces(row)}"
            )
    return table


def test_csp_control_page_loads_everything_and_the_harness_blocks_the_fetch(
    csp_table: dict[str, dict[str, dict[str, Any]]],
) -> None:
    for browser, row in csp_table["4"].items():
        assert loads_everything(row), (browser, row)
        assert row["violations"] == []
        assert row["inline_script_ran"] and row["data_image_loaded"]
        assert row["cssom_style_works"]
        assert not enforces(row)
        assert row["fetch_reached_harness"] is True


def test_csp_decision_follows_the_rule_and_matches_the_record(
    csp_table: dict[str, dict[str, dict[str, Any]]],
) -> None:
    decision = decide(csp_table)
    print(f"\nCSP decision computed: {decision}")
    record = Path(__file__).resolve().parents[1] / "docs" / "brand" / "hub-probe-results.md"
    if not record.is_file():
        pytest.skip("docs/brand/hub-probe-results.md is not written yet")
    lines = re.findall(r"^CSP decision:\s*(.*)$", record.read_text(encoding="utf-8"), re.M)
    assert [line.strip() for line in lines] == [decision]


@pytest.mark.parametrize("browser", BROWSERS)
def test_csp_probe_detects_an_enforced_policy(browser: str, tmp_path: Path) -> None:
    require_browser(browser)
    row = probe_csp(browser, tmp_path / "block", "default-src 'none'")
    # Firefox does not apply a meta policy to local file subresources (measured, see the
    # record), so only code, data URLs, remote loads and fetch are asserted here.
    assert not row["inline_script_ran"]
    assert not row["data_image_loaded"]
    assert row["remote_image_violation"]
    assert row["violations"], "the policy must report violations"
