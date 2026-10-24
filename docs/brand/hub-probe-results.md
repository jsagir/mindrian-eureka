# Hub probe results (phase 2.1, plan 04)

This file records what was measured on 2026-10-24, on one machine, for the items that the UI-SPEC marked UNVERIFIED. Each section has a `Result:` line and a `Fallback:` line. The tests in `tests/test_hub_browser_probe.py` repeat the browser measurements. `tests/test_hub_probe_record.py` checks the structure of this file.

Limits of this record: one machine (Linux under WSL2), headless browsers only, file URLs only. No human looked at a page. Safari was not run. Visual verification is pending.

## Headless browser tool

Result: Playwright 1.58.2 is installed at `~/.npm-global/lib/node_modules/playwright` (command line tool at `~/.npm-global/bin/playwright`). It is not in the folder printed by `npm root -g`, so `find_playwright` also tries the default global folder. Browser builds are in `~/.cache/ms-playwright`. Headless Chromium 145.0.7632.0 and headless Firefox 146.0.1 start and pass all harness tests. WebKit does not start. The launch error is: `Host system is missing dependencies to run browsers. Missing libraries: libgtk-4.so.1, libgraphene-1.0.so.0, libxslt.so.1, libgstallocators-1.0.so.0, libgstapp-1.0.so.0, ...` (the list continues with more GStreamer libraries).

The harness is `tests/hub_browser/driver.cjs` (Node, no package.json, no node_modules) and `tests/hub_browser_support.py`. Measured facts about the harness:

- A negative control page (`tests/hub_browser/probes/negative-control.html`) makes a remote fetch, a remote image, a remote stylesheet and a remote WebSocket. Both browsers report all four. When the detector code is disabled by hand, the control test fails in both browsers.
- Firefox upgrades a remote `http:` image to `https:` and then does NOT pass that second request through the Playwright route. The route alone would miss it. The driver therefore also records every remote `request` event, and it adds a second layer: Firefox sends all remote traffic to a closed local proxy port (the request fails with a proxy refusal), and Chromium resolves no host name.
- Firefox emits no request event for file URLs. The `localRequests` list is complete in Chromium only.
- `page.evaluate` runs through the protocol, so it works on pages with a strict Content-Security-Policy in both browsers.

Fallback: when Node, Playwright or a browser is missing, the browser tests skip with a reason. `EUREKA_REQUIRE_BROWSER=1` turns the skip into a failure (use it in the release check). `EUREKA_PLAYWRIGHT_DIR` points to another Playwright folder.

## WebCrypto on file URLs

Result: `crypto.subtle` is present and `isSecureContext` is true on a file URL in Chromium and in Firefox. A ciphertext made in Python opens in both browsers. The exact derivation:

- Key: `hashlib.pbkdf2_hmac("sha256", passphrase_utf8, salt_16_bytes, 600000, dklen=32)`.
- Cipher: AES-256-GCM, 12 byte nonce, 16 byte tag appended to the ciphertext (the layout WebCrypto expects), made with `cryptography`'s `AESGCM`.
- Associated data: the ASCII text `eureka.hub-envelope.v1|600000`.
- Browser side: `importKey("raw", utf8(passphrase), "PBKDF2")`, then `deriveKey({name: "PBKDF2", salt, iterations: 600000, hash: "SHA-256"}, ..., {name: "AES-GCM", length: 256})`, then `decrypt({name: "AES-GCM", iv, additionalData}, key, ciphertext)`.

A wrong passphrase, one changed ciphertext byte and a changed associated data text each end in an `OperationError` in both browsers, with no text returned. A passphrase with a non-ASCII letter works (both sides use UTF-8). WebKit outcome: the browser does not start here (see the tool section), so nothing was measured. Safari is not covered.

Fallback: when `crypto.subtle` is missing (an old browser, or Safari behaving differently), the locked screen shows the L06 text instead of a password field, and the page opens nothing. The build side keeps `hashlib.pbkdf2_hmac` from the standard library.

## CSP on file URLs

Result: a meta tag Content-Security-Policy works on a file URL in Chromium and in Firefox, with one difference. Four candidates were tried on the same page (external script, external stylesheet with a font file, local image, plus probes for an inline script, an inline style attribute, a `data:` image, a remote image and a remote fetch). Candidate 1 is `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'`. Candidate 2 is candidate 1 with the scheme source `file:` in place of `'self'`. Candidate 3 is candidate 1 with `'unsafe-inline'` added to style-src. Candidate 4 has no meta tag.

