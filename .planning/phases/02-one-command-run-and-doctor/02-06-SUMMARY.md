---
phase: 02-one-command-run-and-doctor
plan: 06
subsystem: run-pipeline-and-cli
tags: [pipeline, cli, exit-codes, determinism, labels, manifest, doctor-wiring]

requires:
  - phase: 02-one-command-run-and-doctor
    provides: "contracts, limits, corpus, mapping, engines, project, output, manifest, console, models, doctor (plans 02-01 to 02-05)"
provides:
  - "run/pipeline.py: RunRequest, RunSummary, run_pipeline (plain function, ready for Phase 3)"
  - "run/command.py: register_commands, build_run_request, run_command, doctor_cli"
  - "cli.py: main(argv) -> int with --version, run and doctor; old subcommands unchanged"
  - "tests that prove RUN-04 (byte-identical repeat runs) and RUN-05 (labels in every file and the summary)"
affects: [phase-3]

tech-stack:
  added: []
  patterns:
    - "Pipeline calls engines.* and corpus.* through the module, so tests patch them"
    - "One broad except at the CLI boundary only; --debug re-raises"
    - "Stages: validate, out-folder check, model check, corpus, engines, project, write, manifest, run-info, publish"

key-files:
  created:
    - src/mindrian_eureka/run/pipeline.py
    - src/mindrian_eureka/run/command.py
    - tests/test_run_pipeline.py
    - tests/test_run_cli.py
    - tests/test_run_determinism.py
    - tests/test_run_labels.py
  modified:
    - src/mindrian_eureka/cli.py
    - src/mindrian_eureka/run/engines.py
    - tests/test_run_engines.py
    - .gitignore

key-decisions:
  - "Manifest settings hold a run block (max_artifacts, top_k, objective). Cache use is not recorded, so cold, warm and no-cache runs give equal manifests. Thread count is recorded in environment.threads_requested, so only the ranked files and the corpus file are compared across thread settings."
  - "Engine warnings are rewritten before they reach notes: the unusual-pairs engine warning that starts with the short engine code is changed to 'The hybrid percentile gate ...' and any standalone short code is removed."
  - "run_command takes an optional argv argument (default sys.argv[1:]) so run-info.json keeps the real command line."
  - "Input folder existence is checked by the corpus builder, as before. A missing model is reported first when both are wrong, because the plan fixes that order."
  - "RunSummary.files lists all six written files (four hashed outputs, manifest.json and run-info.json)."

patterns-established:
  - "Dry run reads and checks the input, loads no model, writes nothing"
  - "Exit codes: 0 ok, 1 EurekaError/unexpected, 2 UsageError or argparse, 130 KeyboardInterrupt"

requirements-completed: [RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, DOC-01, DOC-02]

duration: about 75 min
completed: 2026-10-24
---

# Phase 2 Plan 06: Pipeline, CLI wiring, determinism and label proof Summary

**`eureka run <folder>` now turns a folder of Markdown and CSV files into a hashed output folder (both ranked lists, Markdown report, clean corpus, manifest, run-info) with exit codes 0/1/2/130, and `eureka doctor` and `--version` are on the CLI. Tests prove byte-identical repeat runs and the label in every file.**

## Performance

- **Tasks:** 3 of 3
- **Files:** 6 created, 4 modified
- **Quick suite for the phase** (`tests/test_run_*.py tests/test_doctor.py tests/test_models.py`): 476 passed, 2 skipped, 21.5 s (PROVEN)
- **Full suite:** 668 passed, 27 skipped, 45 subtests passed, 43.9 s (PROVEN). The Phase 2 baseline was 192 passed, 25 skipped. The 2 extra skips are the gated real-model tests (they pass when the variable is set, see below).

## Accomplishments

