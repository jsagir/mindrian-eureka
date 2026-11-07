---
phase: 04-public-example-and-reproduction-guide
plan: 03
subsystem: docs
tags: [reproduction-guide, replay-block, readme, tests, internal-only]

requires:
  - phase: 04-01
    provides: eureka check-example, contract constants (EXAMPLE_COMMAND, RESULT_MATCH, RESULT_NO_MATCH)
  - phase: 04-02
    provides: public example, expected-hashes.json, measured run facts
  - phase: 03
    provides: docs/jhtv-replay-record.md (outcome provenance_gap, room_mark pending_approval)
provides:
  - "docs/reproduce-the-jhtv-method.md: plain-English guide, 17 headings, 7 steps, status internal only"
  - "tests/guide_support.py: replay record contract (path, pending text, reader, statement builder, block reader)"
  - "tests/test_reproduction_guide.py: 15 tests that keep the guide true"
  - "README section 'Reproduce the method on public data'"
affects: [04-04]

tech-stack:
  added: []
  patterns:
    - "One marked block in a doc, compared by a test with a statement derived from one record file"
    - "Doc status derived from a release record front matter by rule, enforced by a test"

key-files:
  created:
    - docs/reproduce-the-jhtv-method.md
    - tests/guide_support.py
    - tests/test_reproduction_guide.py
  modified:
    - README.md

key-decisions:
  - "The replay block holds PENDING_TEXT now. Plan 04-04 replaces it with the statement derived from docs/jhtv-replay-record.md."
  - "The README section and the example README are checked for internal only, the record path and no-go. Only the guide lists the reopen_when ids."
  - "The guide states the model difference (all-MiniLM-L6-v2 here, mdbr-leaf-ir for the replay) and the linux-aarch64 limit in the section What is not reproducible."

patterns-established:
  - "replay_block / replay_statement / read_replay_record: the only path from a Phase 3 record to a sentence in the guide"

requirements-completed: []

duration: 25min
completed: 2026-11-07
---

# Phase 4 Plan 03: Reproduction guide Summary

**A plain-English guide takes a non-author from install to ranked pairs on the public example in 7 steps, states what is and is not reproducible with a source for each claim, and holds the replay statement in one marked block that a test ties to a single Phase 3 record file.**

## Accomplishments

- Guide with the 17 fixed headings, status `internal only` tied to the release record (decision no-go, status draft, gaps G1 G2 G3 G5), and the sentence `Do not publish this guide or the example.`
- Commands in the guide equal the contract constants. Numbers (36 records, 63 pairs, 200 pairs) come from `expected-hashes.json` and a test checks them.
- "What is not reproducible" has 7 bullets: private collection, unusual-pairs fidelity (74 percent, 0.62, 42 percent), wording-engine change of 2026-10-29 (UNVERIFIED on JHTV-size data), model difference, graph services, platform limit (linux-aarch64 only), score limit.
- Replay block: PENDING_TEXT between the markers. `grep -c "Replay outcome"` prints 1. The real Phase 3 record now exists (outcome provenance_gap, room_mark pending_approval), so `test_replay_block_state` accepts PENDING_TEXT or the derived statement. Plan 04-04 fills the block.
- README section added above `## Quick start`: 9 lines added, 0 removed.

## Task Commits

1. Task 1 (RED): support module and tests - `b41483a`
2. Task 2 (GREEN): guide - `1ef7402`
3. Task 3: README pointer - `9cdbfd0`

RED evidence: before the guide existed, `tests/test_reproduction_guide.py` gave 11 failed, 4 passed (the 4 passes are the unit cases of the replay statement, the block markers, the record reader and the package-data exclusion).

## Verification

- `tests/test_reproduction_guide.py` 15 passed. With `test_readme_commands`, `test_public_example`, `test_example_check`, `test_example_command`, `test_partner_bundle`: 79 passed. `test_room_seed_docs` 10 passed. `test_hub_public_fixture`, `test_public_example_fresh`, `test_release_gate_record`, `test_hub_review_record`: 66 passed, 1 skipped (opt-in real run).
- ruff on the 2 new Python files: All checks passed. No source file changed, so mypy and the full-suite baselines are unchanged (the full suite was not run, as the lead asked).
- Repeat-run proof for Step 7, run on 2026-11-07: two runs of the example input into two scratch folders, `diff -r --exclude=run-info.json` printed nothing, and `check-example` on the first gave MATCH (PROVEN). One run took 10.9 s wall.
- `git diff --numstat README.md` before commit: 9 added, 0 removed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan inconsistency] Status test scope for the README section and example README**
- Found during: Task 1
- Issue: the plan asks `test_status_follows_the_release_record` to find every `reopen_when` id in the README section and in the example README. The text the plan prescribes for the README section, and the existing example README, hold no ids.
- Fix: the guide must hold the path, `no-go` and every id. The README section and the example README must hold `internal only`, the record path and `no-go`.
- Files: `tests/test_reproduction_guide.py`

**2. [Rule 3 - Task order] The status test reads the README**
- Issue: Task 2 asks that all tests pass except `test_readme_section`, but `test_status_follows_the_release_record` needs the README section of Task 3.
- Fix: the README edit was made in the working tree before the guide commit, then the guide and the README were committed as 2 separate commits. Each commit holds only its own file.

**3. Wording of the fact "five graph services"**
- The plan table row said the services ran on 2026-10-19. The fact list says request files were saved on 2026-10-19 and the work ran from 2026-10-18 to 2026-10-21. The guide uses the second form.

## Known Stubs

The replay block holds the fixed pending text on purpose. Plan 04-04 replaces it with the statement derived from `docs/jhtv-replay-record.md`. The test already accepts both forms.

## Threat Flags

None. T-04-15 to T-04-20 are covered by tests: phrase pins on the sections, status test, package-data exclusion, name check against the release record, contract-command test, expected-number test, replay block rule.

## UNVERIFIED

- A fresh `uv sync` with network on a clean machine.
- Any platform other than linux-aarch64.
- Whether today's `eureka run` gives the JHTV lists (no comparison on JHTV-size data was run). The guide says so.

## Self-Check: PASSED

- Files exist: `docs/reproduce-the-jhtv-method.md`, `tests/guide_support.py`, `tests/test_reproduction_guide.py`, `README.md`.
- Commits exist: `b41483a`, `1ef7402`, `9cdbfd0`.
