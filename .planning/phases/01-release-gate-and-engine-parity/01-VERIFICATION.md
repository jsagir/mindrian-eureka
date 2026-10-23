---
phase: 01-release-gate-and-engine-parity
verified: 2026-10-23
status: human_needed
score: 5/5 success criteria met in the repo; 0 gaps; 3 owner items open
re_verification: false
human_verification:
  - test: "Release decision in docs/rs-release-gate.md is still status draft, decision no-go, decided_on empty."
    expected: "Owner keeps it draft no-go, or sets internal-only or go. A go is valid only when G1, G2, G3, G5 are closed and condition C1 is done."
    why_human: "Only the owner may change decided_by and decided_on. Plan 01-01 task 3 (owner sign-off) was never run."
  - test: "The release record says the author name 'is not written in this repo'. That sentence is false."
    expected: "Owner decides: scrub the name from tracked .planning/phases/01-release-gate-and-engine-parity/01-RESEARCH.md (5 hits) and correct the sentence in docs/rs-release-gate.md section 3, or accept the name in planning files."
    why_human: "Locked decision and owner rule on names. The pre-existing 'the original author, 2023' comments in src/mindrian_eureka/data/rs/rs-differential-scorer.cjs (lines 33, 212) are open item O1 and need an owner call too."
  - test: "docs/hsi-rs-jhtv-reproduction.md line 108 wrote a room folder name that held a third-party personal name. RESOLVED in quick 261023-q2c: replaced by a scratch copy path."
    expected: "Owner confirms the folder name may stay in a public doc, or the path is shortened."
    why_human: "Privacy and no-real-names rule is an owner judgment."
---

# Phase 1: Release Gate and Engine Parity - Verification

Goal: the maintainer knows whether Eureka may ship publicly, which RS path is canonical, and which HSI command produced the JHTV top_k 200 result.

Method: goal-backward. Summaries not trusted. I read the files, re-ran the suite and re-computed sha256 values.

## Suite

`PYTHONPATH=src pytest tests -q -p no:cacheprovider`: 192 passed, 25 skipped, 45 subtests passed (PROVEN, 23 s).
`PYTHONPATH=src pytest tests/test_rs_engine_parity.py -q`: 11 passed, 3 skipped. The skips are the opt-in live legs (env vars not set).

## Success criteria

| # | Criterion | Verdict | Evidence checked |
|---|-----------|---------|------------------|
| 1 | One written record: RS origin, author attribution, license status, ends in go / no-go | MET (record). Decision still draft. | `docs/rs-release-gate.md`: origin table with 14 sha256 values, section 3 author facts, section 4 license facts, gaps G1-G6, section 7 "Decision: no-go. Status: draft." Front matter `decision: no-go`, `status: draft`, `decided_on: ""`, `decided_by: Jonathan Sagir (owner)`. `tests/test_release_gate_record.py` (12 checks) passes and rejects go with open gaps. A go/no-go exists; it is the default, not an owner sign-off. |
| 2 | Parity test on one fixed input prints rank overlap and score differences | MET | Test run prints a report: layer 1 ranker (set_equal, order_equal, max gap delta 4.87e-05), layer 2 BM25 and LSA deltas, layer 3 overlap@10/20/full = 1.00, spearman, abs gap delta max/median/mean, layer 3b negative cosine 0.86, plugin legacy leg overlap@full 0.51. Fixed input is the committed synthetic corpus (`tests/fixtures/rs_parity/corpus.json`, 32 synthetic documents). Live legs against the real plugin and reference scripts are opt-in and sha256 gated. |
| 3 | Docs name one canonical RS path (or explain both) and cite the parity result | MET | `docs/rs-engine-parity.md`: canonical path C (`eureka-pair-scout`, `hybrid_2026`), decided_by owner, decided_on 2026-10-23, reasons, three-path table with sha256, before and after tie-break numbers, JHTV smoke 0.423 as evidence. `tests/test_rs_engine_parity_record.py` ties every number in the record to the report JSON files. Also linked from `docs/engines/opportunity-pairs.md` and README. |
| 4 | Exact HSI command and settings for JHTV top_k 200 are copyable | MET | `docs/hsi-rs-jhtv-reproduction.md` section 2: `compute-hsi.py <room copy> --tier 1 --top-k 200`, settings table, `cache_params_hash 7affae3c94c6bed9`, wrong-script warning. I re-hashed: LATEST `compute-hsi.py` 5756c84f..., LATEST `rs-engine.py` 044b9ae6..., plugin `rs-engine.py` 57c18df5..., stored `hsi-full-catalog.json` d61f71ae..., `rs-full-catalog.json` 5451e522..., manifest 32c74cce.... All equal the doc. Stored HSI file holds 200 pairs. I did not re-run the 5 minute rebuild (UNVERIFIED by me). The doc marks which flags are INFERRED (no command text in the room). |
| 5 | README and package metadata say RS fidelity is not verified bit-for-bit | MET | `pyproject.toml` line 8 description holds "not verified bit-for-bit". README has the phrase twice plus a "Fidelity of the unusual-pairs engine" section. Manifest, catalog entry, runner and engine guide carry it too. `tests/test_rs_fidelity_statement.py` passes. |

