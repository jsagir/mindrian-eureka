---
phase: 03-host-integration-and-replay-rebuild
plan: 03
subsystem: host-run
tags: [host-run, approval-gate, plan-digest, receipts, HOST-01]
requires: [03-02]
provides:
  - mindrian_eureka.host_run.gate (plan_digest, PlanReceipts, Claim, check_start, RECEIPT_FILE_NAME)
  - mindrian_eureka.host_run.plan (build_plan)
  - Run-time file plan-receipts.sqlite3 (mode 0600) in the Eureka data directory
affects: [03-04, 03-05]
tech-stack:
  added: []
  patterns: ["plain-Python gate, no heavy import", "BEGIN IMMEDIATE single-use claim", "throwaway staging folder removed on exit"]
key-files:
  created:
    - src/mindrian_eureka/host_run/gate.py
    - src/mindrian_eureka/host_run/plan.py
    - tests/test_host_run_gate.py
    - tests/test_host_run_plan.py
  modified: []
key-decisions:
  - "plan_digest covers capability id, objective, scope, snapshot, top_k and artifacts sorted by id (id, source_ref, title, text_sha256). The approval block is not part of it."
  - "claim order: plan_unknown, retry with the same key and approval_ref, plan_expired, plan_consumed, then mark the newest free live row consumed."
  - "A ready plan adds its own warning below 10 usable records, because the corpus builder warns only below 5."
requirements-completed: []
duration: about 20 min
completed: 2026-11-07
---

# Phase 3 Plan 03: Approval gate and plan builder Summary

The host run now has its approval mechanism: a plan digest bound to the exact bundle, a private single-use receipt store with an audit row, a start check with typed refusals, and a plan builder that states what a run reads, writes and ranks before anything starts.

HOST-01 is not complete. This plan covers the gate and the plan only. Do not mark HOST-01 complete before the last plan of the phase.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Gate and plan tests (RED) | a459c9f |
| 2 | Digest, receipt store, start check (GREEN, part 1) | d24d385 |
| 3 | Plan builder (GREEN, part 2) | 3350df8 |

## RED output

Both test files before any source: 34 failed (ModuleNotFoundError for `host_run.gate` and `host_run.plan`) in 0.33 s. The files hold 15 and 12 test functions (34 items with parametrization). Ruff on both files: All checks passed.

## GREEN counts

- After Task 2: `test_host_run_gate.py` 21 passed, 1 failed. The failure is `test_module_import_is_light`, which imports `host_run.plan` (Task 3).
- After Task 3: gate and plan files 34 passed, 0 failed.
- Guard set (`test_run_corpus`, `test_models`, `test_doctor`, `test_host_run_contracts`, `test_host_run_bundle`): 198 passed, 1 skipped, 0 failed.
- Gate, plan, contracts and bundle files together: 62 passed.

## Receipt table

File `plan-receipts.sqlite3`, mode 0600, data directory mode 0700, rollback journal (no side files). Table `receipts`: `receipt_id` (integer, autoincrement), `plan_digest`, `scope_id`, `snapshot_id`, `created_at`, `expires_at`, `consumed_at`, `approval_ref`, `idempotency_key`, `job_id`. It holds digests, ids and times only. Rows older than `RECEIPT_RETENTION_SECONDS` are removed when the store opens.

## Plan key list

Ready plan: `schema_version`, `status`, `label`, `capability_id`, `plan_digest`, `expires_at`, `scope_id`, `snapshot_id`, `objective`, `top_k`, `counts` (`artifacts`, `text_bytes`, `records_usable`, `records_dropped`), `engines`, `model` (`found`, `origin`), `outputs_expected`, `network`, `writes` (`room`, `portfolio`, `job_store`, `derived_vectors`, `plan_receipt`), `approval_required`, `how_to_approve`, `stages`, `warnings`, `host_handoff`.

Blocked plan: `schema_version`, `status`, `label`, `capability_id`, `reason`, `message`, `fix`, `scope_id`, `snapshot_id`, `host_handoff`. Reasons: `too_few_usable_records`, `local_model_unavailable`. A blocked plan records no receipt.

## Refusal codes now raised

`approval_missing`, `plan_mismatch`, `plan_unknown`, `plan_expired`, `plan_consumed` (gate). The plan returns `local_model_unavailable` and `too_few_usable_records` as blocked plans, not as exceptions. Of the 15 codes in `REASONS`, 8 come from `bundle`/`contracts` (plan 03-02), 5 from the gate, 2 from the plan. All 15 codes now have a raiser.

## Lint counts

- ruff on `host_run` and both new tests: All checks passed.
- `ruff check src tests`: 1465 errors (baseline 1465).
- `mypy src`: 88 errors in 17 files (baseline 88). New files add none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan fact wrong] The corpus builder warns below 5 records, not below 10**
- **Found during:** Task 3
- **Issue:** The plan says the builder warns when fewer than 10 usable records exist, and test `test_plan_warns_on_a_small_collection` expects a warning with `10` for 5 records. The builder (`_ENGINE_MIN_RECORDS = 5`) warns only below 5.
- **Fix:** `build_plan` adds its own warning when fewer than 10 usable records exist and no builder warning names 10: "Only N usable records. A collection of 10 or more gives more useful candidates."
- **Files modified:** `src/mindrian_eureka/host_run/plan.py`
- **Commit:** 3350df8

**2. [Plan inconsistency] Task 2 acceptance allows one failing test**
- `test_module_import_is_light` fails after Task 2 as the plan predicted; it passes after Task 3.

**3. [Tool path] Test and lint commands**
- Used `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`, and `ruff` and `mypy` from `/home/jsagi/.local/bin`, as the orchestrator set.

## Boundaries

- Plugin checkouts `MindrianOS-Plugin-release` and `MindrianOS-Plugin`: `git status --short | wc -l` is 0 for both (information only). No plugin file was edited.
- `cli.py` is unchanged. Nothing was pushed. No `story/` or `docs/research/` file was staged.
- The plan makes no network call (test with the `no_network` fixture) and does not load the model.

## Known Stubs

None.

## Threat Flags

None. T-03-11 to T-03-17 mitigations are in place and tested: five start refusals, digest bound to every artifact field, audit row with approval reference and idempotency key, single use with a two-thread test that gives one winner, no text in the receipt file or the plan, `searched` lines never returned and origin text stripped of paths, staging folder removed on exit.

## Self-Check: PASSED

- Files `gate.py`, `plan.py`, `test_host_run_gate.py`, `test_host_run_plan.py`: FOUND
- Commits a459c9f, d24d385, 3350df8: FOUND
