---
phase: 02-one-command-run-and-doctor
plan: 05
subsystem: doctor-and-model-discovery
tags: [doctor, model-discovery, offline, permissions, mypy-strict, ruff, docs]

requires:
  - phase: 02-one-command-run-and-doctor
    provides: "run/contracts.py (EXIT_OK, EXIT_FAILURE), tests/conftest.py fixtures (plan 02-01)"
provides:
  - "models.py: discover_model, ModelResolution, missing_files, missing_model_message, model_fix_text, os_variants"
  - "doctor.py: run_checks, doctor_command, format_report, report_json, CheckResult, Status, Probes"
  - "[tool.mypy] and [tool.ruff] tables in pyproject.toml"
  - "CONTRIBUTING.md Checks section and docs/offline-install.md"
affects: [02-06]

tech-stack:
  added: []
  patterns:
    - "One model search function for doctor and run; a set but invalid source stops the search"
    - "Doctor probes are one frozen dataclass of injectable callables"
    - "Fix text always prints a Linux or macOS line and a Windows line where they differ"

key-files:
  created:
    - src/mindrian_eureka/models.py
    - src/mindrian_eureka/doctor.py
    - tests/test_models.py
    - tests/test_doctor.py
    - docs/offline-install.md
  modified:
    - pyproject.toml
    - CONTRIBUTING.md

key-decisions:
  - "Hugging Face cache roots count only when set (HF_HUB_CACHE, HF_HOME) plus the default root. A fresh environment gives 4 searched lines."
  - "model_fix_text() is public so doctor check D4 and D8 and plan 02-06 print the same fix block."
  - "format_report does not print the fix twice when the message already holds every fix line (check D4)."
  - "[tool.ruff] sets src = [\".\"] so import order stays as the earlier plans wrote it."
  - "Probes.is_posix is a bool, not a callable, so tests inject a plain value."

patterns-established:
  - "Doctor reports PASS, WARN, FAIL with status words; exit code 1 only on FAIL"
  - "Doctor prints fixes and never runs them; the only subprocess call is `uv --version`"

requirements-completed: [DOC-01, DOC-02]

duration: 35min
completed: 2026-10-24
---

# Phase 2 Plan 05: Doctor and model discovery Summary

**`eureka doctor` checks Python, uv, encoder libraries, the local model, cache and data folder permissions and the offline variables, prints the exact fix for Linux or macOS and Windows, and shares one offline model search (flag, two variables, Hugging Face cache) with `eureka run`.**

## Performance

- **Tasks:** 3 of 3
- **Files:** 7 (5 created, 2 modified)
- **Tests:** 82 new tests passed, 1 skipped (real model, needs EUREKA_TEST_MODEL_PATH). Run tests plus doctor, models and capability CLI: 392 passed, 1 skipped.

## Accomplishments

- `discover_model` finds the model in a fixed order and never falls through after a set but invalid source. Cache snapshots follow `refs/main`; two valid snapshots without a ref give a not-ok result that says to pass `--model-path`.
- `missing_model_message` starts with "No local model found." or "The local model is not usable.", lists every searched place and prints the fetch, copy and set steps with both OS lines.
- Doctor checks D1 to D8. A missing model or a missing uv is FAIL. A missing model exits 1 with every searched place listed (DOC-02).
- Folder checks D5 and D6 use the same path rules as `cache.default_cache_path()` and `jobs.default_data_dir()` (a test compares them). Mode, owner and file modes are checked. Nothing is created or changed (a test compares a tree listing with modes before and after).
- `--json` output has schema `eureka.doctor.v1`, sorted keys, indent 2.
- Doctor and models import only the standard library. A subprocess test proves that numpy, torch, scikit-learn, scipy, sentence-transformers and huggingface_hub are not loaded by `run_checks` with injected probes. The no_network fixture proves no connect call.
- Tool tables for mypy and ruff are added. No dependency, extra, script or source changed. `uv.lock` is unchanged and `uv lock --check --offline` passes.

## Task Commits

1. **Task 1: shared model discovery** - `4f6127c` (feat)
2. **Task 2: eureka doctor** - `7cbba47` (feat)
3. **Task 3: tool config, check commands, offline note** - `7b4d956` (chore)

Red and green steps were done locally in one pass per task. There are no separate RED commits, for the same reason as plan 02-01 (new files must be staged for `git commit --only`).

## Decisions Made

See key-decisions in the frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mypy rejected lambda calls in discover_model**
- **Found during:** Task 1
- **Issue:** `Call to untyped function (unknown) in typed context` for the source tuple.
- **Fix:** Typed the tuple as `tuple[Callable[[], _Partial], ...]`.
- **Commit:** `4f6127c`

**2. [Rule 1 - Bug] Fix block compared as a substring of the D4 message**
- **Found during:** Task 2
- **Issue:** The message indents the fix block, so the plain `fix in message` check failed and the report printed the fix twice.
- **Fix:** `_message_holds_fix` compares stripped lines. The report prints the fix once.
- **Commit:** `7cbba47`

**3. [Rule 3 - Blocking] ruff import order changed after the config was added**
- **Found during:** Task 3
- **Issue:** Once `[tool.ruff]` exists, ruff treats `mindrian_eureka` (under `src/`) as first-party. The 11 files of plans 02-01 to 02-05 then failed rule I001, which had passed with no config.
- **Fix:** Set `src = ["."]` in `[tool.ruff]` with a comment. Import order of existing files stays valid. No existing file was edited.
- **Commit:** `7b4d956`

**4. Plan text had `is_posix` as a callable-like probe**
- The plan says "is_posix (os.name == "posix")" and "injected values for ... is_posix". It is a bool field with a default factory.

Total deviations: 4, none changes scope.

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None. The only new process call is `uv --version` with a fixed list, no shell, 10 second timeout (T-02-43). Fix commands for uv install and the Windows `icacls` line are ASSUMED text and are marked in docs/offline-install.md (T-02-45).

## Issues Encountered

- The default D8 loader (real SentenceTransformer load) was not run here. It needs the model and takes about 16 seconds. A gated test exists (`EUREKA_TEST_MODEL_PATH`). UNVERIFIED.
- On this machine the Hugging Face cache holds the model. The doctor returned exit 0 with one WARN (offline variables), seen in a manual run.

## Next Phase Readiness

- Plan 02-06 can call `discover_model(explicit, env=..., home=...)`, `missing_model_message(resolution, explicit_given=...)` and `doctor_command(json_output=..., load_model=..., model_path=..., out=...)` by exact name.
- Plan 02-06 must add the `doctor` subparser and `--model-path`, `--json`, `--load-model` flags in cli.py.
- The lint command in CONTRIBUTING.md runs clean with the new config.

## Self-Check: PASSED

- Files exist: models.py, doctor.py, tests/test_models.py, tests/test_doctor.py, docs/offline-install.md.
- Commits found: 4f6127c, 7cbba47, 7b4d956.
- `git diff --stat -- uv.lock` is empty. No story/ file, STATE.md or ROADMAP.md staged or committed.
