# Phase 2: One-Command Run and Doctor - Research

**Researched:** 2026-10-24
**Domain:** Python CLI orchestration of two local pair-ranking engines, reproducible run manifests, offline setup checks
**Confidence:** HIGH for engine calls, caps, nondeterminism and tooling (read from code and run on this machine). MEDIUM for CSV mapping design (partner headers not received). LOW for enclave specifics (OS and install route unknown).

Tags used below: `[VERIFIED: file:line]` = read in code or run in this session. `[ASSUMED]` = reasoned or from memory, needs confirmation. Engine names: "the unusual-pairs engine" is "Find Unusual Pairs Across a Research Collection" (capability `opportunity.find_cross_domain_pairs`, path `eureka-pair-scout`, scoring `hybrid_2026`). "The wording-and-meaning pairs engine" is "Rank Unusual Pairs by Wording and Meaning" (capability `portfolio.find_hybrid_similarity_pairs`). Code identifiers keep their literal names.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Engine calls (from Phase 1)
- Unusual-pairs engine path = repo `eureka-pair-scout` (docs/rs-engine-parity.md section 3). Plugin script and r-and-d script are not called.
- Wording-and-meaning engine settings = the recorded rebuild: tier 1, top-k 200, on a scratch copy (docs/hsi-rs-jhtv-reproduction.md).
- Lift the top_k cap from 100 to 200 and the artifact cap from 2500 so a 2,117+ record collection is not silently truncated. Truncation must be reported in output and manifest, never silent. Update test_clip_and_cap_decisions_are_documented.
- Record engine version and the stable tie-break rule (stable descending top-7 term sort) in the manifest.

#### Run behavior
- `eureka run` builds a clean corpus first with stable record IDs (what prepare_engine_corpus.py does for the JHTV run), then calls both engines.
- Run manifest fields: input file hashes, record counts, settings, seeds, library and model versions, output file hashes, caps hit.
- Two runs on the same input give byte-identical ranked output; a test proves it (RUN-04).
- Every output file carries "candidate, not verified" and a score-meaning note (RUN-05).
- Works on a scratch copy of the input; never writes into the source folder.

#### Doctor behavior
- Checks Python version, uv, local model presence, cache dir and data dir permissions (owner-only). Each failure prints the exact fix command. A missing model is a clear message and a non-zero exit, never a silent skip (DOC-01, DOC-02).
- Offline: doctor and run make no network calls. No model downloads.

#### Skill-derived constraints
- python-pro: full type hints, `mypy --strict` clean on new modules, ruff clean, dataclasses for manifest and settings, pathlib not os.path, `X | None`, no bare except, no mutable defaults, Google-style docstrings, pytest with fixtures and parametrize.
- cli-developer: `--help` and `--version` work; diagnostics and progress go to stderr, results to stdout or files; no color when not a TTY; non-interactive by default (enclave and CI safe); clean Ctrl+C exit; distinct exit codes (0 ok, 1 failure, 2 usage); consistent flag names; do not rename existing `eureka` subcommands; shell completion if the CLI framework in use supports it cheaply. Skip the 50ms startup target (model load cannot meet it) and say so.
- ml-pipeline (reproducibility parts only): pin and record seeds and library versions; validate input schema before ranking and stop with a clear message on bad input; hash inputs and outputs. No MLflow, Kubeflow or Feast.
- mcp-developer: if the run is exposed through the MCP server in this phase, validate inputs with a schema and return structured errors; wiring /mos:eureka is Phase 3.
- Install target: Oliver's secure-enclave machine, local, shared-screen guidance, no data leaves. Docker path must not regress (Dockerfile, scripts/run-mcp-container).

### Claude's Discretion
- Module layout under src/mindrian_eureka, CLI framework already used in cli.py, input column mapping for CSV (headers not yet received from the partner; make mapping configurable by flags or a small mapping file), fixture design.

### Deferred Ideas (OUT OF SCOPE)
- Hub page (Phase 2.1), MCP /mos:eureka wiring and graph-derive replay rebuild (Phase 3), public example and reproduction guide (Phase 4), password gate (HUB-04).
- Domain-aware filtering, near-duplicate handling (v2).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RUN-01 | `eureka run <folder>` of CSV or Markdown gives ranked pairs from both engines | Section "Engine calls" (exact call per engine), "CLI structure", "Corpus builder" |
| RUN-02 | Clean corpus with stable IDs first | Section "Corpus builder" (ID rules, collision stop, short-record rule), reference script behavior |
| RUN-03 | Run manifest with hashes, counts, settings, seeds, versions, output hashes | Section "Manifest design" |
| RUN-04 | Two runs give identical ranked output, test proves it | Section "Nondeterminism", "Validation Architecture" (stub encoder, cold and warm cache) |
| RUN-05 | Every output file keeps "candidate, not verified" and score-meaning notes | Section "Output files and labels"; polarity pitfall (labels mean opposite things in the two engines) |
| DOC-01 | `eureka doctor` checks Python, uv, model, cache and data dir permissions with exact fix | Section "Doctor design" |
| DOC-02 | Missing model gives clear message, non-zero exit | Section "Doctor design" check D4, run pre-flight |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Offline by default: no network calls; models must already be on disk.
- Determinism: ranking is code, no LLM; seeds and versions are recorded in result provenance.
- Honest labels: every output keeps "candidate, not verified" wording.
- Privacy: embeddings are derived sensitive data; cache and job data stay local with owner-only permissions.
- GSD workflow: all repo edits go through a GSD command (planner and executor concern).
- Repo rules (CONTRIBUTING.md, SECURITY.md): no private room exports, no personal names, no real user data in the repo; use synthetic fixtures. Treat job stores, embeddings, logs and rendered artifacts as sensitive.
- Owner rules (global): no em-dashes anywhere; plain English; never bare "RS" or "HSI" in user-facing text; subagents use STE-style English and fixed report fields.
- Existing tests check `docs/rs-engine-parity.md` for em-dashes and for exact numbers in sections 3 and 3.1 (tests/test_rs_engine_parity_record.py:187-188, 150-157). Any doc edit must keep both.

## Summary

The wording-and-meaning engine IS in this repo. `src/mindrian_eureka/hsi_reference.py` is a near-verbatim copy of the reference script `compute-hsi.py` (it differs from the r-and-d copy with sha256 `5756c84f...` only by a missing `--scope-to-nodes` option and one added key, `surprise_type_meaning`; checked with `diff`). `src/mindrian_eureka/hsi_engine.py` is a JSON-in adapter around it. The adapter `run_hsi` cannot reproduce the recorded rebuild: it caps `top_k` at 100 (hsi_engine.py:64), caps artifacts at 2500 (:34), and builds the dense signal with token chunks (encoders.py:25-48) instead of the reference rule of 200-word chunks, at most 12 per record (hsi_reference.py:504-533). `eureka run` must therefore call the building blocks of `hsi_reference` directly, in the same order as `hsi_reference.main` steps 3 to 5, with a locally loaded encoder. I confirmed that the parameter set of the recorded run hashes to `7affae3c94c6bed9` through `hsi_reference.params_fingerprint` in this repo (run in this session), so the manifest can carry that hash as a cross-check.

The unusual-pairs engine call is `opportunity_pairs.runner.run_document(...)` with `encoder_name="sentence-transformers"`, `scoring="hybrid_2026"`, `top_k=200`, defaults `lex_weight=0.5`, `min_percentile=0.90`. Only three things vary between two in-process runs of each engine: `runner.started_at`, `runner.finished_at`, `resource_use.duration_ms` (unusual-pairs) and `metadata.generated_at` plus `source_trail[].retrieved_at` (wording-and-meaning). I measured this by running each engine twice on the parity fixture. A projected output file that drops those fields is byte-identical. Real-model embeddings were bit-identical across repeats and across 1, 4 and 12 torch threads on this machine (60 texts, MiniLM).

`prepare_engine_corpus.py` exists at `/home/jsagi/MindrianRooms/jhtv-oliver-kuntz/solution-design/full-catalog-run-2026-10-18/prepare_engine_corpus.py` (57 lines). It is JHTV-specific (three fixed CSV names, HTML cleanup, one Markdown file per record under `technology/`). It silently overwrites on a file-name collision and silently relies on the engine to drop bodies under 50 characters. Port its logic (not its data) into a generic, configurable corpus builder that stops on collisions and reports every drop. `mypy --strict` fails today on `cli.py`, `runner.py` and `hsi_engine.py` (15 errors), so strict typing applies to new modules only, behind a typed facade for the untyped `hsi_reference`. mypy 1.19.1, ruff 0.14.10 and pytest 9.0.2 exist only as user-level tools on PATH (`~/.local/bin`), not as project dependencies and not in `uv.lock`; the repo `.venv` has no pytest.

