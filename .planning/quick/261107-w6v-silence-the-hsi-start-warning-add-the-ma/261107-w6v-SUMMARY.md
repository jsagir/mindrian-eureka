---
phase: quick
plan: 261107-w6v
subsystem: mcp-server, packaging, docs
tags: [stderr, hsi, macos, packaging, lock]
requires: []
provides:
  - silent healthy start of eureka-mcp
  - macOS 14 minimum note in the partner guide
  - packaging declared as a dependency
affects: [opportunity_pairs/mcp_server.py, pyproject.toml, uv.lock]
tech-stack:
  added: [packaging>=26.3 (declared, already in lock)]
  patterns: [capture import-time stderr with contextlib.redirect_stderr, replay on failure]
key-files:
  created:
    - src/mindrian_eureka/opportunity_pairs/quiet_import.py
    - tests/test_mcp_start_stderr.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/mcp_server.py
    - docs/partner-run-guide.md
    - pyproject.toml
    - uv.lock
decisions:
  - The capture lives in a new module, quiet_import.py, imported first by mcp_server.py, to avoid E402 on every later import.
  - Lower bound packaging>=26.3 equals the version in uv.lock, as the plan asked.
metrics:
  completed: 2026-11-07
---

# Phase quick Plan 261107-w6v: Silent HSI start warning, macOS 14 note, packaging dependency

A healthy `eureka-mcp` start now writes 0 bytes to stderr; the partner guide states the macOS 14 minimum; `packaging` is declared with a matching lock.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Silent healthy start | 2065d46 | `quiet_import.py` runs the first `hsi_engine` import under `redirect_stderr`. Text is kept in `IMPORT_NOTES`. On failure the text is replayed to stderr and the error is raised again. |
| 2 macOS note and packaging | f4acbf9 | Guide note added (ASSUMED). `packaging>=26.3` added. `uv lock --offline` changed uv.lock by 2 lines (the dependency edge and the requires-dist entry). |

## Verification (PROVEN)

- RED: against the original mcp_server.py, the healthy-start test failed with the `HSI: warning` line on stderr.
- `uv run --no-sync --offline --locked --no-python-downloads eureka-mcp < /dev/null`: exit 0, 0 bytes on stderr.
- `pytest tests/test_mcp_start_stderr.py tests/test_run_engines.py tests/test_hsi_latest_integration.py tests/test_host_run_mcp.py tests/test_capability_cli.py tests/test_mcp_limits_parity.py`: 66 passed.
- `pytest tests/test_partner_bundle.py tests/test_readme_commands.py tests/test_mcp_start_stderr.py`: 34 passed.
- `uv lock --check`: exit 0. `eureka --version` under `--locked`: `eureka 0.1.0`.
- ruff on mcp_server.py: 34 errors, same as HEAD before the change. New files: 0 errors.
- mypy on mcp_server.py and quiet_import.py: 84 errors in 14 files, no error in the new module.
- `git diff --stat src/mindrian_eureka/hsi_reference.py`: empty.

## Deviations from Plan

**1. [Rule 3 - Blocking] New module quiet_import.py.** The plan listed only mcp_server.py. A capture statement placed between imports in mcp_server.py raised 14 new ruff E402 errors (ruff count rule). A first-imported helper module avoids this. No behavior change.

No network was used. `uv lock --offline` resolved.

## Known Stubs

None.

## Self-Check: PASSED

- quiet_import.py, test_mcp_start_stderr.py, this SUMMARY: present.
- Commits 2065d46 and f4acbf9: present.