## Requirements

| ID | Status | Note |
|----|--------|------|
| REL-01 | Record done; decision draft no-go | Owner sign-off open. |
| REL-02 | Satisfied | Criterion 5. |
| ENG-01 | Satisfied | Criterion 2. |
| ENG-02 | Satisfied | Criterion 3. |
| ENG-03 | Satisfied (reproduced, flags inferred) | Criterion 4. |

## Locked decisions

| Decision | Result |
|----------|--------|
| Repo path canonical; JHTV keeps provenance to path B by sha256; 0.42 recorded as evidence | HONORED (parity doc sections 1, 4, 6) |
| `decided_by` is the owner | HONORED |
| Release record does not name the source author; "name held privately" | HONORED in the record (grep for the surname: 0 hits in `docs/rs-release-gate.md`). BUT see finding W1. |
| Default no-go, status draft | HONORED |
| No vendored r-and-d script or similarity_code files | HONORED. `git ls-files` shows no rs-engine.py, compute-hsi.py, lsa.py, comparison.py, sts_bert.py. Only paths and hashes in docs. |
| Tests use PYTHONPATH=src and tmp embedding cache | HONORED (parity doc section 8; no pytest dev group added) |
| Algorithm change | `algorithm.py` diff is 1 logic line: stable descending sort for top-7 terms. LSA max abs delta fell 1.06e-02 to 3.4e-08. Matches the doc. |

## Findings

- W1 (WARNING, resolved in quick 261023-q2c: research file scrubbed, sentence corrected): `docs/rs-release-gate.md` section 3 said "The name is not written in this repo." This is false. The author surname and first name appear 5 times in tracked `.planning/phases/01-release-gate-and-engine-parity/01-RESEARCH.md`. The surname also appears in pre-existing `src/mindrian_eureka/data/rs/rs-differential-scorer.cjs` (lines 33, 212). Section 4 item O1 already notes the .cjs comment. The record's sentence should be corrected or the research file scrubbed. Owner decision.
- W2 (WARNING): `docs/hsi-rs-jhtv-reproduction.md` line 108 included a room folder name with a person's name and a local absolute path. No room file content is in the repo. RESOLVED in quick 261023-q2c (neutral scratch-copy path).
- W3 (WARNING, bookkeeping): `.planning/ROADMAP.md` still shows Phase 1 "0/TBD, Not started" and plans TBD. `.planning/REQUIREMENTS.md` still shows all five IDs "Pending". `.planning/STATE.md` status is "planning". Update after owner sign-off.
- I1 (INFO): 01-01 SUMMARY status is `partial` by design (task 3 owner sign-off). Summaries 02 to 06 are `complete`.
- I2 (INFO): `top_k` cap of 100 in `run_document` and the 2500 artifact cap block a repo-side JHTV rerun (200 pairs, 2117 files). Documented as Phase 2 work in parity section 7. Not a Phase 1 gap.
- I3 (INFO): The overlap of path C with JHTV on the full corpus is not measured. Only a 40 file smoke (0.423) exists, labeled as such.

## Private data

No room text in the repo. Fixtures are synthetic (`syn-001...`, nonsense tokens). Docs hold aggregate numbers, JHTV catalog ids (`technology/C12269` style), hashes and local paths only. Only W2 above.

## Em-dashes and bare names

- Em-dashes in new docs: 0 in `rs-release-gate.md`, `rs-engine-parity.md`, `hsi-rs-jhtv-reproduction.md`; 0 added in README, `opportunity-pairs.md`, `licensing-and-provenance.md`, `pyproject.toml` diffs.
- Bare "RS" / "HSI" as a word (count by file):
  - `docs/rs-release-gate.md`: RS 1, HSI 0
  - `docs/rs-engine-parity.md`: RS 1, HSI 1
  - `docs/hsi-rs-jhtv-reproduction.md`: RS 1, HSI 1
  - README fidelity section: RS 0, HSI 0
  - Every hit is the definition phrase "formerly called RS" or "formerly called HSI". No prose use of the bare short name. (README line 215 table row "RS + HSI signal scout" is outside the new section and was not added by this phase.)

## Open item

The release decision is still `status: draft`, `decision: no-go`, `decided_on` empty. Phases 2 and 3 may proceed. Phase 4 ships internal only until the owner changes it.

## Status reasoning

No truth failed. All 5 success criteria are met in code and docs. Status is `human_needed` because of the owner sign-off on the release record and the two attribution and privacy items (W1, W2).

_Verifier: Claude (gsd-verifier)_