| Candidate | Browser | Script | Stylesheet | Image | Font | Policy reports (directives) | Inline script | Inline style attribute | `data:` image | Remote fetch |
|-----------|---------|--------|------------|-------|------|-----------------------------|---------------|------------------------|---------------|--------------|
| 1 | Chromium | loads | loads | loads | loads | connect-src, img-src, script-src-elem, style-src-attr | blocked | blocked | blocked | blocked by policy |
| 1 | Firefox | loads | loads | loads | loads | connect-src, img-src, script-src-elem, style-src-attr | blocked | blocked | blocked | blocked by policy |
| 2 | Chromium | loads | loads | loads | loads | connect-src, img-src, script-src-elem, style-src-attr | blocked | blocked | blocked | blocked by policy |
| 2 | Firefox | loads | loads | loads | loads | connect-src, img-src, script-src-elem, style-src-attr | blocked | blocked | blocked | blocked by policy |
| 3 | Chromium | loads | loads | loads | loads | connect-src, img-src, script-src-elem | blocked | allowed | blocked | blocked by policy |
| 3 | Firefox | loads | loads | loads | loads | connect-src, img-src, script-src-elem | blocked | allowed | blocked | blocked by policy |
| 4 (none) | Chromium | loads | loads | loads | loads | none | runs | allowed | loads | reaches the harness block |
| 4 (none) | Firefox | loads | loads | loads | loads | none | runs | allowed | loads | reaches the harness block |

More measured facts:

- Setting a style through the page script (`element.style.width = "99px"`) works under every candidate, including candidate 1. Only the `style` attribute in the HTML is blocked by candidate 1. The built page must not use inline `style=` attributes, and must not contain an inline script.
- The font check is indirect. The probe font file is not a real font, so the face ends in the `error` state; the check is that the policy reported no font-src violation and the browser tried the load.
- Firefox 146.0.1 does not apply a meta policy to local file subresources. A page with only `default-src 'none'` still ran an external local script in Firefox, and Chromium blocked it. Firefox did enforce the policy on inline script, on `data:` images, on remote loads and on fetch. So the policy is a real control against network leaks and inline code in both browsers, and it is NOT a control against loading local files in Firefox.
- The candidates 1 and 2 behave the same in both browsers on this machine. Candidate 1 is the stricter text, because `file:` allows any local file.

CSP decision: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'

Decision rule used: the strictest candidate for which script, stylesheet, image and font all load in BOTH browsers, and the policy is enforced (inline script blocked, `data:` image blocked, a remote image reported, the remote fetch reported). The test `test_csp_decision_follows_the_rule_and_matches_the_record` computes the decision from fresh measurements and compares it with the line above.

Fallback: if a later browser version stops loading local files under the chosen policy, the decision becomes "none": no meta tag, and the controls are the static scan of the built page (no remote URL, no inline script) and the page-level request block of the harness.

## WebGL in headless browsers

Result: WebGL context creation works in headless Chromium and headless Firefox. Chromium reports the renderer `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device ...), SwiftShader driver)` both with and without the SwiftShader launch flags. Firefox reports `WebGL 1.0` with a software renderer (llvmpipe). The driver turns WebGL off for a test with `--disable-gpu --disable-3d-apis` (Chromium) or the preference `webgl.disabled` (Firefox); in both browsers `canvas.getContext("webgl")` then returns nothing. Rendering speed on software WebGL was not measured, and no screenshot of a WebGL scene was inspected. Visual verification is pending.

Fallback: a test of the 3D view runs with WebGL on (software renderer) and a separate test runs with WebGL off, to show the fallback screen. If a machine lacks both, the test skips with a reason.

## 3d-force-graph (npm)

Commands run on 2026-10-24 (a development-time call; the hub itself never calls the network):

```text
npm view 3d-force-graph@1.79.1 version license dist.integrity dist.tarball --json
npm view 3d-force-graph time --json
npm view 3d-force-graph dist-tags --json
```

| Field | Value |
|-------|-------|
| Version | 1.79.1 |
| License | MIT |
| Integrity | sha512-iscIVt4jWjJ11KEEswgOIOWk8Ew4EFKHRyERJXJ0ouycqzHCtWwb9E5imnxS5rYF1f1IESkFNAfB+h3EkU0Irw== |
| Tarball | https://registry.npmjs.org/3d-force-graph/-/3d-force-graph-1.79.1.tgz |
| Published | 2026-02-04 (2026-02-04T20:54:45.679Z) |
| Age on 2026-10-24 | 262 days (rule: at least 14 days) |
| Newest version | 1.80.1, published 2026-09-29 (25 days old). It is the `latest` tag. |
| Version between | 1.80.0, published 2026-04-05 |

