---
record: rs-engine-parity
version: 1
canonical_rs_path: eureka-pair-scout (scoring hybrid_2026)
decided_by: Jonathan Sagir (owner)
decided_on: 2026-10-23
status: decided
evidence_report: tests/fixtures/rs_parity/baseline_report_pre_fix.json
---

# Canonical path for the unusual-pairs engine, and the parity result

This record covers "Find Unusual Pairs Across a Research Collection" (id `opportunity.find_cross_domain_pairs`, formerly called RS). The engine finds pairs of documents whose meaning is close and whose vocabulary structure is far apart, or the reverse. Below it is called "the unusual-pairs engine". The related engine "Rank Unusual Pairs by Wording and Meaning" (id `portfolio.find_hybrid_similarity_pairs`, formerly called HSI) is called "the wording-and-meaning pairs engine". File names, ids and code symbols keep their literal names.

Each claim is marked PROVEN (seen in a file or a run), INFERRED (reasoned from PROVEN facts) or UNVERIFIED (not run). All results are candidates, not verified. They are leads for human review.

## 1. Decision

The command `eureka-pair-scout` with scoring `hybrid_2026` (path C) is the canonical path for new runs of the unusual-pairs engine. The owner decided this on 2026-10-23.

Reasons:

1. Its ranker equals the reference ranker. Layer 1 of the parity test shows the same pair set and the same order when both rankers get the same input matrices (PROVEN, section 3).
2. It takes stable JSON ids and has a schema, a cache, jobs and an MCP surface.
3. Path A (the shipped plugin `scripts/rs-engine.py`) is legacy-only. It has no hybrid scoring and cannot be the reference for hybrid scoring.
4. Path B (the reference script outside this repo) has an unresolved distribution status and writes into rooms.

The owner also locked the dense rule: path C embeds title plus body, split in chunks, and averages the chunk vectors. The difference to path B is recorded as evidence in section 4. It is not a defect to fix by matching path B.

Fidelity of the unusual-pairs engine: not verified bit-for-bit against the original package. The repo path ranks with the same logic as the reference script but uses a different dense-input rule (section 3.1 and section 4).

## 2. The three code paths

| Id | Path | sha256 | Scoring | Dense signal | Notes |
|----|------|--------|---------|--------------|-------|
| A | Shipped plugin `scripts/rs-engine.py` (same bytes in beta.59, beta.69 and beta.73) | `57c18df558d83fbffc8e9f7fda905729d0c0fbfe18a1c370b1db816efa3937f1` | Legacy only: `abs(semantic - lsa)` with a fixed threshold. No `--scoring` flag, no BM25. | MiniLM on body text | Cannot make the JHTV file. |
| B | LATEST `engines/rs/shared/scripts/rs-engine.py` (parked copy in the plugin repo under `r-and-d/breakthrough-engines/`) | `044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45` | `hybrid` (default): z-score gap of dense against 0.5 LSA plus 0.5 BM25, percentile gate 0.90 | MiniLM, body text only, one pass, truncated at the model limit, negative cosine clipped to 0 | Made the JHTV pair file. Not vendored here. |
| C | `src/mindrian_eureka/opportunity_pairs/` (repo HEAD `ee5f370` at writing time) | not applicable (repo code) | `hybrid_2026` (default) or `legacy` | MiniLM or BERT through `SentenceTransformerEncoder`: title plus body, chunked, chunk vectors averaged, no clip | Canonical for new runs. |

Warning: the installed plugin copy of `rs-engine.py` looks right and is wrong for hybrid scoring. Check the sha256 before you trust a script. All values in this table are PROVEN, except that path C has no sha256 by design.

## 3. Parity result

How to read it. Layer 1 is the ranker. Layers 2 and 3 are the inputs to the ranker. The test keeps the layers apart so that a difference shows its cause. A low end-to-end overlap with equal layer 1 means the inputs differ, not the ranker.

These numbers come from the code state BEFORE the tie-break fix of plan 01-04. They are read from `tests/fixtures/rs_parity/baseline_report_pre_fix.json` and written with Python format `.4g`. The after-fix numbers are in section 3.1. The input is a synthetic corpus of 32 documents with seeded dense vectors (PROVEN, system `python3` with numpy 2.2.6 and scikit-learn 1.8.0).

