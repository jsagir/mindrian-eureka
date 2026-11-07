---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 08
subsystem: encoder-spike
tags: [gpu-spike, nemotron, spike-script, results-page, owner-run]
status: PARTIAL (checkpoint pending: waiting for the owner-run)

requires:
  - phase: 05-01
    provides: PROFILES["gpu-nemotron"], EncoderSpec
  - phase: 05-05
    provides: manifest key encoder, RunRequest.encoder_profile
provides:
  - "scripts/encoder-spike.py: self-contained spike script (dry run, log, vectors files, page renderer)"
  - "docs/encoder-spike-results.md: results page, every value NOT RUN"
  - "tests that tie the page, the profile revision pin and the overlap threshold to a log file"
affects: [05-07, 05-09]

tech-stack:
  added: []
  patterns: ["a page table that only the script can fill from a log", "fake backend with sentinel values for GPU code"]

key-files:
  created:
    - scripts/encoder-spike.py
    - docs/encoder-spike-results.md
    - tests/test_encoder_spike_script.py
    - tests/test_encoder_spike_record.py
  modified: []

key-decisions:
  - "render-doc also sets the front matter status line (not_run or recorded) from the log, so the owner has no manual edit to forget."
  - "Handle attributes load_seconds and native_max_seq_length carry the load time and the model window; no extra backend method."
  - "The script encodes each text in one model call, no chunking. The page says the CPU vectors for the MiniLM drift run must follow the same rule."

requirements-completed: []

duration: about 40min
completed: 2026-11-08
---

# Phase 5 Plan 08: GPU spike preparation Summary

STATUS: PARTIAL. Tasks 1 and 2 are done. Task 3 (owner-run on the RTX 3060 computer) is a human checkpoint and has NOT run. No GPU number exists in any file.

## What was built

A self-contained script `scripts/encoder-spike.py`, a results page `docs/encoder-spike-results.md` with every value `NOT RUN`, and two test files. The script imports only the standard library at module level, imports nothing from the Eureka package, passes `trust_remote_code=False` and never `True`, and refuses an output folder inside the repository. The page table is rendered from the log by `--render-doc`. Tests make an invented number impossible: with no log file the page must show `NOT RUN` in every value cell, the profile revision may be set only when the log holds the same revision, and the overlap threshold may be set only when the log exists.

## Task commits

| Task | Commit | Subject |
| ---- | ------ | ------- |
| 1 (RED) | 1662acb | test(05-08): add failing tests for the GPU spike script and its results page |
| 2 (GREEN) | 36f9ed7 | feat(05-08): add the self-contained GPU spike script and its results page (all values NOT RUN) |
| 3 | none | human checkpoint, not run |

## RED output (Task 1)

Before the script and the page existed: `4 failed, 24 errors in 0.35s`. The tests failed with FileNotFoundError on the script path. Test counts: 20 test functions in `tests/test_encoder_spike_script.py`, 5 in `tests/test_encoder_spike_record.py`.

## GREEN counts (Task 2)

- `tests/test_encoder_spike_script.py` and `tests/test_encoder_spike_record.py`: 28 passed (parametrized cases included).
- Pinning set plus both new files: `186 passed, 1 skipped`.
  The set: test_hub_assets, test_partner_bundle, test_readme_commands, test_public_example, test_example_check, test_release_gate_record, test_room_seed_docs, test_host_handoff_docs.
- `ruff check scripts/encoder-spike.py` and the two test files: All checks passed. No file in `src` changed, so the ruff and mypy baselines (1452 and 87 errors) did not move.
- `pyproject.toml` and `uv.lock` are not touched.

## Dry-run result

`python3 -I scripts/encoder-spike.py --dry-run --out-dir <scratch outside the repository>` exited 0, printed 8 planned steps, and wrote `gpu-spike-log.json` with `"status": "not_run"` and no number. `--help` works with the standard library only. No output file appeared inside the repository (`docs/encoder-evidence/` does not exist).

## READY and NOT RUN

| Item | State |
| ---- | ----- |
| Script, tested on a fake backend (success, remote code, out of memory, no CUDA, attention fallback, prefix check, drift run, render, download flag) | READY |
| Results page with markers, six headings, How to run | READY |
| Record tests (page follows the log, profile pin, threshold, style, no claim without a log) | READY |
| Run on the RTX 3060 computer | NOT RUN |
| `docs/encoder-evidence/gpu-spike-log.json` | NOT RUN (does not exist) |
| `docs/encoder-evidence/nemotron-bf16-vectors.npz` | NOT RUN (does not exist) |
| Nemotron column of the comparison page (plan 05-07 harness) | NOT RUN |