**Primary recommendation:** Add a new `mindrian_eureka/run/` package (corpus, typed engine facade, pipeline, manifest, writers) and `mindrian_eureka/doctor.py`; wire both into `cli.py` as lazy-importing argparse subcommands; call `run_document` for the unusual-pairs engine and the `hsi_reference` building blocks (not `run_hsi`) for the wording-and-meaning engine; write only projected, timestamp-free, rounded, canonical JSON plus Markdown; keep all volatile data in a separate `run-info.json`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read CSV and Markdown, build clean corpus, stable IDs | CLI process (local Python) | Filesystem (read-only source) | Pure local transform; source folder is never written |
| Dense embeddings (MiniLM) | Local model on disk, in-process | Embedding cache (SQLite, owner-only) | Offline rule; model path discovered locally |
| Unusual-pairs ranking | `opportunity_pairs.runner` (library call) | Embedding cache | Canonical path decided in Phase 1 |
| Wording-and-meaning ranking | `hsi_reference` building blocks (library call) | none (no cache today) | Must reproduce recorded `main()` steps |
| Manifest, hashing, output writing | CLI process | Output folder on disk | Deterministic canonical writer |
| Doctor checks | CLI process (stdlib only, no heavy imports) | OS (permissions, PATH) | Must run before torch is importable |
| MCP exposure of `run` | Out of scope (Phase 3) | none | Phase 3 reuses the pipeline function |

## Answers to the eight research questions

### 1. How each engine is called today, and what `eureka run` must call

**Unusual-pairs engine (canonical path C).**
- CLI: `eureka-pair-scout` -> `opportunity_pairs/cli.py:15-47`. It reads a JSON bundle, calls `validate_request("opportunity.find_cross_domain_pairs", ...)` (cli.py:33) then `run_document(...)` (cli.py:34-39), then `validate_result` (cli.py:40). Runtime errors exit 2 through `parser.exit(2, ...)` (cli.py:47). Legacy; do not copy this exit code rule.
- Entry function: `runner.run_document(document, *, encoder_name, model_path, allow_model_download=False, top_k=20, scoring=None, lex_weight=None, min_percentile=None, job_id="local-rs-run", model_revision=None, cache_path=None, cancel_check=None, stage_callback=None)` (runner.py:31-37).
- Input: dict with `artifacts` list of `{id, title, text, source_ref, corpus}` (runner.py:49-52), optional `objective` (default "", runner.py:128; it does not change ranking, runner.py:198), `mode` default `"local"` (runner.py:46). `run_document` does not call `validate_document`; `load_input` does (runner.py:247). `eureka run` must call `validate_document(document)` (runner.py:251) itself.
- Settings (defaults): `scoring` `hybrid_2026`, `lex_weight` 0.5, `min_percentile` 0.90 (runner.py:108-110). Structural signal: `TfidfVectorizer(stop_words="english", max_features=2000, max_df=0.5)`, `TruncatedSVD(n_components<=80, algorithm="randomized", n_iter=10, random_state=256)` (algorithm.py:66-80), top 7 terms per topic with a stable descending sort (algorithm.py:84-86). Hybrid gate: fewer than 10 eligible pairs returns an empty list (algorithm.py:314-316, runner.py:121-122), so fewer than 5 records gives no candidates.
- Dense signal: `SentenceTransformerEncoder(model_path, allow_download=False)` (runner.py:83, encoders.py:11-21) loads with `local_files_only=True`; text = `title + "\n\n" + text` (algorithm.py:33-34); chunks of `max_seq_length - 2` tokens, batches of 16, chunk vectors averaged (encoders.py:25-48). Cache key includes `method_version="sentence-transformer-chunk-mean-v1"` (runner.py:88).
- Cap: `top_k` must be 0..100 (runner.py:38-39); artifact count at most 2500 in `validate_document` (runner.py:281-282).
- Cache: SQLite at `MINDRIAN_EUREKA_CACHE_DIR` or `~/.cache/mindrian-eureka/embeddings.sqlite3` (cache.py:141-144). Directory 0700, file 0600 (cache.py:30-48). The WAL and SHM side files are not chmod-ed (cache.py:45-49 touches only `self.path`); the 0700 directory protects them.
- Output: `eureka.result.v1` dict. Pair order is `-abs_gap`, then left id, then right id (algorithm.py:320). Pair id `rs-pair-<sha256(sorted ids)[:20]>` (runner.py:130-131).

**Wording-and-meaning engine.**
- It is in this repo twice: `hsi_reference.py` (1501 lines, the reference script copy with its own `main`, hsi_reference.py:1234) and `hsi_engine.py` (120 lines, adapter `run_hsi`, hsi_engine.py:32).
- The recorded rebuild (`compute-hsi.py <room> --tier 1 --top-k 200`) is `hsi_reference.main` with defaults. Its steps: discover Markdown (hsi_reference.py:198-241), cap with `--max-artifacts 3000` by sorted id (1254-1258), `compute_lsa_similarity(texts, seed=42)` (1303, 423-457: TF-IDF 500 features, `TruncatedSVD(random_state=42)`), `compute_bm25_similarity` (1304), lexical = `0.5 * (lsa + bm25)` (1310), tier 1 dense via `make_sentence_transformer_encoder("all-MiniLM-L6-v2")` + `compute_semantic_similarity_tier1(texts, encoder, chunk_words=200)` (1339-1343, 536-548: 200-word windows, at most 12 per record, unit-normalized, summed, cosine, clipped to 0..1), then `compute_hsi_matrix(..., ranking="percentile", top_k=200, min_percentile=0.0, confirm_percentile=0.75)` (1365-1370, 1027-1163).
- Why `run_hsi` is NOT the call: (a) `top_k` capped at 100 (hsi_engine.py:64-65); (b) 2500 artifacts (hsi_engine.py:34-35); (c) its dense step uses the token-chunk `SentenceTransformerEncoder` and reads `MINDRIAN_EUREKA_HSI_MODEL_PATH` (hsi_engine.py:92-96), which is a different dense rule than the recorded run; (d) it stamps `datetime.now` (hsi_engine.py:103). `run_hsi` stays as the MCP adapter (Phase 3).
- `make_sentence_transformer_encoder` calls `SentenceTransformer(model_name)` without `local_files_only` (hsi_reference.py:493-501). Do not use it. Build the encoder from the local model folder with `local_files_only=True` and pass it as `encoder=` to `compute_semantic_similarity_tier1`.
- Settings recorded in the output: tier 1, ranking percentile, lexical hybrid, top_k 200, min_percentile 0.0, confirm_percentile 0.75, model `all-MiniLM-L6-v2`, seed 42, chunking true, schema_version "2.0", `cache_params_hash` `7affae3c94c6bed9` [VERIFIED: reproduced with `hsi_reference.params_fingerprint` in this session; docs/hsi-rs-jhtv-reproduction.md section 2].
- Import side effects: importing `hsi_reference` prints "HSI: warning: lib/core/rs_corpus_exclude.py not importable..." to stderr (hsi_reference.py:152-156) [VERIFIED: seen on import in this session]. `hsi_engine` sets `HSI_NO_AUTO_INSTALL=1` before import (hsi_engine.py:16); `eureka run` must do the same before importing `hsi_reference` (hsi_reference.py:68-69). `compute_hsi_matrix` prints two progress lines to stderr (1060, 1067).

**What `eureka run` must call (exact):**
1. Unusual-pairs engine: `runner.run_document(doc, encoder_name="sentence-transformers", model_path=<local snapshot dir>, top_k=200, scoring="hybrid_2026", lex_weight=0.5, min_percentile=0.90, cache_path=<cache>, stage_callback=<stderr progress>)`.
2. Wording-and-meaning engine, in this order, through one typed facade module: `compute_lsa_similarity(texts, seed=42)`, `compute_bm25_similarity(texts)`, lexical `0.5*(lsa+bm25)`, `compute_semantic_similarity_tier1(texts, encoder=<local>, chunk_words=200)`, `compute_hsi_matrix(artifacts, lsa, semantic, threshold=None, lexical_matrix=lexical, bm25_matrix=bm25, ranking="percentile", top_k=200, min_percentile=0.0, confirm_percentile=0.75, computed_at=<constant>)`.
3. Both legs get the same artifact list sorted by id, and the same text per record (see Open Question 2).

### 2. Where the corpus build step lives and what `prepare_engine_corpus.py` does

Put it in `mindrian_eureka/run/corpus.py`. The reference script (read-only at `/home/jsagi/MindrianRooms/jhtv-oliver-kuntz/solution-design/full-catalog-run-2026-10-18/prepare_engine_corpus.py`; also referenced in 01-RESEARCH.md:552) does:
- Reads three fixed CSV files (`technologies.csv`, `jhu_technologies_engine.csv`, `categories.csv`) with `utf-8-sig`, joins them by case id and tech id.
- Cleans HTML with a stdlib `HTMLParser` subclass (skips `script`, `style`, `head`; newline at block tags), `html.unescape`, collapses spaces, limits blank lines to one.
- Writes one Markdown file per record into `technology/<case_id sanitized with [^A-Za-z0-9_.-]+ -> _>.md`. Content: front matter (title, source ids, url), `# title`, `Catalog record: <id>`, a category-path list, then the body. The record id seen by the engines is therefore `technology/<sanitized case id>`.
- Writes a manifest with `markdown_sha256` per record and a count of records with 50 or more body characters.
- Does NOT: detect two case ids that sanitize to the same file name (the second silently overwrites the first), drop short records (the engines do, silently, at `MIN_BODY_CHARS=50`, hsi_reference.py:159,230), or sort. Every Markdown file embeds the id and category text in the scored body, so those words influence both lexical and dense signals.

