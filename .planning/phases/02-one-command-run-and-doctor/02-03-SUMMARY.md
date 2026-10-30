---
phase: 02-one-command-run-and-doctor
plan: 03
subsystem: engine-facade
tags: [engines, offline, determinism, facade, mypy-strict, parity]

requires:
  - phase: 02-one-command-run-and-doctor
    provides: "limits.py, run/contracts.py (Record, RunError, UsageError), test scaffold (plan 02-01)"
provides:
  - "run/engines.py: one typed module that calls both ranking engines"
  - "Recorded wording-and-meaning settings with params hash 7affae3c94c6bed9"
  - "manifest_engine_sections (engines, settings, seeds, engine_notes)"
  - "stub_encoders fixture in tests/conftest.py"
affects: [02-04, 02-05, 02-06]

tech-stack:
  added: []
  patterns:
    - "Heavy libraries load inside functions; module import stays light so thread limits come first"
    - "Calls into the untyped reference script go through a module held as Any, no type: ignore"
    - "Engine stderr is captured, the engine code is rewritten to plain words, lines go to a progress callback"

key-files:
  created:
    - src/mindrian_eureka/run/engines.py
    - tests/test_run_engines.py
  modified:
    - tests/conftest.py

key-decisions:
  - "The wording-and-meaning engine is called through its four building blocks in the order of hsi_reference.main, never through main or run_hsi."
  - "The unusual-pairs engine loads its own model inside the runner; load_local_encode serves the wording-and-meaning leg."
  - "The runner constant CAPABILITY_VERSION is read from mindrian_eureka.opportunity_pairs (the runner re-exports it) so mypy --strict stays clean."

patterns-established:
  - "Facade functions never print; progress goes to a callback."
  - "Offline variables are assigned (not defaulted) before any engine import."

requirements-completed: [RUN-01, RUN-03, RUN-04]

duration: 40min
completed: 2026-10-24
---

# Phase 2 Plan 03: Engine facade Summary

**One typed module, run/engines.py, calls the unusual-pairs engine through the library runner and the wording-and-meaning engine through the building blocks of the recorded rebuild, offline, with params hash 7affae3c94c6bed9 and a parity guard against hsi_reference.main.**

## Performance

- **Duration:** about 40 min
- **Completed:** 2026-10-24
- **Tasks:** 2 of 2
- **Files modified:** 3 (2 created, 1 modified)
- **Full test suite:** 379 passed, 25 skipped (before this plan: 234 passed, 25 skipped, plus plan 02-02 tests)

## Accomplishments

- `run_unusual_pairs` builds the document in record order, calls `runner.validate_document(max_artifacts=...)` first, then `runner.run_document` with sentence-transformers, hybrid_2026, lex_weight 0.5, min_percentile 0.90, `allow_model_download=False`. A ValueError becomes RunError with the same message.
- `run_wording_and_meaning` calls LSA (seed 42), BM25, the mean of both, the tier 1 meaning signal (200-word chunks), then the ranking (percentile, min_percentile 0.0, confirm 0.75, fixed `computed_at`). It never calls `make_sentence_transformer_encoder`.
- `wording_params_hash(200)` equals 7affae3c94c6bed9 (PROVEN). Hashes for top_k 20 and 100 start with 5b4b370a and 0b2948b9 (PROVEN; 500 gives 85c198f5, also PROVEN).
- Parity guard: on a scratch room of 20 synthetic files with the hashing stub, the facade returns the same 190 ordered pairs and the same ids, rank, hsi_score, lsa_sim, semantic_sim, lexical_sim and bm25_sim as `hsi_reference.main`.
- Import of `engines` loads no numpy, scikit-learn, torch or sentence_transformers (PROVEN by a subprocess test).
- The import-time warning of hsi_reference is captured once and returned as an engine note: "Wording-and-meaning engine: warning: lib/core/rs_corpus_exclude.py not importable, using the built-in fallback exclude-list". Nothing reaches stderr (PROVEN).
- `manifest_engine_sections` returns "engines", "settings", "seeds", "engine_notes". It records the tie-break rule, the reference file sha256 and the params hash.

