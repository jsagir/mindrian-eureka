# Reproduction record: how the JHTV pair results were made

Record id: ENG-03. Checked on 2026-10-23 on a scratch copy of the JHTV room. Each claim is marked PROVEN (seen in a file or a run in this check), INFERRED (reasoned from PROVEN facts) or UNVERIFIED (not run).

Two engines are named in this record. Each name is the catalog name with its job, from `src/mindrian_eureka/data/capability-catalog.v1.json`.

- "Find Unusual Pairs Across a Research Collection" (id `opportunity.find_cross_domain_pairs`, formerly called RS). It finds pairs of documents whose meaning is close and whose vocabulary structure is far apart, or the reverse. Below it is called "the unusual-pairs engine".
- "Rank Unusual Pairs by Wording and Meaning" (id `portfolio.find_hybrid_similarity_pairs`, formerly called HSI). It ranks pairs by how much the wording and the meaning disagree. Below it is called "the wording-and-meaning pairs engine".

Both together make "Screen One Local Snapshot for Opportunity Pair Leads" (id `opportunity.synthesize_discovery_signals`). All results are candidates, not verified. They are leads for human review.

## 1. Outcome

Outcome: reproduced (wording-and-meaning pairs engine, command in section 2). PROVEN. `cache_params_hash` equals `7affae3c94c6bed9`, `pairs_scored` equals 2239786, the ordered list of 200 pairs equals the stored list, and the maximum score difference is 0.0. Only timestamps, `room_dir` and `retrieved_at` fields differ from the stored file.

Outcome: reproduced (unusual-pairs engine, command in section 3, with `RS_MAX_ARTIFACTS=3000`). PROVEN. The ordered list of 200 pairs equals the stored list and the maximum `hybrid_signed_gap` difference is 0.0. Only timestamps, `room_dir` and `verification.source_trail[].retrieval_date` differ.

A first run of the unusual-pairs engine without `RS_MAX_ARTIFACTS` did NOT reproduce the stored file. PROVEN. The script keeps only the first 2000 artifacts by default, and the corpus holds 2117. That run gave `artifact_count` 2000, overlap at 200 of 186/200, first differing rank 1 (the stored rank 1 pair `technology/C12269` + `technology/C17993` was missing), and a maximum `hybrid_signed_gap` difference of 0.8983 on the 186 shared pairs. The JHTV run therefore used a cap of 2117 or more. That the JHTV run set `RS_MAX_ARTIFACTS` is INFERRED from the result: the room holds no command text. That a cap of 2117 or more gives the stored file is PROVEN.

## 2. The command for the wording-and-meaning pairs engine

The command is `compute-hsi.py <room copy> --tier 1 --top-k 200`, run from `LATEST/engines/hsi/scripts`.

- Script: `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/hsi/scripts/compute-hsi.py`
- sha256: `5756c84f4e6c9cb690dac1b23aa913bd606f9046cc45309fe45d32a67b72a24c`
- Parked copy with the same sha256: `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/hsi/scripts/compute-hsi.py` (PROVEN).

Full command line used in this check (system `python3`, offline):

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 \
  /mnt/c/Users/jsagi/Downloads/research/LATEST/engines/hsi/scripts/compute-hsi.py \
  <SCRATCH>/room-hsi --tier 1 --top-k 200 --output <SCRATCH>/hsi-rebuild.json
```

The room argument is a folder that holds only the `technology/` folder. Do not pass other options. Defaults make up the settings (PROVEN from the result metadata and the script):

| Setting | Value |
|---------|-------|
| tier | 1 |
| ranking | percentile |
| lexical | hybrid |
| top_k | 200 |
| min_percentile | 0.0 |
| confirm_percentile | 0.75 |
| model | all-MiniLM-L6-v2 |
| seed | 42 |
| chunking | true |
| schema_version | 2.0 |
| pinecone | false |
| max-artifacts | 3000 (above the 2117 artifacts, so no cut) |

These settings hash to `cache_params_hash 7affae3c94c6bed9`. The hash is the first 16 hex characters of the sha256 of the sorted JSON of the settings. The stored result and the stored cache both hold this value, and the rebuilt result holds it too (PROVEN). A change of `top_k` alone gives other hashes: 20 gives `5b4b370a...`, 100 gives `0b2948b9...`, 500 gives `85c198f5...` (PROVEN in the research step, not re-run here). The `--output` target of the stored run is INFERRED from file stamps (see 01-RESEARCH.md, assumption A1).

Run facts (PROVEN): exit code 0, wall time 5 minutes 10 seconds, peak memory about 1.7 GB. The script printed a warning that `lib/core/rs_corpus_exclude.py` was not importable and that the built-in fallback exclude-list was used. The result still matched the stored file, so the fallback did not change the 200 pairs.

## 3. The command for the unusual-pairs engine

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RS_EMBEDDING_MODEL=minilm RS_MAX_ARTIFACTS=3000 python3 \
  /mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py \
  --mode internal --room <SCRATCH>/room-rs --topk 200 --threshold 0.0 --no-thesis \
  --output <SCRATCH>/rs-rebuild.json
```

