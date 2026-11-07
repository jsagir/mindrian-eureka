---
phase: 04-public-example-and-reproduction-guide
plan: 01
subsystem: testing
tags: [sha256, reproduction, cli, argparse, expected-hashes]

requires:
  - phase: 02.1
    provides: run folder shape, manifest, canonical_json, public fixture hub_public
provides:
  - "mindrian_eureka.example package: contracts, check_run, load_expected, build_expected"
  - "eureka check-example command (exit 0 match, 1 no match, 2 usage)"
  - "scripts/make-example-hashes maker wrapper"
affects: [04-02, 04-03, 04-04]

tech-stack:
  added: []
  patterns:
    - "Exact sha256 equality over the 4 output files; environment differences are INFO only"
    - "Maker refuses unclean runs (changed file, dropped records, cap hit, wrong record count)"

key-files:
  created:
    - src/mindrian_eureka/example/__init__.py
    - src/mindrian_eureka/example/contracts.py
    - src/mindrian_eureka/example/check.py
    - src/mindrian_eureka/example/build.py
    - src/mindrian_eureka/example/command.py
    - scripts/make-example-hashes
    - tests/test_example_check.py
    - tests/test_example_command.py
  modified:
    - src/mindrian_eureka/cli.py

key-decisions:
  - "The expected hashes cover the 4 output files only; manifest.json is compared field by field because it holds platform text."
  - "A mismatch with equal input, settings, model and engine is reported as not reproduced on this machine, never excused."
  - "outputs in the expected file must list exactly the 4 output files, so a crafted file cannot weaken the check."

patterns-established:
  - "Command module with register_x and x_command, lazy import of the heavy part, REPO_ROOT module variable for tests"

requirements-completed: []

duration: 40min
completed: 2026-11-07
---

# Phase 4 Plan 01: Example hash check and maker Summary

**`eureka check-example` compares a finished run with shipped expected sha256 hashes (7 PASS or FAIL checks, exact rule), and `scripts/make-example-hashes` builds the expected file only from a clean real run, with no model and no network.**

## Performance

- **Duration:** about 40 min
- **Tasks:** 2 of 2
- **Files modified:** 9 (8 created, 1 edited)

## Accomplishments

- Checks X1 to X7 (run folder, inputs, settings, model, engine, outputs, label). X6 hashes the bytes on disk and compares them with the expected hash and with the hash that manifest.json lists, so an edit after the run is caught.
- INFO lines show platform, Python and library differences and never change the result.
- Maker refuses a changed file, dropped records, a cap hit and a wrong record count. It refuses to write inside the run folder.
- `load_expected` refuses path traversal, absolute paths, backslashes, bad sha256 values, a wrong schema, missing keys and files above `MAX_JSON_BYTES`. A symbolic link that leaves the run folder is refused.
- `cli.py` change: 4 added lines, 0 removed (import, register call, dispatch).

## Task Commits

1. **Task 1: Contracts, checker and maker, with tests** - `95fe6da` (feat)
2. **Task 2: check-example command, CLI wiring and maker script** - `24024eb` (feat)

RED evidence: before the package existed, `pytest tests/test_example_check.py` stopped at collection with `ImportError: cannot import name 'check' from 'mindrian_eureka.example'`. `tests/test_example_command.py` stopped at collection the same way before `command.py` existed. The RED state was not committed separately; each task is one commit as the plan asks.

## Verification

- `tests/test_example_check.py` 19 passed. With the command tests and `test_run_cli`, `test_hub_cli`, `test_seed_command`, `test_readme_commands`: 98 passed.
- ruff on the new package and test files: All checks passed. `mypy --strict src/mindrian_eureka/example`: no issues in 5 source files.
- Repo baselines unchanged: `ruff check src tests` 1465 errors, `mypy src` 88 errors in 17 files.
- `grep` for numpy, torch, sklearn, socket, urllib, requests in the new package: nothing. A subprocess test shows the heavy libraries absent from `sys.modules` after importing the command and the checker.
- End to end on the public fixture run: `./scripts/make-example-hashes <run> --out <file>` then `uv run --offline eureka check-example tests/fixtures/hub_public/run --expected <file>` gave 7 PASS, `Result: MATCH`, exit 0.
- `git status --short tests/fixtures` prints nothing.

## Deviations from Plan

None - plan executed as written. Small choices:
- The maker prints the `--out` path as the user gave it plus the sha256, so it prints no resolved absolute path.
- The maker script runs from the repo root (as `build-partner-bundle` does), so a caller must give absolute paths. A comment in the script says so.
- The command module has a `REPO_ROOT` variable so tests can point the default lookup at a temporary folder.

## Known Stubs

None. `examples/public-example/expected-hashes.json` does not exist yet; plan 04-02 ships it. Until then `eureka check-example` without `--expected` exits 2 with the fix `Give --expected FILE`.

## Threat Flags

None. Mitigations T-04-01 to T-04-05 are covered by tests (X6 against disk and manifest, path and link refusal, size limit, INFO never changes the result, maker refusals).

## Self-Check: PASSED

- Files exist: all 8 created files and `src/mindrian_eureka/cli.py`.
- Commits exist: `95fe6da`, `24024eb`.