## Task Commits

1. **Task 1: environment helpers, local encoder, unusual-pairs call, stub_encoders fixture** - `e30b117` (feat)
2. **Task 2: wording-and-meaning tests, params hash, manifest sections, parity guard** - `8b1c461` (test)

## Files Created/Modified

- `src/mindrian_eureka/run/engines.py` - the facade (settings and outcome dataclasses, offline and thread helpers, both engine calls, manifest sections)
- `tests/test_run_engines.py` - 27 tests: call shape, error mapping, stub end-to-end, params hash, call order, parity, stderr capture, manifest
- `tests/conftest.py` - added `stub_encoders` (patches `engines.load_local_encode` to `hashing_encode`; `hashing_encoder` patches the runner class)

## Decisions Made

- The code for the wording-and-meaning call was written in the Task 1 commit together with the rest of the module, because it shares private helpers. Task 2 added the tests that prove it. No separate RED commits (the sequential-executor rules use `git commit --only`, which needs tracked files).
- Settings constants were checked against the code: svd_topics_requested 80, tfidf_max_features 2000 and svd_random_state 256 in algorithm.py; method_version in runner.py; chunk_words 200 and max_chunks 12 in hsi_reference.py. All match the plan.
- `run_unusual_pairs` also maps OSError and RuntimeError from the runner (model load and cache errors) to RunError with the doctor fix text. The plan named only ValueError.
- `run_wording_and_meaning` rejects top_k outside 0 to `limits.MAX_TOP_K` with UsageError.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan assumption] fake_model_dir loads without error**
- **Found during:** Task 1, test for load_local_encode
- **Issue:** The plan expects `load_local_encode(fake_model_dir)` to raise RunError. The stub folder (empty `modules.json`) loads as an empty SentenceTransformer, so no error occurs.
- **Fix:** The RunError test uses a missing folder (raises RunError with the doctor fix). A second test loads the stub folder and asserts only that no socket opens (`no_network` list stays empty).
- **Files modified:** tests/test_run_engines.py
- **Commit:** e30b117

**2. [Rule 3 - Blocking] mypy --strict errors on the first draft**
- **Found during:** Task 1 verify
- **Issue:** untyped `set_verbosity_error`, `runner.CAPABILITY_VERSION` not exported for mypy, `Path(module.__file__)` is `str | None`.
- **Fix:** load the transformers logging module as `Any`; import `CAPABILITY_VERSION` from `mindrian_eureka.opportunity_pairs` (same value, the runner imports it from there); annotate the imported reference module as `Any`.
- **Files modified:** src/mindrian_eureka/run/engines.py
- **Commit:** e30b117

**Total deviations:** 2. No scope change.

## Known Stubs

None.

## Threat Flags

None. All mitigations of the plan threat register are in place: local_files_only and offline variables assigned (T-02-21), HSI_NO_AUTO_INSTALL set before the first reference import (T-02-22), params hash, parity test and reference sha256 (T-02-23), captured stderr rewritten to plain words (T-02-24).

## Issues Encountered

None beyond the deviations above. PROVEN: no `.hsi-cache.json` or `.hsi-results.json` appears in `git status`; the parity room lives under pytest `tmp_path`.

## Next Phase Readiness

Plan 02-06 can call `engines.prepare_offline_environment`, `apply_thread_limits`, `engines.load_local_encode` (as a module attribute, so `stub_encoders` works), `run_unusual_pairs`, `run_wording_and_meaning` and `manifest_engine_sections`. UNVERIFIED: a run with the real model (no model files in this environment for tests; the real-model path is only exercised by the guarded failure tests).

## Self-Check: PASSED

- FOUND: src/mindrian_eureka/run/engines.py
- FOUND: tests/test_run_engines.py
- FOUND: commit e30b117
- FOUND: commit 8b1c461
