---
phase: 02-one-command-run-and-doctor
plan: 01
subsystem: engine-limits-and-test-scaffold
tags: [limits, caps, contracts, pytest, hashing-encoder]

requires:
  - phase: 01-release-gate-and-engine-parity
    provides: parity test and parity record that pinned the old caps
provides:
  - limits.py with seven shared run limits (top_k 200, 3,000 artifacts, hard max 5,000)
  - run/contracts.py (exit codes, error classes, label, score meaning, Record, normalizer)
  - test scaffold (HashingEncoder and five fixtures) for plans 02-02 to 02-06
affects: [02-02, 02-03, 02-04, 02-05, 02-06]

tech-stack:
  added: []
  patterns:
    - "Run limits live in one module (limits.py)"
    - "New modules: stdlib-only contracts, mypy --strict clean, ruff clean"
    - "Tests use a hashing encoder and non-autouse fixtures"

key-files:
  created:
    - src/mindrian_eureka/limits.py
    - src/mindrian_eureka/run/__init__.py
    - src/mindrian_eureka/run/contracts.py
    - tests/test_run_limits.py
    - tests/test_run_contracts.py
    - tests/hashing_stub.py
    - tests/conftest.py
    - tests/test_run_scaffold.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/runner.py
    - src/mindrian_eureka/hsi_engine.py
    - tests/test_rs_engine_parity.py
    - docs/rs-engine-parity.md

key-decisions:
  - "validate_document gets a keyword max_artifacts bounded by HARD_MAX_ARTIFACTS; one-argument callers are unchanged."
  - "MCP schemas and pydantic models keep 2,500 artifacts and 100 pairs (Phase 3 item)."
  - "Mapping file shape used by the fixture: schema_version plus a files object keyed by path or '*' (matches plan 02-02)."

patterns-established:
  - "Caps are imported from mindrian_eureka.limits, never written as literals."
  - "Fixtures are opt-in; no conftest fixture runs by default."

requirements-completed: []

duration: 25min
completed: 2026-10-24
---

# Phase 2 Plan 01: Caps lift, shared contracts and test scaffold Summary

**top_k cap 100 to 200 and artifact cap 2,500 to 3,000 in both engine entry points via one limits module, plus stdlib-only run contracts and a model-free pytest scaffold for the rest of Phase 2.**

## Performance

- **Tasks:** 3 of 3
- **Files modified:** 12 (8 created, 4 modified)
- **Full test suite:** 234 passed, 25 skipped (baseline 192 passed, 25 skipped)

## Accomplishments

- The unusual-pairs runner accepts top_k 0 to 200 and rejects 201 with "top_k must be between 0 and 200". The wording-and-meaning adapter uses the same two limits.
- validate_document accepts 3,000 artifacts by default and up to 5,000 with max_artifacts. Larger values and max_artifacts outside 2 to 5,000 raise ValueError.
- test_clip_and_cap_decisions_are_documented pins 200 accepted, 201 rejected, and the no-clip note. The parity record states the lifted caps and still passes its record test.
- run/contracts.py holds exit codes, error classes with fix text, LABEL, SUMMARY_LINE, engine names, score-meaning texts, schema ids, Record, normalize_text and sha256 helpers. Importing it loads no numpy, scikit-learn or torch (PROVEN by a subprocess test).
- Test scaffold: HashingEncoder (64 dimensions, deterministic across processes), and fixtures isolated_env, fake_model_dir, hashing_encoder, no_network, tmp_inputs (CSV and Markdown, 32 synthetic records).

## Task Commits

1. **Task 1: limits.py, caps lifted, pinning test and parity record** - `03ac655` (feat)
2. **Task 2: shared run contracts** - `b7d9753` (feat)
3. **Task 3: test scaffold** - `9fd6bf1` (test)

No separate RED commits: `git commit --only` needs tracked files, and the sequential-executor rules forbid other staging. The RED state was confirmed locally for Task 1 (collection error before limits.py existed).

## Files Created/Modified

- `src/mindrian_eureka/limits.py` - seven shared limits
- `src/mindrian_eureka/opportunity_pairs/runner.py` - import limits; top_k check; max_artifacts keyword
- `src/mindrian_eureka/hsi_engine.py` - same caps
- `src/mindrian_eureka/run/contracts.py`, `run/__init__.py` - shared contracts
- `tests/test_run_limits.py`, `tests/test_run_contracts.py`, `tests/test_run_scaffold.py` - tests
- `tests/hashing_stub.py`, `tests/conftest.py` - scaffold
- `tests/test_rs_engine_parity.py`, `docs/rs-engine-parity.md` - cap pin and record

## Decisions Made

See key-decisions in the frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Subprocess import test ignored PYTHONPATH**
- **Found during:** Task 2
- **Issue:** The plan asks for `python -I -c` with PYTHONPATH=src. The -I flag ignores PYTHON* variables, so the import would fail.
- **Fix:** The test code inserts the source folder into sys.path itself, then imports and checks sys.modules.
- **Files modified:** tests/test_run_contracts.py
- **Commit:** `b7d9753`

**2. [Rule 3 - Blocking] Mapping file shape**
- **Found during:** Task 3
- **Issue:** The plan text says a "*" entry. Plan 02-02 defines the schema as `schema_version` plus `files` keyed by path or "*".
- **Fix:** The tmp_inputs mapping file uses `files: {"*": {...}}` so it validates against the plan 02-02 schema.
- **Files modified:** tests/conftest.py
- **Commit:** `9fd6bf1`

**3. [Rule 3 - Blocking] ruff import order and long lines**
- **Issue:** ruff with the stated selection sorts `mindrian_eureka` imports with third-party imports in tests, and flagged lines over 100 characters.
- **Fix:** Applied the ruff order and shortened lines. No behavior change.

**4. Word "autouse" in conftest docstring**
- The acceptance check `grep -c autouse` counts docstring text. The docstring was reworded.

Total deviations: 4, none changes scope.

## Known Stubs

None. HashingEncoder is a test double by design.

## Issues Encountered

None open.

## Next Phase Readiness

- Plans 02-02 to 02-05 can run in parallel; they import from `mindrian_eureka.limits` and `mindrian_eureka.run.contracts` and use the new fixtures.
- Plan 02-03 adds the `stub_encoders` fixture to tests/conftest.py.
- RUN-01 is not marked complete: this plan only lifts the caps. The command ships in plan 02-06.

## Self-Check: PASSED

- Files exist: limits.py, run/contracts.py, run/__init__.py, tests/conftest.py, tests/hashing_stub.py, tests/test_run_limits.py, tests/test_run_contracts.py, tests/test_run_scaffold.py.
- Commits found: 03ac655, b7d9753, 9fd6bf1.
- `git diff --stat -- uv.lock pyproject.toml` is empty. No story/ file staged or committed.
