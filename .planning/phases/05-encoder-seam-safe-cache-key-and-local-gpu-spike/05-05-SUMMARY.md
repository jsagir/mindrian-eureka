---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 05
subsystem: run-pipeline
tags: [encoder-profile, manifest, cache-identity, wording-engine, cli-flag]

requires:
  - phase: 05-01
    provides: EncoderSpec, PROFILES, profile_spec, encoder_block, make_encoder
  - phase: 05-02
    provides: schema 2 cache key with identity, profile_cache_path
  - phase: 05-03
    provides: run_document(encoder_spec=...)
  - phase: 05-04
    provides: check-example reads the manifest encoder block
provides:
  - "load_local_encode(model_dir, spec=None); run_unusual_pairs(encoder_spec=None); wording_params(top_k, model_name=None)"
  - "RunRequest.encoder_profile and eureka run --encoder-profile NAME"
  - "top-level manifest key encoder (schema eureka.encoder-block.v1) on every run"
  - "encoder_fingerprint on both pair files for a non-default profile only"
affects: [05-06, 05-07, 05-08]

tech-stack:
  added: []
  patterns: ["default profile keeps the legacy calls; the spec is passed to the wording engine only for a named profile", "identity carries the snapshot as revision and a digest of the model file hashes"]

key-files:
  created:
    - tests/test_run_encoder.py
  modified:
    - src/mindrian_eureka/run/engines.py
    - src/mindrian_eureka/run/manifest.py
    - src/mindrian_eureka/run/project.py
    - src/mindrian_eureka/run/pipeline.py
    - src/mindrian_eureka/run/command.py
    - tests/conftest.py
    - tests/test_run_pipeline.py

key-decisions:
  - "Cache safety: the identity of every run holds revision (snapshot name) and model_digest (sha256 of the model file hashes). Two model folders with one profile name get different cache keys unless no model file can be hashed."
  - "When no model file can be hashed, model_digest is None and the manifest encoder block gets a key weights_note that says the weights are not pinned."
  - "The unusual-pairs engine receives the spec for every profile, including the default. The wording engine receives it only for a named profile."

requirements-completed: []

duration: 75min
completed: 2026-11-08
---

# Phase 5 Plan 05: Encoder profile run Summary

**`eureka run --encoder-profile NAME` selects a named profile; every manifest records the encoder block (profile, determinism class, fingerprints, identities with snapshot and model digest); the default run stays byte-identical to the shipped reference.**

Requirements ENC-02, ENC-03, ENC-04 and ENC-05 are covered by this plan. They are not marked complete here; the orchestrator marks them at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | d955f2a | test(05-05): add failing tests for the encoder profile run, the manifest encoder block and the wording engine seam |
| 2 GREEN | ccfd315 | feat(05-05): build the wording engine encoder through the factory and add the manifest encoder parameter |
| 3 GREEN | 10ad49f | feat(05-05): select a named encoder profile in eureka run and record the encoder block in the manifest |
| 3 fix | 5a7f3df | fix(05-05): import the default encoder profile inside register_commands |
| Summary | see git log | docs(05-05): record the encoder profile run plan |

## RED output (Task 1)

`tests/test_run_encoder.py tests/test_run_pipeline.py` before any source change: 16 failed, 28 passed.
- `test_run_encoder.py`: 14 failed. 2 passed: `test_default_pair_files_have_no_new_key` and `test_settings_of_the_default_profile_are_unchanged`. They pin behavior that already holds.
- `test_run_pipeline.py`: 2 failed (`test_happy_path_writes_every_file[markdown|csv]`), only at the `MANIFEST_KEYS` assertion, as the plan expected.
- Older stub suites (`test_run_scaffold`, `test_hub_bridge_fixture`, `test_run_engines`, `test_runner_encoder`): 65 passed with the fixture edits.

## GREEN counts

