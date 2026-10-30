---
phase: 02-one-command-run-and-doctor
plan: 04
subsystem: run-output
tags: [projection, canonical-json, staging, manifest, console, mypy-strict, determinism]

requires:
  - phase: 02-one-command-run-and-doctor
    provides: "run/contracts.py (LABEL, SUMMARY_LINE, schema ids, SCORE_MEANING, Record, UsageError), tests/conftest.py fixtures (plan 02-01)"
provides:
  - "run/project.py: fixed-field projection of both engine results, number-based readings, describe_caps, describe_drops, filter_engine_warnings"
  - "run/output.py: canonical_json, corpus_lines, render_ranked_markdown, StagedRun, FileDigest, is_eureka_run_folder, ensure_out_dir_allowed, OUTPUT_* names"
  - "run/manifest.py: sha256_file, model_fingerprint, collect_environment, tool_version, build_manifest, build_run_info"
  - "run/console.py: Console and use_color"
affects: [02-05, 02-06]

tech-stack:
  added: []
  patterns:
    - "Projection copies a fixed field list, so no time, path or excerpt reaches a hashed file"
    - "The reading of a pair comes from the numbers, never from the engine direction label"
    - "One canonical JSON writer; rounding happens once, in the writer"
    - "Files go to a staging folder next to --out; one os.replace publishes them"
    - "Console strips control characters from messages that carry file data"

key-files:
  created:
    - src/mindrian_eureka/run/project.py
    - src/mindrian_eureka/run/output.py
    - src/mindrian_eureka/run/manifest.py
    - src/mindrian_eureka/run/console.py
    - tests/test_run_project.py
    - tests/test_run_output.py
    - tests/test_run_manifest.py
    - tests/test_run_console.py
  modified: []

key-decisions:
  - "Readings use the sign of signed_difference (unusual-pairs engine) or the order of wording and meaning (wording-and-meaning engine). Tests flip the engine label and prove the reading stays."
  - "round_floats is public in output.py (the plan artifact list names it; the action text said private)."
  - "describe_drops writes one sentence for each drop reason, not one sentence for all drops. A run with two reasons gets two sentences."
  - "Optional wording-and-meaning scores (lexical, bm25, percentile, z, second_signal) appear only when the engine result has them."
  - "Console removes control characters (including ESC) from messages, because messages can carry data from input files."

patterns-established:
  - "StagedRun creates the staging folder in __init__ and removes it in __exit__ unless publish() moved it."
  - "publish() moves an old Eureka run aside, renames staging into place, then removes the old folder; on a rename failure the old folder returns."

requirements-completed: [RUN-03, RUN-04, RUN-05]

duration: 35min
completed: 2026-10-24
---

# Phase 2 Plan 04: Output layer Summary

**Fixed-field projection with number-based readings, one canonical JSON writer, a staged output folder published by one rename, a timestamp-free manifest with a separate run-info file, and a stderr/stdout console helper.**

## Performance

- **Duration:** about 35 min
- **Completed:** 2026-10-24
- **Tasks:** 3 of 3
- **Files created:** 8 (4 source modules, 4 test files)
- **New tests:** 120 (32 project, 46 output, 42 manifest and console)
- **Full test suite:** 499 passed, 25 skipped (PROVEN, run after task 3)

## Accomplishments

