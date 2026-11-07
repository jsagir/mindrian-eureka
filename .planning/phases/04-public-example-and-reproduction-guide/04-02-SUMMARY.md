---
phase: 04-public-example-and-reproduction-guide
plan: 02
subsystem: testing
tags: [sha256, reproduction, public-example, arxiv, cc0, fresh-checkout]

requires:
  - phase: 04-01
    provides: eureka check-example, scripts/make-example-hashes, expected-hash contract
  - phase: 02.1
    provides: public fixture tests/fixtures/hub_public (36 arXiv files, CC0)
provides:
  - "examples/public-example: README, expected-hashes.json, reference-run (5 files)"
  - "Default-suite tests: hash file, license, reference run, drift guard, privacy, README wording"
  - "Fresh-checkout tests with an opt-in real-model run"
affects: [04-03, 04-04]

tech-stack:
  added: []
  patterns:
    - "Reference run = a new real-model run of the current engine, never the older frozen hub run"
    - "Fresh-checkout test: copy tracked and new files into an empty folder, PYTHONPATH holds only the copy"

key-files:
  created:
    - examples/public-example/README.md
    - examples/public-example/expected-hashes.json
    - examples/public-example/reference-run/corpus/records.jsonl
    - examples/public-example/reference-run/ranked-pairs.md
    - examples/public-example/reference-run/unusual-pairs.json
    - examples/public-example/reference-run/wording-and-meaning-pairs.json
    - examples/public-example/reference-run/manifest.json
    - tests/test_public_example.py
    - tests/test_public_example_fresh.py
  modified:
    - src/mindrian_eureka/example/contracts.py
    - src/mindrian_eureka/example/build.py

key-decisions:
  - "The reference run uses all-MiniLM-L6-v2; the JHTV replay used mdbr-leaf-ir. The expected file records this in example.model_note."
  - "Status is Internal only, tied to the no-go decision in docs/rs-release-gate.md."
  - "Input is reused in place from tests/fixtures/hub_public/input (CC0); nothing under tests/fixtures changed."

patterns-established:
  - "Drift guard: test_engine_identity_is_current compares params hash and engine file hashes with the current code and prints the rebuild steps"

requirements-completed: []

duration: 12min
completed: 2026-11-07
---

# Phase 4 Plan 02: Public example Summary

**A real-model reference run of 36 CC0 arXiv abstracts, with an expected-hash file, an internal-only README and tests that include a fresh-checkout run.**

## Performance

- Duration: about 12 min of work (the plan measured run times of 10 to 22 s each)
- Tasks: 3 of 3
- Files: 9 created, 2 edited

## Measured results (PROVEN, 2026-11-07, linux-aarch64, 12 cores, no GPU)

Records: 36 used, 0 dropped, no cap hit. Unusual-pairs engine 63 pairs. Wording-and-meaning engine 200 pairs. Model all-MiniLM-L6-v2.

| Setup | Python | numpy / torch / sentence-transformers | Threads | Cache | Wall | Same files as A1 |
|---|---|---|---|---|---|---|
| A1 | 3.12.12 | 2.5.4 / 2.14.1+cpu / 5.7.0 | 1 | empty | 22 s | reference |
| A2 | 3.12.12 | 2.5.4 / 2.14.1+cpu / 5.7.0 | 1 | default | 11 s | yes, `diff -r` empty |
| B | 3.12.12 | 2.5.4 / 2.14.1+cpu / 5.7.0 | 12 | default | 10 s | yes |
| C | 3.12.3 (system) | 2.2.6 / 2.11.0 / 5.3.0 | 1 | default | 15 s | yes |

`check-example` gave MATCH and exit 0 on the reference run, A2, B and C. C printed INFO lines for 11 version differences. `eureka hub` on the reference run exited 0. Peak memory 0.82 GB comes from the feasibility check, not from these runs.

The 4 output files are byte-equal across A1, A2, B and C. `manifest.json` differs for C (environment text) and for B (thread count), so it is outside the hash rule, as plan 04-01 decided.

## Task Commits

1. Task 1: reference run and expected hashes - `d46ec16`
2. Task 2: README and default-suite tests - `3f45472`
3. Task 3: fresh-checkout tests - `a53d270`

## Verification

- `pytest tests/test_public_example.py tests/test_public_example_fresh.py`: 16 passed, 1 skipped (opt-in test, reason shown).
- Opt-in real run with `EUREKA_EXAMPLE_REAL_RUN=1`, under `nice -n 19`, from a copy of the tracked files: 1 passed in 7.7 s (11 s wall with start-up). Outputs are byte-equal to the reference run; one flipped byte gives exit 1. The same test also passed under `uv run --offline --with pytest` (17 passed, 8 s).
- With `test_example_check`, `test_example_command`, `test_hub_public_fixture`, `test_hub_public_example`, `test_release_gate_record`: 107 passed, 1 skipped.
- ruff on the new test files: All checks passed. Baselines unchanged: `ruff check src tests` 1465 errors, `mypy src` 88 errors in 17 files.
- `git status --short tests/fixtures` prints nothing. `grep shell=True` in the fresh test prints nothing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Model note in the expected file**
- Found during: Task 1
- Issue: the lead instruction and the plan note require the expected-hash file to record that the example uses all-MiniLM-L6-v2 and the JHTV replay used mdbr-leaf-ir. The maker had no key for it.
- Fix: added `EXAMPLE_MODEL_NOTE` to `src/mindrian_eureka/example/contracts.py` and an `example.model_note` key in `build_expected`. The file was rebuilt from the same run folder. Plan 04-01 tests still pass (31 passed).
- Files: `src/mindrian_eureka/example/contracts.py`, `src/mindrian_eureka/example/build.py`
- Commit: `d46ec16`

**2. [Rule 1 - Bug in plan wording] Privacy scan "last word" of decided_by**
- Issue: `decided_by` is `Jonathan Sagir (owner)`. Its last word is `(owner)`, which the README must be allowed to use.
- Fix: the test strips the parenthesis, then checks the full value, the full name and the surname.
- File: `tests/test_public_example.py`

**3. Wording of time claims**
- The plan said runs take minutes in places. README says about 15 seconds and 0.82 GB, from the measured values.

## Known Stubs

None.

## Threat Flags

None. T-04-08 to T-04-14 are covered by tests (license pin, privacy scan, status text, drift guard, argument-list subprocesses, import-path test).

## UNVERIFIED

- `uv sync` on a clean machine with network. The fresh-checkout tests use the interpreter and libraries that already exist.
- Any platform other than linux-aarch64. Only 4 setups on one machine were run.
- Peak memory was not re-measured here.

## Self-Check: PASSED

- Files exist: README.md, expected-hashes.json, 5 reference-run files, both test files.
- Commits exist: `d46ec16`, `3f45472`, `a53d270`.