- `test_run_encoder.py`: 16 passed.
- `tests/test_run_*.py`, `tests/test_host_run_*.py`, `test_hub_bridge_fixture`, `test_runner_encoder`, `test_doctor_encoder`: 649 passed, 1 skipped, 0 failed.
- Full suite (uv environment with the test extras, before the fix commit 5a7f3df): 1891 passed, 8 skipped, 1 failed, 45 subtests passed. The one failure was `test_example_check_encoder.py::test_import_weight_stays_light` (see Deviations). After the fix that file and the other touched files pass (95 passed). The full suite was not run a second time.
- Pinning set on system Python with `PYTHONPATH=src:tests` (`test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`, `test_mcp_start_stderr`, `test_example_check_encoder`, `test_run_encoder`, `test_encoder_extra`): 204 passed. `test_partner_bundle.py` passed.
- Locked environment (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder`): `test_mcp_start_stderr`, `test_run_encoder`, `test_run_pipeline`, `test_run_engines`, `test_host_run_job`: 101 passed.

## Real-model proof (PROVEN, MiniLM snapshot 1110a243..., no GPU)

Scratch folder outside the repository, `--threads 1`, own cache folder:
- Cold cache: `eureka run tests/fixtures/hub_public/input` then `eureka check-example` printed `Result: MATCH. This run is identical to the shipped expected hashes.`
- Warm cache (same cache folder, 36 entries after the cold run): `Result: MATCH`.
- `cmp` of `corpus/records.jsonl`, `ranked-pairs.md`, `unusual-pairs.json`, `wording-and-meaning-pairs.json` against `examples/public-example/reference-run/`: identical for the cold and the warm run (8 of 8).
- Manifest `encoder`: `determinism_class` `cpu-exact`, profile `cpu-default`, `revision` = the snapshot name, `model_digest` = 64 hex, no `gpu` key. The cold and warm manifests have equal `encoder` blocks.
- `EUREKA_EXAMPLE_REAL_RUN=1 tests/test_public_example_fresh.py`: 5 passed (before and after the fix commit).
- After commit 5a7f3df a third cold run (new cache folder) again printed `Result: MATCH`.
- The real library accepted `revision=<snapshot>` for a local folder. The default output did not change.
- Manifest sha256 of the default run is now `4f038567...` (the earlier value `b2b6c6e9...` is from before the encoder block existed). The manifest is not among the four hashed files.

## Lint counts

- `ruff check src tests`: 1452 errors (baseline 1452). Changed files: no new finding.
- `mypy src`: 87 errors in 16 files (baseline 87 in 16). A first draft raised 88; the local variable `encoder` in `load_local_encode` got the type `Any` and the count returned to 87.
- `grep -c "os.environ.get\|os.getenv"` on `pipeline.py` and `command.py`: 0 and 0 before and after. No variable is read.
- `hsi_reference.py` and `partner_bundle/` unchanged (`git status --short` empty). `engines.wording_params_hash(200)` prints `bea4c100c2013300`.
- Import weight: `engines` imports none of numpy, sklearn, torch, sentence_transformers.

## Cache safety (caller note)

The cache key of a profile spec uses `spec.model_id` and not the folder path. This plan closes the gap through the identity: `revision` (the snapshot name of a Hugging Face layout folder, else None) and `model_digest` (sha256 over the sorted JSON of the model file hashes that `model_fingerprint` already computes). A changed weight file gives another digest and another cache key. `test_snapshot_and_digest_come_from_the_model_folder` proves it: run 1 has `misses` equal to the record count, run 2 has 0, and after one byte is added to the weight file run 3 has `misses` equal to the record count again. A flat folder with no hashable file gets `model_digest` None; the block then holds `weights_note` ("The model weights are not pinned ..."); `test_digest_is_missing_and_said_so_when_no_model_file_can_be_hashed` pins that. The plan did not name `weights_note`; it is an addition (see Deviations). The determinism class is not changed by it.

## Behavior summary

- Validation order in `_validate`: top-k, record limit, side-car, then unknown profile name (`UsageError`, names listed), then a named profile without `--model-path` and without `--dry-run` (`UsageError`, fix names `--model-path` and the model id). Both run before any model search. The run never falls back to another model for a named profile.
- Default profile: pair files, `settings`, `seeds`, `tool.engines`, cache file `embeddings.sqlite3` and console text unchanged. The wording engine still gets `load_local_encode(model_dir)` with one argument.
- Named profile: cache file `embeddings-<profile>.sqlite3`; wording settings and params hash name the profile model; both pair files gain `encoder_fingerprint`; one summary warning with the words `gpu-approx` and `overlap`; manifest `encoder.gpu` holds name and CUDA version for a `cuda` device only.
- `encoder_block` has the keys `schema`, `profile`, `determinism_class`, `unusual_pairs`, `wording_and_meaning` (each with `fingerprint` and `identity`), plus `gpu` and `weights_note` only when they apply. No string in it starts with `/`.

## Deviations from Plan

**1. [Rule 1 - Bug in my own change] Module-level import broke an import-weight guard.** The first version of `command.py` imported `DEFAULT_PROFILE` from `encoder_spec` at module level. `test_import_weight_stays_light` (plan 05-04) requires that importing the example commands loads no `encoder_spec`. The full suite found it. Fix: the import moved into `register_commands`. Commit 5a7f3df (1 file). The plan listed 2 source files in the Task 3 commit; there is now one more small fix commit.

**2. [Rule 2 - Cache safety] `weights_note` key.** Added on the instruction of the caller: when no model file can be hashed, the manifest block says plainly that the weights are not pinned. Pinned by a test. The plan did not list it.

**3. [Info] Pinned test changes.** `tests/test_run_pipeline.py::MANIFEST_KEYS` gained `"encoder"` (the plan names this). `tests/conftest.py`: `hashing_encoder` also sets the `cpu-default` profile width to 64 with `monkeypatch.setitem`, and the `stub_encoders` function `_load` takes `(model_dir, spec=None)`. No assertion was weakened or deleted.

**4. [Info] Skip count.** The full suite in the uv environment reported 8 skipped. The caller baseline names 29. The cause is not investigated (the uv environment has more optional libraries than system Python). No test of this plan is skipped.

## Known Stubs

None.

## UNVERIFIED

- A real run with `gpu-nemotron` on a CUDA computer; the `gpu` details on a real GPU (`_gpu_details` only ran as a patched stub).
- A Hugging Face cache layout other than the single-file weights layout (sharded weights: `MODEL_FILES` lists `model.safetensors` and `pytorch_model.bin` only, so a sharded model could give a digest that does not cover all weights).
- The 2,117-record scale.
- Full-suite count after commit 5a7f3df (only the touched and pinning files were re-run).
- The locked-environment run of the full suite (only five files were run there).

## Threat flags

None. T-05-21 to T-05-26 are mitigated as the plan states, each with a named test. The block holds ids and hashes only; `gpu` holds the device name and CUDA version. `pyproject.toml` and `uv.lock` are unchanged.

## Self-Check: PASSED

- Files exist: `tests/test_run_encoder.py`, `pipeline.py`, `command.py`, `engines.py`, `manifest.py`, `project.py`.
- Commits d955f2a, ccfd315, 10ad49f and 5a7f3df exist in `git log`.
- No `story/`, `docs/research/`, `.gitkeep` or quick-folder file staged or committed.