- Script: `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py`
- sha256: `044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45`
- Parked copy with the same sha256: `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py` (PROVEN).
- Do not pass `--no-verify`. All 200 stored pairs carry a `verification` block (PROVEN), so the verify step ran.
- `--scoring hybrid`, `--min-percentile 0.9` and `--lex-weight 0.5` are defaults. The stored metadata shows these values (PROVEN). That the original run passed no other flag is INFERRED: the rebuilt metadata equals the stored metadata, key by key, except the timestamp, `room_dir` and `provenance.computed_at` (PROVEN).
- `RS_EMBEDDING_MODEL=minilm` selects the all-MiniLM-L6-v2 model. The stored metadata names this model (PROVEN). That the original run set this variable is INFERRED.
- `RS_MAX_ARTIFACTS` must be 2117 or more (see section 1). The value 3000 was used here. Any value from 2117 up gives the same result (INFERRED: the cap only cuts a list longer than the cap).

Run facts (PROVEN): exit code 0 for the capped-at-3000 run. Python 3.12.3, numpy 2.2.6.

## 4. Wrong-script warning

Three files named `rs-engine.py` and three files named `compute-hsi.py` exist. Only the LATEST file makes the JHTV result.

| File | Path | sha256 | Can make the JHTV file |
|------|------|--------|------------------------|
| `rs-engine.py`, shipped plugin | `/home/jsagi/dev/MindrianOS-Plugin/scripts/rs-engine.py` | `57c18df558d83fbffc8e9f7fda905729d0c0fbfe18a1c370b1db816efa3937f1` | no |
| `rs-engine.py`, LATEST | `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py` | `044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45` | yes |
| `rs-engine.py`, parked r-and-d copy | `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py` | `044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45` | yes (same bytes) |
| `compute-hsi.py`, shipped plugin | `/home/jsagi/dev/MindrianOS-Plugin/scripts/compute-hsi.py` | `bb0b76bbb3de9692753fd7a243e72306c324b0e61a550aa23a0dc578c212a4a9` | no |
| `compute-hsi.py`, LATEST | `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/hsi/scripts/compute-hsi.py` | `5756c84f4e6c9cb690dac1b23aa913bd606f9046cc45309fe45d32a67b72a24c` | yes |
| `compute-hsi.py`, parked r-and-d copy | `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/hsi/scripts/compute-hsi.py` | `5756c84f4e6c9cb690dac1b23aa913bd606f9046cc45309fe45d32a67b72a24c` | yes (same bytes) |

The shipped plugin scripts cannot make the JHTV files (PROVEN with `--help`). The shipped `rs-engine.py` has no `--scoring` flag, so it can only write the old `abs(semantic - lsa)` result with a fixed threshold. The shipped `compute-hsi.py` has no `--top-k` flag, so it cannot write a top 200 percentile result. Each run in this check recorded the sha256 of the script before the run. Do not run a script whose sha256 differs.

The scripts are not vendored in this repo. They are called by path and checked by sha256. The distribution status of these scripts is open (see `docs/rs-release-gate.md`).

## 5. Environment

| Item | JHTV run (stored in the result) | This check, system `python3` | Cross-check, repo `.venv` |
|------|--------------------------------|------------------------------|---------------------------|
| Python | 3.12.3 | 3.12.3 | 3.12.12 |
| numpy | 2.2.6 | 2.2.6 | 2.5.4 |
| scikit-learn | 1.8.0 | 1.8.0 | 1.9.1 |
| sentence-transformers | 5.3.0 | 5.3.0 | 5.7.0 |

All values are PROVEN (read from interpreters and from the stored provenance). Every run set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. No network call was made by design (INFERRED: the offline variables block the model hub, and no other network code runs in these modes).

Cross-version check (PROVEN). The unusual-pairs engine run with the repo `.venv` python gave the same ordered list of 200 pairs as the system python run, overlap 200/200, maximum `hybrid_signed_gap` difference 0.0, on this corpus. One change was needed: the `.venv` has no `requests` module, and the script imports it at load time. A stub `requests` module in the scratch folder was put on `PYTHONPATH` for that one run. The stub raises on any call. Internal mode makes no HTTP call, so the stub did not change a number (INFERRED). The wording-and-meaning pairs engine was not run in the `.venv` (UNVERIFIED).

## 6. Inputs and outputs

