# Phase 1: Release Gate and Engine Parity - Research

**Researched:** 2026-10-23
**Domain:** Source-provenance record, two-engine parity test, recovery of a run command (Python, numpy, scikit-learn, pytest)
**Confidence:** HIGH for the facts below (each one was read or run on this machine). MEDIUM for the go / no-go (a human decision, no legal advice given).

Label key. PROVEN = read in a file or run in this session. INFERRED = reasoned from PROVEN facts. UNVERIFIED = not run. These map to the usual tags: PROVEN is [VERIFIED], INFERRED and UNVERIFIED are [ASSUMED].

## Summary

Three premises in the task brief are wrong or incomplete. The planner must use the corrected facts.

1. The JHTV RS result file (`rs-full-catalog.json`) was NOT produced by the shipped plugin script `scripts/rs-engine.py` (beta.59, beta.69 and beta.73 all have sha256 `57c18df5...`). That script has no `--scoring` flag and no BM25 code. It can only write the old `abs(semantic - lsa)` result. The JHTV file has `schema 2026.1`, `scoring hybrid`, and per-pair `verification` blocks. Those come from a different script: `LATEST/engines/rs/shared/scripts/rs-engine.py`, sha256 `044b9ae6...`. A byte-identical copy is parked in the plugin repo at `r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py`. So there are THREE RS code paths, not two.
2. The original `similarity_code` package IS on this machine: `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/` (5 files, 434 lines). It is byte-identical to the copy in the plugin repo at `.planning/phases/89-reverse-salient-engine/source/`. The Eureka docs say it is absent. That is true only for the Eureka checkout. The PowerPoint deck was not found on disk.
3. The HSI command is recoverable. The script is `LATEST/engines/hsi/scripts/compute-hsi.py` (sha256 `5756c84f...`). It has `--top-k` (default 20) and `--min-percentile` (default 0.0). The shipped plugin `compute-hsi.py` (sha256 `bb0b76bb...`) has neither. The command `compute-hsi.py <room> --tier 1 --top-k 200` reproduces the recorded `cache_params_hash 7affae3c94c6bed9` exactly.

On parity: the ranking logic (z-score gap plus percentile gate) of the Eureka RS path is identical to the LATEST reference when both get the same similarity matrices. All measured disagreement comes from how the dense (semantic) signal is built, plus two small items (a tie-break in the repo, a negative-cosine clip in the reference).

**Primary recommendation:** Run Phase 1 as three independent tracks. (a) REL-01/REL-02: write one provenance and release-gate record with default decision NO-GO for public distribution, plus the plain-words fidelity text. (b) ENG-01/ENG-02: build a layered parity test (ranker layer exact, component layer tolerant, end-to-end layer report-only until the dense-input decision) and record Eureka `eureka-pair-scout` `hybrid_2026` as canonical for new runs. (c) ENG-03: record the HSI and RS commands below and verify them on a COPY of the JHTV room.

## User Constraints

No `CONTEXT.md` exists for this phase (`ls .planning/phases/01-release-gate-and-engine-parity/` shows only this file). There are no locked decisions, no discretion list, and no deferred ideas from a discuss step.

Constraints taken from `.planning/PROJECT.md`, `STATE.md` and `ROADMAP.md` (treat as binding):
- Offline by default. Determinism. "Candidate, not verified" labels. Privacy of embeddings and room data.
- The go / no-go gates public shipping in Phase 4 only. Phases 2 and 3 proceed on a no-go.
- REL-02 wording depends on the REL-01 record and the ENG-01 result.
- Peer uncommitted edits exist under `story/`. Use `--only` or explicit file lists. Never stage or revert them.
- Plugin repo edits are out of scope for Phase 1.

## Project Constraints (from CLAUDE.md and owner rules)

- GSD workflow only. No direct edits outside a GSD command. (`/home/jsagi/dev/mindrian-eureka/CLAUDE.md`)
- Honest labels, offline, determinism, privacy (same file, Constraints section).
- Agent protocol: STE-style English; no direct address to the human; a subagent never asks the human; return `NEEDS_HUMAN: <question>`. (`~/.claude/protocols/agent-interaction-protocol.md`)
- No em-dashes; use hyphens. (owner memory)
- No real names or emails of testers or advisors in tracked repos. (owner memory) The REL-01 record names an external source author. See Open Question 3.
- Executors never push. The main session reviews every commit ahead of origin before a push. (owner memory)
- Add only synthetic or approved evaluation data. Do not commit private room exports. (`CONTRIBUTING.md`)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-01 | Written record of RS source origin, author attribution, license status, go / no-go | Section "REL-01": all evidence on disk, the gap list, the record format and path |
| REL-02 | README and package metadata state RS fidelity (not verified bit-for-bit) | Section "REL-02": quoted current wording, edit locations, a list of proven deviations to name |
| ENG-01 | A test runs plugin `rs-engine.py` and repo `eureka-pair-scout` on one fixed input and reports rank overlap and score differences | Section "ENG-01": three-path map, smoke results, layered test design, thresholds |
| ENG-02 | One canonical RS path, or a documented reason to keep both, with the parity result as evidence | Section "ENG-02": recommendation and decision table |
| ENG-03 | Exact HSI command that produced `top_k 200` found or rebuilt and recorded | Section "ENG-03": candidate table, rebuilt command, verification steps |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Provenance and release-gate record | Repo docs (`docs/`) | `tests/` (a presence check) | A human decision recorded in git; a test only checks the file and its fields |
| Fidelity wording | README + `pyproject.toml` + capability manifest/catalog | CLI result `limitations` text | Package metadata is what a non-author sees first |
| RS parity test | `tests/` (pytest) | Optional reference script outside the repo (env var) | The reference script has unresolved distribution status; do not copy it into the repo |
| Canonical RS path | `src/mindrian_eureka/opportunity_pairs/` | `docs/engines/opportunity-pairs.md` | The repo owns the runtime; the plugin is a host |
| HSI/RS command record | `docs/` (reproduction record) | JHTV room (read-only evidence) | Evidence stays in the room; the record lives in the repo |

## Standard Stack

### Core (already in the repo)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.11 (repo `.venv` 3.12.12) | Runtime | `pyproject.toml` `requires-python` |
| numpy | 2.5.4 in `.venv`; 2.2.6 on system python3 | Matrices, z-scores | Declared `numpy>=2.0,<3` |
| scikit-learn | 1.9.1 in `.venv`; 1.8.0 on system python3 | TF-IDF, TruncatedSVD | Declared `>=1.6,<2` |
| sentence-transformers | 5.7.0 in `.venv`; 5.3.0 on system python3 | Local MiniLM | Optional extra `modern-encoder` |
| pytest | 9.0.2 (system, `/home/jsagi/.local/bin/pytest`) | Test runner | Existing tests use `pytest` functions, `monkeypatch`, `tmp_path`, `pytest.importorskip` |