Prescriptions for the generic builder (port the logic, not the data; the HTML cleaner is stdlib-only):
- Record = `{id, title, text, source_ref, source_file, source_locator, text_sha256}`.
- ID rules: Markdown `<relative path without .md, posix>` (root-level files get their stem; the reference engine skips root-level files, hsi_reference.py:209-210, so this is a deliberate divergence to document). CSV `<file stem>/<sanitized id-column value>` using the same sanitizer `[^A-Za-z0-9_.-]+ -> _`; when the mapping has no id column, `<file stem>/h<first 12 hex of sha256(NFC text)>`. Row numbers are not used as IDs (they change when a partner re-sends the file).
- Stop (exit 1) on: duplicate IDs (list both sources), a missing id value, a record text over 1,000,000 characters (the limit in hsi_engine.py:45), total text over 20 MiB (runner.py:283-284), fewer than 2 usable records. Warn on fewer than 5 records (the unusual-pairs engine returns nothing under 10 eligible pairs).
- Drop and report (never silent): bodies under 50 stripped characters, with the list of dropped IDs and reason in the corpus report and manifest. Apply the 50-character rule in the builder so both engines see the same records. Without this, the HSI discover step would drop records the unusual-pairs engine keeps, and the two result sets would not describe one corpus.
- Normalize before hashing and ranking: `unicodedata.normalize("NFC", ...)`, `\r\n` and `\r` to `\n`, strip. Hash the raw file bytes separately for the manifest input hashes.
- Sort records by id (code-point order) once, at the end. Everything downstream depends on this order (see section 4).
- CSV reading: `csv` stdlib, `encoding="utf-8-sig"`, `newline=""`, explicit `--delimiter` (default comma). Raise `csv.field_size_limit` (default 131072 characters would fail on long descriptions) to the 1,000,000 record limit [ASSUMED: default limit is 131072 as in CPython docs; verify in a test with a 200,000 character cell].
- Text assembly from the mapping: `text` columns joined by a blank line, with an optional label line per column (the reference writes "Stated unmet need:"), optional `extra_fields` appended as "Label: value" lines, optional `value_maps` to decode coded values (the partner will send coded state values), optional HTML cleanup (`auto` = apply when the cell contains `<` followed by a letter).
- Mapping: a small JSON file validated with `jsonschema` (already a dependency), flags for the single-file case. Without a mapping or flags, a CSV stops the run with exit 2 and prints the headers it found plus a ready-to-edit mapping skeleton. This is how the pending partner headers drop in without code change. Multi-file joins (as JHTV did with three files) are out of scope; the user pre-joins, or use one mapping entry per file.
- Output of the builder into the run folder: `corpus/records.jsonl` (one canonical JSON line per record, sorted by id) and the corpus report inside the manifest. Never write into the source folder; refuse an `--out` inside the input folder.

### 3. Existing cap and clip logic and the exact lines to change

| Item | Where | Today | Change |
|------|-------|-------|--------|
| `top_k` limit in `run_document` | runner.py:38-39 | `top_k < 0 or top_k > 100`, message "top_k must be between 0 and 100" | Use `MAX_TOP_K = 200`; message "top_k must be between 0 and 200" |
| Artifact limit in `validate_document` | runner.py:281-282 | `> 2500`, "Artifact limit is 2,500 per run" | Use `MAX_ARTIFACTS` constant |
| Test that pins the cap | tests/test_rs_engine_parity.py:481-493 | calls with `top_k=101`, expects `ValueError` matching "top_k must be between 0 and 100" | Call with `top_k=MAX_TOP_K + 1`, match the new message; keep the first assertion (clip note, lines 483-484) and add one that `top_k=200` is accepted. Update comment at line 485 and docstring at line 482 ("top_k at most 100") |
| Module docstring decision line | tests/test_rs_engine_parity.py:33 | "Phase 2 must lift it to 200" | Reword to "lifted to 200 in Phase 2" |
| Docs | docs/rs-engine-parity.md:133, 136, 162 | Rows say path C raises above 100 and rejects above 2500; section 7 row says "Phase 2 must lift it" | Update to "lifted to 200 / 3000 in Phase 2". Keep the word `top_k` in section 7 (tests/test_rs_engine_parity_record.py:174), keep the tie-break row containing "fixed" (line 227), no em-dash (line 187-188) |
| Wording-and-meaning adapter | hsi_engine.py:34-35, 64-65 | 2500, 100 | Use the same constants (consistency; `eureka run` does not call this path) |

Clip: there is no clip in path C by owner decision (docs/rs-engine-parity.md section 7, test lines 483-484 via `_layer3b_negative_cosine`). Do not add one. The wording-and-meaning engine clips cosine to 0..1 by design (hsi_reference.py:457, 548); leave it.

Artifact cap value: both reference scripts end at or above 2117 only with an explicit cap (the unusual-pairs reference script defaults to 2000 through `RS_MAX_ARTIFACTS`, the wording-and-meaning script to 3000 through `--max-artifacts`; docs/hsi-rs-jhtv-reproduction.md sections 1-3). Recommend `MAX_ARTIFACTS = 3000` in a new `src/mindrian_eureka/limits.py` with `MAX_TOP_K = 200`, and `eureka run --max-artifacts N` (hard ceiling 5000). Memory is quadratic: the recorded wording-and-meaning run peaked near 1.7 GB at 2117 records (docs/hsi-rs-jhtv-reproduction.md section 2), so 3000 records is roughly 3.4 GB [ASSUMED: scaling by n squared]. Behavior above the cap: deterministic truncation to the first N ids in sorted order (this is what the reference does, hsi_reference.py:1254-1258), a warning on stderr, a line in every output header, and `caps_hit` in the manifest with limit, records in, records used, dropped count and a sha256 of the dropped id list. A `top_k` above 200 is a usage error (exit 2), not a truncation. Also record `top_k_reached` (returned pairs equal `top_k`) per engine.

Other surfaces that still say 100 or 2500 and stay stricter until Phase 3: `mcp_server.py:59-60, 71-72`; `data/schemas/cross-domain-pairs-input.v1.json:122,129`; `hsi-pairs-input.v1.json:60,89`; `discovery-signals-input.v1.json:101-131`; `opportunity_discovery.py:26`; `discovery_workflows.py:298-300`. Consequence: `eureka-pair-scout --top-k 200` still fails schema validation at cli.py:33. Recommend a test that asserts the constants equal what the schemas allow only for the surfaces `eureka run` uses, and list the rest as a Phase 3 item. Decision for the planner: lifting all surfaces now is possible but widens the change into MCP; this research recommends not doing it.

### 4. Sources of nondeterminism and how to get byte-identical output

Measured in this session (system python 3.12.3, numpy 2.2.6, scikit-learn 1.8.0): two in-process runs of each engine on `tests/fixtures/rs_parity/corpus.json` with the stored vectors differ only in `runner.started_at`, `runner.finished_at`, `resource_use.duration_ms` (unusual-pairs) and `metadata.generated_at`, `hsi_pairs[].source_trail[].retrieved_at` (wording-and-meaning). The ranked `outputs` hash was equal. MiniLM encoding of 60 texts (16 to 700 words) was bit-identical on repeat and with 1, 4 and 12 torch threads [VERIFIED: experiment in scratchpad].

| Source | Evidence | Effect | Control |
|--------|----------|--------|---------|
| Timestamps and durations | runner.py:42,167,169; hsi_engine.py:103; hsi_reference.py:1147 | Changes bytes every run | Never copy them into hashed files. Project engine results to a fixed field list. Pass a constant `computed_at`. Put real times only in `run-info.json` |
| Absolute paths | `room_dir` in `hsi_reference.main` metadata (1441); model path in `runner` `model_provider` (181) | Differs by machine and folder | Projection omits them. Manifest stores relative input names and model file digests, not absolute paths |
| File discovery order | `os.walk` with unsorted `dirs` (hsi_reference.py:203-205); only files are sorted (214) | Artifact order, and so tie order, can change with directory layout | Own walker with `sorted(rglob)` on posix relative path; final sort by id |
| Tie order | HSI uses `np.argsort(-rounded, kind="stable")` over pair index (hsi_reference.py:1099-1101) with scores rounded to 4 decimals; many ties | Order of tied pairs equals artifact order | Corpus sorted by id gives a fixed pair index. The unusual-pairs ranker ties on ids (algorithm.py:320) |
| Python sets | algorithm.py:82-87 (membership only), :229 (counting, then sorted), hsi_reference.py:512,670 (sorted); `PYTHONHASHSEED` has no effect on any output order I found | None | Do not iterate a set into output. Add a lint-style test that the projection sorts keys |
| Dict order | JSON writers keep insertion order | Order of keys | `json.dumps(..., sort_keys=True)` in one canonical writer |
| Random seeds | SVD `random_state=256` (algorithm.py:79) and `42` (hsi_engine.py:70, hsi_reference.py:448) | Fixed | Record both in the manifest |
| Threads and BLAS | torch intra-op threads; OpenBLAS threads 12 here [VERIFIED: `threadpoolctl.threadpool_info()`] | Last-bit float changes are possible across thread counts or machines | Embedding bits were thread-independent here; BLAS thread independence for the SVD and matrix products is UNVERIFIED. Round floats in output files (below). Record `threadpool_info()` in the manifest. Offer `--threads N` that sets `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` before numpy is imported (possible because `run` imports lazily) and `torch.set_num_threads`. Do not force one thread by default (slows a 5 minute run) |
| Float sums | numpy pairwise sums on fixed-shape arrays | Deterministic for fixed shapes and library | Nothing extra |
| Embedding cache | cache.py:98-110 stores float64 lossless (`savez_compressed`); hit path returns the stored array | Warm run equals cold run | Test cold versus warm equality; add `--no-cache` (temp cache path) for the test and for users |
| Model files differ | different snapshot or revision | Different vectors | Record sha256 of weight, config, tokenizer and modules files in the manifest; the unusual-pairs engine itself only warns "Model identity is recorded as the supplied local path" (runner.py:103-104), so filter that warning from the projected output and replace it with the digest note |
| Library versions | JHTV record shows equal output on numpy 2.2.6 and 2.5.4 for one corpus (docs/hsi-rs-jhtv-reproduction.md section 5) | Cross-machine drift possible | Do not promise cross-machine byte identity; promise same-machine, same-environment identity and record versions |
| Locale and newlines | `open()` defaults, CRLF input | Different text | Explicit `utf-8-sig`, NFC, `\n` normalization; write with `newline="\n"` |

