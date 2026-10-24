## 02.1-05
- Commits: 0c26db3, 208cce1, 2749c6a, 2ad904d.
- Full suite: 880 passed, 27 skipped, 45 subtests passed.
- Ruff: PASS. Mypy strict: PASS for model.py and verify.py.
- Focused model, verifier, and reader tests: 81 passed.
- Deviations: none. PairSide fields carry each pair's source links per TypedDict.
- UNVERIFIED: UI rendering and owner brand review remain for later plans.

## 02.1-06
- Commits: f5ffd76, 2d8e81e, 337bb04.
- Full suite: 936 passed, 27 skipped, 45 subtests passed.
- Asset tests: 56 passed; offline wheel check executed; book comparisons not skipped.
- Ruff: PASS. Mypy strict: PASS. mos-brand doctor: PASS.
- Deviations: four CLI-refused Theo files copied by the permitted byte-identical fallback.
- UNVERIFIED: exact bundled versions for ngraph.events, ngraph.graph, preact, and part of three; notices retained.

## 02.1-07
- Commits: cfa22c9, 77c6b17.
- Full suite: 979 passed, 27 skipped, 45 subtests passed.
- Fixture tests: 43 passed. Ruff: PASS. Mypy: not applicable to data and test-only changes.
- Real model: 36 records; 63 unusual pairs; 200 wording pairs; all five files byte-identical across two completed runs.
- Deviations: interrupted one slow multithread attempt; completed both runs with matching one-thread settings and no-sync offline environment.
- UNVERIFIED: Phase 4 fresh-checkout hashes and UI visuals. The real fixture has one neighborhood and zero bridges.
