# Codex verify unchecked

## ANSWER

`3d-force-graph@1.79.1` is MIT licensed and was published 2026-02-04, older than the required two weeks.
In headless Chromium, PBKDF2, AES-GCM and a local script under CSP `'self'` work on `file://`.
The test covers Chromium only; it does not close the Firefox or Safari verification requirement.

## EVIDENCE

- UI-SPEC `:595`: requires MIT and bundled notices, and says the pin age was unchecked.
- `npm view 3d-force-graph time --json`, field `1.79.1`: `2026-02-04T20:54:45.679Z`; `npm view 3d-force-graph@1.79.1 license --json`: `MIT`.
- UI-SPEC `:566-74`: describes PBKDF2/AES-GCM gate and marks `file://` WebCrypto unverified across browsers.
- Headless test: Playwright `1.58.2`, installed Chromium, temporary `file://` page. PBKDF2 derived an AES-GCM key; encrypt/decrypt returned the original text. Result: `PASS`.
- Same test used meta CSP `default-src 'none'; script-src 'self'; connect-src 'none'` and loaded a sibling JS file. Result: `PASS`, no browser console errors.
- Chromium was launched with Playwright's Node API from the installed global package. `playwright --version` and an actual browser run both succeeded.
- `pyproject.toml:11-22`: declared Python dependencies contain no crypto library. This does not rule out transitive packages; the UI gate uses browser WebCrypto.
- `run/engines.py:62-89,91-117,482-518`: manifest serializer writes `settings.unusual_pairs` and `settings.wording_and_meaning` from their settings dataclasses. Their relevant fields include `min_percentile`; wording settings also include `confirm_percentile`.
- `run/engines.py:79-88,108-116`: current defaults include unusual-pairs `min_percentile=0.90`, wording `min_percentile=0.0` and `confirm_percentile=0.75`.
- `run/engines.py:342-370`: wording reference parameters also record `threshold: None`; do not invent a fixed threshold when none is recorded.
- UI-SPEC `:311,679`: read each engine's own `manifest.settings`; if no cut-off is recorded, show no invented value and omit the weaker-pairs control.

## UNVERIFIED

- WebCrypto and CSP behavior in Firefox and Safari, including actual installed browsers.
- Whether the UI's complete gated hub works from disk; the probe tested the algorithms and CSP in isolation.
- Whether `0.90`, `0.0`, or `0.75` are the correct user-facing graph cut-offs. The source records setting fields, but the UI must define what each field means before labeling it.

## RISK

A Chromium-only success could be mistaken for cross-browser support. Engine percentiles are not automatically equivalent to a visible link threshold.

## NEXT

In planning, map each displayed per-engine cut-off to a defined manifest field and keep the browser matrix open until Firefox and Safari are checked.