Input corpus (PROVEN): 2117 files under `engine-input-room/technology/` in the run folder of a scratch copy of the partner room: `$SCRATCH/partner-room/solution-design/full-catalog-run-2026-10-18/`.

- Manifest: `engine-input-manifest.json`, sha256 `32c74cceafdf37b1085f6c89c41a59ee640f9ef27546e679c33ce068f80d5312`. It holds `markdown_sha256` for each of the 2117 records.
- Check: every file of every scratch copy has the manifest sha256 (0 mismatches in 3 copies).
- Corpus digest: sha256 of the sorted lines `path:markdown_sha256` (one line per record, `path` as `technology/Cxxxxx.md`, joined with newline, no trailing newline) = `8e7625a3feb1d5ede83390eb31c524b6b048814558c733adc6c7fb9452cfc1b4`.

Stored outputs (PROVEN, sha256):

| File | sha256 |
|------|--------|
| `hsi-full-catalog.json` | `d61f71ae0d67838cbbb6e004f8be83519e1e98264174af9697ae74a8e5b4f7d1` |
| `rs-full-catalog.json` | `5451e522bac0ade0939e1b0d587a9603c6d83f07cf5e0a192dbb0860d870ff08` |

Rebuilt outputs on scratch copies (PROVEN, sha256). The bytes differ from the stored files only in the timestamp fields listed in section 1:

| File | sha256 | Note |
|------|--------|------|
| `hsi-rebuild.json` | `5e53cb7a2df9e38cbda423306288becd51aa90aad7b2eed3f3234fd79b8c3577` | wording-and-meaning pairs engine, reproduced |
| `rs-rebuild2.json` | `f62401141c2968107a62a7718bcdc601bd7615afe5eef5d5e6cc1d7505e2e1a9` | unusual-pairs engine, `RS_MAX_ARTIFACTS=3000`, system python, reproduced |
| `rs-rebuild-venv.json` | `305fa2eec8a611663032c1c0744072f3ba2b240613de758048663a76bd107dac` | same, repo `.venv` python, reproduced |
| `rs-rebuild.json` | `d40e5c04dfaba2f035e0e4e6affbb4e7f0a32d188a8731891c44f47c58f7ad0b` | default cap 2000, NOT reproduced (186/200) |

The JHTV room was not changed (PROVEN). The sha256 of the six JHTV files (the two result files, the manifest, `.hsi-cache.json`, `.hsi-results.json`, `.rs-engine-cache.json`) were equal before and after all runs, no file in the run folder was newer than the snapshot marker, and the count of files in `engine-input-room/technology/` stayed 2117.

## 7. Verification steps

1. Copy only the `technology/` folder of `engine-input-room/` into a new scratch room. Delete any cache file. Never run into the real room: both scripts write cache and result files into the room argument.
2. Check each copied file against `markdown_sha256` in `engine-input-manifest.json`.
3. Check the sha256 of each script against section 4.
4. Run the commands in sections 2 and 3 (offline variables set, system `python3`, a separate fresh copy for each engine). Expect about 5 minutes for the first and a few minutes for the second.
5. Wording-and-meaning pairs engine. Compare with `hsi-full-catalog.json`: `cache_params_hash` is `7affae3c94c6bed9`, `metadata.ranking.pairs_scored` is 2239786 (2117 x 2116 / 2), the ordered list of `(left_id, right_id)` of the 200 `hsi_pairs` is equal, and each `hsi_score` is within 1e-3. First pair: `technology/C11722` + `technology/C15549`. Second pair: `technology/C14402` + `technology/C15631`.
6. Unusual-pairs engine. Compare with `rs-full-catalog.json`: 200 pairs, the ordered list of `(source_artifact_id, target_artifact_id)` is equal, and each `hybrid_signed_gap` is within 1e-3. First pair: `technology/C12269` + `technology/C17993`. Second pair: `technology/C17109` + `technology/C17716`.
7. If an order differs, report the overlap at 200 and the first differing rank, then check the library versions and `RS_MAX_ARTIFACTS`. Do not claim "reproduced" on a set match alone.

## 8. Limits

- The flag set of the unusual-pairs engine and the `RS_MAX_ARTIFACTS` and `RS_EMBEDDING_MODEL` settings are INFERRED from the result metadata and from the match. The stored run left no command text.
- The `--output` target of each stored run is INFERRED from file stamps.
- The run used one machine and one set of library versions. The `.venv` cross-check covers the unusual-pairs engine only.
- The overlap of the repo path (`eureka-pair-scout`) with the JHTV unusual-pairs file on the full corpus is not measured here. A 40-file smoke test gave 0.42 (see the parity record). This record does not change that number.
- Results stay candidates, not verified. Reproducing a ranking proves that the settings are known. It does not prove that a pair is novel or valuable.