Result: the pin 1.79.1 is MIT licensed, 262 days old, so it passes the 14 day rule of UI-SPEC section 14. The integrity string above is what the registry reports; it was not yet checked against a downloaded file. The license text and notices inside the tarball were not yet read.

Fallback: if 1.79.1 is missing or younger than 14 days when plan 06 vendors the file, use the newest version that is at least 14 days old, and the owner confirms the change because D-12 names 1.79.1. Plan 06 downloads the tarball, checks it against the integrity string, and a person checks the package pages (threat T-02.1-15).

## Crypto library dependency

Commands and outputs on 2026-10-24:

```text
$ grep -n 'name = "cryptography"' -A2 uv.lock
194:name = "cryptography"
195-version = "50.0.2"

$ grep -n '"pyjwt' uv.lock
622:    { name = "pyjwt", extra = ["crypto"] }      (inside the mcp 2.3.0 block)

$ sed -n 1188,1191p uv.lock
[package.optional-dependencies]
crypto = [
    { name = "cryptography" },
]

$ grep -n "cryptography" pyproject.toml
(no output)

$ python3 -c "import cryptography; print(cryptography.__version__)"       # system Python
46.0.3

$ .venv/bin/python -c "import cryptography; print(cryptography.__version__)"   # project environment
50.0.2
```

In `uv.lock`, `cryptography` is reached only through `mcp` (the `mcp-server` extra), which needs `pyjwt` with its `crypto` extra. The `mindrian-eureka` package lists only `jsonschema`, `numpy` and `scikit-learn` as base dependencies, and `pyproject.toml` has no direct `cryptography` line. The project environment on this machine has `cryptography` 50.0.2 because extras were installed there, not because the base install needs it.

Result: `cryptography` is NOT a base dependency. A base `uv sync` does not install it. Decision: add an optional extra named `hub-gate` with `cryptography` (plan 06 edits `pyproject.toml`). PBKDF2 needs only the standard library `hashlib.pbkdf2_hmac`; only AES-GCM needs the library.

Fallback: if the library is missing when `--password-env` is used, the build stops with exit code 2 and a fix text that names `uv sync --extra hub-gate`. The tests that make a ciphertext use `pytest.importorskip("cryptography")`.

## Safari (WebKit)

Result: not testable here. WebKit does not start on this machine (see "Headless browser tool": missing system libraries), and no Safari was available. Nothing about Safari is claimed. The gate, the CSP and the 3D view need a human check in Safari in plan 19.

Fallback: the locked screen shows L06 ("This browser cannot unlock the file. Open the page in a current browser.") when `crypto.subtle` is missing, and the CSP meta tag is optional hardening, so a Safari difference in either degrades to a clear message and not to a leak.

## Engine cut-offs in the manifest

The manifest `settings` section is written from the engine settings dataclasses in `src/mindrian_eureka/run/engines.py` (`manifest_engine_sections`). The keys below were read from that code and checked against a manifest from a stub run in `tests/test_hub_probe_record.py`. No manifest from a real model run exists on this machine.

- `settings.unusual_pairs.min_percentile`: default 0.90. The percentile gate for pairs of the unusual-pairs engine.
- `settings.wording_and_meaning.min_percentile`: default 0.0. The percentile gate for pairs of the wording-and-meaning engine. The value 0.0 hides nothing.
- `settings.wording_and_meaning.confirm_percentile`: default 0.75. The percentile at which the second wording signal confirms a pair. It is a confirmation level, not a display cut-off.

Reading of the engine code (not a run): both engines apply `min_percentile` before ranking (`opportunity_pairs/algorithm.py` line 318 and `hsi_reference.py` line 1095), so pairs below the gate may be absent from the pair files of the run. The wording engine also records `threshold: None` in its reference parameters (`engines.py` line 375); the hub must not invent a number for it.

Result: each engine has a named percentile gate in `settings`, and the keys exist in a stub-run manifest. Whether a percentile gate equals a visible link cut-off, and whether the run folder still holds pairs below the gate, is UNVERIFIED and goes to plan 08.

Fallback: a missing key means "no cut-off" (B06 text, and no "Show weaker pairs" control). A value of 0.0 means the engine hides nothing. The hub never invents a number.
