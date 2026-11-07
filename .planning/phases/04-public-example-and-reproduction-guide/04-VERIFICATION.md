---
phase: 04-public-example-and-reproduction-guide
verified: 2026-11-07T00:00:00Z
status: human_needed
score: 4/4 roadmap criteria verified, plus 3/3 side checks
overrides_applied: 0
human_verification:
  - test: "A non-author follows docs/reproduce-the-jhtv-method.md on a second machine, from uv sync to eureka check-example."
    expected: "Steps 1 to 4 finish without help. check-example prints Result: MATCH on the same platform, or prints INFO lines on another platform."
    why_human: "All runs so far were on one machine (linux-aarch64) by the author side. Guide clarity for a stranger cannot be checked by grep."
  - test: "Owner signs off the release decision in docs/rs-release-gate.md."
    expected: "decided_on is set and status leaves draft. Until then the example and the guide stay internal only."
    why_human: "Only the owner can change the decision. The record is decision no-go, status draft, reopen_when G1 G2 G3 G5."
---

# Phase 4: Public Example and Reproduction Guide Verification Report

**Phase Goal:** A stranger can reproduce a documented run from public data and knows exactly what is and is not reproducible about the JHTV method.
**Verified:** 2026-11-07
**Status:** human_needed
**Re-verification:** No, initial verification.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A small public dataset ships with a license record and `eureka run` finishes on it end to end | VERIFIED | 36 input files in `tests/fixtures/hub_public/input` (counted). `SOURCE.md` names CC0 1.0, the URL and a quoted statement. `EUREKA_EXAMPLE_REAL_RUN=1 pytest tests/test_public_example_fresh.py`: 5 passed in 17.5 s. The test copies tracked files to an empty folder, runs `eureka run` with the real model, and compares the outputs. |
| 2 | Output hashes match the shipped expected hashes, and a check fails on a difference | VERIFIED | `eureka check-example examples/public-example/reference-run --expected examples/public-example/expected-hashes.json`: X1 to X7 PASS, `Result: MATCH`, exit 0. Tamper check in a scratch copy: 1 byte of `ranked-pairs.md` flipped. X6 FAIL, `Result: NO MATCH`, exit 1. |
| 3 | A plain-English guide walks a non-author from install to ranked pairs | VERIFIED (clarity for a stranger: human item 1) | `docs/reproduce-the-jhtv-method.md` has 7 steps: install, doctor, run, check hashes, read ranked pairs, hub, own folder. Commands match the CLI. `modern-encoder` extra exists in `pyproject.toml`. A glossary and a mismatch table are present. |
| 4 | Guide states what is and is not reproducible, includes the Phase 3 replay outcome, keeps "candidate, not verified" | VERIFIED | Sections "What is reproducible" and "What is not reproducible" (7 bullets, each with a source). Replay block states "Replay outcome: provenance gap", matches `outcome: provenance_gap` and `room_mark: pending_approval` in `docs/jhtv-replay-record.md`. The block is derived by code and compared by a test. The label appears in the intro, Steps 5 and 7, the replay block, and the last bullet. |

**Score:** 4/4

### Side checks

| Check | Status | Evidence |
|-------|--------|----------|
| Release status stays internal only (decision no-go) | VERIFIED | `docs/rs-release-gate.md` front matter: `decision: no-go`, `status: draft`, `decided_on: ""`. Guide, example README and top-level README section all say internal only and cite the record. A test ties the guide status to the record. |
| No personal name or institution name in the guide and example README | VERIFIED | Grep for Sagir, Jonathan, Johns, Hopkins, JHU, university, institute found none in either file. "JHTV" appears as the method name required by the roadmap. It is not expanded. "Partner" is used for the room owner. |
| No em dash in added doc text | VERIFIED | `grep -c "—"` gives 0 in the guide and the example README. The added lines of the README section (commit 9cdbfd0) and all added lines in README.md and docs since b41483a contain 0 em dashes. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `examples/public-example/README.md` | VERIFIED | Status, data, license pointer, 4 commands, check table. |
| `examples/public-example/expected-hashes.json` | VERIFIED | Inputs, settings, model, engine, 4 output hashes, model note. |
| `examples/public-example/reference-run/` (5 files) | VERIFIED | Passes `check-example`. |
| `src/mindrian_eureka/example/` (contracts, check, build, command) | VERIFIED | Wired in `cli.py`. The command ran and gave exit codes 0 and 1. |
| `scripts/make-example-hashes` | EXISTS | Not run here. Drift guard test passes. |
| `docs/reproduce-the-jhtv-method.md` | VERIFIED | Substantive. 16 guide tests pass. |
| `docs/jhtv-replay-record.md` | VERIFIED | Phase 3 record, read by the guide test. |
| README section "Reproduce the method on public data" | VERIFIED | 9 lines added, links to both docs. |

### Key Links

| From | To | Status |
|------|----|--------|
| Guide replay block | `docs/jhtv-replay-record.md` | WIRED (derived by `tests/guide_support.py`, equality tested) |
| Guide status | `docs/rs-release-gate.md` | WIRED (tested) |
| `check-example` | `expected-hashes.json` | WIRED (default path and `--expected`) |
| README | guide and example README | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted tests | `pytest tests/test_reproduction_guide.py tests/test_public_example.py tests/test_example_check.py tests/test_example_command.py` | 59 passed | PASS |
| Real-model fresh checkout run | `EUREKA_EXAMPLE_REAL_RUN=1 pytest tests/test_public_example_fresh.py` | 5 passed, 17.5 s | PASS |
| Match | `check-example` on reference run | exit 0 | PASS |
| Tamper | `check-example` on a 1-byte-flipped copy under the scratchpad | exit 1 | PASS |

Probe Execution: no probes declared. SKIPPED.

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| EXM-01 (public dataset runs end to end with `eureka run`, ships expected hashes) | SATISFIED | Truths 1 and 2 |
| EXM-02 (plain-English guide, states reproducible and not) | SATISFIED, pending human read-through | Truths 3 and 4 |

No orphaned requirements. Note: the REQUIREMENTS.md checkboxes and traceability rows for EXM-01 and EXM-02 still read Pending, and the ROADMAP Phase 4 plan list is unchecked. The orchestrator owns those edits.

### Anti-Patterns

No TBD, FIXME or XXX in the guide, the example README or `src/mindrian_eureka/example/` (the guide grep returned nothing relevant). No stubs found. The PENDING_TEXT branch was removed in 04-04.

### Human Verification Required

1. **Second-machine run by a non-author.** Test: follow the guide from `uv sync --extra modern-encoder` to `check-example`. Expected: no help needed; MATCH on linux-aarch64, INFO lines elsewhere. Why human: clarity for a stranger, and hash equality on another platform is UNVERIFIED (the guide says so).
2. **Release sign-off.** Test: the owner sets the decision in `docs/rs-release-gate.md`. Expected: until then the example and guide stay internal only. Why human: owner decision. Open gaps G1, G2, G3, G5.

### Gaps Summary

No gaps. All four roadmap criteria hold in the repo. Two human items remain. Known limits, all stated in the guide: JHTV collection private, unusual-pairs engine not bit-for-bit verified, replay outcome is a provenance gap, hash equality checked on one platform only.

---

_Verified: 2026-11-07_
_Verifier: Claude (gsd-verifier)_