- `run_pipeline(request, console)` does the stages in the planned order. A missing model stops the run before the corpus is read (exit 1, message starts "No local model found.", no output folder). A failure or Ctrl+C leaves no staging folder and keeps an earlier run intact.
- The command layer maps outcomes to exit codes. Progress, warnings and errors go to stderr. The summary goes to stdout and ends with the label sentence. `--json` prints one canonical JSON object. `--quiet` hides progress, not warnings. No traceback unless `--debug`.
- `cli.py` diff is 27 added and 5 removed lines. No line of the capabilities, capability or schema branches was removed. `main(argv=None) -> int`. `import mindrian_eureka.cli` and `--help` load none of numpy, sklearn, scipy, torch, sentence_transformers (PROVEN by two subprocess tests).
- RUN-04 tests: two runs, CSV runs, cold cache, warm cache, `--no-cache`, a moved input folder, CRLF copy, shuffled CSV rows, `--threads 1` all give equal ranked files. The first four also give equal manifest.json. run-info.json differs and holds the manifest hash. No timestamp, temp path, home path or model path appears in any file except run-info.json. All JSON files re-serialize to the same bytes with `canonical_json`.
- RUN-05 tests: every file under the output folder holds "candidate, not verified". Both ranked files have `label`, the matching `score_meaning`, a label and a non-empty reading on each pair. The readings follow the numbers. The Markdown report has both engine names, the summary line and both score-meaning texts. No short engine code in the report, stdout, stderr, any help text, the missing-model error, or any value of the JSON files. No "validated finding" or "proven" in the report.
- `.gitignore` has `eureka-run/` (1 line).

## Task Commits

1. **Task 1: pipeline** - `3056168` (feat)
2. **Task 2: command layer, cli.py wiring, .gitignore** - `eb01438` (feat)
3. **Task 3: determinism and label tests** - `6f6198e` (test)
4. **Deviation fix: quiet model libraries** - `0b32070` (fix)

No separate RED commits (same reason as plans 02-01 to 02-05: `git commit --only` needs staged files and the code and tests of one module were written together).

## Real-model run (replaces the manual human check)

Machine: this WSL2 host, Python 3.12.3. Model found in the Hugging Face cache (snapshot 1110a243...). Data: the 32 synthetic records of `tests/fixtures/rs_parity/corpus.json` written as Markdown in a scratch folder. No partner or room folder was used.

`eureka doctor` (exit 0):

```
Eureka doctor
[PASS] D1 Python: Python 3.12.3.
[PASS] D2 uv: uv 0.9.4 found on PATH.
[PASS] D3 Libraries: All encoder libraries can be imported.
[PASS] D4 Local model: Model folder .../models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243... (from Hugging Face cache).
[PASS] D5 Cache folder: /home/jsagi/.cache/mindrian-eureka does not exist yet; it will be created with mode 700.
[PASS] D6 Data folder: /home/jsagi/.local/share/mindrian-eureka has mode 700.
[WARN] D7 Offline variables: Not set to 1: HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE. `eureka run` sets them itself.
Result: 6 passed, 1 warnings, 0 failed.
```

`eureka run <folder> --no-cache` (exit 0, about 5 to 8 s wall time):

```
Eureka run finished.
Records: 32 used, 32 read, 0 dropped
Find Unusual Pairs Across a Research Collection: 50 pairs (unusual-pairs.json)
Rank Unusual Pairs by Wording and Meaning: 200 pairs (wording-and-meaning-pairs.json)
Report: ranked-pairs.md
Manifest: manifest.json (sha256 55d8c29522b20175015d79da62c4c9d48546747f3da7981f47d453b1373bee98)
Caps hit: none
All results are candidates, not verified. They are leads for human review.
```

Two manual real-model runs (before and after the noise fix) gave the same manifest sha256 (55d8c295...). The gated test `test_real_model_runs_are_equal_across_hash_seeds` (two subprocess runs, PYTHONHASHSEED 0 and 1) passed in 71 s: unusual-pairs.json, wording-and-meaning-pairs.json, ranked-pairs.md, records.jsonl and manifest.json are byte-equal (PROVEN on this machine).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Model-library noise and color codes on stderr**
- **Found during:** Task 3, real-model run
- **Issue:** The first load of the model (inside the unusual-pairs engine, before the engine facade lowered log levels) printed a "LOAD REPORT" with ANSI escape codes and a progress bar to stderr, with output piped. This breaks "no color when not a TTY".
- **Fix:** `prepare_offline_environment()` now also sets `TRANSFORMERS_VERBOSITY=error` and `HF_HUB_DISABLE_PROGRESS_BARS=1` with `setdefault`. A user value is kept. A test pins both. A second real run shows clean stderr.
- **Files modified:** src/mindrian_eureka/run/engines.py, tests/test_run_engines.py
- **Commit:** `0b32070`