| Metric | Value | Meaning |
|--------|-------|---------|
| `layers.layer1_ranker.max_abs_gap_delta` | 4.865e-05 | Ranker only, same matrices: same pair set, same order, largest gap difference. |
| `layers.layer2_bm25.max_abs_delta` | 2.4e-07 | BM25 matrix, largest difference to path B. |
| `layers.layer2_lsa.max_abs_delta` | 0.01064 | LSA matrix, largest difference to path B. Cause: top-7 term tie order (section 7). |
| `layers.layer2_lsa.spearman` | 0.9999 | Rank agreement of the LSA values. |
| `layers.layer3_end_to_end.overlap_at_10` | 1 | Shared pairs in the top 10, end to end with shared dense vectors. |
| `layers.layer3_end_to_end.overlap_at_20` | 1 | Same, top 20. |
| `layers.layer3_end_to_end.overlap_at_full` | 1 | Same, all 50 pairs. |
| `layers.layer3_end_to_end.spearman_rank` | 0.9994 | Rank agreement on the shared pairs. |
| `layers.layer3_end_to_end.sign_agreement` | 1 | The direction label of the gap never flips. |
| `layers.plugin_legacy_leg.overlap_at_full` | 0.51 | Path A against path C in legacy scoring. Report only. |
| `layers.layer4_real_model.overlap_at_10` | 0.6 | Real MiniLM on the synthetic corpus, top 10. Report only. |
| `layers.layer4_real_model.overlap_at_20` | 0.7 | Same, top 20. |
| `layers.layer4_real_model.overlap_at_full` | 0.74 | Same, all pairs (37 of 50 shared). |
| `layers.layer4_real_model.spearman_rank` | 0.6209 | Rank agreement on the 37 shared pairs. |
| `layers.layer4_real_model.spearman_signed_gap` | 0.8919 | Agreement of the signed gap. |
| `layers.layer4_real_model.sign_agreement` | 1 | Direction label agrees. |

Verdict line from the report: ranker equal; bm25 max abs delta 2.4e-07, lsa max abs delta 1.1e-02; end to end overlap 1.00 with shared dense vectors; dense input differs on real models (see layer 4).

The negative-cosine case (layer 3b) is a known difference. With negative cosines in the fixture, the overlap without a clip is 0.86 and with the clip injected it is 1.00 (PROVEN, in the same report).

### 3.1 After the tie-break fix

These numbers come from the code state AFTER the tie-break fix of plan 01-04. They are read from `tests/fixtures/rs_parity/report_after_tie_break_fix.json` and written with Python format `.4g`. The input, the machine and the libraries are the same as in the table above (PROVEN). Only the rows that moved are explained here. A test checks every value against the report file.

| Metric | Value | Meaning |
|--------|-------|---------|
| `layers.layer1_ranker.max_abs_gap_delta` | 4.865e-05 | Ranker only, same matrices: same pair set, same order, largest gap difference. |
| `layers.layer2_bm25.max_abs_delta` | 2.4e-07 | BM25 matrix, largest difference to path B. |
| `layers.layer2_lsa.max_abs_delta` | 3.371e-08 | LSA matrix, largest difference to path B. Fell from 0.01064 to this value after the tie-break fix. |
| `layers.layer2_lsa.spearman` | 1 | Rank agreement of the LSA values. |
| `layers.layer3_end_to_end.overlap_at_10` | 1 | Shared pairs in the top 10, end to end with shared dense vectors. |
| `layers.layer3_end_to_end.overlap_at_20` | 1 | Same, top 20. |
| `layers.layer3_end_to_end.overlap_at_full` | 1 | Same, all 50 pairs. |
| `layers.layer3_end_to_end.spearman_rank` | 1 | Rank agreement on the shared pairs. |
| `layers.layer3_end_to_end.sign_agreement` | 1 | The direction label of the gap never flips. |
| `layers.plugin_legacy_leg.overlap_at_full` | 0.51 | Path A against path C in legacy scoring. Report only. |
| `layers.layer4_real_model.overlap_at_10` | 0.6 | Real MiniLM on the synthetic corpus, top 10. Report only. |
| `layers.layer4_real_model.overlap_at_20` | 0.7 | Same, top 20. |
| `layers.layer4_real_model.overlap_at_full` | 0.74 | Same, all pairs (37 of 50 shared). |
| `layers.layer4_real_model.spearman_rank` | 0.6238 | Rank agreement on the 37 shared pairs. |
| `layers.layer4_real_model.spearman_signed_gap` | 0.8938 | Agreement of the signed gap. |
| `layers.layer4_real_model.sign_agreement` | 1 | Direction label agrees. |

What changed. The LSA difference to path B fell from 0.01064 to 3.371e-08, below the tight limit of 1e-6. The end-to-end rank agreement with shared dense vectors rose from 0.9994 to 1, because layer 3 uses the fixed LSA step. Layer 1, the BM25 matrix and the negative-cosine case did not change. Layer 4 moved in the third decimal (rank agreement 0.6209 before, 0.6238 after).

