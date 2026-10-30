---
phase: 01-release-gate-and-engine-parity
plan: 03
status: complete
subsystem: testing
tags: [parity, unusual-pairs-engine, pytest, fixtures, golden-files]
requirements: [ENG-01]
requires: []
provides:
  - tests/test_rs_engine_parity.py (layered parity test and report contract)
  - tests/fixtures/rs_parity/ (synthetic corpus, seeded vectors, two golden files, pre-fix baseline report)
  - scripts/generate_rs_parity_golden.py (maintainer tool that regenerates the goldens)
affects: [01-04, 01-05, 01-06]
key-files:
  created:
    - scripts/generate_rs_parity_golden.py
    - tests/test_rs_engine_parity.py
    - tests/fixtures/rs_parity/corpus.json
    - tests/fixtures/rs_parity/reference_vectors.json
    - tests/fixtures/rs_parity/golden_reference.json
    - tests/fixtures/rs_parity/golden_plugin_legacy.json
    - tests/fixtures/rs_parity/baseline_report_pre_fix.json
  modified: []
commits:
  - 9d49f75 test(01-03): synthetic fixtures and golden generator
  - 88fe2bd test(01-03): layered parity test (layers 1-3, 3b, plugin legacy leg)
  - 23f36f1 test(01-03): live reference legs, real-model layer, pre-fix baseline report
---

# Phase 1 Plan 03: Parity test for the unusual-pairs engine Summary

A layered parity test compares the plugin scripts with the repo engine on one fixed synthetic input. The engine is "Find Unusual Pairs Across a Research Collection" (id opportunity.find_cross_domain_pairs, formerly called RS). The test prints rank overlap and score differences. It shows that the ranker is equal and that the whole difference comes from the inputs to the ranker.

Path ids: A = shipped plugin rs-engine.py (legacy scoring only, sha256 57c18df5...). B = LATEST reference rs-engine.py (sha256 044b9ae6...). C = repo eureka-pair-scout.

## Results (pre-fix baseline, system python3 with numpy 2.2.6 and scikit-learn 1.8.0)

| Layer | Result |
|-------|--------|
| 1 Ranker, same injected matrices | Same pair set, same order, max abs gap delta 4.9e-05 (limit 5e-3). PROVEN equal. |
| 2 BM25 matrix | max abs delta 2.4e-07 (limit 5e-4). |
| 2 LSA matrix | max abs delta 1.06e-02, Spearman 0.9999. Tight limit 1e-6 is a strict expected failure (top-7 term tie-break, plan 01-04). |
| 3 End to end, shared dense vectors | overlap at 10, 20 and full = 1.00; rank Spearman 0.9994; signed gap Spearman 0.9998; sign agreement 1.00; abs gap delta max 2.1e-02, median 3.8e-04, mean 1.6e-03. |
| 3b Negative cosine (signed case) | Path C does not crash. Overlap 0.86 without the clip, 1.00 with the clip injected. Reported as a KNOWN DIFFERENCE. |
| Plugin legacy leg (path A vs path C legacy) | overlap at 10 = 0.70, at full = 0.51, rank Spearman 0.776, abs score delta median 0.26. Report only. |
| 4 Real MiniLM (opt-in) | overlap at 10 = 0.60, at 20 = 0.70, at full = 0.74 (37 of 50 pairs shared), rank Spearman 0.62, signed gap Spearman 0.89, sign agreement 1.00, abs gap delta median 0.22. Report only. |

Cause of layer 4: path B embeds the body text once and truncates. Path C embeds title and body, chunks and averages. The owner decided the path C rule is canonical. Phase 1 does not change it.

The same fixed-fixture tests also pass with the repo venv libraries (numpy 2.5.4, scikit-learn 1.9.1): 9 passed, 3 skipped, 1 xfailed, same LSA delta 1.06e-02.

Full suite: 169 passed, 25 skipped, 1 xfailed, 45 subtests passed (32 s). `git status -- src` shows no change under src.

## What was built

- Fixtures: 32 synthetic documents (4 pseudo-word topic vocabularies, 8 per topic, each mixes two topics, 3 to 5 rare tokens each). Seeded float32 vectors of dimension 64 in two cases, `nonneg` and `signed`, with distinct stub model names. Total fixture size 224 KB. No JHTV text, no `technology/` id.
- Goldens: path B output and its LSA, BM25 and clipped dense matrices (8 decimals) for both cases; path A legacy output for the `nonneg` case. Headers hold the script sha256, library versions, corpus and vector sha256.
- Generator: refuses any script whose sha256 differs from the expected hash (verified: a wrong path exits 1 before any run). Uses a temp room outside the repo, no room.db, offline env vars. Running it twice gives byte-identical corpus and vector files.
- Test module: report contract in `build_parity_report()`; printed with `capsys.disabled()`; JSON written when `EUREKA_PARITY_REPORT_PATH` is set. Opt-in live legs run path B and path A as subprocesses after a sha256 check (verified: wrong script fails with the sha256 message). Layer 4 runs only with `EUREKA_RS_PARITY_REAL_MODEL` and `EUREKA_RS_REFERENCE_SCRIPT`.
- Baseline: `baseline_report_pre_fix.json` was taken with the live legs and layer 4 enabled, before any change under src.

## Deviations from Plan

1. **[Rule 1 - Bug] Reference room title and body.** The reference script keeps a leading `# heading` inside the body and reads the title from it, so a first fixture run missed its embedding cache (hash mismatch) and fell back to the real model. Both cases then gave the same pairs. Fix: the generator writes each room file as body text only; the title comes from the file stem, so corpus titles are `Syn 001` to `Syn 032` (not "Synthetic record NNN"). Fixtures regenerated before the first commit.
2. **[Plan contingency applied] Tie-break exposure.** The first fixture gave an LSA delta of 3e-8, so the strict xfail would have been unusable. Cause: tied rare tokens of one document change the topic-term set but not the membership count when all of them match. Fix: every third rare token is written with a capital letter. TF-IDF folds case (columns stay tied) while the raw-token membership count does not match it. The LSA delta is now 1.06e-02. A first try with every second token gave a layer 3 rank Spearman of 0.988 (below the 0.99 limit), so the milder every-third rule was chosen. This is a synthetic fixture choice, stated here for honesty.
3. **Fixture commit.** The regenerated fixtures were committed together with the test module (second commit) because they changed after the first commit.

## Known Stubs

None.

## Threat Flags

None. Threat register items T-01-11 to T-01-16 are mitigated as planned: synthetic fixtures only, sha256 check before any run, tmp cache path and distinct stub model name in every test, offline env vars, temp room outside the repo, no vendored reference file (`find tests -name rs_math.py -o -name rs-engine.py -o -name lsa.py` returns nothing).

## Notes for later plans

- Plan 01-04: remove the `xfail(strict=True)` on `test_layer2_lsa_matrix_tight_limit` after the stable top-7 tie-break fix. The strict xfail will report XPASS (failure) until the marker is removed. Re-run with `EUREKA_PARITY_REPORT_PATH` to produce a post-fix report.
- Plans 01-05 and 01-06 read `baseline_report_pre_fix.json`. Keys: paths, libraries, layers (layer1_ranker, layer2_bm25, layer2_lsa, layer3_end_to_end, layer3b_negative_cosine, plugin_legacy_leg, layer4_real_model), verdict.
- Test run needs `PYTHONPATH=src pytest`. No pytest dev group was added.

## Self-Check: PASSED

- Files exist: generator, test module, 4 fixtures, baseline report.
- Commits exist: 9d49f75, 88fe2bd, 23f36f1.
