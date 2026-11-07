---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 07
subsystem: encoder-comparison
tags: [encoder-compare, minilm, mdbr-leaf-ir, nemotron, dense-top-200, evidence-log]
status: DONE (CPU part); Nemotron column awaits the owner run

requires:
  - phase: 05-01
    provides: EncoderSpec, profile_spec, custom_spec, make_encoder
  - phase: 05-04
    provides: example.check.ranking_overlap
  - phase: 05-08
    provides: scripts/encoder-spike.py and docs/encoder-spike-results.md (encoding rule, npz layout)
provides:
  - "scripts/encoder-compare.py: comparison harness (dense top-200 overlap, timings, vectors in and out, table render, update mode)"
  - "docs/encoder-evidence/cpu-compare-log.json: log of the CPU run (schema eureka.encoder-compare-log.v1)"
  - "docs/encoder-evidence/minilm-cpu-vectors.npz: MiniLM vectors, one call per text, for the spike drift run"
  - "docs/encoder-comparison.md: page with a table rendered from the log"
affects: [05-09]

key-files:
  created:
    - scripts/encoder-compare.py
    - tests/test_encoder_compare.py
    - docs/encoder-comparison.md
    - docs/encoder-evidence/cpu-compare-log.json
    - docs/encoder-evidence/minilm-cpu-vectors.npz
  modified: []

key-decisions:
  - "The MiniLM vectors use the encoding rule of scripts/encoder-spike.py: one model call for all texts, no token-window chunking, unit rows in float32. The rule is stored in the npz (encoding_rule) and in the log."
  - "Update mode (--update-log, --vectors-in) adds the Nemotron file to the CPU log without loading a model, so the MiniLM timings stay from this computer. It writes docs/encoder-evidence/compare-log.json; the record tests then follow that file."
  - "The default run and every shipped file are unchanged. No source file, pyproject.toml or uv.lock changed."

requirements-completed: []

duration: about 45min
completed: 2026-11-08
---

# Phase 5 Plan 07: Encoder comparison harness Summary

STATUS: DONE for the CPU part. MiniLM measured on 36 records. The `mdbr-leaf-ir` column and the Nemotron column are NOT RUN, each with its reason in the log. The Nemotron column needs the owner-run spike (plan 05-08).

## Commits

| Step | Commit | Subject |
| ---- | ------ | ------- |
| Task 1 (RED) | a693438 | test(05-07): add failing tests for the encoder comparison harness and its page |
| Test fix | 3c0065a | test(05-07): fix the label scan, follow the merged log, add the update-log test |
| Task 2 (GREEN) | 6dcbe24 | feat(05-07): add the encoder comparison harness, the CPU run log and the comparison page (4 files) |
| Summary | see git log | docs(05-07): record the encoder comparison plan |

## RED output

Before the script, the page and the evidence existed: `4 failed, 12 errors in 0.23s` (16 tests; FileNotFoundError on the script path, the page and the log). Ruff on the test file: All checks passed.

## GREEN counts

