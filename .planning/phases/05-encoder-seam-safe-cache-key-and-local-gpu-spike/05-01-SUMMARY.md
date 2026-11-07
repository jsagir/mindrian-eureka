---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 01
subsystem: encoder
tags: [encoder-spec, sentence-transformers, make_encoder, uv-lock, gpu-encoder]

requires:
  - phase: 04.1
    provides: green baseline (1735 passed, 29 skipped)
provides:
  - "mindrian_eureka.encoder_spec: EncoderSpec (14-field identity), PROFILES (cpu-default, gpu-nemotron), custom_spec, profile_spec, encoder_block, determinism constants, RESULT_LABEL"
  - "make_encoder factory and Encoder protocol in opportunity_pairs/encoders.py"
  - "spec-aware SentenceTransformerEncoder (spec-less path unchanged)"
  - "optional extra gpu-encoder with a matching uv.lock"
affects: [05-02, 05-03, 05-04, 05-05, 05-08]

tech-stack:
  added: ["optional extra gpu-encoder (no new locked package)"]
  patterns: ["stdlib-only spec module", "factory passes spec= only for a non-legacy spec"]

key-files:
  created:
    - src/mindrian_eureka/encoder_spec.py
    - tests/test_encoder_spec.py
    - tests/test_encoder_factory.py
    - tests/test_encoder_extra.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/encoders.py
    - tests/hashing_stub.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "The factory is not wired into the runner or the engines yet (05-03 and 05-05 do that)."
  - "gpu-nemotron revision stays None until the spike (05-08)."
  - "The spec path reads the model width with get_embedding_dimension when present, to avoid a FutureWarning on stderr."

requirements-completed: []

duration: 55min
completed: 2026-11-08
---

# Phase 5 Plan 01: Encoder seam Summary

**A stdlib-only EncoderSpec with a 14-field fingerprint, two named profiles, one make_encoder factory, a spec-aware SentenceTransformerEncoder with an unchanged default path, and an optional gpu-encoder extra with a lock that adds no package.**

Requirements ENC-01 and ENC-07 are covered by this plan. They are not marked complete here; the orchestrator marks them at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | 17f8dea | test(05-01): add failing tests for the encoder spec, profiles and factory |
| 2 GREEN | ce93160 | feat(05-01): encoder spec, two named profiles and one make_encoder factory |
| 3 | 9e5b557 | chore(05-01): add the optional gpu-encoder extra and its lock |
| Summary | see git log | docs(05-01): record the encoder seam plan |

## RED output (Task 1)

`tests/test_encoder_spec.py tests/test_encoder_factory.py`: 47 failed, 2 passed. The 2 passing tests pin today's behavior (legacy construction and the legacy-encode oracle), as the plan expected. The first draft of the oracle test failed because the fake model made fewer than 17 chunks; the fake window was lowered to 12 tokens so the test crosses the 16-chunk slice limit. This was a test fix before the RED commit.

Task 3 RED: `tests/test_encoder_extra.py` gave 4 failed, 2 passed before the pyproject edit.

## GREEN counts

