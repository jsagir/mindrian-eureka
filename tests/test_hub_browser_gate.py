"""Exercise the optional gate from local files; all passphrases are synthetic.

WebKit does not start here. Safari remains a human check in Plan 19.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import js_assignment
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.gate import encrypt_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.output import canonical_json
from test_hub_browser_core import CHECKS, METRICS, scenario

GATE = str(CHECKS / "gate-state.js")
PASS = "synthetic browser gate passphrase é"


def check(name: str, **args):
    return {"kind": "eval", "file": GATE, "as": name, "args": args}


def probe(tmp_path: Path) -> str:
    script = tmp_path / "gate-probe.js"
    script.write_text('''
window.__gateTransitions = [];
new MutationObserver(() => {
  const status = document.getElementById('hub-locked-status');
  const value = status?.textContent;
  if (value && window.__gateTransitions[window.__gateTransitions.length - 1] !== value) {
    window.__gateTransitions.push(value);
    if (!window.__gateBegin) window.__gateBegin = performance.now();
  }
  if (!window.__gateEnd && window.HubApp?.data) window.__gateEnd = performance.now();
}).observe(document, {subtree: true, childList: true, characterData: true});
''')
    return str(script)


def gated_hub(tmp_path: Path, mode: str | None = None, *, hostile=False) -> Path:
    pytest.importorskip("cryptography")
    run = make_run_folder(tmp_path, hostile=hostile)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out, password=PASS), Console(stderr=io.StringIO()))
    if mode:
        path = out / "hub-data.js"
        envelope = json.loads(path.read_text().removeprefix("window.HUB_ENVELOPE = ").rstrip(";\n"))
        if mode in {"ciphertext", "nonce"}:
            target = envelope if mode == "ciphertext" else envelope["cipher"]
            key = "ciphertext" if mode == "ciphertext" else "nonce"
            raw = base64.b64decode(target[key])
            target[key] = base64.b64encode(bytes([raw[0] ^ 1]) + raw[1:]).decode()
        elif mode == "truncated":
            envelope["ciphertext"] = envelope["ciphertext"][:-3]
        elif mode == "iterations":
            envelope["kdf"]["iterations"] += 1
        elif mode == "envelope-schema":
            envelope["schema"] = "eureka.hub-envelope.v0"
        else:
            data = (b"not json" if mode == "not-json"
                    else canonical_json({"schema": "eureka.hub-data.v0"}))
            envelope = encrypt_payload(data, PASS, load_run(run).manifest_sha256)
        path.write_bytes(js_assignment("HUB_ENVELOPE", envelope))
    return out


def submit(password: str):
    return [{"kind": "fill", "selector": "#hub-passphrase", "value": password},
            {"kind": "press", "selector": "#hub-passphrase", "key": "Enter"}]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_locked_state_and_right_passphrase(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = gated_hub(tmp_path)
    titles = [record.title for record in load_run(tmp_path / "run").records]
    result = scenario(out, browser, initScripts=[probe(tmp_path)], steps=[
        check("locked", titles=titles), *submit(PASS),
        check("open", wait="unlocked", titles=titles)])
    locked, opened = result["locked"], result["open"]
    assert locked["h1"] == DECK["L01"] and locked["face"].endswith("theo-boundary.svg")
    assert locked["status"] == "" and locked["focus"] == "hub-passphrase"
    assert locked["limitCopy"] and locked["meaning"] == DECK["L02"]
    assert not locked["hasTitle"] and not locked["hasDistinctID"] and locked["bindings"] == 0
    assert not any(item["visible"] for item in locked["hidden"])
    assert DECK["G13"] in locked["noscript"]
    assert not opened["locked"] and opened["schema"] == "eureka.hub-data.v1"
    assert opened["h1"] == DECK["B01"] and opened["face"].endswith("theo-handover.svg")
    assert opened["hasTitle"] and opened["count"] == 30
    assert opened["focus"] == "hub-title" and opened["fieldValue"] == ""
    assert DECK["L04"] in opened["transitions"]
    assert opened["storage"] == {"local": 0, "session": 0, "cookie": ""}
    assert opened["unlockMs"] is not None
    print(f"{browser} unlock: {opened['unlockMs']:.4f} ms")


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_wrong_passphrase_and_show_hide(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(gated_hub(tmp_path), browser, steps=[check("start"),
        {"kind": "click", "selector": "#hub-passphrase-toggle"}, check("shown"),
        {"kind": "click", "selector": "#hub-passphrase-toggle"}, check("hidden"),
        *submit("synthetic wrong passphrase"), check("wrong", wait=DECK["L05"])])
    assert result["start"]["autocomplete"] == "off"
    assert result["shown"]["fieldType"] == "text"
    assert result["shown"]["togglePressed"] == "true"
    assert result["shown"]["toggleText"] == DECK["L03.hide"]
    assert result["hidden"]["fieldType"] == "password"
    assert result["hidden"]["toggleText"] == DECK["L03.show"]
    wrong = result["wrong"]
    assert wrong["locked"] and wrong["schema"] is None and wrong["status"] == DECK["L05"]
    assert wrong["focus"] == "hub-passphrase" and wrong["face"].endswith("theo-boundary.svg")
    assert all(target["width"] >= 44 and target["height"] >= 44 for target in wrong["targets"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("mode,copy", [("ciphertext", "L05"), ("nonce", "L05"),
    ("truncated", "L05"), ("iterations", "L05"), ("envelope-schema", "L05"),
    ("not-json", "L08"), ("schema", "L08")])
def test_changed_or_damaged_payload(tmp_path: Path, browser: str, mode: str, copy: str) -> None:
    require_browser(browser)
    state = scenario(gated_hub(tmp_path, mode), browser, steps=[*submit(PASS),
        check("state", wait=DECK[copy])])["state"]
    assert state["locked"] and state["schema"] is None and state["status"] == DECK[copy]
    assert state["face"].endswith("theo-limit.svg" if copy == "L08" else "theo-boundary.svg")
    assert state["bindings"] == 0 and not any(item["visible"] for item in state["hidden"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_no_webcrypto_fails_closed(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = gated_hub(tmp_path)
    script = tmp_path / "no-crypto.js"
    script.write_text("Object.defineProperty(window.crypto, 'subtle', {value: undefined});")
    state = scenario(out, browser, initScripts=[str(script)], steps=[check("state")])["state"]
    assert state["status"] == DECK["L06"] and state["disabled"] and state["locked"]
    assert state["schema"] is None and state["bindings"] == 0


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_hostile_data_unlocks_as_text(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(gated_hub(tmp_path, hostile=True), browser, steps=[*submit(PASS),
        check("state", wait="unlocked")])["state"]
    assert state["schema"] == "eureka.hub-data.v1" and not state["injected"]


def test_locked_widths(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 1280):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900},
                      {"kind": "eval", "file": METRICS, "as": str(width)}])
    result = scenario(gated_hub(tmp_path), steps=steps)
    for width, metric in result.items():
        assert metric["scrollWidth"] <= int(width) and metric["minimum"] >= 13
        assert metric["targets"] == []