Read the real-model rows with care. The repo path ranks with the same logic as the reference script, but it builds the dense input by a different rule (title plus body, chunk-mean, against body only, truncated). On the real model it does not reproduce the reference ranking at the meaning-signal level: overlap 0.74 over the full list, rank correlation 0.6238 on these fixtures, and 0.423 on the 40-file JHTV smoke (section 4). The tie-break fix did not close this gap, and it was not meant to. The owner decision keeps the repo rule canonical. Fidelity to the original method is not verified bit-for-bit.

Output change from the fix. The fix changes LSA values in tie cases. For a corpus with exact term ties, the ranked output can differ from output made before 2026-10-23.

Verdict line from the report: ranker equal; bm25 max abs delta 2.4e-07, lsa max abs delta 3.4e-08; end to end overlap 1.00 with shared dense vectors; dense input differs on real models (see layer 4).

## 4. JHTV smoke figures (not reproducible from the repo)

Label: measured 2026-10-23 on 40 files sampled from the JHTV catalog (every 53rd file of `technology/`); scratch scripts; real text, so not committed; full-corpus overlap UNVERIFIED. Only aggregate numbers appear here. The measurements are PROVEN as measured on those 40 files.

- Path B and path C on the same 40 files, real MiniLM: both gave 78 pairs. Overlap at 78 is 0.423, at 10 is 0.30, at 20 is 0.45, at 50 is 0.42.
- On the 33 shared pairs: Spearman of the signed gap 0.85, rank Spearman 0.65, sign agreement 0.97, median absolute gap difference 0.23, maximum 3.88.
- Attribution run: with the LSA matrix and the dense matrix of path B, the path C ranker gives overlap 1.000. The ranker is equal.
- With the dense matrix of path C, the overlap is 0.423. The dense cosines have Spearman 0.805 and a maximum absolute difference of 0.463.
- LSA matrices: Spearman 0.9987, maximum absolute difference 0.0227 before the tie-break fix, 2.8e-8 after it (measured in a patched in-memory copy).
- A shared hashing stub for both paths gives set overlap 1.00 and rank Spearman 0.9998.

In plain words: the difference comes from how the dense signal is built, not from the ranker. Path B embeds the body only and truncates it. Path C embeds title plus body, chunks it and averages the chunks. Per the owner decision this is evidence and is not fixed by matching path B. The overlap at the full JHTV corpus (2117 files, top 200) is UNVERIFIED. It was not measured.

## 5. Known differences

B is the reference script and C is the repo path. The first column names the item. Rows 1 to 15 come from the research step (PROVEN unless marked). Row 16 comes from plan 01-02.

| Item | Path B | Path C | Effect on ranking |
|------|--------|--------|-------------------|
| Input form | Walks a room folder of `.md` files, strips front matter, skips bodies under 50 characters, id is `section/stem` | JSON list of artifacts with `id`, `title`, `text`, `source_ref` | None once the same artifacts are chosen. |
| Text for LSA and BM25 | title, newline, body | title, two newlines, body, stripped | None. Measured differences are 6e-8 and 3e-8. |
| Dense text | body only | title plus body | Changes every cosine. |
| Dense encoding | One call, truncated at the model limit | Chunks of limit minus 2 tokens, chunk vectors averaged | Main source of disagreement. |
| Negative cosine | Clipped to 0 | Not clipped | Changes pairs only when a cosine is negative (layer 3b). A known difference. |
| Float precision | LSA and BM25 as float32, gap rounded to 4 decimals in output | float64 | Gap differences up to 1.1e-3. |
| Top-7 LSA terms | Stable descending sort | `np.argsort` order, ties differ | LSA difference up to 0.0227 on 40 real files, none in that ranking. Fixed in plan 01-04 (section 3.1). |
| SVD components | `max(1, min(80, n-1, terms-1))` | `min(n-1, terms-1, 80)`, raises below 1 | Same for normal corpora. |
| Degenerate corpus | Returns identity | Raises `ValueError` | Edge case only. |
| Percentile gate | Needs 10 eligible pairs | Same | Same. |
| Ranker | z-score gap, percentile with average rank for ties | Same math | Identical (layer 1). |
| Tie order in output | Index order | Gap, then left id, then right id | Same when artifacts are in sorted id order. |
| `top_k` | Any value | `run_document` raises above 100 | The JHTV file holds 200 pairs. Path C cannot write that count today. |
| Seed | 256 for SVD | 256 for SVD | Same. |
| Edge writes | Writes graph edges when `.mindrian/room.db` exists | None | Use a scratch copy for path B. |
| Artifact cap | Keeps the first 2000 artifacts by default (env `RS_MAX_ARTIFACTS`) | Rejects more than 2500 artifacts | PROVEN, see section 6. The JHTV corpus holds 2117 files. |

