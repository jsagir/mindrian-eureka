---
phase: quick
plan: 261107-wuy
subsystem: partner-bundle
tags: [launcher, powershell, windows, uv-sync]
requires: []
provides:
  - start.ps1 passes the uv sync arguments as a PowerShell array
affects:
  - src/mindrian_eureka/partner_bundle/launchers.py
  - tests/test_partner_bundle.py
key-files:
  modified:
    - src/mindrian_eureka/partner_bundle/launchers.py
    - tests/test_partner_bundle.py
decisions:
  - Build the sync command as `$SyncArgs` (array) and call `& $Uv @SyncArgs`; keep a joined `$SyncText` only for display lines.
metrics:
  tasks: 1
  files: 2
  completed: 2026-11-07
requirements: [PKG-07]
---

# Phase quick Plan 261107-wuy: Windows launcher, uv sync arguments as an array

One-liner: `start.ps1` now runs `uv sync` through an argument array with splatting, so a bundle path with spaces (for example `C:\Users\Jane Doe\...`) stays one argument.

## What changed

- `launchers.py` (START_PS1): `$Sync` string and `$Sync.Split(" ")` replaced by `$SyncArgs = @("sync", "--offline", "--no-index", "--find-links", "$Bundle\wheels", "--extra", "modern-encoder", "--extra", "hub-gate")`. The no-wheels form is the array without `--no-index` and `--find-links`. The call is `& $Uv @SyncArgs`.
- The `step 1` line and the `-DryRun` "would run" line print `$SyncText` (`$SyncArgs -join " "`). The visible text is the same as before for a path without spaces.
- The docker launcher `$Flags = "...".Split(" ")` (constant flags, no path) is unchanged.
- Tests (RED first, 2 failures, then GREEN): `test_start_ps1_passes_the_sync_arguments_as_an_array` and `test_start_ps1_sync_has_no_split_on_a_path`.
- `docs/partner-run-guide.md` was not changed. It already states that the launchers are ASSUMED and lists no Windows launcher limits.

## Verification

- PROVEN: pinning set (test_hub_assets, test_partner_bundle, test_readme_commands, test_public_example, test_example_check, test_release_gate_record, test_room_seed_docs, test_host_handoff_docs): 158 passed.
- PROVEN: ruff repo count 1465 (baseline 1465; one E501 from the new test was fixed). mypy 88 errors in 17 files (baseline).
- PROVEN: host bundle built under a folder named `dir with space`; `bash start.sh --dry-run` ran and printed its commands. The dry run joins the array with spaces for display only, so the printed text does not show quoting. The real bash run uses the quoted arrays `SYNC=(... --find-links "$BUNDLE/wheels" ...)` and `"${SYNC[@]}"`, read in the source. The bash launcher was not changed. It was not run without `--dry-run`.

## Deviations from Plan

None - plan executed as written.

## Known limits

- ASSUMED: the PowerShell fix works on a Windows machine. pwsh is not installed here. Only text tests cover it. The syntax uses PowerShell 5.1 features only (array literal, `-join`, splatting).
- The bash dry run was done on a no-wheels host bundle (`--wheels skip`), so the `--find-links` path form was not in its output.

## Known Stubs

None.

## Self-Check: PASSED

- Commit 4be74df exists (launchers.py, tests/test_partner_bundle.py).