- `tests/test_encoder_compare.py`: 17 passed, 0 skipped (the real MiniLM reproduction test ran).
- Pinning set (hub_assets, partner_bundle, readme_commands, public_example, example_check, release_gate_record, room_seed_docs, host_handoff_docs) plus compare, spike script and spike record tests: 203 passed, 1 skipped (the skip is old).
- With the locked-environment command (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder`): compare, partner_bundle, hub_assets: 98 passed, 1 skipped.
- `tests/test_hub_public_fixture.py` and `tests/test_run_scaffold.py`: 57 passed.
- `eureka check-example examples/public-example/reference-run`: Result: MATCH.
- `ruff check scripts/encoder-compare.py tests/test_encoder_compare.py`: All checks passed. No file in `src` changed, so the ruff (1452) and mypy (87) counts did not move. `pyproject.toml` and `uv.lock` are untouched.
- `docs/encoder-evidence/*` are not git-ignored (`git check-ignore -v` printed nothing).

## Encoding rule and npz layout (coordination with plan 05-08)

The spike script encodes each text in one model call with no chunking, and reads `ids` and `vectors` from the CPU npz. The harness uses `encoder.encode_raw` (the existing one-call method) and then normalizes rows to length 1 in float32, which is what `normalize_embeddings=True` gives. The npz holds `ids` (36 strings, record order), `vectors` (36 by 384, float32), `fingerprint` and `encoding_rule` (strings). The spike script was not edited.

`test_npz_layout_agrees_with_the_spike_script` runs the spike script's own `run_minilm_drift` with a fake backend on the saved file: the ids, the model texts and the pair keys equal those of the spike script, the overlap is 1.0, no error. The batch size differs (the encoder default 32 here, 16 in the spike); this changes padding only and is UNVERIFIED as to the last decimals.

Important side fact: the longest text is 328 tokens and the MiniLM window is 256, so the one-call rule truncates at least one text. The chunked rule of `eureka run` would split it. Both numbers are in the table.

## Log summary (docs/encoder-evidence/cpu-compare-log.json)

Run on 2026-11-08, aarch64 Linux, 12 cores, 1 torch thread, `nice -n 19`.

| Field | Value |
| ----- | ----- |
| MiniLM status | run |
| Vector width | 384 |
| Load seconds | 2.24 |
| Encode seconds, 3 repeats | 1.109, 1.165, 1.350 |
| Texts per second (median) | 30.90 |
| Load average before / after (1, 5, 15 min) | [0.52, 0.64, 1.32] / [0.52, 0.64, 1.32] |
| Fingerprint | sha256:d7a078069ffe764f154b572c7a870f89f7bdeceba6f3b19a6a86a88c32b5bebd |
| Dense top-200 overlap, MiniLM with MiniLM | 1.0000 (trivial) |

The machine load was low during the run (uptime showed 0.47 to 0.56 before and after). The two equal load samples come from the kernel one-minute window, which updates slowly; the timings stay indicative.

## NOT RUN columns

- `mdbr-leaf-ir`: re-checked on 2026-11-08. The folder `~/.mindrian/model-cache/MongoDB/mdbr-leaf-ir` still holds `config.json`, `tokenizer.json`, `tokenizer_config.json` and `onnx/model_quantized.onnx` plus its data file. No `modules.json`, no safetensors file. Probe result: cannot load as a sentence-transformers folder; ONNX files only. onnxruntime was not added and the ONNX file was not opened.
- Nemotron: the model needs a GPU computer; this session cannot reach one. The owner-run spike of plan 05-08 produces `nemotron-bf16-vectors.npz`.

## Update path for the owner (no model needed)

`python3 scripts/encoder-compare.py --update-log docs/encoder-evidence/cpu-compare-log.json --vectors-in nemotron=docs/encoder-evidence/nemotron-bf16-vectors.npz --out docs/encoder-evidence/compare-log.json --render-page docs/encoder-comparison.md`

This keeps the MiniLM timings of this run, fills the Nemotron column from the file (ids checked in order, `allow_pickle=False`) and renders the page. A smoke run with a random 16-wide file (kept outside the repository) gave status `from_file` and a MiniLM-to-Nemotron overlap of 0.32; that number is a test artifact, not a result, and is in no repository file.

## Deviations from Plan

**1. [Rule 2 - Missing functionality] Update mode**
- **Found during:** Task 2
- **Issue:** The plan's next-step command (`--vectors-in nemotron=... --render-page`) would load MiniLM again and replace the CPU timings by timings from the owner computer.
- **Fix:** Added `--update-log`, `--minilm-vectors` and the function `update_log`, with a test. The page next step names this command.
- **Commit:** 6dcbe24

**2. [Rule 1 - Test bug] Label scan in the number test**
- **Found during:** Task 2
- **Issue:** The test that scans table cells for unlogged numbers also scanned the Measure label cell (digits in "top-200", "Nemotron-3").
- **Fix:** The scan skips the label cell; the page and log tests follow `compare-log.json` once it exists. Row label shortened to "Nemotron". No assertion was weakened: the value cells are still scanned.
- **Commit:** 3c0065a

**3. [Scope note] Extra options**
- `--threads` (requested by the orchestrator) and 4 extra tests (update mode, engine overlap, npz-spike agreement, import weight). The table has two extra rows (longest text, model window) to expose the truncation fact from the log.

## UNVERIFIED

- Nemotron column: no number exists.
- `mdbr-leaf-ir` column: no number exists.
- Timings under load: single run, one thread, kernel load about 0.5.
- Engine-level overlap (`--engine-run`): needs an owner-run `eureka run`; the log field is null. Only the function is tested (reference against itself gives 1.0).
- Real GPU vectors against the CPU npz in the spike drift run: the layout is tested with a fake backend only.
- Whether the batch-size difference (32 against 16) moves any decimal in the drift run.

## Known Stubs

None. NOT RUN cells are intended.

## Threat Flags

None. No network call, no install, no remote code. The log holds no path, host name or user name (tested).

## Self-Check: PASSED

- scripts/encoder-compare.py, tests/test_encoder_compare.py, docs/encoder-comparison.md, docs/encoder-evidence/cpu-compare-log.json, docs/encoder-evidence/minilm-cpu-vectors.npz: FOUND
- Commits a693438, 3c0065a, 6dcbe24: FOUND in git log
- Nothing under story/ staged or committed.
