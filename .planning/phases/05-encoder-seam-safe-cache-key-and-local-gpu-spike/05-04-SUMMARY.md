---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 04
subsystem: example-check
tags: [check-example, ranking-overlap, determinism-class, gpu-approx, fail-closed]

requires:
  - phase: 05-01
    provides: determinism class names and the encoder manifest block shape
provides:
  - "ranking_overlap(run_ids, reference_ids) in example/check.py"
  - "check_run(run_folder, expected, *, reference_run=None) with a gpu-approx branch of check X6"
  - "example/contracts.py: ENCODER_KEY, DETERMINISM_*, OVERLAP_FILES, GPU_APPROX_MIN_OVERLAP (None), NO_THRESHOLD_TEXT, GPU_APPROX_NOTE"
  - "eureka check-example passes the reference-run folder next to the expected-hash file when it exists"
affects: [05-05, 05-08]

tech-stack:
  added: []
  patterns: ["threshold read at call time through the module, so a test can replace it", "the class selects the weaker path only for X6; X2 to X5 and X7 always run"]

key-files:
  created:
    - tests/test_example_check_encoder.py
  modified:
    - src/mindrian_eureka/example/check.py
    - src/mindrian_eureka/example/contracts.py
    - src/mindrian_eureka/example/command.py

key-decisions:
  - "GPU_APPROX_MIN_OVERLAP is None. A gpu-approx run is never a MATCH until the spike sets the number."
  - "An unknown or unreadable class gives an X6 FAIL with no note (NOT_REPRODUCED_TEXT would mislead)."
  - "A pair file with no list of pairs or a pair without pair_id raises UsageError (exit 2), like the other readers."

requirements-completed: []

duration: 35min
completed: 2026-11-08
---

# Phase 5 Plan 04: check-example for non-exact runs Summary

**`eureka check-example` compares a run of class gpu-approx with the shipped reference run by pair-id overlap (corpus still by bytes), fails closed on every unclear case, and never reports a match while the overlap threshold is unmeasured; the exact path is unchanged.**

Requirement ENC-04 is covered by this plan. It is not marked complete here; the orchestrator marks it at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | 151bf9b | test(05-04): add failing tests for check-example on non-exact encoder runs |
| 2 GREEN | d49a5e6 | feat(05-04): compare non-exact encoder runs by ranking overlap in check-example |
| Summary | see git log | docs(05-04): record the check-example non-exact plan |

## RED output (Task 1)

`tests/test_example_check_encoder.py` before any source change: 15 failed, 1 passed. The passing test is `test_import_weight_stays_light`, which pins today's behavior. The exact-path test failed because `check_run` had no `reference_run` keyword. 16 test functions (17 cases with the parametrized one).

## GREEN counts

- `test_example_check_encoder`, `test_example_check`, `test_example_command`, `test_public_example`, `test_reproduction_guide`: 75 passed.
- Pinning set plus the plan files (`test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`, `test_mcp_start_stderr`): 209 passed, 1 skipped, 0 failed. `test_partner_bundle.py` passed.
- Locked environment (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder --with pytest`): `test_example_check_encoder`, `test_example_command`, `test_mcp_start_stderr`: 35 passed.

## check-example on the shipped reference run (PROVEN)

`uv run --offline eureka check-example examples/public-example/reference-run` ends with
`Result: MATCH. This run is identical to the shipped expected hashes.` and exit 0.
A copy with 1 byte appended to `ranked-pairs.md` prints the not-reproduced note and `Result: NO MATCH`, exit 1.
`contracts.GPU_APPROX_MIN_OVERLAP` prints `None`.

## Lint counts

- `ruff check src tests`: 1452 errors (caller baseline 1454; before this plan 1452). No new finding in the changed files; `ruff format --check` clean on the example package.
- `mypy src`: 87 errors in 16 files (baseline 87 in 16). `mypy --strict src/mindrian_eureka/example`: no issues (before and after).
- Import rule: 0 code lines import numpy, torch or `encoder_spec` in the three source files. `test_import_weight_stays_light` confirms none of the heavy modules loads.
- No em-dash or en-dash in `check.py` or `contracts.py`.

## Behavior

- Absent `encoder` block or class `cpu-exact`: the same `_check_outputs` runs. Text and JSON are byte-equal to the old report, with or without `reference_run` (`test_exact_class_and_missing_block_are_unchanged`).
- Class `gpu-approx`, X6 order: (1) each output file must equal the hash that the run's own manifest lists, else `changed after the run`; (2) the reference folder must exist and hold the expected hashes, else `reference run` or `reference run does not match`; (3) the corpus file must equal the expected hash by bytes; (4) overlap per pair file; (5) the threshold: None fails with `no overlap threshold has been measured yet`, a number fails when any overlap is below it.
- `ranked-pairs.md` is derived from the pair files and is not compared in the approximate path (its hash still must equal the manifest hash).
- Report: note is `GPU_APPROX_NOTE`; one INFO line names the profile and the two fingerprints; JSON gains `determinism_class` and `ranking_overlap` only for the approximate path.
- Unknown class (for example `gpu-fast`) and an unreadable block give an X6 FAIL that holds `unknown determinism class` plus the name, or `encoder block`.

## Deviations from Plan

None. The plan was executed as written. One note: the "no threshold" detail line also carries the words "so a gpu-approx run is not a match" after the required sentence.

## Open item

`GPU_APPROX_MIN_OVERLAP` stays None until the owner-run spike (plan 05-08) records the measured drift. A follow-up quick task sets it from that record. A test in plan 05-08 ties the constant to the record (`docs/encoder-spike-results.md`). No threshold number was invented in this plan.

## Known Stubs

None. The `None` threshold is a deliberate, documented gate.

## UNVERIFIED

- A real gpu-approx run: no GPU on this computer. The approximate path ran only on edited copies of the public fixture run.
- That plan 05-05 writes the `encoder` block under the key `encoder` with the same shape as `encoder_block` (this plan only reads it).
- Full-suite count after this plan (the orchestrator runs it).

## Threat flags

None. T-05-16 to T-05-20 are mitigated as the plan states, each with a named test. No package was installed; `pyproject.toml` and `uv.lock` are unchanged.

## Self-Check: PASSED

- Files exist: `tests/test_example_check_encoder.py`, the three changed source files.
- Commits 151bf9b and d49a5e6 exist in `git log`.
- No `story/`, `docs/research/`, `.gitkeep` or quick-folder file staged or committed.
