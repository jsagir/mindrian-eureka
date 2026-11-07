---
phase: 03-host-integration-and-replay-rebuild
plan: 04
subsystem: host-run
tags: [host-run, envelope, job, cleanup, HOST-01]
requires:
  - phase: 03-02
    provides: normalize_request, stage_bundle, pair-screen-output.v1 schema
provides:
  - mindrian_eureka.host_run.envelope.build_result (hash-checked result envelope)
  - mindrian_eureka.host_run.execute (build_job_request, JobConsole, run_pair_screen_job)
  - JobManager branch for capability opportunity.run_pair_screen
affects: [03-05, 03-07]
tech-stack:
  added: []
  patterns: ["exact file text plus sha256 in the result", "private run folder deleted in a finally block", "silent console with cancel check between stages"]
key-files:
  created:
    - src/mindrian_eureka/host_run/envelope.py
    - src/mindrian_eureka/host_run/execute.py
    - tests/test_host_run_envelope.py
    - tests/test_host_run_job.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/jobs.py
key-decisions:
  - "run_pair_screen_job checks the cancel flag once before staging, so a cancel before the first stage never writes host text to disk."
  - "The envelope reads the four listed files by fixed name and compares each with manifest.json; it never reads a path from the manifest."
requirements-completed: []
duration: about 35 min
completed: 2026-11-07
---

# Phase 3 Plan 04: Pair screen result envelope and job Summary

A durable job now stages a host bundle, runs the Phase 2 pipeline on it with no embedding cache, returns a schema-valid envelope that holds the exact text of the small output files with their sha256, and deletes its private folder in every case.

HOST-01 is not complete. This plan covers the run and the result. The MCP tools and the catalog entry follow in plan 03-05. Do not mark HOST-01 complete before the last plan of the phase.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Envelope and job tests (RED) | 620b28f |
| 2 | Result envelope builder (GREEN, part 1) | e2b7999 |
| 3 | Job runner and job branch (GREEN, part 2) | 4617c7c |

## RED output

Both test files before any source: 27 failed (ModuleNotFoundError for `host_run.envelope` and `host_run.execute`; `test_jobs_py_change_is_additive` failed on the missing string). The files hold 10 and 17 test functions.

## GREEN counts

- After Task 2: `tests/test_host_run_envelope.py` 10 passed.
- After Task 3: envelope and job files 27 passed, 0 failed (about 5 s).
- Guard set (`test_host_run_contracts`, `test_host_run_bundle`, `test_run_pipeline`, `test_run_determinism`, `test_graph_relations`, `test_hsi_latest_integration`): 104 passed, 1 skipped, 9 subtests passed, 0 failed.

## Envelope keys

`schema_version`, `capability_id`, `status`, `job_id`, `label`, `summary_line`, `scope`, `approval`, `counts`, `caps_hit`, `warnings`, `manifest_sha256`, `files`, `id_map`, `outputs`, `host_handoff`, `room_write`, `portfolio_write`, `persistence`. The five `files` paths, sorted: `corpus/records.jsonl` (hash only), `manifest.json`, `ranked-pairs.md`, `unusual-pairs.json`, `wording-and-meaning-pairs.json` (exact text inline).

## Job folder layout

`<data dir>/host-runs/<job id>/in/artifacts.csv`, `<job id>/mapping.json`, `<job id>/out/` (mode 0o700; files 0o600). The whole `<job id>` folder is removed in a `finally` block on success, failure and cancel. Tests prove this for all three, and prove that no `embeddings.sqlite3` and no `.staging-` folder remain.

## Stage names the callback saw

`Reading sources`, `Writing the clean corpus`, `Ranking with Find Unusual Pairs Across a Research Collection`, `structural-scoring`, `semantic-scoring`, `pair-ranking`, `complete`, `Loading the local model`, `Ranking with Rank Unusual Pairs by Wording and Meaning`, `Writing files`. The engine adds the four lowercase stage names. They give extra cancel points.

## Lint counts

- `ruff check` on `host_run` and the two new test files: All checks passed.
- `ruff check src tests`: 1465 errors, same as the baseline.
- `mypy src`: 88 errors in 17 files, same as the baseline. No error in `host_run` or `jobs.py`.
- `jobs.py` diff: 7 insertions, 0 deletions. One `elif` branch only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in own edit] Docstring held the word run-info**
- **Found during:** Task 2 acceptance grep (`run-info` must give 0)
- **Fix:** Reworded the module docstring and amended the unpushed Task 2 commit (`e2b7999`; first sha before amend was `166f8e7`, not kept).
- **Files modified:** `src/mindrian_eureka/host_run/envelope.py`

**2. [Rule 2 - interpretation] Cancel check before staging**
- **Issue:** The plan lists the cancel check only inside the console and after the pipeline.
- **Fix:** One extra check before `stage_bundle`, so a cancel at job start writes no host text. `test_cancel_between_stages` still cancels inside the pipeline (third call).
- **Commit:** 4617c7c

**3. [Interpretation] Data directory mode**
- The job creates a missing data directory and `host-runs` with mode 0o700, so the planned mode test holds when the job makes the folder. An existing data directory is not changed.

**4. [Tool path] Test and lint commands**
- The orchestrator set `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`; `ruff` and `mypy` ran from `/home/jsagi/.local/bin`. `ruff format` was applied to the new files.

## Plugin checkout (information only)

`git status --short | wc -l` of `/home/jsagi/dev/MindrianOS-Plugin-release`: 0 at the end of this plan. No plugin file was edited.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-03-18 to T-03-23 and T-03-26 are in place and tested: no cache, private folder deleted in a `finally` block, job id pattern, hash check, no room path or room string in `host_run`, silent console, `verified_by_engine` false. T-03-24 and T-03-25 are accepted as planned.

## Self-Check: PASSED

- Created files `envelope.py`, `execute.py`, both test files: FOUND
- Commits 620b28f, e2b7999, 4617c7c: FOUND
- Nothing from `story/` staged; `cli.py` untouched; `tests/fixtures` clean; nothing pushed.