- New tests: `test_encoder_spec.py` and `test_encoder_factory.py` 49 passed (1 real-MiniLM test ran, not skipped). `test_encoder_extra.py` 6 passed.
- Guard set (`test_run_engines`, `test_rs_engine_parity`, `test_rs_hybrid_2026`, `test_analogy_lineage`, `test_wrong_number_fixes`, `test_mcp_start_stderr`, `test_run_cli` plus the two new files): 166 passed, 3 skipped, 0 failed.
- Pinning set (`test_encoder_extra`, `test_hub_assets`, `test_hub_probe_record`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`, `test_mcp_start_stderr`): 177 passed, 1 skipped, 0 failed (before the test_encoder_extra lock-key fix; that file then passed 6 of 6).
- Opt-in real-model run `EUREKA_EXAMPLE_REAL_RUN=1 tests/test_public_example_fresh.py`: 5 passed.
- With `PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder --with pytest`: `test_mcp_start_stderr`, `test_encoder_factory`, `test_run_engines` 50 passed.
- Full suite (system python, `PYTHONPATH=src:tests python3 -m pytest tests`): 1790 passed, 29 skipped, 0 failed (baseline 1735 plus 55 new tests).

## Lock diff (7 lines, no new package)

1. `gpu-encoder = [` under the package `optional-dependencies` (4 lines with its 2 names and the closing bracket)
2. `sentence-transformers` requirement line with marker `extra == 'gpu-encoder'`, `>=5.4.1,<6`
3. `transformers` requirement line with marker `extra == 'gpu-encoder'`, `>=5.2,<6`
4. `provides-extras` line now lists `gpu-encoder` after `modern-encoder`

`git diff -U0 uv.lock | grep -c "^+name = "` printed 0. `uv lock --check --offline` exits 0 (`Resolved 76 packages`). `uv lock --offline` needed no network. Core dependencies are still `jsonschema`, `numpy`, `scikit-learn`. torch stays on the CPU index.

## Lint counts

- `ruff check` on `encoder_spec.py`, `encoders.py`, the 3 new test files and `hashing_stub.py`: all clean.
- `ruff check src tests`: 1456 errors (baseline 1465).
- `mypy src`: 87 errors in 16 files (baseline 88 in 17). No error in `encoder_spec.py` or `encoders.py`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Format-only edits to `ReferenceBertEncoder` lines.** The acceptance gate needs `ruff check` clean on the whole of `encoders.py`. The file held 5 old line-length errors in `ReferenceBertEncoder` and in `encode`. Only line wrapping changed there; no logic changed. Also changed: `Callable` and `Sequence` import from `collections.abc`; `zip(..., strict=True)` in `encode` (the two sequences always have equal length); a type annotation on `grouped` (this removed one mypy error). Commit ce93160.

**2. [Rule 1 - Bug] FutureWarning on the spec path.** Current sentence-transformers renames `get_sentence_embedding_dimension` to `get_embedding_dimension` and warns. A warning on stderr could break the silent-start rule if the spec path ever runs in `eureka-mcp`. The spec path now uses the new name when it exists and falls back to the old name. Commit ce93160.

**3. [Info] A pre-existing failure set.** With `uv run --extra mcp-server` (mcp 2.x client shape), 12 tests in `test_host_run_mcp.py` and `test_host_run_mcp_reach.py` fail with `'CallToolResult' object is not subscriptable`. The same 12 fail on a `git archive HEAD` copy of `src` taken before these changes. They pass on the system python used by the baseline. They are unrelated to this plan. Not fixed.

No test was weakened or deleted. The only change to an existing test file is `tests/hashing_stub.py`, which gained the keyword `spec` as the plan states.

## Known Stubs

None.

## UNVERIFIED

- The Nemotron prefix whitespace (`query: ` and `passage: `).
- The `sdpa` attention setting loading on the owner's stack.
- The dtype form that transformers 5.x accepts (`model_kwargs={"dtype": torch.bfloat16}` is used; a string form may also work).
- The unpinned `gpu-nemotron` revision (stays None).
- That `get_embedding_dimension` exists on the sentence-transformers version of the owner's GPU machine (the fallback covers the old name).
- The `gpu-nemotron` profile never ran on a real model in this plan. All GPU-path tests use a fake library and a fake torch module.

Plan 05-08 (the spike record) settles all of these.

## Threat flags

None. No new endpoint, auth path or file access. T-05-01 to T-05-05 are mitigated as the plan states (no `trust_remote_code` in code; device always set; 14-field identity; 4096 cap; lock regenerated in the same commit).

## Self-Check: PASSED

- Files exist: encoder_spec.py, the 3 new test files, the changed encoders.py, pyproject.toml, uv.lock.
- Commits 17f8dea, ce93160, 9e5b557 exist in `git log`.
- No `story/`, `docs/research/` or `.gitkeep` file staged or committed.