The JHTV run recorded numpy 2.2.6, scikit-learn 1.8.0, sentence-transformers 5.3.0, Python 3.12.3. System `python3` has exactly these versions (PROVEN). Use system `python3` for reproduction of the JHTV commands. The repo `.venv` has newer versions.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.17.1 (system only) | Spearman in scratch scripts | Do NOT add to the repo. Compute Spearman with numpy rank arrays in the test. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest from system | `[dependency-groups] dev = ["pytest"]` in `pyproject.toml` | The repo has no pytest declaration (not in `pyproject.toml`, not in `uv.lock`, not in `.venv`). Tests run as `PYTHONPATH=src pytest tests`. Adding a dev group changes `uv.lock` and needs network. Decide in Wave 0. |

**Installation:** No new runtime package is needed in Phase 1.

**Version verification:** versions above were read with `.venv/bin/python -c`, `python3 -c`, and `pytest --version` on 2026-10-23.

## Package Legitimacy Audit

Phase 1 installs no new external package. `pytest` is already installed system-wide (9.0.2) and is an established package, but the registry check and slopcheck were not run. If the planner adds a pytest dev group, tag it [ASSUMED] and gate it behind one human-verify step.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pytest | PyPI | UNVERIFIED | UNVERIFIED | UNVERIFIED | not run | Optional; only if a dev group is added |

**Packages removed due to slopcheck [SLOP] verdict:** none (not run).
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### The three RS code paths (PROVEN)

| Id | Path | sha256 (first 8) | Scoring | Dense signal | Notes |
|----|------|------------------|---------|--------------|-------|
| A | Shipped plugin: `~/.claude/plugins/cache/mindrian-marketplace/mos/2.0.0-beta.73/scripts/rs-engine.py` (same file as `/home/jsagi/dev/MindrianOS-Plugin/scripts/rs-engine.py`; identical in beta.59, .69, .73) | 57c18df5 | Legacy only: `abs(semantic - lsa)`, `--threshold` default 0.30. No `--scoring`, no BM25, no percentile. | `RS_EMBEDDING_MODEL=minilm`: MiniLM on body text only | Cannot produce the JHTV file |
| B | LATEST / parked reference: `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py`; copy at `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py` (tracked by plugin commit `87c25f4c8`, 2026-10-09) | 044b9ae6 | `--scoring hybrid` (default): z-gap of dense vs (0.5 LSA + 0.5 BM25), percentile gate `--min-percentile` 0.90 | MiniLM, body text only, one pass, truncated at the model limit (256 word pieces), negative cosine clipped to 0 | Produced the JHTV RS file. Imports `lib/core/rs_math.py` from its own tree (sha `2188e885`, float64), NOT the shipped one (sha `710c1442`) |
| C | Eureka repo: `src/mindrian_eureka/opportunity_pairs/` (`algorithm.py`, `runner.py`, `encoders.py`); CLI `eureka-pair-scout`, MCP `scout_start` | n/a | `hybrid_2026` (default) or `legacy` | MiniLM (or BERT) via `SentenceTransformerEncoder`: input is `title + body`, chunked to model limit, chunk vectors averaged, no clip | Ledger calls it an independent implementation of B's scoring |

Proof that B made the JHTV file (PROVEN): the JHTV metadata block equals the metadata block that B writes on a 40-file smoke run, key by key, except `artifact_count`, `room_dir`, timestamps and `topk_requested`. All 200 JHTV pairs carry a `verification` block, so `--no-verify` was not used. `engine-input-room/` has no `.rs-engine-results.json`, so `--output` pointed at `../rs-full-catalog.json` (INFERRED).

Proof that A cannot (PROVEN): `grep bm25_similarity_matrix` finds it in the plugin repo only in the parked `r-and-d` copy (`git log --all -S` returns commit `87c25f4c8` only). `scripts/rs-engine.py --help` has no `--scoring`.

### System Architecture Diagram (parity test)

```
fixed synthetic corpus (N=32, committed JSON)
        |
        +--> Layer 1  RANKER: inject the same 3 matrices (LSA, BM25 via text, dense) ------+
        |        reference B PairScorer.topk   vs   Eureka rank_pairs_hybrid_2026           |
        |        expect: same pair set, same order, |gap delta| <= 5e-3                      |
        |                                                                                    v
        +--> Layer 2  COMPONENTS: LSA matrix, BM25 matrix   (B/rs_math vs Eureka)       parity report
        |        expect: BM25 max abs <= 5e-4; LSA max abs <= 1e-6 after tie-break fix   (JSON + stdout:
        |                                                                                 overlap@k, Spearman,
        +--> Layer 3  END TO END with one shared dense stub (seeded vectors)             score deltas, verdict)
        |        B: vectors pre-seeded in .rs-engine-cache.json (no model needed)             ^
        |        C: monkeypatch SentenceTransformerEncoder to return the same vectors        |
        |        expect: overlap@k >= 0.95, top-10 identical, Spearman(rank) >= 0.99 --------+
        |
        +--> Layer 4  REAL MODEL (optional, env var, report-only)
                 MiniLM on the real encoder in both paths; prints overlap and Spearman,
                 never fails until ENG-02 fixes the dense-input rule
```

### Recommended Project Structure
```
tests/
  test_rs_engine_parity.py          # layers 1-3 always run; reference-script legs skip without the env var
  fixtures/rs_parity/
    corpus.json                     # synthetic artifacts (id, title, text, source_ref)
    reference_vectors.json          # seeded dense vectors, one per artifact id
    golden_reference.json           # B output for the corpus + header: script sha256, command, numpy/sklearn versions
docs/
  rs-release-gate.md                # REL-01 record (new)
  rs-engine-parity.md               # ENG-01/02 result + canonical decision (new)
  hsi-rs-jhtv-reproduction.md       # ENG-03 command record (new)
scripts/
  generate_rs_parity_golden.py      # optional: regenerates golden from B via EUREKA_RS_REFERENCE_SCRIPT
```

### Pattern 1: Reference script by env var, never vendored
**What:** The test reads `EUREKA_RS_REFERENCE_SCRIPT` (path to B) and `EUREKA_RS_ORIGINAL_DIR` (path to the original five files). If unset, the live legs skip and the committed golden is used.
**When to use:** Always. B is marked "local evaluation only pending distribution review" in `docs/engine-source-ledger.md`. The original five files have no license text. Copying either into a public repo would be an unforced release decision.
**Example:** the existing test style in `tests/test_rs_hybrid_2026.py` (`monkeypatch.setattr(runner, "cached_encode", ...)`).

### Pattern 2: Seed B's embedding cache so B runs without a model
**What:** B reads `<room>/.rs-engine-cache.json` before it loads any model. Entry format (PROVEN from `rs-engine.py` lines 843-875 and 953-962):
`{"version": "1", "embeddings": {"<artifact id>": {"hash": sha256(text)[:16], "model": "all-MiniLM-L6-v2", "vector": [...]}}}`
With every entry a hit and `RS_EMBEDDING_MODEL=minilm`, B never imports sentence-transformers. PROVEN on a 32-doc synthetic room (run succeeded offline, `edges_written 0`).
**Eureka side:** `monkeypatch.setattr(runner, "SentenceTransformerEncoder", Stub)` where `Stub.encode` returns the same vectors keyed by `model_text`.