**2. [Rule 1 - Bug] Short engine code in an engine warning**
- **Found during:** Task 1 design check of the label rule
- **Issue:** The unusual-pairs engine warning for small collections starts with the short engine code. It would reach the notes of the ranked files and stderr (a collection under 5 records, or any collection with fewer than 10 eligible pairs).
- **Fix:** `_plain_engine_text` in pipeline.py rewrites it to "The hybrid percentile gate ..." and removes any standalone short code. A label test runs a 4-record collection and checks files and stderr.
- **Files modified:** src/mindrian_eureka/run/pipeline.py, tests/test_run_labels.py
- **Commit:** `3056168`, `6f6198e`

**3. [Rule 3 - Blocking] Gated real-model test could not find installed libraries**
- **Found during:** Task 3
- **Issue:** `isolated_env` moves HOME, so the subprocess lost the user site folder that holds scikit-learn on this machine.
- **Fix:** The test passes `PYTHONUSERBASE=site.getuserbase()` (captured at interpreter start).
- **Files modified:** tests/test_run_determinism.py
- **Commit:** `6f6198e`

**4. [Rule 3 - Blocking] Acceptance grep `print(` matched `model_fingerprint(`**
- **Fix:** The import is aliased to `describe_model`. `grep -v '^#' pipeline.py | grep -c "print("` prints 0.
- **Commit:** `3056168`

Total deviations: 4, none changes scope.

## Skipped by decision (recorded as the plan asks)

- **Shell completion:** skipped. argparse needs the third-party `argcomplete` package, and the enclave install must stay small.
- **50 ms startup target:** skipped. Loading the model takes seconds (about 5 s of the 8 s real run here; the plan notes about 16 s on the research machine). `eureka --help` itself imports no heavy library.

## Known Stubs

None.

## Threat Model Coverage

T-02-51: `ensure_out_dir_allowed` runs before any work; tests: out inside input, foreign non-empty out. T-02-52: input tree hash unchanged (Markdown and CSV). T-02-53: `no_network` list stays empty in pipeline tests; offline variables set before engine import. T-02-54: umask 077 during the run (restored, tested), folder 0o700, files 0o600 (tested). T-02-55: no traceback by default; a test checks that no sentence of the input reaches stdout or stderr. T-02-56: engine error and KeyboardInterrupt tests show no staging folder and the earlier run intact; exit 130 and the interrupt line. T-02-57: `--no-cache` uses a tempfile folder and leaves the default cache folder absent (tested). T-02-58: label test walks every output file. T-02-SC: `git diff --stat -- uv.lock Dockerfile scripts/run-mcp-container pyproject.toml` is empty.

## Threat Flags

None.

## UNVERIFIED

- Byte-equality across different BLAS thread counts with the real model (the stub test cannot show it). The gated test varies the hash seed, not the thread count.
- Byte-equality across different machines, CPUs or library versions.
- Windows behavior (file modes, `icacls` fix lines, path handling).
- A run near the 3,000-record cap and its memory use.

## Issues Encountered

- The tree holds uncommitted edits of another session under story/. None was staged, edited or reverted.

## Next Phase Readiness

- Phase 3 can call `run_pipeline(RunRequest(...), Console(...))` and validate a request with a schema. The MCP server does not expose the run in this phase.
- `RunSummary.to_json_dict()` has schema id `eureka.run-summary.v1`.

## Self-Check: PASSED

- Files exist: pipeline.py, command.py, test_run_pipeline.py, test_run_cli.py, test_run_determinism.py, test_run_labels.py (all under their paths above).
- Commits found: 3056168, eb01438, 6f6198e, 0b32070.
- ruff clean on all new source and test files; mypy --strict clean on src/mindrian_eureka/run, doctor.py, models.py, limits.py (15 files).
- No story/ file, STATE.md or ROADMAP.md touched.
