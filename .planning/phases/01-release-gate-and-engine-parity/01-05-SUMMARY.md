---
phase: 01-release-gate-and-engine-parity
plan: 05
subsystem: engine-parity
status: complete
tags: [ENG-02, canonical-path, parity-record, drift-test]
requires: ["01-02", "01-03"]
provides:
  - docs/rs-engine-parity.md
  - tests/test_rs_engine_parity_record.py
affects: [01-06, phase-02-eureka-run]
key-files:
  created:
    - docs/rs-engine-parity.md
    - tests/test_rs_engine_parity_record.py
  modified: []
decisions:
  - "Path C (eureka-pair-scout, hybrid_2026) is the canonical path for new runs of the unusual-pairs engine (owner, 2026-10-23)."
  - "The JHTV unusual-pairs file is a result of path B (sha256 044b9ae6...), a different method version for the dense signal."
metrics:
  tasks: 2
  completed: 2026-10-23
requirements: [ENG-02]
---

# Phase 1 Plan 05: Canonical path record for the unusual-pairs engine

One record names the canonical path, gives the parity result as evidence, and explains how the JHTV file relates. A test guards the record.

## Result

- `docs/rs-engine-parity.md` has the 7 front matter keys (`status: decided`, `decided_on: 2026-10-23`) and 9 sections in the planned order.
- Section 3 holds 16 metric rows. Each value is the `.4g` form of a value in `tests/fixtures/rs_parity/baseline_report_pre_fix.json`. The baseline has a non-null layer 4, so the 6 layer 4 rows are included. The text says these are pre-fix numbers and that plan 01-06 adds the after-fix numbers.
- Section 4 holds the 40-file JHTV smoke figures (overlap 0.423) with the label "scratch scripts; real text, so not committed; full-corpus overlap UNVERIFIED". Aggregate numbers only.
- Section 6 quotes the two Outcome lines of `docs/hsi-rs-jhtv-reproduction.md` exactly and states the new facts from plan 01-02:
  - PROVEN: the default cap `RS_MAX_ARTIFACTS` of 2000 gives 186 of 200 overlap and a missing stored rank 1. With `RS_MAX_ARTIFACTS=3000` the file is reproduced exactly.
  - INFERRED: the original run set a cap of 2117 or more.
  - PROVEN: the wording-and-meaning pairs engine command reproduces exactly (5 minutes 10 seconds).
- Section 7 lists the open items. The tie-break row says "Pending, scheduled in plan 01-04. Plan 01-06 sets the final status." The `top_k` row says Phase 2 must lift the cap of 100 to 200, so the one-command run can match the 200-pair JHTV file.
- `tests/test_rs_engine_parity_record.py` has 9 tests and passes. One test tampers a copy of section 3 and checks that the drift check reports it.

## Deviations from Plan

**1. [Rule 2 - Missing detail] Artifact cap row added to the known-differences table.**
- Issue: the new fact about `RS_MAX_ARTIFACTS` belongs to the differences. Path C rejects more than 2500 artifacts in `validate_document` (read in `runner.py`), so the 2117 JHTV files fit.
- Fix: one extra row (row 16) in section 5.
- Commit: c2075e7.

**2. [Naming rule] Section headings use catalog-style wording.**
- Issue: the plan headings say "RS paths". The owner rule bars bare "RS" in prose. Headings are "The three code paths" and "Open fix list for path C". Literal ids, file names and code symbols (`canonical_rs_path`, `rs-engine.py`, `RS_MAX_ARTIFACTS`) are kept.
- The test uses the same headings.

**3. [Detail] Test matches the metric key inside backticks** and checks the value column of the table row, not any part of the line. This is stricter than the plan.

No other deviation.

## Auth gates

None.

## Known Stubs

None.

## Threat Flags

None. No catalog text is in the record (T-01-20). The numbers are checked by a test (T-01-21). The author surname is absent from the record and the test (T-01-22). No file of plan 01-04 was touched and the parity test was not run (T-01-23).

## Limits

- Path C HEAD in the record is `ee5f370`, the commit at writing time. Plan 01-04 commits came later.
- The full-corpus overlap of path C with the JHTV file is UNVERIFIED.
- The record does not yet hold the after-fix numbers. Plan 01-06 adds them in a "### 3.1" subsection. The drift test reads only the text before that subsection.

## Commits

- c2075e7: docs(01-05): record the canonical path for the unusual-pairs engine with the parity result
- c1621d2: test(01-05): check structure and number drift of the canonical-path record

## Self-Check: PASSED

- docs/rs-engine-parity.md and tests/test_rs_engine_parity_record.py exist.
- Commits c2075e7 and c1621d2 exist.
- `PYTHONPATH=src pytest tests/test_rs_engine_parity_record.py -q -p no:cacheprovider`: 9 passed.
- The record has no em-dash and no original-author surname. The test file has no `/home` or `/mnt` path.
