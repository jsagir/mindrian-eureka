---
phase: quick
plan: 261107-wif
subsystem: packaging
tags: [packaging, optional-extra, partner-bundle, uv-lock]
requires: [261107-w6v]
provides:
  - core dependency list of 3 entries again
  - optional extra `bundle = ["packaging>=26.3"]`
affects: [pyproject.toml, uv.lock, scripts/build-partner-bundle]
key-files:
  modified:
    - pyproject.toml
    - uv.lock
    - scripts/build-partner-bundle
    - src/mindrian_eureka/partner_bundle/builder.py
    - tests/test_partner_bundle.py
decisions:
  - Only the owner-run bundle builder needs `packaging`; it moves to the `bundle` extra.
  - The pin test tests/test_hub_assets.py is not edited.
requirements: [PKG-07]
metrics:
  tasks: 1
  files: 5
completed: 2026-11-07
---

# Quick 261107-wif: packaging moves to an optional bundle extra

Core `dependencies` are `jsonschema`, `numpy`, `scikit-learn` again. `packaging>=26.3` sits in the new extra `bundle`.

## Commits

- 727dc23: `pyproject.toml` and `uv.lock`. The lock diff only moves the `packaging` edge from the root dependencies to the `bundle` extra (plus `provides-extras`).
- 2b86358: `scripts/build-partner-bundle` now runs `uv run --offline --extra bundle python -m ...`. The BundleError fix text in `builder.py` names `uv run --offline --extra bundle` and the script. New test `test_missing_packaging_fix_names_the_bundle_extra` pins the text (no network).

## Lock

`uv lock --offline` resolved with no network. No online `uv lock` was needed.

## Verification (PROVEN)

- `uv lock --check`: exit 0.
- Full pinning file set (`test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`): 156 passed.
- `uv run --no-sync --offline --locked --no-python-downloads eureka --version`: `eureka 0.1.0`.
- `scripts/build-partner-bundle --target host --wheels skip --out <scratch>`: exit 0, 1058 files. With the default wheel step offline the builder stops with the existing "needs the network" error (exit 2); this is expected and unrelated.
- ruff `src tests`: 1465 (baseline 1465). mypy `src`: 88 errors in 17 files (baseline).
- `docs/partner-run-guide.md` names only `scripts/build-partner-bundle`, not a bare `uv run`; no change needed.

## Deviations from Plan

[Rule 1 - Bug] The first version of the fix text was a line over 100 characters (ruff E501, count 1466). It was wrapped; the count is back at 1465.

## Known Stubs

None.

## Self-Check: PASSED
