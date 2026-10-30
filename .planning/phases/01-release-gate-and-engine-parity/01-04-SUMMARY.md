---
phase: 01-release-gate-and-engine-parity
plan: 04
status: complete
subsystem: engine
tags: [lsa, tie-break, parity, unusual-pairs-engine]
requirements: [ENG-01, ENG-02]
requires: ["01-03"]
provides:
  - Stable top-7 term order in structural_similarity (path C)
  - tests/fixtures/rs_parity/report_after_tie_break_fix.json
  - Pinned decisions: no negative-cosine clip in path C; top_k cap of 100 stays in Phase 1
affects: [01-05, 01-06, phase-2]
key-files:
  modified:
    - src/mindrian_eureka/opportunity_pairs/algorithm.py
    - tests/test_rs_engine_parity.py
  created:
    - tests/fixtures/rs_parity/report_after_tie_break_fix.json
commits:
  - 9e663ab fix(01-04): stable top-7 term order in the unusual-pairs engine LSA step
  - db51724 test(01-04): after-fix parity report and pinned clip and cap decisions
---

# Phase 1 Plan 04: Stable top-7 term order Summary

Path C (repo eureka-pair-scout) of "Find Unusual Pairs Across a Research Collection" now picks the top 7 terms of each LSA topic with a stable descending sort. Tied terms keep the lower term index first, as in the original `lsa.py`. The strict xfail on the tight LSA limit test is removed in the same commit. The tight limit (1e-6) now passes: max abs delta is 3.37e-08.

## Code change

`structural_similarity` in `algorithm.py`: `np.argsort(component)[-7:][::-1]` became `sorted(enumerate(component), key=..., reverse=True)[:7]`. Python's sort is stable, also with `reverse=True`, so equal values keep index order. Nothing else changed: no change to meta keys, dense path, `_bm25_cosine`, the ranker or `run_document`. Diff of `src/` is 4 lines (3 added, 1 removed).

## Before and after (live legs and real-model layer on, system python3, numpy 2.2.6, scikit-learn 1.8.0)

| Key | Before | After |
|-----|--------|-------|
| layer1 ranker max abs gap delta | 4.87e-05 | 4.87e-05 |
| layer2 BM25 max abs delta | 2.40e-07 | 2.40e-07 |
| layer2 LSA max abs delta | 1.064e-02 | 3.37e-08 |
| layer2 LSA Spearman | 0.99990 | 1.00000 |
| layer3 abs gap delta max | 2.06e-02 | 4.90e-05 |
| layer3 abs gap delta median | 3.81e-04 | 3.08e-05 |
| layer3 abs gap delta mean | 1.56e-03 | 2.82e-05 |
| layer3 rank Spearman | 0.99942 | 1.00000 |
| layer3 signed gap Spearman | 0.99981 | 1.00000 |
| layer3 overlap at 10, 20, full | 1.00 | 1.00 |
| layer3 sign agreement | 1.00 | 1.00 |
| layer3b overlap unclipped / clip injected | 0.86 / 1.00 | 0.86 / 1.00 |
| plugin legacy leg overlap at 10 / full | 0.70 / 0.51 | 0.70 / 0.51 |
| layer4 real model overlap at 10 / 20 / full | 0.60 / 0.70 / 0.74 | 0.60 / 0.70 / 0.74 |
| layer4 rank Spearman | 0.6209 | 0.6238 |
| layer4 signed gap Spearman | 0.8919 | 0.8938 |
| layer4 abs gap delta median | 0.2185 | 0.2192 |

Layer 1 and the BM25 matrix are unchanged, as expected. The plan expected layer 3 to stay unchanged. It changed: layer 3 runs path C end to end, so it uses the fixed LSA matrix. The gap to path B fell by about two orders of magnitude. This is a correct consequence of the fix, not a defect. The layer 3 limits (overlap 0.95, Spearman 0.99) still pass with a wider margin. Layer 4 moved in the third decimal; its gap to path B comes from the dense-input rule (owner decision, unchanged).

## Decisions recorded

- No negative-cosine clip in path C. The clip is a path B step. The canonical rule is the repo path. Recorded in the test module docstring and pinned by `test_clip_and_cap_decisions_are_documented` (the `layer3b_negative_cosine` note contains "known difference").
- `run_document` keeps `top_k` at most 100 in Phase 1. The same test pins that `top_k=101` raises `ValueError("top_k must be between 0 and 100")`. Phase 2 must lift the cap to 200 for the one-command run and must update this test.

## Provenance and version

`runner.py` carries `CAPABILITY_VERSION` and `method_version` strings. No test pins a value that the fix changes. No version was bumped. RISK for plans 01-05 and 01-06: the fix changes LSA values in tie cases. Ranked output can differ from earlier versions for corpora with exact term ties. The parity record must state this.

## Test results

- `PYTHONPATH=src pytest tests/test_rs_engine_parity.py tests/test_rs_hybrid_2026.py`: 19 passed (live legs and layer 4 on).
- Full suite: 171 passed, 25 skipped, 45 subtests passed, 0 xfailed. Before the plan: 169 passed, 1 xfailed.
- Existing tests: none pinned the old tie order. No expected value was edited.
- Live legs used the sha256-checked scripts: path B `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py`, path A `/home/jsagi/dev/MindrianOS-Plugin/scripts/rs-engine.py`, real model `sentence-transformers/all-MiniLM-L6-v2` (offline).

## Deviations from Plan

1. **[Expectation corrected] Layer 3 changed.** The plan said layer 3 stays unchanged within 1e-9. It improved, because it consumes the fixed LSA step. Table above. No code action needed.
2. **[Rule 3] Removed the now-unused `LSA_TIE_REASON` constant** from the test module, after the xfail mark was removed.

## Known Stubs

None.

## Threat Flags

None. T-01-17 to T-01-19 mitigated: change limited to the top-7 selection, before and after reports committed, tmp cache path in every test, no network, no package install.

## Notes for later plans

- Plan 01-05 and 01-06: read `report_after_tie_break_fix.json` for the final numbers. `baseline_report_pre_fix.json` is unchanged.
- Peer files were not touched. `story/` and `.planning/.mindrian/` were not staged. STATE.md and ROADMAP.md were not edited.

## Self-Check: PASSED

- Files exist: algorithm.py change, test module, after-fix report.
- Commits exist: 9e663ab, db51724.
