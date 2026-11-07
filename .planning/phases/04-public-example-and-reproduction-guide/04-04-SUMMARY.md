---
phase: 04-public-example-and-reproduction-guide
plan: 04
subsystem: docs
tags: [reproduction-guide, replay-block, provenance-gap, release-status, internal-only]

requires:
  - phase: 03
    provides: docs/jhtv-replay-record.md (outcome provenance_gap, room_mark pending_approval)
  - phase: 04-03
    provides: guide with a pending replay block, guide_support reader and statement builder
provides:
  - "docs/reproduce-the-jhtv-method.md: replay block filled from the Phase 3 record"
  - "tests/test_reproduction_guide.py: block demands the record, new key-isolation test"
affects: []

tech-stack:
  added: []
  patterns:
    - "Replay statement is derived by code from one record file; a test compares the guide block with it"

key-files:
  created: []
  modified:
    - docs/reproduce-the-jhtv-method.md
    - tests/guide_support.py
    - tests/test_reproduction_guide.py

key-decisions:
  - "The Phase 3 record matched the contract of plan 04-03 (path, keys, format), so no adaptation of REPLAY_RECORD_PATH, the reader or the statement text was needed (P-15 not triggered)."
  - "The PENDING_TEXT constant was removed. No pending branch remains in code or tests."

patterns-established:
  - "test_statement_uses_only_listed_keys: extra record keys carrying marker text must not change the statement"

requirements-completed: []

duration: 20min
completed: 2026-11-07
---

# Phase 4 Plan 04: Replay outcome in the guide Summary

**The guide now states "Replay outcome: provenance gap" for the graph-derive replay (2,130 claims, 2,267,385 pairs, OPP-027 to OPP-031), derived by code from `docs/jhtv-replay-record.md`; the example hashes did not drift; release status stays INTERNAL ONLY.**

## Precondition (P-15)

- Phase 3 plan: 03-06 (HOST-02 replay record, commit 8400d87), SUMMARY `03-06-SUMMARY.md`; SUMMARY files 03-01 to 03-07 present in `.planning/phases/03-host-integration-and-replay-rebuild/`.
- Record file: `docs/jhtv-replay-record.md`, front matter `outcome: provenance_gap`, `room_mark: pending_approval`, `label: candidate, not verified`, `checked_on: 2026-11-07`. PROVEN (read).
- The ROADMAP Progress row of Phase 3 still reads "0/TBD, Not started". The orchestrator owns ROADMAP.md; the row is stale. Not edited here.
- The record shape equals the contract of plan 04-03. No change to the path, reader or statement text.

## Accomplishments

- Task 1: `test_replay_block_state` now requires the record file and equality of the block with `replay_statement(read_replay_record())`. It also requires that "not recorded yet" is absent. New `test_statement_uses_only_listed_keys` injects marker text into extra keys (`label`, `note`, `title`, `checked_on`, `opportunity`) and proves the statement does not change. `label` is excluded from the real-record loop because the fixed label is constant statement text.
- Task 2: the replay block holds the derived statement. No other sentence of the guide changed. The outcome is `provenance_gap`, so the table row and the "What is reproducible" list needed no fix.
- Drift guard: `test_engine_identity_is_current` passed. `expected-hashes.json` and `reference-run` are unchanged (`git status --short examples` prints nothing). No rebuild was needed (P-16 not triggered).

## Task Commits

1. Task 1 (RED): `03d82f3` - test(04-04): require the Phase 3 replay record and pin the listed keys
2. Task 2 (GREEN): `53d14ec` - docs(04-04): fill the replay block of the guide from the Phase 3 record

RED evidence: after Task 1, `tests/test_reproduction_guide.py` gave 1 failed (`test_replay_block_state`, pending text still in the guide), 15 passed.

## Verification

- `tests/test_reproduction_guide.py` 16 passed after Task 2.
- Task 2 verify set (`test_reproduction_guide`, `test_public_example`, `test_example_check`, `test_example_command`, `test_readme_commands`, `test_hub_public_fixture`, `test_release_gate_record`): 121 passed in 39.8 s.
- Opt-in real-model test `EUREKA_EXAMPLE_REAL_RUN=1 nice -n 19 pytest tests/test_public_example_fresh.py`: 5 passed in 105.6 s.
- ruff on the 8 Phase 4 test files: All checks passed. `mypy --strict src/mindrian_eureka/example`: no issues in 5 source files.
- Gates: `grep -c "not recorded yet"` prints 0; `grep -c "Replay outcome:"` prints 1; `git status --short tests/fixtures` prints nothing; `git status --short` shows only `story/` entries and `docs/research/` that existed before.
- Full suite: NOT run by this executor, by order of the lead. The orchestrator runs it. Baseline: 1624 passed, 28 skipped, 0 failed.

## Deviations from Plan

None - plan executed as written. Two notes:
- The plan names `uv run --offline --with pytest python -m pytest`. The lead set the test command to `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`. This summary used the lead command.
- The plan item 6 asks for a full-suite step and a failure list. Both go to the orchestrator.

## Release status

INTERNAL ONLY. The release decision is `no-go` with status `draft` in `docs/rs-release-gate.md`; the gaps G1, G2, G3 and G5 stay open. The owner changes the record; an executor does not, and `decided_on` stays empty.

The status is written in 4 places: the guide (`docs/reproduce-the-jhtv-method.md`), the example README (`examples/public-example/README.md`), the README section "Reproduce the method on public data", and this summary. The status follows the record and a test enforces it (`test_status_follows_the_release_record`, plan 04-03). The release record was not changed.

## Known Stubs

None. The pending text is gone from the guide and from the support module.

## Threat Flags

None. T-04-21 to T-04-25 are covered: the block is derived by code and compared by test (T-04-21), the key-isolation test (T-04-22), the drift guard passed and the real-run test passed (T-04-23), the record is required and the pending words count is 0 (T-04-24), the status test stays green (T-04-25).

## UNVERIFIED

- The human check of the plan is PENDING and is not marked done: a person who is not the author follows `docs/reproduce-the-jhtv-method.md` on a second machine, from `uv sync` to `Result: MATCH`, and writes down each unclear sentence and each failed command. The owner reports back.
- The install on a clean machine with a network or a carried wheel set.
- The guide read by a person who is not the author.
- Hash equality on a platform other than the checked setups of the example README (linux-aarch64 only is listed).
- The 2,117-record scale (Phase 2 human item).
- The full suite on the final tree (the orchestrator runs it).

## Self-Check: PASSED

- Files exist: `docs/reproduce-the-jhtv-method.md`, `tests/guide_support.py`, `tests/test_reproduction_guide.py`, `docs/jhtv-replay-record.md`.
- Commits exist: `03d82f3`, `53d14ec`.
