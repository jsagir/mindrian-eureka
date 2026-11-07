---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 06
subsystem: host-run-result
tags: [encoder-profile, host-result, schema, docs, plugin-hand-offs]

requires:
  - phase: 05-05
    provides: manifest key encoder (schema eureka.encoder-block.v1)
provides:
  - "optional key encoder in the host run result (copy of the manifest block)"
  - "docs/encoder-profiles.md: profiles, never-mix rule, run record, selection, check, install, unrouted build sites, plugin hand-offs"
affects: [05-07, 05-08]

tech-stack:
  added: []
  patterns: ["additive optional key in a closed schema: required list and top-level closure unchanged", "doc table equals code by test"]

key-files:
  created:
    - docs/encoder-profiles.md
    - tests/test_encoder_docs.py
  modified:
    - src/mindrian_eureka/host_run/envelope.py
    - src/mindrian_eureka/data/schemas/pair-screen-output.v1.json
    - docs/mos-eureka-engine-run-contract.md
    - tests/test_host_run_envelope.py
    - tests/test_host_run_contracts.py

key-decisions:
  - "The encoder key is a deep copy of the manifest block and appears only when the manifest holds a mapping under encoder. Older run folders give a result without the key."
  - "The schema property has type object and no nested properties. The shape is documented in words and pinned by the block unit tests."

requirements-completed: []

duration: 40min
completed: 2026-11-08
---

# Phase 5 Plan 06: Encoder key of the host result and the encoder profiles page Summary

**The host run result carries the encoder block as an optional key, and `docs/encoder-profiles.md` records the profiles, the never-mix rule, the four unrouted build sites and ten plugin hand-offs, each with a source and a mark.**

Requirements ENC-02, ENC-05 and ENC-10 are covered. They are not marked complete here; the orchestrator marks them at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | 0ebdb43 | test(05-06): add failing tests for the encoder key of the host result and the encoder profiles page |
| 2 GREEN | 39e1388 | feat(05-06): carry the encoder block in the host run result as an optional key |
| 3 GREEN | 46ba40e | docs(05-06): add the encoder profiles page with the follow-up build sites and the plugin hand-offs |
| Summary | see git log | docs(05-06): record the encoder result key and profiles page plan |

## RED output (Task 1)

`tests/test_host_run_envelope.py tests/test_host_run_contracts.py tests/test_encoder_docs.py` before any source change: 12 failed, 35 passed.
- Failed: `test_result_carries_the_encoder_block`, `test_encoder_block_is_a_copy`, `test_output_schema_has_an_optional_encoder_object`, and all 9 tests of `test_encoder_docs.py`.
- `test_result_without_a_block_has_no_encoder_key` passed in RED. It pins behavior that already holds (no key without a block). The test is kept.

## GREEN counts