- `project_unusual_pairs` and `project_wording_and_meaning` copy only named fields. A recursive test on a full stub result finds none of the keys started_at, finished_at, duration_ms, generated_at, retrieved_at, model_provider, room_dir, excerpt, source_trail, extracted_sentence, review_context, breakthrough_potential. It also finds no excerpt text, no model path and no timestamp.
- Both engines use the label structural_transfer with opposite meaning. The reading is derived from the numbers. Parametrized tests flip the label and the reading stays. Two polarity tests confirm the documented meaning for each engine.
- `pair_id` is "pair-" plus 20 hex of sha256 over the two sorted ids joined by NUL. It is equal for both engines and for either id order.
- `canonical_json` gives sorted keys, indent 2, UTF-8 without BOM, LF, floats rounded to 6 decimals, minus zero mapped to zero. NaN and infinity raise ValueError at any depth.
- `StagedRun` stages next to `--out` (mode 0o700, files 0o600 on POSIX). It publishes by `os.replace`. It replaces only an Eureka run folder (manifest schema match) or an empty folder. After an exception no `.staging-` folder remains and `--out` does not exist (test).
- `ensure_out_dir_allowed` refuses: out equal to or inside input, input inside out, out is a file, out is a non-empty foreign folder, parent is a file.
- `build_manifest` holds no clock value. Tests check no absolute path (tmp path and home folder) and no timestamp pattern. Two builds give equal dicts and equal canonical bytes. A jsonschema check requires all manifest keys, engine fields and output item fields.
- `model_fingerprint` handles a Hugging Face cache layout with symlinked blobs (name "org/name", 40-hex snapshot) and a plain folder.
- `collect_environment` returns BLAS entries without file paths and survives a missing threadpoolctl.
- `manifest.py` import loads no numpy and no torch (subprocess check).
- `Console` writes progress, warnings and errors to stderr, results to stdout. Color shows only on the `warning:` and `eureka:` prefixes of a TTY stream when NO_COLOR is unset and TERM is not dumb. It never reads stdin.

## Task Commits

1. **Task 1: projection** - `1ec44e3` (feat)
2. **Task 2: canonical writer, corpus lines, Markdown, staged folder** - `8c9ec28` (feat)
3. **Task 3: manifest, run-info, console** - `6d564df` (feat)

## Verification

- `pytest tests/test_run_project.py tests/test_run_output.py tests/test_run_manifest.py tests/test_run_console.py`: 120 passed (PROVEN).
- `mypy --strict` on the four new source modules: no issues (PROVEN).
- `ruff check --select E,F,I,UP,B --line-length 100` on all new files: clean (PROVEN).
- No em-dash and no standalone short engine code in project.py, output.py, manifest.py, console.py (PROVEN by regex check). project.py has 0 numpy imports.
- Full suite: 499 passed, 25 skipped (PROVEN).

## Deviations from Plan

None - plan executed as written. Three small choices inside the plan scope:

- `round_floats` is public (see key-decisions).
- `describe_drops` groups by reason (see key-decisions).
- Console control-character stripping is an addition for the "terminal" trust boundary of the threat model (Rule 2). It changes no plan behavior for normal text.

## Threat Model Coverage

- T-02-31: fixed field list plus recursive forbidden-key test.
- T-02-32: replacement only of an Eureka run folder or an empty folder; overlap with the input refused.
- T-02-33: staging 0o700 and files 0o600 on POSIX. UNVERIFIED on Windows (chmod failure is ignored by design). Plan 02-06 sets umask 077.
- T-02-34: staging folder plus one rename; exception and block exit discard the staging folder.
- T-02-35: absolute paths, backslash paths, drive letters and ".." raise ValueError.
- T-02-36: tests check tmp path and home folder absent, BLAS file paths omitted.
- T-02-37: label-flip tests.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or schema surface.

## Issues Encountered

None.

## Next Phase Readiness

Plan 02-05 and plan 02-06 can import the names listed in `provides`. Plan 02-06 must:

- build `outputs` for `build_manifest` from `FileDigest.as_dict()` plus per-file extras (`pairs`, `top_k_reached`) before hashing;
- write `manifest.json` last, then hash it for `run-info.json`;
- set umask 077 and call `ensure_out_dir_allowed` before it creates a `StagedRun`;
- pass `filter_engine_warnings` over engine warnings before it puts them in `notes`.

## Self-Check: PASSED

- FOUND: src/mindrian_eureka/run/project.py, output.py, manifest.py, console.py
- FOUND: tests/test_run_project.py, test_run_output.py, test_run_manifest.py, test_run_console.py
- FOUND commits: 1ec44e3, 8c9ec28, 6d564df