### Anti-Patterns to Avoid
- **Do not point B at a room that has `.mindrian/room.db`.** B writes `REVERSE_SALIENT` edges there. Use a temp room. (`write_reverse_salient_edges` returns 0 when the db is missing.)
- **Do not run reference scripts inside the JHTV room.** They write `.rs-engine-cache.json`, `.hsi-cache.json` and `.hsi-results.json` there. A cache hit can also skip recompute and hide a mismatch. Copy the room first.
- **Do not reuse an embedding cache file between test runs.** See Pitfall 1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile rank and z-score | A new ranker for the test | The repo functions `_zscore_pairs`, `_percentile_ranks`, `rank_pairs_hybrid_2026` | The test must exercise the shipped code |
| Reference RS | A copy of B inside `tests/` | Env var path plus a committed golden file | Rights are unresolved (REL-01) |
| Spearman | scipy import | numpy: `np.argsort(np.argsort(x))` ranks, then `np.corrcoef` | scipy is not a repo dependency |
| Offline dense vectors | A fake encoder class in production code | `monkeypatch` in the test | Production code stays honest |
| Original-algorithm oracle | Vendor `lsa.py` | Optional live leg reading `EUREKA_RS_ORIGINAL_DIR` | Same rights reason; needs NLTK stopwords data, not installed |

**Key insight:** the ranker is already proven equal. The only open parity questions are inputs to the ranker. A test that mixes both hides the cause. Layered tests show the cause.

## REL-01: RS source origin, authors, license (facts and gaps)