Canonical writer rules (one function used for every file): `json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"`, UTF-8 without BOM, `-0.0` mapped to `0.0`, floats rounded to 6 decimals for unusual-pairs signals (wording-and-meaning values are already rounded to 4 decimals by the engine), reject NaN and infinity (`allow_nan=False`). Rank order is taken from the engine as returned, never re-sorted by rounded values.

Write outputs to a staging folder next to `--out`, hash them there, then rename into place, so an interrupted run never leaves a half-written folder that looks complete.

### 5. Manifest design and doctor design

**Manifest** (`manifest.json`, schema `eureka.run-manifest.v1`, canonical writer, no timestamps, no absolute paths, no hostname, carries the label):

```json
{
  "schema_version": "eureka.run-manifest.v1",
  "label": "candidate, not verified",
  "score_meaning": "...",
  "tool": {"name": "mindrian-eureka", "version": "0.1.0", "engines": {
    "unusual_pairs": {"capability_id": "opportunity.find_cross_domain_pairs", "capability_version": "0.1.0", "scoring": "hybrid_2026", "tie_break": "stable descending top-7 term sort (lower term index first on equal values)"},
    "wording_and_meaning": {"capability_id": "portfolio.find_hybrid_similarity_pairs", "reference": "hsi_reference.py", "reference_sha256": "<sha256 of the installed hsi_reference.py bytes>"}}},
  "inputs": {"files": [{"path": "records.csv", "bytes": 0, "sha256": "..."}], "mapping_sha256": "...", "folder_digest": "sha256 of sorted 'path\\tsha256' lines"},
  "corpus": {"records_read": 0, "records_used": 0, "dropped": [{"id": "...", "reason": "body_under_50_chars"}], "corpus_digest": "sha256 of sorted 'id\\ttext_sha256' lines", "caps_hit": []},
  "settings": {"unusual_pairs": {"top_k": 200, "lex_weight": 0.5, "min_percentile": 0.9, "mode": "local", "svd_topics_requested": 80, "tfidf_max_features": 2000},
               "wording_and_meaning": {"tier": 1, "top_k": 200, "ranking": "percentile", "lexical": "hybrid", "min_percentile": 0.0, "confirm_percentile": 0.75, "chunk_words": 200, "max_chunks": 12, "cache_params_hash": "7affae3c94c6bed9"}},
  "seeds": {"unusual_pairs_svd_random_state": 256, "wording_and_meaning_lsa_seed": 42},
  "model": {"name": "all-MiniLM-L6-v2", "snapshot": "<40-hex dir name when from the Hugging Face cache>", "files": {"model.safetensors": "sha256", "config.json": "sha256", "modules.json": "sha256", "tokenizer.json": "sha256"}},
  "environment": {"python": "3.12.3", "implementation": "CPython", "platform": "linux-x86_64", "libraries": {"numpy": "...", "scikit-learn": "...", "scipy": "...", "sentence-transformers": "...", "torch": "...", "transformers": "...", "tokenizers": "...", "huggingface-hub": "..."}, "blas": [{"api": "openblas", "version": "0.3.29", "num_threads": 12}], "threads_requested": null},
  "outputs": [{"path": "unusual-pairs.json", "sha256": "...", "pairs": 200, "top_k_reached": true}],
  "engine_notes": ["fallback exclude-list message from hsi_reference import recorded here"]
}
```
- Hashing: sha256, streamed in 1 MiB blocks, hex. Input hashes cover raw bytes read at load time (hash while reading, so a file changed mid-run cannot mismatch). The manifest cannot hold its own hash: print it on stdout in the final summary and in `run-info.json`.
- Versions come from `importlib.metadata.version` (the pattern is already in hsi_reference.py:1166-1171), BLAS from `threadpoolctl.threadpool_info()` (a scikit-learn dependency, in uv.lock) [VERIFIED]. Missing library = `null`, not an error.
- Model digests: hash the files that define the model (weights 90 MB takes well under a second to hash). This closes the runner warning at runner.py:103-104.
- `run-info.json` (not hashed, not part of the identity claim): `started_at`, `finished_at`, `duration_ms`, `argv` without input contents, `manifest_sha256`. It also carries the label, so the "every output file" rule holds without exception.

**Doctor** (`mindrian_eureka/doctor.py`, stdlib imports only at module level; a check returns `CheckResult(id, status, message, fix)` with status `PASS | WARN | FAIL`). Exit 0 when there is no FAIL, 1 when any FAIL, 2 on usage error. Output is a plain table on stdout (the report is the result), status words always printed (color is never the only signal), `--json` for machines. Doctor makes no network call and imports no heavy library except in the optional `--load-model` check.

| ID | Check | FAIL when | Exact fix text printed |
|----|-------|-----------|------------------------|
| D1 | Python | `sys.version_info < (3, 11)` (matches `requires-python` in pyproject.toml) | `Python <found> is too old. Eureka needs 3.11 or newer. Run: uv python install 3.12   (offline machine: ask the administrator to install Python 3.11 or newer, then run: uv sync --extra modern-encoder)` |
| D2 | uv | `shutil.which("uv")` is None; version read with `uv --version` | `uv was not found on PATH. Install it from https://docs.astral.sh/uv/getting-started/installation/ (offline machine: copy the uv binary from a trusted release to a folder on PATH). Then run: uv --version` |
| D3 | Encoder libraries | `importlib.util.find_spec("sentence_transformers")` is None (the `modern-encoder` extra) or numpy or scikit-learn missing | `Run: uv sync --extra modern-encoder   (offline machine: install from a local wheel folder with: uv sync --extra modern-encoder --offline)` |
| D4 | Local model | No valid model folder found (DOC-02) | `No local model found. Searched: <each path>. Put the all-MiniLM-L6-v2 folder on this machine, then either set MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/all-MiniLM-L6-v2 or pass --model-path. On a machine with internet, fetch it once and carry it in: uv run hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir all-MiniLM-L6-v2` (the `hf` command syntax is [ASSUMED]; the `hf` binary exists in .venv/bin) |
| D5 | Cache dir | exists and not owner-only (mode & 0o077 != 0) or not owned by the current user or not writable; if missing, PASS with "will be created with mode 700" after checking the nearest existing parent is writable | `Run: chmod 700 <dir>` ; for files `chmod 600 <dir>/embeddings.sqlite3*` |
| D6 | Data dir | same rules for `MINDRIAN_EUREKA_DATA_DIR` or `~/.local/share/mindrian-eureka` (jobs.py:25-28 creates it 0700) | `Run: chmod 700 <dir>` |
| D7 | Offline environment | WARN only: report whether `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` are set (`run` sets them itself) | `Optional: export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` |
| D8 | Model loads (only with `--load-model`) | local load or one-sentence encode fails, or vector width is not 384 [ASSUMED width] | The exception text plus the D4 fix |

Model discovery (shared by doctor and run, one function, no network): (1) `--model-path`; (2) `MINDRIAN_EUREKA_RS_MODEL_PATH` (already used by Dockerfile, scout_cli.py:34, analogy_fitness.py:118); (3) `MINDRIAN_EUREKA_HSI_MODEL_PATH` (hsi_engine.py:92); (4) Hugging Face cache snapshot of `sentence-transformers/all-MiniLM-L6-v2`: roots `HF_HUB_CACHE`, `HF_HOME/hub`, `~/.cache/huggingface/hub` [ASSUMED order, matches huggingface_hub documentation from memory]; choose the snapshot named in `refs/main`, else stop with a message listing the snapshots (this machine has two: `1110a243...` named by `refs/main`, and `c9745ed1...`; both hold the main model files, and whether their weights are equal was not checked) [VERIFIED: directory listing]. A folder is valid when it has `config.json`, `modules.json`, a weight file (`model.safetensors` or `pytorch_model.bin`) and a tokenizer file (`tokenizer.json` or `vocab.txt`). Pass the resolved snapshot directory (not the hub id) to both engines.

Permissions on non-POSIX systems: report `SKIP (permissions not checked on this operating system)` with status WARN, never silent. The enclave OS is unknown (Open Question 4).

### 6. CLI structure

Current state: `cli.py:13-97` is one `main()` with `argparse`, `prog="eureka"`, `add_subparsers(dest="command", required=True)` (line 18), subcommands `capabilities`, `capability`, `schema`, `workflow`; dispatch is an `if args.command in (...)` chain whose `else` branch prints the workflow document (lines 36, 95-97); results go to stdout as JSON (line 97). No `--version`. Tests call `main()` after patching `sys.argv` (tests/test_capability_cli.py:11-15), so `main` must keep working with no arguments.

