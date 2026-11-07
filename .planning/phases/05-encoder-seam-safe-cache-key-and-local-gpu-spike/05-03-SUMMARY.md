---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 03
subsystem: encoder-seam
tags: [runner, doctor, encoder-spec, cache-identity, fingerprint, determinism-class]

requires:
  - phase: 05-01
    provides: EncoderSpec, profiles, make_encoder
  - phase: 05-02
    provides: schema 2 cache key with identity, expected_dimension check
provides:
  - "run_document(encoder_spec=None): encoder built through make_encoder, cache keyed by spec.identity() and spec.dimension"
  - "every output carries label and encoder_fingerprint; method_details.encoder gains profile, fingerprint, determinism_class, identity"
  - "one gpu-approx warning sentence for a non-exact setup"
  - "eureka doctor --encoder-profile NAME adds check D9; D9 replaces D8 when the model is loaded"
affects: [05-05]

tech-stack:
  added: []
  patterns: ["legacy call stays identical: custom_spec(model_path, revision) gives the old constructor call", "doctor probes extended with encoder_loader and cuda_available"]

key-files:
  created:
    - tests/test_runner_encoder.py
    - tests/test_doctor_encoder.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/runner.py
    - src/mindrian_eureka/doctor.py
    - src/mindrian_eureka/run/command.py
    - tests/test_wrong_number_fixes.py

key-decisions:
  - "The resolved revision (spec revision, or model_revision when the spec has none) feeds the download rule, the encoder call, the cache call and method_details.encoder.revision. For a legacy call it equals model_revision."
  - "reference-bert keeps its own encoder call; it gets identity=custom_spec identity and expected_dimension=None. A non-custom spec with reference-bert raises ValueError."
  - "D9 returns WARN, not FAIL, for a missing model folder without --load-model, and for a spike profile whose revision is not pinned."

requirements-completed: []

duration: 40min
completed: 2026-11-08
---

# Phase 5 Plan 03: Runner and doctor seam Summary

**The unusual-pairs runner builds its encoder with make_encoder, keys the embedding cache by the full encoder identity and the declared width, and stamps each output with the label and the encoder fingerprint; `eureka doctor --encoder-profile NAME` adds the optional check D9.**

Requirements ENC-02, ENC-03, ENC-05 and ENC-06 are covered by this plan. They are not marked complete here; the orchestrator marks them at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | 7eb1148 | test(05-03): add failing tests for the runner seam, cache identity and the doctor encoder probe |
| 2 GREEN | d4e6a3a | feat(05-03): build the unusual-pairs encoder through make_encoder and key the cache by encoder identity |
| 3 GREEN | 1b5deb4 | feat(05-03): add the optional encoder profile check D9 to eureka doctor |
| Summary | see git log | docs(05-03): record the runner and doctor seam plan |

## RED output (Task 1)

Run of the three files before any source change: 21 failed, 26 passed.
- `test_runner_encoder.py`: 8 failed (no `encoder_spec` keyword). The legacy-call test and the module-agreement test passed: they pin behavior that already holds.
- `test_doctor_encoder.py`: 10 failed (no `encoder_profile`, no D9, no new probe fields, no flag).
- `test_wrong_number_fixes.py`: 3 failed (the seeded cache used the identity of the bare-folder spec; the runner did not pass it yet).

## GREEN counts

- `tests/test_runner_encoder.py`, `tests/test_wrong_number_fixes.py`: 37 passed (after Task 2).
- Guard set of the plan (`test_rs_engine_parity`, `test_rs_hybrid_2026`, `test_run_engines`, `test_run_pipeline`, `test_run_limits`, `test_hsi_latest_integration`, `test_opportunity_discovery_direction_contract`, `test_mcp_limits_parity`, `test_host_run_job`, `test_host_run_mcp`, `test_mcp_start_stderr` plus the two files above): 182 passed, 3 skipped, 0 failed.
- `test_doctor_encoder`, `test_doctor`, `test_run_cli`, `test_runner_encoder`: 101 passed, 1 skipped.
- Pinning set on system Python (the four above plus `test_mcp_start_stderr`, `test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`, `test_embedding_cache_key`): 293 passed, 2 skipped, 0 failed. `test_partner_bundle.py` passed.
- Locked environment (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder --with pytest`): `test_doctor_encoder`, `test_doctor`, `test_runner_encoder`, `test_mcp_start_stderr`, `test_run_engines`, `test_wrong_number_fixes`, `test_embedding_cache_key`: 165 passed, 1 skipped.

## Real-model proof of the default path (PROVEN)

- `EUREKA_EXAMPLE_REAL_RUN=1 pytest tests/test_public_example_fresh.py`: 5 passed.
- By hand, scratch folder outside the repository, `--threads 1`: cold cache run then `eureka check-example` gave `Result: MATCH`. A second run with the same cache folder (warm) gave `Result: MATCH`. Both manifests had the same sha256 (`b2b6c6e9...c073895`).

## Doctor outputs (PROVEN on this computer, no GPU)

- `eureka doctor`: no D9 line. `--json` keys `['checks', 'ok', 'schema_version']`, ids `D1` to `D7`.
- `eureka doctor --encoder-profile cpu-default`: `[PASS] D9 Encoder profile: Profile cpu-default: libraries found (dtype default, device cpu). Add --load-model ...`.
- `eureka doctor --encoder-profile gpu-nemotron`: `[FAIL] D9 ... needs a CUDA device, but torch reports none.` with a fix that names a CUDA build of torch and says this project does not lock it. Exit code 1.
- `grep -c "os.environ.get\|os.getenv" doctor.py`: 0 before and 0 after. No new environment variable is read.

## Lint counts

- `ruff check` on `runner.py`, `doctor.py`, `command.py`: 34 findings before, 33 after. New test files: clean.
- `mypy src`: 87 errors in 16 files (baseline 87 in 16).

## Deviations from Plan

**1. [Rule 1 - Bug in my own test stub] Narrow stub vectors were all zero.** In `test_declared_width_is_enforced` the stub sliced a 64-wide hashed vector to 3 or 5 values; some rows became all zero and `modern_semantic_similarity` refused them. Fix: lift each narrow row by `np.arange(1, width + 1)`. The test intent is unchanged. The fix went into the Task 2 commit (2 files in that commit: `runner.py` and `test_runner_encoder.py`; the plan listed 1).

**2. [Info] Pinned test changed.** `tests/test_wrong_number_fixes.py::_seed_rs_cache` now passes `identity=custom_spec(MODEL_PATH).identity()` to `EmbeddingCache.key`. This is the new correct behavior the plan names. No assertion was weakened or deleted.

## Known Stubs

None.

## UNVERIFIED

- A real load of the `gpu-nemotron` profile (no GPU on this computer, F2 of 05-CONTEXT).
- The D9 text on a computer with CUDA, and a real `--load-model` run of D9 with the MiniLM model (only fake loaders and a fake `sentence_transformers` module were used).
- Full-suite count after this plan (the orchestrator runs it).

## Threat flags

None. T-05-10 to T-05-15 are mitigated as the plan states. `git diff --name-only 7eb1148~1 HEAD` lists no `pyproject.toml` or `uv.lock`.

## Self-Check: PASSED

- Files `tests/test_runner_encoder.py`, `tests/test_doctor_encoder.py`, `runner.py`, `doctor.py`, `command.py` exist.
- Commits 7eb1148, d4e6a3a and 1b5deb4 exist in `git log`.
- No `story/`, `docs/research/`, `.gitkeep` or quick-folder file staged or committed.