- Task 2 set (`test_host_run_envelope`, `test_host_run_contracts`, `test_host_handoff_docs`, `test_host_run_mcp`, `test_host_run_job`, `test_room_seed_docs`): 99 passed.
- Task 3 set (the page tests plus `test_host_handoff_docs`, `test_readme_commands`, `test_room_seed_docs`, `test_release_gate_record`): 55 passed.
- Verify set of Task 3 (page, envelope, contracts, handoff docs, `test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`): 205 passed, 1 skipped, 0 failed. `test_partner_bundle.py` passed.
- Locked environment (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder`): envelope, contracts, `test_host_run_mcp`, `test_host_run_job`, `test_host_run_mcp_reach`, `test_host_handoff_docs`, `test_encoder_docs`: 118 passed.
- System Python (mcp 1.25.0, `PYTHONPATH=src:tests`): `test_host_run_mcp_reach`, `test_host_run_envelope`, `test_encoder_docs`, `test_mcp_start_stderr`: 49 passed.
- The full suite was not run (the orchestrator runs it).

## Lint counts

- ruff `src tests`: 1452 errors (baseline 1452; no rise). `envelope.py` and the three test files: `All checks passed!`.
- mypy `src`: 87 errors in 16 files (baseline 87 in 16; no rise).
- Schema check: `19 False False` (19 required keys, closed top level, `encoder` not required).
- House style on the contract page and the new page: 0 long dash characters, 0 uppercase short engine codes.

## Hand-offs

The plugin session reads this section. Full text and sources are in `docs/encoder-profiles.md`.

1. The environment allowlist drops new `MINDRIAN_*` variables, so a profile switch needs a request field (INFERRED; PROVEN that unlisted variables are dropped).
2. Add a request field `encoder_profile` to the pair-screen input and pass the model path through `MINDRIAN_EUREKA_RS_MODEL_PATH`; built in a later engine phase (ASSUMED).
3. The block schema id `eureka.encoder-block.v1` is the contract version marker; the plugin checks only the project name and the `eureka-mcp` script (PROVEN for the check, INFERRED for the use).
4. One `vec0` table for each profile, with its width: 384 (partner store) and 2048 (`gpu-nemotron`); never two encoders in one table (PROVEN for the 384 table).
5. The 0.55 CONVERGES floor in `graph-derive-classifier.cjs` must be tuned again for each profile; 2,165 of 2,267,385 pairs reach it on the 384 vectors (PROVEN).
6. Failure reason `local_model_unavailable` stays; the install text names the extra `gpu-encoder`, and the plugin list of allowed extras may not accept it (INFERRED).
7. Show `determinism_class` next to every pair and keep the label candidate, not verified (PROVEN for the key, ASSUMED for the display).
8. Check Canon Part 8 at source; this repository read it only from a plugin summary (UNVERIFIED).
9. Capture the stderr of an `eureka-mcp` start once; a healthy start writes 0 bytes (pinned by a test here; INFERRED for the plugin side).
10. A green doctor does not prove that the server starts: no `mcp` import check, no Node.js check; only D9 is new (PROVEN).

## Deviations from Plan

None. The plan ran as written. Two small choices:
- Task 1: "a run folder made by the pipeline" is built as a copy of the frozen run with the block from `encoder_block(...)` written into the copied `manifest.json` (the manifest is not hashed inside itself). The pipeline output itself is covered by `tests/test_run_encoder.py` (plan 05-05).
- Task 3: paragraphs of the page were wrapped to stay under the 400 character line limit of the house style test.

## Known Stubs

None.

## Threat Flags

None. The new key copies a block that holds ids, hashes, device name and CUDA version only (plan 05-05 scans the manifest for path strings). No file in a plugin checkout was read for write, edited or run with git. Every changed file sits under `src`, `docs`, `tests` or `.planning`.

## UNVERIFIED

- The full plugin environment allowlist (only the fact that unlisted `MINDRIAN_*` variables are dropped is PROVEN).
- Canon Part 8 at its source (read from a plugin CLAUDE.md summary only).
- The OpenMDW-1.1 license text in full and any legal review.
- Web-sourced model facts of `nvidia/Nemotron-3-Embed-1B-BF16` (prefix whitespace, attention setting, dtype string, revision pin, VRAM fit) until `docs/encoder-spike-results.md` records them.
- The plugin start stderr (the research never captured it).
- The full suite after this plan (the orchestrator runs it).

## Parallel work

Plan 05-08 edited `scripts/encoder-spike.py`, `docs/encoder-spike-results.md` and two spike tests in the same tree. No test of this plan failed because of a half-written file of plan 05-08. Plan 05-06 touched none of those files.

## Self-Check: PASSED

- Files found: `docs/encoder-profiles.md`, `tests/test_encoder_docs.py`, `src/mindrian_eureka/host_run/envelope.py`, `src/mindrian_eureka/data/schemas/pair-screen-output.v1.json`.
- Commits found: 0ebdb43, 39e1388, 46ba40e.