### What is known (PROVEN unless marked)
| Fact | Evidence (path) |
|------|-----------------|
| Five original files exist: `comparison.py`, `lsa.py`, `paper_cleaning.py`, `paper_gathering.py`, `sts_bert.py`. 434 lines in total. | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/` (dir mtime 2026-04-12) |
| Same five files are in the plugin repo, byte-identical. sha256: `comparison.py` aef65081..., `lsa.py` a3672fea..., `paper_cleaning.py` dbf5f402..., `paper_gathering.py` dd2a46fd..., `sts_bert.py` d0edc2c3... The directory is gitignored (`.planning/*`), so it is not in git history. | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/` ; `git check-ignore -v` returns `.gitignore:97:.planning/*` |
| The files have no license header, no copyright line, no author line. The only matches for "copyright" are string literals in `paper_cleaning.py` that strip publisher notices from abstracts. | `grep -n -i "copyright\|licen\|author"` on the five files |
| The plugin planning record says: "Received the original implementation from Newton Kwan (research paper code, 5 files, ~250 LOC)", dated 2026-04-12. | `.planning/phases/89-reverse-salient-engine/PLAN.md` line 53 |
| The plugin cites the algorithm as "Kwan 2023" and "Newton Kwan et al. (2023)". No journal, venue, DOI, or URL for any paper was found in any file searched. "et al." names no other person. | `rs-engine.py` header; `rs_math.py` docstring; `.planning/phases/89-reverse-salient-engine/RESEARCH.md` lines 202-207; grep of `MindrianOS`, `PWS-Book`, `rethinking-mindrianos`, `Theo/.planning` found no other mention |
| Line-count mismatch: `PLAN.md` says "~250 LOC"; `ALGORITHM-SOURCE.md` says 438; actual is 434. Minor, but the record should state the measured number. | as above |
| The deck: file name in the origin note is `Algorithmic Generation of Solutions.pptx`, 15 slides, "file dated 2025-04-20". Other names in docs: `Algorithmic Generation of Reverse Salient Solutions (1).pptx` and `... of Solutions (1) (1).pptx`. The deck file was NOT found under `/mnt/c/Users/jsagi/Downloads` or `/home/jsagi` (maxdepth 6 name search). The deck text was extracted once (2026-09-23). The note lists no author on the slides. | `/home/jsagi/MindrianOS/research/2026-09-23-origin-concept-algorithmic-generation-of-rs-solutions.md` (byte-identical copy in `rethinking-mindrianos/research/`); `.planning/phases/89-reverse-salient-engine/ALGORITHM-SOURCE.md` front matter |
| Date conflict: code attributed to 2023; deck file dated 2025-04-20; code received 2026-04-12. | the three sources above |
| The plugin is BSL 1.1, Licensor Jonathan Sagir, "(c) 2024-2026". | `/home/jsagi/dev/MindrianOS-Plugin/LICENSE` |
| The Eureka repo has no top-level `LICENSE` on purpose. | `docs/licensing-and-provenance.md` |
| The Eureka ledger row for RS says: "User-provided research; upstream authorship and redistribution rights unresolved"; "Local evaluation only pending rights review"; "independent implementation ... no source file copied". | `docs/engine-source-ledger.md` row `RS / opportunity.find_cross_domain_pairs` (line 30) |
| Eureka ships CJS files with the header `Copyright (c) 2026 Mindrian. BSL 1.1.` that mention "Kwan 2023" in comments. | `src/mindrian_eureka/data/rs/rs-differential-scorer.cjs` lines 2 and 33 |
| The Eureka Python RS reuses the same numeric settings as `lsa.py` (2000 features, `max_df` 0.5, 80 components, `n_iter` 10, seed 256, top 7 terms), but the code text is different (no loop copy). Whether parameter reuse needs a permission is a question for the owner, not for this research. | `algorithm.py` lines 53-73 vs `lsa.py` |

### What is unknown (the gap list)
1. Who wrote the code beyond one name. Who is in "et al."
2. Whether a paper exists, and its citation (venue, year, DOI).
3. What terms Newton Kwan (or an institution) attached when the code was handed over. No email, license, or note was found.
4. Who wrote the deck, and whether the deck and code have the same owner.
5. Whether the owner holds written permission to adapt or redistribute the code or the method description.
6. Whether any employer or institution of the author has a claim. (Stated as a gap only.)

### Proposed record format
**Path:** `/home/jsagi/dev/mindrian-eureka/docs/rs-release-gate.md` (new). Add one link line to `docs/licensing-and-provenance.md`. Do not rename existing files.

**Front matter (all fields required; a test checks presence and enum values):**
```yaml
---
record: rs-source-release-gate
version: 1
decision: no-go            # enum: go | no-go | internal-only
decision_scope: public distribution of the RS engine (eureka-pair-scout, hybrid_2026 and legacy) and its docs
decided_by: ""             # a human name or role; an agent must not fill this
decided_on: ""             # YYYY-MM-DD, empty until a human decides
status: draft              # enum: draft | decided
reopen_when:               # list of the gap numbers below that must close
  - G1
  - G2
  - G3
  - G5
evidence_checked_on: 2026-10-23
---
```
**Body sections, in this order:** 1 Summary (one paragraph, plain words). 2 Origin facts (table: item, path, sha256, PROVEN/UNKNOWN). 3 Author and citation facts. 4 License facts (original files: none stated; plugin: BSL 1.1; Eureka: no license by design). 5 What the repo copied versus reimplemented (parameters equal, code text independent, CJS files carry BSL headers). 6 Gap list G1-G6 (the six unknowns above), each with "who can close it" and "what closes it" (for example "written reply from the source author stating permitted use and preferred citation"). 7 Decision and conditions. 8 Effect on phases (Phases 2 and 3 proceed; Phase 4 ships internal-only on `no-go`).

**Default decision to write:** `no-go` with `status: draft`. Reason (facts only): G1, G2, G3 and G5 are open, and the repo's own docs say they must close before production distribution. `decided_by` and `decided_on` stay empty. A human completes them. The planner needs a `checkpoint:human-verify` task for this.

## ENG-01: How the paths differ and the parity test

### Differences, with proof (B = reference, C = Eureka)
| Item | B (LATEST rs-engine.py) | C (Eureka) | Effect on ranking |
|------|-------------------------|-----------|-------------------|
| Input | Walks a room dir; `.md` files; strips front matter; skips bodies under 50 chars; id is `section/stem` | JSON list of artifacts with `id`, `title`, `text`, `source_ref` | none after the same artifacts are chosen |
| Text for LSA/BM25 | `title + "\n" + body` | `title + "\n\n" + body`, stripped | none (tokenizers ignore the extra newline); PROVEN by 6e-8 and 3e-8 deltas |
| Dense text | body only | `title + body` | changes every cosine |
| Dense encoding | one `encode()` call, truncated at model limit (256 word pieces for MiniLM) | split into chunks of limit-2 tokens, chunk vectors averaged | the main source of disagreement |
| Negative cosine | clipped to 0 (`cosine_matrix(clip=True)`) | not clipped | changes pairs only if a cosine is negative; PROVEN (see smoke 4) |
| Float precision | LSA and BM25 returned as float32; gap rounded to 4 decimals in output | float64 | gap deltas up to 1.1e-3 |
| LSA top-7 terms | `sorted(..., reverse=True)[:7]` (stable; matches the original `lsa.py`) | `np.argsort(component)[-7:][::-1]` (tie order differs) | changes LSA by up to 0.0227 on a 40-doc real sample; zero effect on that sample's ranking |
| SVD components | `max(1, min(80, n-1, terms-1))` | `min(n-1, terms-1, 80)`; raises if below 1 | same |
| Degenerate corpus | `rng == 0` returns identity | raises `ValueError` | edge case only |
| Percentile gate | needs 10 eligible pairs | same | same |
| Ranker | z-gap, `percentile_rank_matrix` (average rank for ties) | `_zscore_pairs`, `_percentile_ranks` (same math) | identical (PROVEN below) |
| Tie order in output | `np.lexsort((j, i, -gap))` by index | `sorted(key=(-gap, left.id, right.id))` | same if artifacts are in sorted id order |
| `top_k` | any | `run_document` raises above 100 | JHTV used 200; Eureka cannot reproduce that count today |
| Seed | 256 (SVD) | 256 (SVD) | same |
| Edge writes | writes to `.mindrian/room.db` if present | none | use a temp room |

### Measured results (smoke tests run in this session)
Scratch files are in `/tmp/claude-1000/-home-jsagi/5a1774bc-a933-4bca-9f46-2d886586e3b1/scratchpad/`. The env for every run: system `python3` 3.12.3 (numpy 2.2.6, scikit-learn 1.8.0, sentence-transformers 5.3.0), `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.

| # | Test | Command / script | Result |
|---|------|------------------|--------|
| 1 | B on 40 real JHTV files (every 53rd file of `engine-input-room/technology/`, copied to scratch) | `RS_EMBEDDING_MODEL=minilm python3 <B> --mode internal --room <scratch>/room40 --topk 100 --threshold 0.0 --no-thesis --no-verify --output b_out.json` | 78 pairs, 38 s, `scoring hybrid` |
| 2 | C on the same 40 files, real MiniLM | `run_document(doc, encoder_name="sentence-transformers", model_path="sentence-transformers/all-MiniLM-L6-v2", top_k=100, scoring="hybrid_2026", min_percentile=0.9, cache_path=<scratch>)` (script `run_repo.py`) | 78 pairs, 15 s. overlap@78 = 0.423, @10 = 0.30, @20 = 0.45, @50 = 0.42. On the 33 shared pairs: Spearman of signed gap 0.85, rank Spearman 0.65, sign agreement 0.97, median abs gap delta 0.23, max 3.88 |
| 3 | Attribution (script `attrib.py`): feed the same matrices to the Eureka ranker | V1 B-lsa + B-dense; V2 Eureka-lsa + B-dense; V3 B-lsa + Eureka-dense; V4 Eureka-lsa + Eureka-dense | V1 overlap 1.000, top-10 1.0. V2 overlap 1.000 (the tie-break does not change this ranking). V3 and V4 overlap 0.423. Dense cosines: Spearman 0.805, max abs diff 0.463. LSA: Spearman 0.9987, max abs diff 0.0227 |
| 4 | Shared deterministic dense stub, real files (script `attrib2.py`; B with `RS_EMBEDDING_MODEL=hashing`, C with a stub that calls B's `_embed_hashing`) | see script | set overlap 1.00; order differs (max rank shift 2); rank Spearman 0.9998; top-10 and top-20 overlap 1.0; max abs gap delta 0.024 |
| 5 | Tie-break fix check (script `tie.py`) | replace `np.argsort(...)[-7:][::-1]` with `sorted(enumerate(c), key=..., reverse=True)[:7]` in a patched in-memory copy | LSA max abs diff to B falls from 0.0227 to 2.8e-8. Ranker-only run: same order as B, max abs gap delta 1.06e-3 (BM25 float32 in B) |
| 6 | Synthetic 32-doc corpus with seeded vectors injected into B's cache and a stub in C (scripts `syn.py`, `syn2.py`, `syn3.py`) | non-negative vectors | set overlap 1.0, same order, max gap delta 5.0e-5 (B rounds to 4 decimals). With signed vectors (negative cosines): overlap 0.88, max gap delta 0.86 (B clips at 0) |
| 7 | Same LSA code in `.venv` (numpy 2.5.4, sklearn 1.9.1) and system python (script `envcmp.py`) on the synthetic corpus | | max abs diff 0.0 |

Caveat: tests 1-5 use 40 files. Overlap at 2117 files and top-200 is UNVERIFIED. A full-corpus comparison is feasible (JHTV run times from file stamps: HSI about 2.5 min, RS about 1 min after embeddings) but was forbidden here.

### Proposed pass rules (with reasons)
| Layer | Metric | Pass rule | Reason |
|-------|--------|-----------|--------|
| 1 Ranker, injected matrices | top-k pair set and order | identical | Test 3 V1 and test 5 give 100% and same order |
| 1 | abs delta of `hybrid_signed_gap` per pair | <= 5e-3 | Observed max 1.06e-3 from B's float32 BM25. 5x margin |
| 2 BM25 matrix | max abs delta | <= 5e-4 | Observed 1.3e-4 (real) and 6e-8 (synthetic) |
| 2 LSA matrix | max abs delta | <= 1e-6 after the tie-break fix; before the fix, assert only Spearman >= 0.99 and mark the test `xfail(strict=True)` for the tight rule | Observed 2.8e-8 after the fix, 0.0227 before |
| 3 End to end, shared dense vectors, non-negative | overlap@k | >= 0.95 | Observed 1.0. Allow a few swaps at the percentile edge from float32 |
| 3 | top-10 identical set | yes | Observed 1.0 |
| 3 | Spearman of ranks on shared pairs | >= 0.99 | Observed 0.9998 |
| 3 | signed gap sign agreement | 1.0 | Direction label must not flip |
| 3b Negative-cosine case | document as a KNOWN DIFFERENCE; assert only that Eureka does not crash and that B-clip behaviour is reproduced when the test applies `np.clip(sim, 0, 1)` to the stub vectors | n/a | The decision to clip belongs to ENG-02 |
| 4 Real MiniLM | print overlap@k, Spearman, score deltas | report only | Observed overlap 0.42 comes from the dense-input rule (title, chunking), not from a bug |

What the test must print (success criterion 2): rank overlap at k = 10, 20, and full k; Spearman of signed gap and of rank; max, median, mean abs score delta; the path ids; both script sha256 values; library versions; a one-line verdict.

### ENG-02 recommendation
Record `eureka-pair-scout` with `hybrid_2026` (path C) as the canonical RS path for new runs. Reasons: (a) its ranker equals the reference ranker (PROVEN); (b) it takes stable JSON IDs, has a schema, a cache, jobs and an MCP surface; (c) path A is legacy-only and cannot be the reference for hybrid; (d) path B is a script outside the repo with unresolved distribution status and writes into rooms.

Record these as honest limits in `docs/rs-engine-parity.md`:
- The JHTV RS file is a result of path B. Path C does not reproduce it at the dense level (42% overlap on a 40-file sample). The JHTV candidates stay valid as leads from path B and must cite B's sha256 `044b9ae6...`.
- To reproduce the JHTV RS file, run path B (command in the ENG-03 section).
- Path A stays in the plugin as legacy. It is out of Phase 1 scope.
- Open fix list for path C, each small and testable: tie-break (use stable descending sort); decide on the negative-cosine clip; decide the dense-input rule (title or no title; chunk-mean or truncate); lift the `top_k <= 100` cap (Phase 2 will need 200).
- The owner decides the dense-input rule. See Open Question 1.

## ENG-03: The HSI command

### Candidates (PROVEN)
| Candidate | Path | Evidence | Verdict |
|-----------|------|----------|---------|
| LATEST `compute-hsi.py` | `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/hsi/scripts/compute-hsi.py`, sha256 `5756c84f4e6c9cb690dac1b23aa913bd606f9046cc45309fe45d32a67b72a24c`. Same sha256 at `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/hsi/scripts/compute-hsi.py`. Matches the Eureka ledger row for HSI. | `--help` has `--top-k` (default 20), `--min-percentile` (0.0), `--ranking percentile`, `--lexical hybrid`, `--max-artifacts` (3000), `--seed` (42), `--model` (all-MiniLM-L6-v2), `--tier` (1). Results metadata fields equal the JHTV file. | THE SCRIPT |
| Shipped plugin `compute-hsi.py` | `/home/jsagi/dev/MindrianOS-Plugin/scripts/compute-hsi.py`, sha256 `bb0b76bb...` | Only `--tier --threshold --output --scope-to-nodes`. No top-k, no percentile, no `pairs_scored`. | Cannot have made the file |
| Eureka `hsi_reference.py` | `/home/jsagi/dev/mindrian-eureka/src/mindrian_eureka/hsi_reference.py`, sha256 `05023269...` | An adapted port packaged for MCP; not a CLI that writes a room result | Not the script |
| Command text in the JHTV room or Eureka repo | grep for `compute-hsi`, `top-k 200`, `--topk 200` in the room (excluding the input corpus) and in `/home/jsagi/dev/mindrian-eureka` | Only the two result JSON files mention `compute-hsi`; no file holds a command line | No recorded command exists |

### Proof that `--tier 1 --top-k 200` + defaults is the command (PROVEN)
- The script hashes its settings: `params_fingerprint(params)` = first 16 hex chars of sha256 of `json.dumps(params, sort_keys=True)`. Params: `tier 1, threshold None, ranking percentile, lexical hybrid, top_k 200, min_percentile 0.0, confirm_percentile 0.75, claim_level False, dense_vectors None, model all-MiniLM-L6-v2, seed 42, chunking True, allow_lexical_only False, schema_version "2.0", pinecone False`.
- Computed with the real function: `7affae3c94c6bed9`. The recorded value in `hsi-full-catalog.json` and in `engine-input-room/.hsi-cache.json` is `7affae3c94c6bed9`. Changing only `top_k` gives different hashes (20: `5b4b370a...`, 100: `0b2948b9...`, 500: `85c198f5...`). Script `hashcheck.py` in the scratch dir.
- A 40-file smoke run of the command gave the same `cache_params_hash` and the same metadata, key by key, except corpus-dependent values (`artifact_count`, `pairs_scored`, spectral summary, timestamps, `room_dir`).
- `pairs_scored 2239786` equals 2117 x 2116 / 2 (PROVEN by arithmetic).
- File stamps (INFERRED): `hsi-full-catalog.json` was written at 17:19:18.2918 and `.hsi-cache.json` at 17:19:18.2939, so `--output` pointed at `hsi-full-catalog.json`. `.hsi-results.json` (17:19:47) is a byte-identical later copy.

### Command to record
```bash
# Use system python3 (numpy 2.2.6, scikit-learn 1.8.0, sentence-transformers 5.3.0 = the JHTV versions).
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 \
  /home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/hsi/scripts/compute-hsi.py \
  <COPY_OF_engine-input-room> --tier 1 --top-k 200 --output <SCRATCH>/hsi-rebuild.json
```
RS command for the same run (INFERRED flags from the result metadata; PROVEN to give the same metadata on a smoke run):
```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RS_EMBEDDING_MODEL=minilm python3 \
  /home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py \
  --mode internal --room <COPY_OF_engine-input-room> --topk 200 --threshold 0.0 --no-thesis \
  --output <SCRATCH>/rs-rebuild.json
```
`--scoring`, `--min-percentile 0.9` and `--lex-weight 0.5` are defaults. Do not pass `--no-verify`.

### Verification steps (execution tasks; heavy, so UNVERIFIED here)
1. Copy `engine-input-room/` (the `technology/` folder only) to a scratch dir. Never run into the JHTV room. Both scripts write cache and result files into the room argument.
2. Run the two commands. Expected time: a few minutes each.
3. HSI compare with `hsi-full-catalog.json`: `metadata.ranking.pairs_scored == 2239786`; `cache_params_hash == 7affae3c94c6bed9`; the ordered list `(left_id, right_id)` of the 200 `hsi_pairs` is equal; `hsi_score` within 1e-3. First pair: `technology/C11722` + `technology/C15549`; second: `technology/C14402` + `technology/C15631`.
4. RS compare with `rs-full-catalog.json`: 200 pairs; ordered `(source_artifact_id, target_artifact_id)` equal; `hybrid_signed_gap` within 1e-3. First pair: `technology/C12269` + `technology/C17993`.
5. If the order differs: report overlap at 200 and the first differing rank; check library versions first. Do not claim "reproduced" on a set match alone.
6. Write the result and both commands to `docs/hsi-rs-jhtv-reproduction.md`. Record: script paths and sha256, the command lines, python and library versions, input corpus hash (`engine-input-manifest.json` has per-file sha256), output sha256.
If the full run does not match, the record still states the command, with "settings reproduced, ranking not reproduced" and the measured difference.

## REL-02: Where the fidelity text goes

### Current wording (quoted)
- `README.md` line 214, table "Readiness at a glance": `| RS opportunity-pair discovery | Runnable CLI and durable stdio MCP jobs; experimental pending evaluation. |`
- `README.md` line 244: `This repo has no blanket license because some source-derived methods still need rights review.`
- `README.md` has NO sentence about RS fidelity, the original package, or bit-for-bit (grep returned none).
- `pyproject.toml`: `description = "Local-first, evidence-linked opportunity discovery capabilities for MindrianOS"`. No `readme`, `license`, `classifiers`, or `[project.urls]` key.
- `capabilities/opportunity.find_cross_domain_pairs/manifest.json` line 17: `"Reference mode is based on source-analysis notes and has not been proven bit-for-bit equivalent to the original package."`
- `src/mindrian_eureka/data/capability-catalog.v1.json` (RS entry) limitations: `"Reference equivalence to the original RS package and model evaluation remain open."` (no "bit-for-bit" words)
- `src/mindrian_eureka/opportunity_pairs/runner.py` line 199 (result `limitations`): `"The reference BERT mode follows the documented source method; bit-for-bit equivalence to the original package has not been established."`
- `docs/engines/opportunity-pairs.md` line 120: "The implementation is **not yet verified bit-for-bit** against the PPTX package; original source availability, author attribution, and licensing must be resolved before production distribution."

### Edit locations
1. `README.md`: add a short section "Reverse Salient (RS) fidelity" after "Readiness at a glance", and extend the RS row. Plain words, no jargon.
2. `pyproject.toml`: add `readme = "README.md"` so the statement ships in the wheel metadata (`dist/mindrian_eureka-0.1.0-py3-none-any.whl` exists; rebuild is not needed in Phase 1). Append a short clause to `description`, for example "RS ranking is not verified bit-for-bit against its original source." Do NOT add a `license` key or a license classifier: that is a rights statement and belongs to REL-01.
3. Keep the capability manifest, the catalog entry and the `docs/engines/opportunity-pairs.md` paragraph consistent. Check for a test that compares `capabilities/*/manifest.json` with the catalog before editing either (grep `tests/test_capability_cli.py` in the plan).
4. Update the `docs/engines/opportunity-pairs.md` line that says the original package is "not present in this checkout": the files exist on the maintainer machine (paths and hashes in the REL-01 record). Keep "not in this repo".

### What the text must say (all PROVEN deviations from the original five files)
Read directly from the original `lsa.py`, `sts_bert.py`, `comparison.py`:
- D1 The original splits text with `split(" ")`; both ports split on any whitespace.
- D2 The original removes NLTK English stop words before TF-IDF, in addition to scikit-learn's list; both ports skip the NLTK step.
- D3 The original BERT step feeds raw 512-token segments with no `[CLS]`/`[SEP]`; Eureka uses 510 tokens plus the two special tokens.
- D4 The original BERT matrix is `(m - mean(m)) / max|m| + 0.5` and then min-max rescaled; Eureka uses `max|m - mean|` and no second rescale (the final range differs; this matters for `legacy` scoring only; z-scores in `hybrid_2026` remove it). The invariance claim is INFERRED from the formulas.
- D5 The original ranks by `|bert - lsa|` and shows the top 1000. Eureka's default `hybrid_2026` (BM25 mix, z-gap, percentile gate) is NOT in the original. It is the LATEST 2026 extension.
- D6 The JHTV run used MiniLM, not `bert-large-cased`.
- D7 Small corpora use fewer than 80 topics (documented adaptation).
- D8 The top-7 term tie-break differs from the original (fixable; see ENG-02).
- D9 The original reads cleaned Scopus abstracts; Eureka reads whatever the caller supplies.
Suggested plain sentence: "Eureka's RS ranking is a reimplementation of a method from research code. It has not been checked bit-for-bit against that code, and its default scoring adds steps the original does not have. Treat results as leads."

## Plans and waves (split proposal)

| Plan | Requirements | Wave | Files touched | Depends on |
|------|--------------|------|---------------|------------|
| 01-01 Provenance and release-gate record (draft, `no-go`) + presence test + human checkpoint to set `decided_by`/`decided_on` | REL-01 | 1 | `docs/rs-release-gate.md`, `docs/licensing-and-provenance.md` (link), `tests/test_release_gate_record.py` | none |
| 01-02 HSI and RS command recovery: write the record, run both commands on a scratch copy, compare, record the result | ENG-03 | 1 | `docs/hsi-rs-jhtv-reproduction.md` | none (read-only on the JHTV room) |
| 01-03 Parity test, layers 1-3 with synthetic fixture and golden; layer 4 optional; report output | ENG-01 | 1 | `tests/test_rs_engine_parity.py`, `tests/fixtures/rs_parity/*`, optional `scripts/generate_rs_parity_golden.py` | none |
| 01-04 Path C small fixes (stable tie-break; clip decision; keep `top_k` cap decision for Phase 2) + parity tightening | ENG-02 (evidence) | 2 | `src/mindrian_eureka/opportunity_pairs/algorithm.py`, tests | 01-03 |
| 01-05 Canonical-path record `docs/rs-engine-parity.md` with the parity result, plus owner decision on dense-input rule | ENG-02 | 2 | `docs/rs-engine-parity.md`, `docs/engines/opportunity-pairs.md` | 01-03, 01-04, and 01-02 (for the JHTV overlap number) |
| 01-06 Fidelity wording in README, `pyproject.toml`, manifest, catalog, engine guide | REL-02 | 3 | `README.md`, `pyproject.toml`, `capabilities/opportunity.find_cross_domain_pairs/manifest.json`, `src/mindrian_eureka/data/capability-catalog.v1.json`, `docs/engines/opportunity-pairs.md` | 01-01, 01-05 (wording depends on both) |

Plans 01-01, 01-02 and 01-03 touch disjoint files and can run in parallel in wave 1. Plan 01-04 changes `algorithm.py`; keep it out of wave 1 so the parity test first records the "before" numbers.

Out of scope for Phase 1: any edit to `/home/jsagi/dev/MindrianOS-Plugin`; the `eureka run` command; lifting the `top_k` cap (note for Phase 2); pushing.

## Common Pitfalls

### Pitfall 1: Stale embedding cache hides or fakes a mismatch
**What goes wrong:** The Eureka cache key is text digest + encoder + model path + revision + method version. It does not include vector values. A stub that returns different vectors for the same text and model name still hits the old rows. PROVEN: the first synthetic comparison showed overlap 0.68 only because `syn_cache.sqlite3` held vectors from an earlier run; with a fresh cache it was 1.0.
**How to avoid:** Every test passes `cache_path=tmp_path / "x.sqlite3"`. Use a distinct stub model name per vector set.
**Warning signs:** Results change when a test is run twice with different stubs.

### Pitfall 2: Reference scripts write into the room they read
**What goes wrong:** B writes `.rs-engine-cache.json`, `.rs-engine-results.json` and, if `.mindrian/room.db` exists, graph edges. `compute-hsi.py` writes `.hsi-cache.json`, `.hsi-results.json`. A cache hit makes `compute-hsi.py` skip work.
**How to avoid:** Always use a scratch copy. Pass `--output` to scratch. Delete cache files before a verification run.

### Pitfall 3: Wrong script, right-looking name
**What goes wrong:** Three `rs-engine.py` files and three `compute-hsi.py` files exist. The installed plugin copy looks right and is wrong.
**How to avoid:** Every record states the sha256 of the script used. The parity test header and the reproduction record print it.

### Pitfall 4: Comparing at different library versions
**What goes wrong:** `.venv` has numpy 2.5.4, scikit-learn 1.9.1; the JHTV run used 2.2.6 and 1.8.0. LSA was identical across the two on the synthetic corpus (PROVEN), but real-corpus behaviour is UNVERIFIED. The randomized SVD could differ.
**How to avoid:** Run the JHTV reproduction with system `python3`. Run the committed-fixture tests in both; keep the thresholds above.

### Pitfall 5: Treating a low overlap as a bug in the ranker
**What goes wrong:** Overlap 0.42 on real MiniLM looks like a failure. It comes from dense inputs. Layer 1 and layer 3 show the ranker is equal.
**How to avoid:** Keep the layers separate; print per-layer results.

### Pitfall 6: Putting real JHTV text in the repo
**What goes wrong:** The 40-file smoke used real catalog text. Committing it would break `CONTRIBUTING.md` ("synthetic or explicitly approved evaluation data").
**How to avoid:** The committed fixture is the synthetic corpus described above. Scratch files stay in the scratchpad.

### Pitfall 7: Committing over peer edits
**What goes wrong:** `git status` shows many modified and untracked files under `story/`.
**How to avoid:** `gsd-tools query commit ... --files <explicit list>`; never `git add -A`.

## Code Examples

### Seed B's cache so it runs offline (PROVEN pattern, script `syn2.py`)
```python
# Source: /home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/rs/shared/scripts/rs-engine.py lines 839-875, 953-962
cache = {a["id"]: {"hash": hashlib.sha256(a["text"].encode()).hexdigest()[:16],
                   "model": "all-MiniLM-L6-v2", "vector": vec.astype("float32").tolist()}
         for a, vec in zip(artifacts, vectors)}
(room / ".rs-engine-cache.json").write_text(json.dumps({"version": "1", "embeddings": cache}))
# run: RS_EMBEDDING_MODEL=minilm python3 rs-engine.py --mode internal --room <room> --topk 100 --threshold 0.0 --no-thesis --no-verify --output out.json
```

### Eureka side with the same vectors (pattern from `tests/test_rs_hybrid_2026.py`)
```python
import mindrian_eureka.opportunity_pairs.runner as runner
class Stub:
    def __init__(self, *a, **k): ...
    def encode(self, texts, cancel_check=None):
        return np.stack([vectors_by_model_text[t.strip()] for t in texts]).astype(np.float64)
monkeypatch.setattr(runner, "SentenceTransformerEncoder", Stub)
result = runner.run_document(doc, encoder_name="sentence-transformers", model_path="stub-v1",
                             top_k=100, scoring="hybrid_2026", min_percentile=0.9,
                             cache_path=tmp_path / "c.sqlite3")
```

### Metrics with numpy only
```python
def overlap_at(a, b, k): return len(set(a[:k]) & set(b[:k])) / k
def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])
```

### Stable top-7 term order (tie-break fix; PROVEN to bring LSA within 2.8e-8)
```python
# replaces: top = np.argsort(component)[-7:][::-1]
top = [i for i, _ in sorted(enumerate(component), key=lambda x: x[1], reverse=True)[:7]]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `abs(semantic - lsa)` with fixed 0.30 cutoff (path A, shipped) | z-score gap + BM25 mix + percentile gate (path B, path C) | LATEST package, 2026-10-09 (parked copy) | Different candidates; fidelity claims apply to the old form only |
| Top-1000 `|bert - lsa|` (original) | `top_k` capped at 100 (path C) | Eureka 2026-10 | JHTV top-200 cannot be reproduced by path C |
| `compute-hsi.py` threshold 0.30 (shipped) | percentile ranking with `--top-k` (LATEST) | LATEST package, 2026-10-08 | The shipped plugin cannot make the JHTV HSI file |

**Deprecated or outdated in the Eureka docs:** the statement that the original package is absent. It is absent from the repo only.

## Runtime State Inventory

Not a rename or migration phase. Omitted on purpose. One note: the JHTV room holds cache and result files (`.hsi-cache.json`, `.hsi-results.json`, `.rs-engine-cache.json`) that a careless re-run would change. Work on a copy.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RS `--output` pointed to `../rs-full-catalog.json` and HSI `--output` to `../hsi-full-catalog.json` (from missing default files and file stamps) | ENG-03 | Low. Output path does not change numbers. |
| A2 | The 40-file overlap (0.42) is indicative for the full 2117-file top-200 | ENG-01 | Medium. Real overlap could be higher or lower. A full run in execution settles it. |
| A3 | `.venv` library versions give the same real-corpus LSA as system versions | Pitfalls | Medium. Test with the JHTV copy in both. |
| A4 | A pytest dev group can be added to `pyproject.toml` and `uv.lock` | Standard Stack | Low. Needs network; fall back to `PYTHONPATH=src pytest`. |
| A5 | pytest is a legitimate PyPI package at its current version | Package Legitimacy | Low. Not checked with slopcheck. |
| A6 | Default decision `no-go` is the right draft state | REL-01 | Low. A human sets the final value. |
| A7 | D4 (BERT matrix normalization difference has no effect on `hybrid_2026`) | REL-02 | Low. z-score is affine invariant by construction. |

## Open Questions

1. **Which dense-input rule is canonical for path C?**
   - Known: path B embeds the body only, one pass, truncated; path C embeds title + body, chunk-mean. Overlap on a 40-file sample is 0.42.
   - Unclear: whether the owner wants JHTV-compatible output (B rule) or full-text coverage (C rule).
   - Recommendation: keep path C as is and record B as the JHTV reference. NEEDS_HUMAN: confirm "Is path C chunk-mean on title + body the accepted canonical dense rule?"
2. **May the REL-01 record state `go`, `internal-only` or `no-go`?**
   - Known: G1, G2, G3, G5 are open.
   - Recommendation: write `no-go`, `status: draft`; a human decides. NEEDS_HUMAN: set `decided_by` and `decided_on`.
3. **May the record name the source author in a tracked file?**
   - Known: the name already appears in the plugin repo and in a Eureka `.cjs` comment ("Kwan 2023"). An owner rule bars real names of testers or advisors in tracked repos. The author is neither, but the rule is close.
   - Recommendation: keep the name; flag it for the owner in the checkpoint task.
4. **Where can the deck and any hand-over message be found?**
   - Known: not on disk by name search. 
   - Recommendation: add to the gap list; owner searches mail or chat.
5. **Will the real-corpus LSA match across library versions?**
   - Recommendation: include one check in plan 01-02.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| system `python3` | JHTV reproduction | yes | 3.12.3 (numpy 2.2.6, sklearn 1.8.0, ST 5.3.0) | none needed |
| repo `.venv` | tests | yes | 3.12.12 (numpy 2.5.4, sklearn 1.9.1, ST 5.7.0) | system python |
| `uv` | repo workflow | yes | 0.9.4 | none |
| pytest | tests | yes (system only) | 9.0.2 | `PYTHONPATH=src /home/jsagi/.local/bin/pytest tests` |
| MiniLM weights | layer 4, reproduction | yes | `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` (2 snapshots) | stubs for layers 1-3 |
| Reference RS script (B) | live legs | yes | `/mnt/c/Users/jsagi/Downloads/research/LATEST/...` and plugin `r-and-d/` | committed golden |
| Reference HSI script | ENG-03 | yes | same two locations | none |
| Original `similarity_code` | optional oracle leg | yes | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/` | skip |
| NLTK stopwords data | optional oracle leg | no | `nltk.corpus.stopwords` raises LookupError | skip the oracle leg; network is not allowed |
| seaborn | running original `lsa.py` as is | no | import fails | not needed; the oracle leg re-derives only the steps |
| Network | none | n/a | not used | all runs used `HF_HUB_OFFLINE=1` |

Baseline test suite (PROVEN): `PYTHONPATH=src pytest tests -q` finishes in about 21 s with no failures (some skips).

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json`. The formal section is omitted. The parity test design above is the test plan for this phase.

Quick run: `PYTHONPATH=/home/jsagi/dev/mindrian-eureka/src /home/jsagi/.local/bin/pytest tests/test_rs_engine_parity.py -q -p no:cacheprovider`. Full run: `PYTHONPATH=src pytest tests -q -p no:cacheprovider`. Wave 0 gaps: `tests/test_rs_engine_parity.py`, `tests/fixtures/rs_parity/`, `tests/test_release_gate_record.py`, and the pytest declaration decision.

## Security Domain

`security_enforcement` is on (ASVS level 1). Phase 1 adds no network surface, no auth, no user input parser.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | none |
| V3 Session Management | no | none |
| V4 Access Control | no | none |
| V5 Input Validation | limited | The parity test feeds fixed JSON through the existing `validate_document` path |
| V6 Cryptography | no | sha256 from `hashlib` for records only |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Running a reference script that writes into a room | Tampering | Scratch copy; explicit `--output` |
| Importing a reference script by path executes its code | Elevation | Use only the two known paths whose sha256 is in this file; the test prints the sha256 and refuses a mismatch |
| Room text leaking into the repo or to a service | Information disclosure | Synthetic fixtures only; no Theo, Brain or web calls; scratch files stay outside git |
| Network use by model loaders | Information disclosure | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` in every command |

## Sources

### Primary (read or run in this session, HIGH confidence)
- `/home/jsagi/dev/mindrian-eureka/src/mindrian_eureka/opportunity_pairs/{algorithm,runner,encoders,cli}.py`
- `/home/jsagi/dev/mindrian-eureka/docs/{engine-source-ledger,licensing-and-provenance,open-decisions,algorithm-origins-and-rationale}.md`, `docs/engines/opportunity-pairs.md`, `README.md`, `pyproject.toml`, `capabilities/opportunity.find_cross_domain_pairs/manifest.json`, `src/mindrian_eureka/data/capability-catalog.v1.json`, `CONTRIBUTING.md`
- `/home/jsagi/.claude/plugins/cache/mindrian-marketplace/mos/2.0.0-beta.73/scripts/rs-engine.py`, `/home/jsagi/dev/MindrianOS-Plugin/{scripts/rs-engine.py,scripts/compute-hsi.py,lib/core/rs_math.py,LICENSE}`
- `/home/jsagi/dev/MindrianOS-Plugin/r-and-d/breakthrough-engines/engines/{rs,hsi}/...` (scripts and `rs_math.py`)
- `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/{rs/shared/scripts/rs-engine.py,hsi/scripts/compute-hsi.py}`
- `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/*.py`
- `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/{PLAN,RESEARCH,ALGORITHM-SOURCE}.md` and `source/*.py`
- `/home/jsagi/MindrianOS/research/2026-09-23-origin-concept-algorithmic-generation-of-rs-solutions.md`
- `/home/jsagi/MindrianRooms/jhtv-oliver-kuntz/solution-design/full-catalog-run-2026-10-18/{rs-full-catalog.json,hsi-full-catalog.json,mindrian-eureka-jhtv-workflow-review.md,prepare_engine_corpus.py,engine-input-room/.hsi-cache.json}`
- Smoke scripts and outputs in `/tmp/claude-1000/-home-jsagi/5a1774bc-a933-4bca-9f46-2d886586e3b1/scratchpad/` (`run_repo.py`, `compare.py`, `attrib.py`, `attrib2.py`, `tie.py`, `syn.py`, `syn2.py`, `syn3.py`, `syn5.py`, `envcmp.py`, `hashcheck.py`, `b_out.json`, `repo_out.json`, `hsi40.json`)

### Secondary / Tertiary
- None. No web search was used. No room content went to Theo, Brain or the web.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - read from files and live interpreters.
- Architecture (three paths, ranker equality): HIGH - proven by sha256 and by controlled runs.
- Pitfalls: HIGH - three were hit during this research.
- REL-01 gaps: HIGH for what is on disk; the legal meaning is out of scope.
- Full-corpus reproduction: UNVERIFIED - not run by rule.

**Research date:** 2026-10-23
**Valid until:** 2026-11-22, or until any of the three scripts, the plugin cache, or the JHTV room files change (re-check the sha256 values first).
