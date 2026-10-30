---
phase: 01-release-gate-and-engine-parity
plan: 02
subsystem: engine-parity
status: complete
tags: [ENG-03, reproduction, jhtv, scratch-copy]
requires: []
provides:
  - docs/hsi-rs-jhtv-reproduction.md
affects: [phase-02-eureka-run]
key-files:
  created:
    - docs/hsi-rs-jhtv-reproduction.md
  modified: []
decisions:
  - "The unusual-pairs engine needs RS_MAX_ARTIFACTS of 2117 or more to reproduce the JHTV file; the script default of 2000 cuts the corpus."
metrics:
  tasks: 3
  completed: 2026-10-23
requirements: [ENG-03]
---

# Phase 1 Plan 02: Reproduction record for the JHTV pair results

One record gives the exact commands that made the JHTV pair files, and a rebuild on scratch copies matched both stored files.

## Result

- The wording-and-meaning pairs engine (catalog name "Rank Unusual Pairs by Wording and Meaning", formerly called HSI): `compute-hsi.py <room copy> --tier 1 --top-k 200` from `LATEST/engines/hsi/scripts`. Outcome: reproduced. PROVEN. `cache_params_hash` `7affae3c94c6bed9`, `pairs_scored` 2239786, 200 ordered pairs equal, score delta 0.0. Only timestamps, `room_dir` and `retrieved_at` differ.
- The unusual-pairs engine (catalog name "Find Unusual Pairs Across a Research Collection", formerly called RS): `rs-engine.py --mode internal --topk 200 --threshold 0.0 --no-thesis` with `RS_EMBEDDING_MODEL=minilm` and `RS_MAX_ARTIFACTS=3000`. Outcome: reproduced. PROVEN. 200 ordered pairs equal, score delta 0.0.
- Repo `.venv` python (newer numpy, scikit-learn, sentence-transformers) gave the same 200 ordered pairs and score delta 0.0 for the unusual-pairs engine. PROVEN.
- The JHTV room is unchanged. PROVEN. The sha256 of the six JHTV files were equal before and after, no file was newer than the snapshot marker, and the file count stayed 2117.

## Deviations from Plan

### Differences found against the research file

**1. [Finding] Default run of the unusual-pairs engine did not reproduce the stored file.**
- Found during: Task 2.
- Issue: the plan command has no cap setting. `rs-engine.py` keeps the first 2000 artifacts by default (`RS_MAX_ARTIFACTS`, default 2000). The corpus holds 2117. The run without the setting gave `artifact_count` 2000, overlap at 200 of 186/200, first differing rank 1, max `hybrid_signed_gap` delta 0.8983 on the 186 shared pairs.
- Fix: a second run with `RS_MAX_ARTIFACTS=3000` on a fresh scratch copy reproduced the stored file exactly. The record states both runs. The record marks as INFERRED that the original run set the cap.
- Files modified: docs/hsi-rs-jhtv-reproduction.md.
- Commit: 1517aa9.

**2. [Rule 3 - Blocking] The repo `.venv` has no `requests` module.**
- Issue: `rs-engine.py` imports `requests` at load time, so the cross-version run (Run C) failed with exit 1.
- Fix: a stub `requests` module in the scratch folder on `PYTHONPATH` for that one run. No package was installed. Internal mode makes no HTTP call. The record states the stub.

No other deviation. The plan was executed as written, with the extra run in item 1.

## Auth gates

None.

## Known Stubs

None. The only stub is the scratch `requests` module in the session scratchpad, which is not committed.

## Threat Flags

None. No new network surface, auth path or file access in the repo.

## Limits

- The flag set and the cap of the original run are INFERRED. The room holds no command text.
- The wording-and-meaning pairs engine was not run in the repo `.venv`. UNVERIFIED.
- The full-corpus overlap of the repo path (`eureka-pair-scout`) with the JHTV unusual-pairs file is not measured here. It stays for the parity record (plan 01-05). The 40-file figure 0.42 is unchanged.

## Commits

- 1517aa9: docs(01-02): record the JHTV pair-engine commands and their reproduction on a scratch copy

Scratch files (not committed): `/tmp/claude-1000/-home-jsagi/5a1774bc-a933-4bca-9f46-2d886586e3b1/scratchpad/eureka-phase1-eng03/`.

## Self-Check: PASSED

- docs/hsi-rs-jhtv-reproduction.md exists and holds the required strings (checked with the plan verify command, no missing string, no em-dash, original source author name absent).
- Commit 1517aa9 exists.