Prescriptions:
- Keep argparse (stdlib; zero new dependencies; important for an enclave install). Do not add click, typer, rich or argcomplete. Shell completion is not cheap with argparse (needs the third-party `argcomplete`); skip it and say so in the plan.
- `def main(argv: Sequence[str] | None = None) -> int:` with `parser.parse_args(argv)`; existing branches return 0; console script `eureka = mindrian_eureka.cli:main` calls `sys.exit(main())`, which is compatible. Add `--version` (`importlib.metadata.version("mindrian-eureka")`, fallback `mindrian_eureka.__version__`).
- Add `run` and `doctor` subparsers before the `workflow` fallback; change the `else:` to an explicit `elif args.command == "workflow"`. Do not rename `capabilities`, `capability`, `schema`, `workflow`. Handlers import lazily (`from .run.command import run_command` inside the branch) so `--help`, `--version`, `doctor` and the old commands never import numpy or torch; this also lets `run` set thread environment variables before numpy loads. Skip the 50 ms startup target: model load alone took 16.4 s here and importing the engines took about 9 s [VERIFIED: experiment].
- `eureka run FOLDER [--out DIR] [--mapping FILE] [--id-column C --title-column C --text-column C ... --source-column C --delimiter D] [--model-path P] [--max-artifacts N] [--top-k N] [--objective TEXT] [--threads N] [--no-cache] [--dry-run] [--force] [--json] [-q/--quiet] [--no-color]`. `--top-k` default 200, max 200. `--dry-run` builds and validates the corpus, prints counts and drops, loads no model, writes nothing. Default `--out` is `./eureka-run`; if it exists it is replaced only when it contains a `manifest.json` with schema `eureka.run-manifest.v1`; otherwise exit 2 ("output folder exists and is not an Eureka run").
- `eureka doctor [--json] [--load-model] [--model-path P] [--no-color]`.
- Exit codes: 0 success (a run with zero candidates on a small corpus is success with a stderr warning); 1 runtime failure (bad input data, missing model, engine error, doctor FAIL); 2 usage error (argparse default, bad flag combination, `--out` inside the input folder, `top_k` above 200); 130 on Ctrl+C (Unix convention; add to the list). Remove the staging folder on interrupt. Wrap the handler: `KeyboardInterrupt` -> message "Interrupted. No output was written." -> 130. Never print a traceback unless `--debug`; print one line `eureka: <message>` plus the fix text to stderr.
- Streams: progress, warnings, errors on stderr (use `stage_callback` for the unusual-pairs stages `structural-scoring`, `semantic-scoring`, `pair-ranking`, `complete`, runner.py:62,66,107,168; plain lines for the other stages). Final summary on stdout: output file paths, record and pair counts, manifest sha256, caps hit, and the line "All results are candidates, not verified. They are leads for human review." (CONTEXT specifics). `--json` prints the same summary as one JSON object for Phase 3 reuse.
- Color: only on stderr/stdout that is a TTY, only when `NO_COLOR` is unset, `TERM` is not `dumb`, and `--no-color` is absent; implement in 10 lines, never required to read the output. Non-interactive: no prompts anywhere.
- Quiet third-party noise: set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `TOKENIZERS_PARALLELISM=false` before importing sentence-transformers, and silence the transformers load report and the "Token indices sequence length is longer than..." warning that `SentenceTransformerEncoder.encode` triggers (seen in this session's experiment). Redirect `hsi_reference` import-time stderr into the manifest `engine_notes`.
- Set `os.umask(0o077)` at the start of `run` so the output folder and files are owner-only (privacy constraint). On non-POSIX this is a no-op; doctor says so.

### 7. Validation Architecture (requested explicitly; `workflow.nyquist_validation` is `false` in `.planning/config.json`, so this section is optional for the workflow)

Tooling facts [VERIFIED in this session]:
- `uv run mypy --version` -> `mypy 1.19.1 (compiled: yes)`; `uv run ruff --version` -> `ruff 0.14.10`; `uv run pytest --version` -> `pytest 9.0.2`. These resolve to `~/.local/bin/{mypy,ruff,pytest}` on PATH, outside the project environment. `uv.lock` contains none of them (`grep -c` = 0). The repo `.venv` (Python 3.12.12, numpy 2.5.4, scikit-learn 1.9.1, sentence-transformers 5.7.0) has no pytest: `.venv/bin/python -m pytest` fails. The system python3 (3.12.3, numpy 2.2.6, scikit-learn 1.8.0, sentence-transformers 5.3.0, torch 2.11.0+cu130) runs the suite.
- Full suite: `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` -> 192 passed, 25 skipped, 45 subtests passed in 144 s (2 min 24 s) [VERIFIED]. Phase 1 documented the same invocation and decided against a dev dependency group because it would change `uv.lock` (docs/rs-engine-parity.md section 8).
- No `[tool.mypy]` or `[tool.ruff]` configuration exists in pyproject.toml. Default ruff on all of `src` reports 41 findings; on `cli.py`, `runner.py`, `hsi_engine.py` it is clean. `mypy --strict --follow-imports=silent` reports 15 errors in those three files (cli.py:49 one; hsi_engine.py six including `no-untyped-call` on `hsi_reference` functions; runner.py eight). So: strict gate = new modules only, via a `[[tool.mypy.overrides]]` list or an explicit file list in the plan's verify command. Calls into the untyped `hsi_reference` need one typed facade (`run/engines.py`) with local `# type: ignore[no-untyped-call]` comments, or a per-module override `disallow_untyped_calls = false` for that one module. Adding `[tool.ruff]`/`[tool.mypy]` tables needs no new dependency [ASSUMED: tool tables do not affect `uv.lock`, so the Docker `uv sync --frozen --no-dev` is unaffected].

Test framework:

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (user-level), plain pytest style with fixtures and `parametrize` for new tests (existing files mix pytest functions and `unittest`) |
| Config file | none; tests run with `PYTHONPATH=src` |
| Quick run command | `PYTHONPATH=src python3 -m pytest tests/test_run_*.py tests/test_doctor.py -q -p no:cacheprovider` (target under 30 s; stub encoder, no model load) |
| Full suite command | `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` (about 2.5 min) |
| Strict typing gate | `mypy --strict --follow-imports=silent src/mindrian_eureka/run src/mindrian_eureka/doctor.py src/mindrian_eureka/limits.py` |
| Lint gate | `ruff check src/mindrian_eureka/run src/mindrian_eureka/doctor.py src/mindrian_eureka/limits.py tests/test_run_*.py tests/test_doctor.py` |

Phase requirements to tests:

| Req | Behavior | Type | Command | File exists? |
|-----|----------|------|---------|--------------|
| RUN-01 | `eureka run` on a CSV folder and on a Markdown folder writes both ranked files | integration (stub encoder, in-process `main([...])`) | `pytest tests/test_run_pipeline.py -q` | Wave 0 |
| RUN-01 | Both engines get the same record list and order | unit | `pytest tests/test_run_pipeline.py::test_engines_receive_same_sorted_records` | Wave 0 |
| RUN-01 | Wording-and-meaning leg params hash equals `7affae3c94c6bed9` | unit | `pytest tests/test_run_engines.py::test_params_fingerprint_matches_recorded_rebuild` | Wave 0 |
| RUN-01 | Caps: `top_k=200` accepted, 201 rejected; `test_clip_and_cap_decisions_are_documented` updated | unit | `pytest tests/test_rs_engine_parity.py::test_clip_and_cap_decisions_are_documented` | exists, edit |
| RUN-02 | Stable IDs: same content in different row order and CRLF gives same IDs and corpus digest | unit parametrized | `pytest tests/test_run_corpus.py` | Wave 0 |
| RUN-02 | ID collision stops with exit 1 and names both sources; missing id value stops; short record is dropped and reported | unit | same file | Wave 0 |
| RUN-02 | Mapping file schema errors and missing mapping print headers and skeleton, exit 2 | unit | same file | Wave 0 |
| RUN-02 | Source folder is byte-unchanged after a run (hash tree before and after); `--out` inside source rejected | integration | `pytest tests/test_run_pipeline.py::test_source_folder_is_never_written` | Wave 0 |
| RUN-03 | Manifest has every required field, input and output hashes verify against disk, no absolute path, no timestamp | unit | `pytest tests/test_run_manifest.py` | Wave 0 |
| RUN-03 | `caps_hit` is filled when `--max-artifacts` is below the record count | integration | `pytest tests/test_run_pipeline.py::test_cap_hit_is_reported_everywhere` | Wave 0 |
| RUN-04 | Two runs into two folders: `unusual-pairs.json`, `wording-and-meaning-pairs.json`, `ranked-pairs.md`, `manifest.json` byte-identical; cold cache equals warm cache | integration | `pytest tests/test_run_determinism.py` | Wave 0 |
| RUN-04 | Optional real-model run twice (skipped unless `EUREKA_TEST_MODEL_PATH` is set) | integration, gated | same file | Wave 0 |
| RUN-05 | Every file in the output folder (JSON, Markdown, manifest, run-info, corpus lines) contains "candidate, not verified"; every ranked JSON has `score_meaning`; stdout summary contains the label | integration | `pytest tests/test_run_labels.py` | Wave 0 |
| RUN-05 | Direction wording derives from the signal values, not from the label name | unit parametrized | same file | Wave 0 |
| DOC-01 | Each failing check prints its exact fix: patched `sys.version_info`, `shutil.which` -> None, bad directory modes (`chmod 755`), missing library | unit | `pytest tests/test_doctor.py` | Wave 0 |
| DOC-02 | Missing model: exit 1, message lists searched paths and the fix; `run` without a model exits 1 before reading engines, no traceback | integration | `pytest tests/test_doctor.py::test_missing_model_is_loud tests/test_run_pipeline.py::test_run_without_model_fails_clearly` | Wave 0 |
| CLI | `--help`, `--version` exit 0; old subcommands unchanged (existing `tests/test_capability_cli.py`); exit 2 on usage error; no ANSI when not a TTY | unit | `pytest tests/test_run_cli.py tests/test_capability_cli.py` | Wave 0 / exists |
| Offline | Run and doctor open no socket: patch `socket.socket.connect` to raise | integration | `pytest tests/test_run_pipeline.py::test_run_makes_no_network_call` | Wave 0 |

Sampling: per task commit run the quick command; per wave merge run the full suite; phase gate is the full suite green, `mypy --strict` and `ruff check` clean on the new files, and one manual real-model run on a small folder recorded in the SUMMARY.

Wave 0 gaps:
- [ ] `tests/conftest.py` (none exists today): `hashing_encoder` fixture (deterministic feature-hashing vectors, 64 dimensions, L2-normalized, no model files) that patches `runner.SentenceTransformerEncoder` and the facade's encoder factory; a `tmp_inputs` factory that writes the 32 synthetic documents of `tests/fixtures/rs_parity/corpus.json` as a CSV and as a Markdown folder inside `tmp_path` (no new committed data); an `isolated_env` fixture that points `HOME`, `MINDRIAN_EUREKA_CACHE_DIR`, `MINDRIAN_EUREKA_DATA_DIR`, `HF_HOME` at `tmp_path`.
- [ ] `tests/test_run_corpus.py`, `test_run_engines.py`, `test_run_manifest.py`, `test_run_pipeline.py`, `test_run_determinism.py`, `test_run_labels.py`, `test_run_cli.py`, `test_doctor.py`.
- [ ] `[tool.mypy]` and `[tool.ruff]` tables in pyproject.toml (config only).
- [ ] Decision on tool installation (Open Question 5).

### 8. Pitfalls and risks

See the Common Pitfalls section below (enclave install, pending partner CSV headers, and the engine-specific traps).

## Standard Stack

### Core (no new third-party dependency)
| Library | Version (this machine) | Purpose | Why |
|---------|------------------------|---------|-----|
| Python stdlib: `argparse`, `csv`, `html.parser`, `html`, `hashlib`, `json`, `pathlib`, `unicodedata`, `importlib.metadata`, `importlib.util`, `shutil`, `stat`, `os`, `signal`, `dataclasses`, `contextlib` | 3.12.3 (project needs >=3.11) | CLI, corpus, hashing, doctor | Already the style of the repo; zero install risk in an enclave |
| numpy | 2.2.6 system, 2.5.4 repo venv (pyproject `>=2.0,<3`) | Matrices in both engines | Existing dependency |
| scikit-learn | 1.8.0 system, 1.9.1 repo venv (`>=1.6,<2`) | TF-IDF and SVD in both engines | Existing dependency |
| jsonschema | existing (`>=4.20,<5`) | Validate the mapping file and the manifest in tests | Existing dependency |
| sentence-transformers | 5.3.0 system, 5.7.0 repo venv (extra `modern-encoder`, `>=5.0,<6`) | Local MiniLM | Existing optional extra; `eureka run` requires it |
| threadpoolctl | 3.6.0 system (transitive of scikit-learn) | BLAS thread and version record | Already in `uv.lock`; use with a guarded import |

### Supporting
| Library | Purpose | When |
|---------|---------|------|
| `hsi_reference` (in repo) | Wording-and-meaning building blocks | Always, through the typed facade |
| `opportunity_pairs.runner` / `cache` / `encoders` (in repo) | Unusual-pairs call, embedding cache, local encoder | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click, typer | Nicer completion, but a new install in an enclave and an `eureka` entry point rewrite; rejected |
| Own typed facade | Making `hsi_reference` fully typed | 1500 lines of reference code; edits would drift from the reference script; rejected |
| `hsi_reference.main()` on a scratch room | In-process building blocks | `main` walks a room folder, writes `.hsi-cache.json`, exits through `sys.exit`, stamps `room_dir`; the building blocks give the same numbers without those side effects. Fidelity is protected by the `7affae3c94c6bed9` check and a stub-vector parity test against `main()` on a temp room |
| `run_hsi` | Direct use | Cannot reach 200 pairs, wrong dense rule; rejected |

**Installation:** nothing new. Users run `uv sync --extra modern-encoder` (the existing extra). `eureka run` needs it; doctor D3 checks it.

**Version verification:** versions above were read from the running interpreters and `uv.lock` in this session, not from the network. No package is added.

## Package Legitimacy Audit

No external package is added or recommended in this phase, so the slopcheck gate has nothing to evaluate.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none added) | - | - | - | - | n/a | n/a |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none. `threadpoolctl` is already locked in `uv.lock` as a scikit-learn dependency; the plan imports it behind `try/except ImportError`.