## UNVERIFIED

Every row of the results table is `NOT RUN`. The log fields are:

- environment.python, environment.platform, environment.torch, environment.transformers, environment.sentence_transformers, environment.numpy
- environment.cuda_available, environment.cuda_runtime, environment.driver, environment.gpu_name, environment.gpu_memory_bytes
- model.id, model.revision, model.file_count, model.total_bytes, model.sharded_weights, model.error
- load.bf16.ok, load.bf16.seconds, load.bf16.attention_used, load.bf16.error, load.needs_remote_code
- load.fp32.ok, load.fp32.seconds, load.fp32.error
- embedding.dimension, embedding.max_seq_length, embedding.prompts, embedding.query_prefix_confirmed, embedding.document_prefix_confirmed
- texts.count, texts.max_tokens
- speed.bf16.texts_per_second, speed.fp32.texts_per_second
- memory.bf16.peak_allocated_bytes, memory.fp32.peak_allocated_bytes
- drift.bf16_vs_fp32.top200_overlap, drift.minilm_gpu_vs_cpu.top200_overlap

Also UNVERIFIED: the real backend (`RealBackend`) has not run on any computer. It was only read and linted. Whether the Hugging Face repository is gated, the real prefix strings, the revision, and the need for remote code are open until the owner-run. The model-card facts in the plan stay UNVERIFIED.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Extra log rows and fields for errors**
- **Found during:** Task 2
- **Issue:** The plan list of `LOG_FIELDS` had no place for a snapshot failure. A failed download would leave no reason in the table.
- **Fix:** Added the row `model.error` to `LOG_FIELDS`; an error cell shows `none` when the matching step succeeded, else `NOT RUN`. Added `model.files` (file list) and `drift.minilm_gpu_vs_cpu.error` to the log skeleton (not in the table).
- **Commit:** 36f9ed7

**2. [Rule 2 - Missing critical functionality] render-doc sets the front matter status**
- **Found during:** Task 2
- **Issue:** The plan left the status line `status: recorded` to a manual edit. A forgotten edit would leave a page that says `not_run` next to a real log.
- **Fix:** `--render-doc` sets the line from the log (`not_run` when the log status is `not_run`, else `recorded`). `test_page_state_follows_the_log` checks the same rule.
- **Commit:** 36f9ed7

**3. [Rule 3 - Blocking] Repository detection for the out-dir rule**
- **Found during:** Task 2
- **Issue:** A fixed parent-of-scripts folder would refuse the output folder when the owner copies the script to another place (for example the home folder).
- **Fix:** The script looks upward from its own folder for `.git` or `examples/public-example`; with none found it applies no repository check.
- **Commit:** 36f9ed7

No other deviation. Peer plan 05-06 files were not touched. No test of the pinning set failed.

## Known Stubs

None. The `NOT RUN` cells are intended and are the plan result until the owner-run.

## Threat Flags

None. No new network path: the real backend downloads only when `--allow-download` is given, and only on the owner computer. No remote code. No package installs ran in this repository.

## Risks for the owner-run

- MiniLM drift run: the script encodes each text in one model call without chunking. If the CPU vectors file of plan 05-07 was made with the token-window chunk rule, the overlap would measure the chunk rule and not the GPU. Plan 05-07 must state its rule. The page says this.
- Peak memory with window 4096 and batch 16 on 12 GB is unknown. An out-of-memory error in the second run is recorded and does not erase the first run.
- Package names (torch, transformers, sentence-transformers, numpy, huggingface-hub) are ASSUMED legitimate. The owner checks each on pypi.org first (page, How to run, step 1).

## Next step (resume, only after the owner returns `gpu-spike-log.json`)

Put the log and `nemotron-bf16-vectors.npz` into `docs/encoder-evidence/`. Run `python3 scripts/encoder-spike.py --render-doc docs/encoder-spike-results.md --log docs/encoder-evidence/gpu-spike-log.json`. Run the plan 05-07 harness with `--vectors-in nemotron=...`. Run the two record tests. The pin of the revision, the prefix strings and the threshold stay owner decisions for a follow-up quick task. Do not edit `encoder_spec.py` or `example/contracts.py` in the resumed run.

## Self-Check: PASSED

- scripts/encoder-spike.py: FOUND
- docs/encoder-spike-results.md: FOUND
- tests/test_encoder_spike_script.py: FOUND
- tests/test_encoder_spike_record.py: FOUND
- Commits 1662acb and 36f9ed7: FOUND in git log
- No GPU number in any file: grep of the page shows only `NOT RUN` cells.
