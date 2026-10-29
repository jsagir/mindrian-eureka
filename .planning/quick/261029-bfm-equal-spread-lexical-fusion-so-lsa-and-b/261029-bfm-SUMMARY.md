---
quick: 261029-bfm
status: complete
implementation_commit: b405fe7
---

# Equal-spread lexical fusion so LSA and BM25 each hold half the vote

Defect: the hybrid lexical leg was the raw average `0.5 * (lsa + bm25)`. Both legs are cosines in [0, 1], but their spreads differ per corpus. On the hub corpus (36 docs, 630 pairs) LSA std is 0.0505 and BM25 std is 0.0242 (ratio 2.09x); the raw average gave the hybrid variance share 51% to LSA and 12% to BM25, so the leg with the larger spread took the vote (PROVEN by the planner probe).
Rule: `hsi_reference.fuse_lexical_hybrid(lsa, bm25)` standardises each leg over the pairs (upper triangle, k=1), averages the 2 z-scores, maps back to the pooled mean and pooled spread, clips to [0, 1], keeps symmetry, sets the diagonal to 1.0. Guard: fewer than 3 pairs or a leg spread below 1e-12 returns the raw average unchanged (that guard line, `raw = 0.5 * (lsa + bm25)` at hsi_reference.py:353, is the only `= 0.5 * (lsa` match left in `src/`; the pasted reference helper needs it).
Call sites: `hsi_engine.run_hsi` (hybrid branch), `hsi_reference.main`, `run/engines.run_wording_and_meaning`. The `lsa` and `bm25` single-leg modes and the degraded `lexical-only-bm25-proxy` branch are unchanged.
Provenance: key `lexical_fusion` (`equal_spread_average` for hybrid, `none` otherwise) in `engines.wording_params`, the CLI params dict, and `run_hsi` metadata. `RECORDED_PARAMS_HASH` moved from 7affae3c94c6bed9 to bea4c100c2013300 because the settings dict gained the key; `wording_params_hash(200)` prints bea4c100c2013300, top_k 20 prefix 9412dcb5, top_k 100 prefix 9d8cd3b4. The frozen hub manifest keeps 7affae3c94c6bed9 as the record of that run.
RED: `tests/test_lexical_fusion.py` 1 error at collection (`ImportError: cannot import name 'fuse_lexical_hybrid'`); `tests/test_run_engines.py -k "params_hash or recorded_settings or call_order"` 4 failed, 29 deselected. GREEN: new module 8 passed; both files together 41 passed.
Targeted set (7 files): 131 passed, 3 skipped. Parity verdict line: `bm25 max abs delta 2.4e-07, lsa max abs delta 3.4e-08` (unchanged).
Full suite `tests/`: 1298 passed, 6 skipped, 45 subtests passed, 1 failed in 478 s; the 1 failure is the pre-existing `tests/test_hub_assets.py::test_book_source_is_byte_identical[tokens.css-...]` case, not touched here.
Lint: ruff `src tests` 1466 errors (baseline 1467; hsi_engine.py 14 of 15, hsi_reference.py 55 of 55, run/engines.py and both test files `All checks passed!`); mypy `src` 88 errors in 17 files (baseline 88, pre-existing).
Honest labels: `candidate, not verified` count in `src/` is 4 before and after; 0 occurrences in the source diff.
No file under `tests/fixtures/` changed (`git status --short tests/fixtures/` prints 0 lines). Nothing from `story/` staged. Nothing pushed. Implementation commit b405fe7 (5 files: 3 sources, 2 tests).