## Architecture Patterns

### System Architecture Diagram

```
eureka run FOLDER --out OUT
   |
   v
[argparse: parse flags]--bad usage-->(stderr msg, exit 2)
   |
   v
[pre-flight: model discovery, offline env, umask 077, --out checks]--no model-->(stderr msg + fix, exit 1)
   |
   v
[corpus builder]  CSV(+mapping) / Markdown --> normalize NFC+LF --> id rules --> drop <50 chars (reported)
   |                 hash raw bytes while reading       collision/missing id/too big --> (exit 1)
   v
sorted records (by id) --cap check--> [caps_hit recorded, deterministic cut]
   |
   +------------------------------+--------------------------------+
   v                              v
[unusual-pairs engine]         [wording-and-meaning engine]
 run_document(...)              lsa(seed 42) + bm25 -> lexical
 hybrid_2026, top_k 200         tier-1 dense (200-word chunks) -> compute_hsi_matrix(top_k 200)
 embedding cache (SQLite 0600)  no cache
   |                              |
   +--------------+---------------+
                  v
        [projection: drop timestamps/paths, add label + score meaning + direction wording from signs]
                  v
        [canonical writer: staging dir, rounded floats, sorted keys] --> hash each file
                  v
        [manifest.json (no times)] + [run-info.json (times, manifest hash)] --> atomic rename to OUT
                  v
        stdout summary ("candidate, not verified") ; stderr progress/warnings
```

### Recommended Project Structure
```
src/mindrian_eureka/
├── cli.py                 # add run/doctor subparsers, --version; lazy imports; main(argv) -> int
├── limits.py              # MAX_TOP_K = 200, MAX_ARTIFACTS = 3000, HARD_MAX_ARTIFACTS = 5000
├── doctor.py              # checks D1-D8, stdlib only at import time
├── models.py              # model discovery and validation (shared by doctor and run)
└── run/
    ├── __init__.py
    ├── settings.py        # frozen dataclasses: RunSettings, EngineSettings, CapHit
    ├── mapping.py         # mapping schema + loader
    ├── corpus.py          # readers, ids, normalization, drops, caps
    ├── engines.py         # typed facade: unusual-pairs call, wording-and-meaning building blocks
    ├── project.py         # engine result -> eureka.run-pairs.v1 projection, labels, direction wording
    ├── manifest.py        # versions, hashes, manifest + run-info dataclasses
    ├── output.py          # canonical writer, staging dir, Markdown report
    ├── console.py         # stderr/stdout helpers, color rule, progress
    └── command.py         # run_command(args) -> int (exit codes)
tests/
├── conftest.py            # new: hashing_encoder, tmp_inputs, isolated_env
└── test_run_*.py, test_doctor.py
```

### Pattern 1: Typed facade over untyped reference code
**What:** One module calls `hsi_reference` and returns typed dataclasses; all `type: ignore[no-untyped-call]` live there. **When:** every call into `hsi_reference`.
```python
# Source: this repo, hsi_reference.py:423,460,536,1027 and hsi_engine.py:16
from __future__ import annotations
import os
os.environ["HSI_NO_AUTO_INSTALL"] = "1"          # must run before the import below
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

def run_wording_and_meaning(records: Sequence[Record], encoder: Callable[[list[str]], np.ndarray],
                            *, top_k: int) -> list[dict[str, Any]]:
    from mindrian_eureka import hsi_reference as ref   # import inside, capture import-time stderr
    texts = [r.model_text for r in records]
    lsa = ref.compute_lsa_similarity(texts, seed=42)                      # type: ignore[no-untyped-call]
    bm25 = ref.compute_bm25_similarity(texts)                             # type: ignore[no-untyped-call]
    semantic = ref.compute_semantic_similarity_tier1(texts, encoder=encoder, chunk_words=200)  # type: ignore[no-untyped-call]
    pairs, _ = ref.compute_hsi_matrix(                                     # type: ignore[no-untyped-call]
        [{"id": r.id, "text": r.model_text, "title": r.title, "path": r.source_ref} for r in records],
        lsa, semantic, threshold=None, lexical_matrix=0.5 * (lsa + bm25), bm25_matrix=bm25,
        ranking="percentile", top_k=top_k, min_percentile=0.0, confirm_percentile=0.75,
        computed_at="1970-01-01T00:00:00+00:00")
    return list(pairs)
```