## 6. How the JHTV results relate

The JHTV pair file for the unusual-pairs engine is a result of path B (sha256 `044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45`). Path C is a different method version for the dense signal. JHTV candidates stay valid as leads. They must cite the path B sha256.

The rebuild commands are in [docs/hsi-rs-jhtv-reproduction.md](hsi-rs-jhtv-reproduction.md). The record there says (quoted exactly):

Outcome: reproduced (wording-and-meaning pairs engine, command in section 2). PROVEN. `cache_params_hash` equals `7affae3c94c6bed9`, `pairs_scored` equals 2239786, the ordered list of 200 pairs equals the stored list, and the maximum score difference is 0.0. Only timestamps, `room_dir` and `retrieved_at` fields differ from the stored file.

Outcome: reproduced (unusual-pairs engine, command in section 3, with `RS_MAX_ARTIFACTS=3000`). PROVEN. The ordered list of 200 pairs equals the stored list and the maximum `hybrid_signed_gap` difference is 0.0. Only timestamps, `room_dir` and `verification.source_trail[].retrieval_date` differ.

Facts from plan 01-02 that this record depends on:

- PROVEN: the script of path B keeps only the first 2000 artifacts by default (env `RS_MAX_ARTIFACTS`, default 2000). The JHTV corpus holds 2117 files. With the default cap the JHTV result is NOT reproduced: 186 of 200 pairs overlap and the stored rank 1 pair is missing. With `RS_MAX_ARTIFACTS=3000` the result IS reproduced exactly: 200 ordered pairs equal, maximum difference 0.0.
- INFERRED: the original JHTV run set a cap of 2117 or more. The room holds no command text.
- PROVEN: the command of the wording-and-meaning pairs engine, `compute-hsi.py <copy> --tier 1 --top-k 200`, reproduces its stored file exactly (run time 5 minutes 10 seconds).
- PROVEN: path B gives the same 200 pairs with the repo `.venv` libraries (numpy 2.5.4, scikit-learn 1.9.1).

## 7. Open fix list for path C

| Item | Decision or status | Owner |
|------|--------------------|-------|
| top-7 term tie-break | Fixed in plan 01-04; evidence in section 3.1 (LSA max abs delta 3.371e-08, at most 1e-6). | Phase 1 plan 01-04 |
| negative-cosine clip | Not applied in path C, because the canonical rule is the repo path. Documented as a known difference, covered by layer 3b. | Owner decision, recorded here |
| dense-input rule | Repo rule: title plus body, chunk-mean. Locked by the owner on 2026-10-23. | Owner (Jonathan Sagir) |
| top_k cap of 100 in `run_document` | Unchanged in Phase 1. Phase 2 must lift it to 200, so that the one-command run can match the stored JHTV file size (200 pairs). | Phase 2 |

## 8. How to run the parity test

Command:

```bash
PYTHONPATH=src pytest tests/test_rs_engine_parity.py -q -p no:cacheprovider
```

Optional environment variables:

- `EUREKA_RS_REFERENCE_SCRIPT`: path to the path B script. Turns on the live reference legs and, with `EUREKA_RS_PARITY_REAL_MODEL`, layer 4.
- `EUREKA_RS_PLUGIN_SCRIPT`: path to the path A script. Turns on the live plugin legacy leg.
- `EUREKA_RS_PARITY_REAL_MODEL`: local model path. Runs layer 4 with the real encoder; it needs `EUREKA_RS_REFERENCE_SCRIPT` too. Report only.
- `EUREKA_PARITY_REPORT_PATH`: write the JSON report to this path.

Rules:

- Every test uses a tmp embedding cache path.
- A live leg refuses a script whose sha256 differs from the expected value.
- The generator of the golden files is `scripts/generate_rs_parity_golden.py`. It refuses a script with another sha256 too.
- No pytest dev group is added. The repo runs tests as `PYTHONPATH=src pytest`, and a dev group would change `uv.lock`.
- The record test is `tests/test_rs_engine_parity_record.py`. It fails when a number in section 3 differs from the baseline report file.

## 9. Scope

Path A stays in the plugin as legacy. It is out of scope for Phase 1. Phase 1 edits no file in the plugin repo. The scripts of path A and path B are not vendored in this repo. They are called by path and checked by sha256.
