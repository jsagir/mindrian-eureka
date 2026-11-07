---
phase: 03-host-integration-and-replay-rebuild
plan: 02
subsystem: host-run
tags: [host-run, contracts, schemas, staging, HOST-01]
requires: []
provides:
  - mindrian_eureka.host_run.contracts (normalize_request, HostRunError, REASONS, constants)
  - mindrian_eureka.host_run.bundle (stage_bundle, record_id_for, StagedBundle)
  - Schemas eureka.pair-screen-input.v1 and eureka.pair-screen.v1
affects: [03-03, 03-04, 03-05]
tech-stack:
  added: []
  patterns: ["plain-Python host package, no heavy import", "one sanitizer shared by the collision check and the staging"]
key-files:
  created:
    - src/mindrian_eureka/host_run/__init__.py
    - src/mindrian_eureka/host_run/contracts.py
    - src/mindrian_eureka/host_run/bundle.py
    - src/mindrian_eureka/data/schemas/pair-screen-input.v1.json
    - src/mindrian_eureka/data/schemas/pair-screen-output.v1.json
    - tests/host_run_support.py
    - tests/test_host_run_contracts.py
    - tests/test_host_run_bundle.py
  modified: []
key-decisions:
  - "A single text over MAX_RECORD_CHARS is refused with bundle_too_large (same code as the total limit); the message tells the two apart."
  - "id_map values are a frozen dataclass StagedArtifact (artifact_id, source_ref), keyed by record id."
  - "approval null is accepted as no approval; the schema still types approval as an object."
requirements-completed: []
duration: about 25 min
completed: 2026-11-07
---

# Phase 3 Plan 02: Host run contracts, schemas and bundle staging Summary

The host run now has its interface: closed request rules with 15 typed refusal codes, two published JSON schemas, and a staging step that writes a host bundle as one private CSV and one mapping file that the Phase 2 corpus builder reads with matching record ids.

HOST-01 is not complete. This plan covers the contract part only. Do not mark HOST-01 complete before the last plan of the phase.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Test support, contract and bundle tests (RED) | 92e4cfe |
| 2 | Contracts and the two schemas (GREEN, part 1) | 1cc91b0 |
| 3 | Bundle staging (GREEN, part 2) | a60537d |

## RED output

`tests/test_host_run_contracts.py` and `tests/test_host_run_bundle.py` before any source: 28 failed (ModuleNotFoundError for `mindrian_eureka.host_run`). The files hold 15 and 10 test functions (28 items with parametrization).

## GREEN counts

- After Task 2: contracts file 17 passed, 1 failed. The failing test is `test_package_imports_stay_light`; it imports `host_run.bundle`, which Task 3 creates. See Deviations.
- After Task 3: contracts and bundle files 28 passed, 0 failed.
- Guard set (`test_run_corpus`, `test_run_mapping`, `test_run_pipeline`) plus the 28 new tests: 174 passed, 0 failed.

## Schema ids

- `eureka.pair-screen-input.v1`: closed at the top, `artifacts` 2 to 3000, `top_k` 1 to 200, corpus enum `["room"]`, closed `approval` block.
- `eureka.pair-screen.v1`: closed at the top, `room_write` and `portfolio_write` const `not_performed`, `approval.verified_by_engine` const false, `files` rule: `inline` true needs `content`, `inline` false forbids it.

## The 15 refusal codes

`bad_request`, `too_many_artifacts`, `bundle_too_large`, `duplicate_artifact_id`, `id_collision`, `artifact_hash_mismatch`, `external_corpus_refused`, `approval_missing`, `approval_bad_reference`, `plan_unknown`, `plan_expired`, `plan_consumed`, `plan_mismatch`, `local_model_unavailable`, `too_few_usable_records`. This plan raises 8 of them. The other 7 belong to the gate and the job (plans 03-03 and 03-04).

## Lint counts

- `ruff check` on the new package and new tests: All checks passed.
- `ruff check src tests`: 1465 errors, same as the baseline.
- `mypy src`: 88 errors in 17 files, same as the baseline. The new package adds none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan inconsistency] Task 2 acceptance says 0 failed, but one test needs Task 3**
- **Found during:** Task 2
- **Issue:** `test_package_imports_stay_light` (written in Task 1 as planned) imports `host_run.bundle`, which exists only after Task 3. After Task 2 the contracts file shows 17 passed, 1 failed.
- **Fix:** None. A stub `bundle.py` would hide the gap. The test passes after Task 3 (28 passed).
- **Commit:** 1cc91b0 (Task 2), a60537d (Task 3 closes it)

**2. [Rule 2 - interpretation] One text over 1,000,000 characters maps to bundle_too_large**
- **Found during:** Task 1
- **Issue:** The planned test `test_bundle_size_rule` uses two texts of 11 MiB. Each text exceeds the per-record limit, and the plan places the per-artifact check before the total check. No code was named for the per-record case.
- **Fix:** A text over `MAX_RECORD_CHARS` gives `bundle_too_large`, with a message that names the artifact position. The test also checks 21 texts of 1,000,000 characters against the 20 MiB total.
- **Commit:** 92e4cfe, 1cc91b0

**3. [Tool path] Test and lint commands**
- The orchestrator set `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`; `ruff` and `mypy` ran directly from `/home/jsagi/.local/bin`. Counts match the planned baselines.

## Plugin checkout (information only)

`git status --short | wc -l` of `/home/jsagi/dev/MindrianOS-Plugin-release`: 0 at the end of this plan (1 at the end of plan 03-01). No plugin file was edited by this plan.

## Known Stubs

None.

## Threat Flags

None. T-03-04 to T-03-10 mitigations are in place and tested: closed key list, hash match, collision check against the corpus sanitizer, size limits, no echo of text or paths in refusals, modes 0700 and 0600, external corpus refused.

## Self-Check: PASSED

- All 8 created files: FOUND
- Commits 92e4cfe, 1cc91b0, a60537d: FOUND
- Nothing from `story/` staged; `cli.py` untouched; nothing pushed.