### Pattern 2: Canonical writer and staging
```python
# Source: reasoning from measured volatile fields (see section 4)
def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")

def write_atomic_tree(staging: Path, final: Path) -> None:
    ...  # hash files in staging, write manifest last, os.replace(staging, final)
```

### Pattern 3: Direction wording from signs
The two engines use the same label `structural_transfer` with OPPOSITE meaning (hsi_reference.py:1015-1024; tests/test_wrong_number_fixes.py:150-152,189-198). Unusual-pairs: `structural_transfer` = meaning higher than wording ("same meaning in different words", runner.py:147). Wording-and-meaning: `structural_transfer` = wording higher than meaning ("shared words with different meaning"). In the projection write a plain sentence per pair from the numbers (`semantic > lexical` or the reverse) and never print the bare label as the explanation.

### Anti-Patterns to Avoid
- **Calling `hsi_reference.main()` on the user's folder:** it writes `.hsi-cache.json` and results into the room argument (docs/hsi-rs-jhtv-reproduction.md section 7 step 1).
- **Using `run_hsi` for the recorded rebuild:** different dense rule and caps.
- **Dumping the raw `eureka.result.v1`:** carries timestamps, the model path and 1,600-character source excerpts per side; project instead.
- **Silent skips:** every drop, cap, empty result and degraded mode must appear in stderr, outputs and manifest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ranking, LSA, BM25, percentile, spectral profile | New scoring code | `runner.run_document`, `hsi_reference` functions | Phase 1 parity work and the JHTV reproduction depend on them |
| Embedding cache | New cache | `opportunity_pairs.cache.EmbeddingCache` | Already owner-only, lossless, content-addressed |
| Local encoder loading | New loader | `encoders.SentenceTransformerEncoder` (unusual-pairs leg); `SentenceTransformer(path, local_files_only=True)` wrapped as a callable for the other leg | Offline guard already coded |
| JSON validation | Manual checks of the mapping | `jsonschema` | Already a dependency |
| CSV parsing | Split on commas | `csv` stdlib with `utf-8-sig` | Quoted newlines, BOM |
| HTML cleanup | Regex strip | stdlib `html.parser.HTMLParser` + `html.unescape` (the reference script's approach) | Entities, nested tags |
| Hashing | Custom | `hashlib.sha256`, streamed | Standard |
| Library versions | Parsing `pip freeze` | `importlib.metadata.version` | Pattern exists at hsi_reference.py:1166 |
| BLAS info | Parsing `numpy.show_config` | `threadpoolctl.threadpool_info()` | Already locked |

**Key insight:** the risk in this phase is orchestration drift, not algorithms. Reuse the engine code unchanged and prove equality with a stub-vector parity test against `hsi_reference.main` on a temporary room.

## Common Pitfalls

### Pitfall 1: Using the adapter instead of the recorded steps
**What goes wrong:** `run_hsi` gives a different wording-and-meaning ranking than the recorded top 200. **Why:** token-chunk dense rule, cap 100. **Avoid:** facade per Pattern 1 plus a test that the params hash is `7affae3c94c6bed9`. **Warning sign:** `semantic_method` strings or `top_k` errors in logs.

### Pitfall 2: Artifact order drives tie order
**What goes wrong:** same data, different order of pairs with equal 4-decimal scores. **Why:** stable argsort over pair index (hsi_reference.py:1099-1101); unsorted `os.walk` (203-205). **Avoid:** sort records by id once, before both engines. **Warning sign:** two runs differ only among tied scores.

### Pitfall 3: Opposite meanings behind one label
**What goes wrong:** a reader trusts `structural_transfer` in the wording-and-meaning file as "same meaning in different words". **Avoid:** derived plain sentence per pair and a score-meaning note in every file (RUN-05).

### Pitfall 4: Silent truncation and silent drops
**What goes wrong:** records over the cap or under 50 characters vanish. The JHTV run proved the cost: the default 2000 cap lost the stored rank 1 pair (docs/hsi-rs-jhtv-reproduction.md section 1). **Avoid:** `caps_hit` and `dropped` in manifest, header lines in outputs, stderr warning.

### Pitfall 5: Import-time side effects
**What goes wrong:** importing `hsi_reference` may call a package auto-installer when `HSI_NO_AUTO_INSTALL` is not `1` (hsi_reference.py:62-69) and prints a stderr warning (152-156). **Avoid:** set the variable first; capture the warning into `engine_notes`.

### Pitfall 6: Network attempts hidden in library defaults
**What goes wrong:** `make_sentence_transformer_encoder("all-MiniLM-L6-v2")` resolves through the hub when the cache is incomplete (hsi_reference.py:493-501). **Avoid:** never call it; pass a local folder with `local_files_only=True`; set the offline variables; test with a blocked socket.

### Pitfall 7: Enclave install
**What goes wrong:** `uv sync` needs the network, and `torch` comes from an explicit CPU index (pyproject.toml `[[tool.uv.index]] pytorch-cpu`). The enclave may have no PyPI route, no uv, a different OS, or Windows (permissions checks differ). **Avoid:** doctor prints offline-aware fixes (wheel folder, copied uv binary, copied model folder); `eureka run` makes no network call; model is a copied folder; document the offline install path in the plan; test the offline claim with a blocked socket. The Docker path (Dockerfile ENTRYPOINT `eureka-mcp`, `--network none`, read-only root, `HOME=/tmp`) is unaffected as long as new code is plain package modules and pyproject dependency tables are unchanged; running `eureka run` inside the container needs an entrypoint override and a writable bind mount for `--out`. [ASSUMED: the enclave route; Open Question 4]
**Warning sign:** doctor D3 or D4 fails on the first shared-screen session.

### Pitfall 8: Partner CSV headers are not known
**What goes wrong:** hard-coded column names fail on the first real file; coded state values read as noise to the lexical signal. **Avoid:** mapping file plus flags, a stop-with-skeleton message for unmapped CSV, `value_maps` for coded values, `--delimiter`, `utf-8-sig`, large-cell limit, `--dry-run` for the 2026-10-27 shared-screen session. Expect: multi-file joins, delimiter variants, HTML in cells, empty text cells.

### Pitfall 9: CSV field size limit
**What goes wrong:** `_csv.Error: field larger than field limit` on long descriptions. **Avoid:** raise `csv.field_size_limit` to the 1,000,000-character record limit; test it. [ASSUMED default 131072]

### Pitfall 10: Cold start and long runtime without feedback
**What goes wrong:** the user thinks the run hung (model load 16 s, imports 9 s here; the recorded wording-and-meaning run took 5 min 10 s on 2117 records; the unusual-pairs run takes minutes). **Avoid:** stage lines on stderr with elapsed seconds; `--quiet` to silence.

### Pitfall 11: Model snapshot ambiguity
**What goes wrong:** the Hugging Face cache on this machine holds two snapshots of the same model; picking the wrong one changes vectors. **Avoid:** follow `refs/main`; record the snapshot id and file digests in the manifest; if ambiguous, stop and ask for `--model-path`.

### Pitfall 12: Mixed typing state
**What goes wrong:** `mypy --strict` fails on legacy files, blocking the gate. **Avoid:** gate only new files; fix the one-line `cli.py:49` annotation if `cli.py` is added to the strict list.

### Pitfall 13: Candidate wording drift
**What goes wrong:** a helper file (corpus lines, run-info, Markdown) omits the label. **Avoid:** one `LABEL` constant and a test that walks every file in the output folder.

## Code Examples

### Cap constants and the test edit
```python
# src/mindrian_eureka/limits.py
MAX_TOP_K = 200
MAX_ARTIFACTS = 3000
HARD_MAX_ARTIFACTS = 5000

# runner.py:38-39 (replace)
if top_k < 0 or top_k > MAX_TOP_K:
    raise ValueError(f"top_k must be between 0 and {MAX_TOP_K}")
```
```python
# tests/test_rs_engine_parity.py:481-493 (shape of the edit)
with pytest.raises(ValueError, match="top_k must be between 0 and 200"):
    runner.run_document(..., top_k=201, ...)
```

### Doctor permission check
```python
# Source: reasoning; cache.py:30-48 creates dirs 0700 and files 0600
import os, stat
def owner_only(path: Path) -> tuple[bool, str]:
    info = path.stat()
    mode = stat.S_IMODE(info.st_mode)
    ok = info.st_uid == os.geteuid() and mode & 0o077 == 0
    return ok, f"mode {mode:o}"
```

### Color rule
```python
def use_color(stream: TextIO, no_color_flag: bool) -> bool:
    return (not no_color_flag and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb" and stream.isatty())
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Run reference scripts by path with sha256 checks (Phase 1 reproduction) | Library calls in the repo with recorded settings and a manifest | No private path, no room writes |
| `top_k` 100 and 2500 artifacts in `run_document` | 200 and 3000 with reported caps | Matches the JHTV file size |
| Stamped times inside results | Times only in `run-info.json` | Byte-identical ranked output |

**Deprecated/outdated:** `make_sentence_transformer_encoder` for offline use (no local-only guard); reading `MINDRIAN_EUREKA_HSI_MODEL_PATH` as a separate model for `eureka run` (one model for both legs).

## Runtime State Inventory

Not a rename or migration phase. Omitted on purpose. One related fact: cache and data directories (`~/.cache/mindrian-eureka`, `~/.local/share/mindrian-eureka`) persist state between runs; the run must not depend on their content (cold equals warm test).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Memory for 3000 records is about 3.4 GB (scaled from 1.7 GB at 2117) | Q3 | Out-of-memory on a small enclave machine; lower the default cap or add a memory warning |
| A2 | `csv` default field limit is 131072 characters | Q2, Pitfall 9 | None if wrong; the test covers it |
| A3 | Hugging Face cache root order is `HF_HUB_CACHE`, `HF_HOME/hub`, `~/.cache/huggingface/hub` | Q5 | Model not found on a machine with unusual env; `--model-path` is the escape hatch |
| A4 | `uv run hf download <repo> --local-dir <dir>` is the correct fetch command | Q5 D4 | Wrong fix text; re-check with `hf download --help` when writing the doctor message |
| A5 | MiniLM output width is 384 | Q5 D8 | D8 false failure; read width from the loaded model instead |
| A6 | `[tool.mypy]`/`[tool.ruff]` tables do not change `uv.lock` and do not affect the Docker `--frozen` sync | Q7 | Docker build error; check by running `uv lock --check` offline |
| A7 | Both legs should score the same text per record, `title + "\n\n" + text` | Open Question 2 | Different from the JHTV file shape; changes fidelity claims in Phase 4 |
| A8 | Truncation (not refusal) above the artifact cap is the right default | Q3 | Owner may prefer to refuse; the manifest records it either way |
| A9 | The enclave machine is POSIX and has uv or a copied uv binary | Pitfall 7 | Doctor permission checks and the install steps need a Windows branch |
| A10 | `HF_HUB_DISABLE_TELEMETRY` and `TOKENIZERS_PARALLELISM` names are current | Q6 | Harmless if ignored |
| A11 | BLAS thread count does not change SVD or matrix-product bits on one machine | Q4 | Rare last-bit drift; rounding to 6 decimals and `--threads` mitigate; add a manual check |

## Open Questions

1. **What text does each engine score for a record?**
   - Known: the JHTV engine input was a Markdown file whose body began with `# title`, id and category lines; the unusual-pairs path prepends the title itself (algorithm.py:33-34); the wording-and-meaning reference scores the body only.
   - Unclear: whether to match the JHTV shape or one shared rule.
   - Recommendation: both legs score `title + "\n\n" + text` (one rule, simple to explain). State in Phase 4 that this is not identical to the JHTV file shape. Owner confirmation wanted.
2. **Is a missing `uv` a failure or a warning in doctor?**
   - Known: DOC-01 lists `uv` as a check; an installed wheel or the Docker image runs without it.
   - Recommendation: FAIL (matches the literal requirement and the README install route). Planner may downgrade to WARN when the active environment is not uv-managed.
3. **Should `eureka run` also write the standalone engine JSON (full `eureka.result.v1` and reference-shaped `hsi_pairs`)?**
   - Recommendation: no in Phase 2; the hub (Phase 2.1) and MCP (Phase 3) read the projected files. Add `--keep-raw` only if a reviewer asks.
4. **What operating system and install route does the enclave machine have?**
   - Unknown. Drives offline wheel handling, permission checks, color rules. Ask before the 2026-10-27 session; the plan should include a one-page offline install note.
5. **Add pytest, mypy and ruff as a dev dependency group?**
   - Known: they are not project dependencies; Phase 1 avoided a group because it changes `uv.lock`; the Docker image uses `--no-dev` and `--frozen`.
   - Recommendation: keep the user-level tools for now, document the exact commands, and decide the dev group together with the next `uv lock` run (needs network).
6. **Artifact cap behavior and value.** Recommendation above (3000, truncate and report, `--max-artifacts` to 5000). Owner may prefer refusal.
7. **Cross-engine view.** `opportunity_discovery.run_signal_synthesis` merges both engines without fusing scores (opportunity_discovery.py:60-110). Phase 2 can add a flag `also_in_other_engine` per pair cheaply; the combined view itself belongs to the hub.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | everything | yes | system 3.12.3, repo venv 3.12.12 | none needed |
| uv | install route, D2 | yes | 0.9.4 | copied binary |
| numpy / scikit-learn | both engines | yes | system 2.2.6 / 1.8.0; venv 2.5.4 / 1.9.1 | none |
| sentence-transformers, torch | dense signal | yes | system 5.3.0 / 2.11.0+cu130; venv 5.7.0 / 2.14.1+cpu | stub encoder in tests only |
| Local MiniLM model | real runs | yes | HF cache `models--sentence-transformers--all-MiniLM-L6-v2`, `refs/main` = `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; a second snapshot `c9745ed1...` exists | `--model-path` |
| pytest | tests | yes (user-level) | 9.0.2 at `~/.local/bin/pytest`; not in repo `.venv` | run with system python3 |
| mypy | typing gate | yes (user-level) | 1.19.1 | none |
| ruff | lint gate | yes (user-level) | 0.14.10 | none |
| Cores / RAM | real runs | yes | 12 cores, 17 GB total | lower `--max-artifacts` |
| Network | not required | not used | - | - |

**Missing dependencies with no fallback:** none on this machine. Unknown for the enclave machine (Open Question 4).
**Missing dependencies with fallback:** project-level dev tools (see Open Question 5).

## Security Domain

### Applicable ASVS Categories (level 1 per config)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | none (local CLI) |
| V3 Session Management | no | none |
| V4 Access Control | yes (file level) | owner-only umask 077, 0700 folders, 0600 files; refuse `--out` inside the source folder; never follow symlinks out of the input folder (use `Path.resolve()` and check containment) |
| V5 Input Validation | yes | `jsonschema` for the mapping; explicit limits (1,000,000 characters per record, 20 MiB total, cell limit); `csv` stdlib; reject NaN/inf; treat source text as untrusted data (it is only hashed, tokenized and embedded, never executed or interpolated into shell) |
| V6 Cryptography | yes (integrity only) | `hashlib.sha256`; no custom crypto; hashes are integrity records, not secrets |
| V7 Errors and Logging | yes | no traceback by default; no record text in logs; stderr lines carry ids and counts only |
| V12 Files | yes | path traversal in Markdown ids and CSV ids is closed by the sanitizer; output written only under `--out` through a staging folder |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through record ids or `--out` | Tampering | Sanitize ids; resolve and contain paths; reject `--out` inside input |
| Symlink in input folder pointing outside | Information disclosure | Skip symlinks that resolve outside the folder, report them |
| Output readable by other users | Information disclosure | umask 077, 0700/0600; doctor checks cache and data dirs |
| Hidden network call at model load | Information disclosure | `local_files_only=True`, offline env, blocked-socket test |
| Auto-install of packages at import | Tampering | `HSI_NO_AUTO_INSTALL=1` before importing `hsi_reference` |
| Oversized or hostile input (zip-bomb style CSV cell) | Denial of service | Size limits before ranking; fail with a clear message |
| Source text in logs | Information disclosure | Log ids and counts only |
| Derived embeddings in the cache | Information disclosure | Existing 0700 dir and 0600 file; document `eureka-pair-cache-clear` |

## Sources

### Primary (HIGH confidence): read or run in this session
- `src/mindrian_eureka/cli.py`, `hsi_engine.py`, `hsi_reference.py`, `opportunity_discovery.py`, `scout_cli.py`, `contracts.py`, `opportunity_pairs/{runner,algorithm,cache,encoders,cli,jobs,mcp_server}.py` (line numbers cited inline)
- `docs/hsi-rs-jhtv-reproduction.md`, `docs/rs-engine-parity.md`, `tests/test_rs_engine_parity.py`, `tests/test_rs_engine_parity_record.py`, `tests/test_wrong_number_fixes.py`, `tests/test_capability_cli.py`, `tests/test_hsi_latest_integration.py`
- `pyproject.toml`, `uv.lock`, `Dockerfile`, `scripts/run-mcp-container`, `.planning/{REQUIREMENTS,ROADMAP,STATE,config}`, `02-CONTEXT.md`, `CLAUDE.md`, `SECURITY.md`, `CONTRIBUTING.md`
- Read-only: `/home/jsagi/MindrianRooms/jhtv-oliver-kuntz/solution-design/full-catalog-run-2026-10-18/prepare_engine_corpus.py` (logic summarized; no data copied)
- Runs: `diff` of `hsi_reference.py` against the r-and-d `compute-hsi.py`; two-run difference experiment on the parity fixture; MiniLM bit-identity experiment across thread counts (scripts in the session scratchpad, outside the repo); `params_fingerprint` check; full test suite; `mypy --strict` and `ruff` probes; `threadpoolctl` probe

### Secondary (MEDIUM confidence)
- Python and `huggingface_hub` behavior from memory where tagged `[ASSUMED]`

### Tertiary (LOW confidence)
- Enclave machine characteristics: no source; Open Question 4

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new dependency, versions read locally.
- Architecture and engine calls: HIGH, read from code and cross-checked by running.
- Nondeterminism: HIGH for in-process fields and embeddings on this machine; MEDIUM for BLAS-level bit identity across thread counts (A11).
- CSV mapping: MEDIUM, headers pending.
- Doctor fix texts: MEDIUM, two commands tagged assumed (A3, A4).
- Pitfalls: HIGH for repo-specific, LOW for enclave.

**Research date:** 2026-10-24
**Valid until:** 2026-11-23 (stable repo; re-check if `hsi_reference.py`, `runner.py` or the model snapshot change)
