---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
verified: 2026-11-08T00:00:00Z
status: human_needed
score: 5/7 roadmap success criteria verified; criterion 5 not run (owner checkpoint); criterion 6 partial (CPU column only)
overrides_applied: 0
re_verification: false
head: ce5e7f3
gaps: []
deferred:
  - truth: "GPU spike record of Nemotron-3-Embed-1B-BF16 on the RTX 3060 (criterion 5, ENC-08 run part)"
    addressed_in: "owner-run checkpoint of plan 05-08 (not a later phase)"
    evidence: "05-08-SUMMARY.md 'Next step'; docs/encoder-spike-results.md steps 1-8"
  - truth: "Memory guard for the pair-screen job at 3,000 artifacts"
    addressed_in: "REQUIREMENTS.md v2 LIM-01"
    evidence: "REQUIREMENTS.md line 70"
  - truth: "Plugin-side wiring of the pair-screen routes"
    addressed_in: "REQUIREMENTS.md v2 PLG-01 (plugin repo, nearest fit plugin Phase 374)"
    evidence: "REQUIREMENTS.md line 71"
  - truth: "Topic taxonomy layer (OpenAlex Topics)"
    addressed_in: "REQUIREMENTS.md v2 TAX-01 (parked by owner)"
    evidence: "REQUIREMENTS.md line 72"
  - truth: "Local NIM hosting of the embedding model"
    addressed_in: "REQUIREMENTS.md v2 NIM-01 (kept as a later option by owner)"
    evidence: "REQUIREMENTS.md line 73"
human_verification:
  - test: "Run the spike on the RTX 3060 machine (docs/encoder-spike-results.md, 'How to run', steps 1-8) and return gpu-spike-log.json (and nemotron-bf16-vectors.npz)."
    expected: "The log says whether Nemotron loads and embeds on the card, with dimension, load time, peak memory, prefixes and remote-code need. Then render the page with --render-doc and fill the Nemotron column with encoder-compare.py --update-log."
    why_human: "The GPU is on the owner's machine. This session has no GPU. Every GPU field is NOT RUN, which is correct until a log exists."
  - test: "Owner decisions that follow from the log: pin the gpu-nemotron revision, confirm the two prefix strings, set GPU_APPROX_MIN_OVERLAP, accept or refuse remote code, keep or drop the profile."
    expected: "A follow-up quick task edits encoder_spec.py and example/contracts.py from the log values."
    why_human: "Owner decisions (D-04). Today revision is None, GPU_APPROX_MIN_OVERLAP is None."
  - test: "Confirm the fingerprint placement deviation: the pair files of the DEFAULT profile do not carry encoder_fingerprint (the manifest does); the pair files of a non-default profile do."
    expected: "Owner accepts this reading of success criterion 4 ('manifest and every ranked result carry an encoder fingerprint'), or orders the field in default pair files (which changes the shipped hashes and the reference run)."
    why_human: "Trade-off between criterion 4 wording and the byte-identity rule (criterion 3). ENC-05 in REQUIREMENTS.md already states the narrower rule."
  - test: "Decide what to do with the mdbr-leaf-ir column (NOT RUN: the local folder holds ONNX files only)."
    expected: "Owner supplies a sentence-transformers folder of MongoDB/mdbr-leaf-ir, or accepts a NOT RUN column. Without it no two-encoder overlap exists in the repo."
    why_human: "Needs a model folder this session does not have."
  - test: "Earlier open items carried from Phase 4.1: start.ps1 on Windows from a path with a space; the memory limit decision at 3,000 artifacts (now recorded as LIM-01); Windows ACL check; macOS 14 bundle run; release-gate sign-off in docs/rs-release-gate.md; owner item O1 (rs-differential-scorer.cjs comments)."
    expected: "Unchanged; each stays ASSUMED or UNVERIFIED in the docs."
    why_human: "Need real Windows and macOS machines or an owner decision."
---

# Phase 5: Encoder seam, safe cache key and local GPU spike - Verification Report

**Phase goal:** Eureka builds every encoder in one place, never reuses a vector made by a different encoder setup, and can run one named local GPU encoder on the user's own computer, while MiniLM stays the default and every default result stays byte-identical.
**Verified:** 2026-11-08 at HEAD ce5e7f3. Initial verification (no earlier 05-VERIFICATION.md).
**Status:** human_needed. No gap in the code or the docs blocks the phase. The two GPU-dependent parts (criterion 5, GPU part of criterion 6) cannot be done here by design (plan 05-08 ends at an owner checkpoint).

## Result in short

The seam, the cache, the manifest block, check-example, the doctor probe, the extra, the hand-off page, the spike script, the comparison harness and the READMEs all exist, are wired, and behave as claimed. I re-ran the key claims and they hold. Default output stays byte-identical on a real-model run. No GPU number exists anywhere. Three items need the owner (spike run, decisions, fingerprint placement). Six small warnings are listed below.

## Observable truths (roadmap success criteria)

| # | Criterion | Status | Evidence (PROVEN = I ran or read it) |
|---|-----------|--------|--------------------------------------|
| 1 | One EncoderSpec and one make_encoder build every encoder; two pair engines use it first; other sites follow; hsi_reference.py not edited | VERIFIED with warnings W1, W2 | `encoder_spec.py` (243 lines, 14-field identity) and `make_encoder` in `opportunity_pairs/encoders.py:131`. `runner.py:96` and `run/engines.py:249` build through it. `git diff 874f40b..HEAD --stat -- src/mindrian_eureka/hsi_reference.py` is empty; sha256 595460b0... equals `expected-hashes.json`. Unrouted sites are listed with risk in `docs/encoder-profiles.md` (see site table below). |
| 2 | Cache key holds the full identity; a vector of one setup is never returned for another; old entries ignored | VERIFIED | Scratch script run with `python -I` (see "Cache safety" below): 10 identity variants all miss; schema-1 key misses; a 100-wide vector under the right key is rejected and deleted; an encoder that returns the wrong width raises. `SCHEMA_VERSION = 2`. |
| 3 | Default run on the public example gives MATCH; suite green with MiniLM unchanged | VERIFIED (suite by orchestrator) | `eureka check-example examples/public-example/reference-run ...` gives `Result: MATCH`, exit 0. A fresh real-model run (`eureka run tests/fixtures/hub_public/input --threads 1 --no-cache`, 13 s) then `check-example` gives `Result: MATCH`, exit 0. One flipped byte in a scratch copy gives `Result: NO MATCH`, exit 1. Full suite not run by me (orchestrator: 1929 passed, 29 skipped, 0 failed). |
| 4 | Manifest and every ranked result carry an encoder fingerprint and the label; a non-CPU run is compared by overlap | VERIFIED with owner item H3 | Manifest of the fresh run holds `encoder` (schema `eureka.encoder-block.v1`, profile, `cpu-exact`, two fingerprints, 14-field identities, no path). Library runner sets `label` and `encoder_fingerprint` on each output (`runner.py:160-161`). Host result has optional `encoder` key (`host_run/envelope.py:249`). Pair files carry `encoder_fingerprint` for a non-default profile only (`pipeline.py:437,445`); default pair files do not (so the shipped hashes hold). gpu-approx check: see truth 4b. |
| 5 | A recorded spike shows whether Nemotron loads and embeds on the RTX 3060, every number from a run log | NOT RUN (human_needed) | By design. `docs/encoder-spike-results.md` has `status: not_run` and 38 rows, all NOT RUN. No `gpu-spike-log.json` or Nemotron vectors file exists in the repo. The script and the 8 owner steps are ready (truth 7). |
| 6 | Measured comparison of MiniLM, mdbr-leaf-ir, Nemotron on the 36-record example: top-200 overlap and texts per second | PARTIAL (human_needed) | Only the MiniLM column ran (384 wide, 2.24 s load, 30.90 texts per second, 328 max tokens). The only overlap cell with a number is MiniLM against itself (1.0000), which is trivial. `mdbr-leaf-ir` is NOT RUN with a reason (local folder has ONNX files only, no `modules.json` or weight file). Nemotron is NOT RUN (no GPU). So no overlap between two different encoders exists yet. ENC-09 allows NOT RUN columns with reasons, so the requirement is met in letter; the roadmap goal of a three-way measurement is not yet reached. |
| 7 | READMEs refreshed and checked against code and a run | VERIFIED | Claim table below. |

### Truth 4b: gpu-approx never MATCH

`GPU_APPROX_MIN_OVERLAP: float | None = None` at `example/contracts.py:87`. I copied the fresh run to scratch and set `encoder.determinism_class` to `gpu-approx`. `check-example` printed `FAIL X6 ... overlap 1.0000 of 63 / 1.0000 of 200 ... no overlap threshold has been measured yet, so a gpu-approx run is not a match`, then `Result: NO MATCH`, exit 1, even though overlap was 1.0. PROVEN.

## Hands-on checks

### 1. Byte identity (PROVEN)
Reference run: MATCH, exit 0. Tampered copy: NO MATCH, exit 1. Fresh real-model run (`nice -n 19`, `--threads 1`, `--no-cache`, 13 s): MATCH, exit 0. The reference-run files and `expected-hashes.json` are unchanged since Phase 5 started (`git diff 8674480..HEAD -- examples` shows only 4 added README lines). `algorithm.py` and `hsi_reference.py` sha256 equal the values in `expected-hashes.json`.

### 2. Cache safety (PROVEN, scratch script in the scratchpad, `python -I`)
Through `cached_encode` with the real `EmbeddingCache`:
- Same spec: miss, then hit.
- A change of dtype, device (cuda), document prefix, query prefix, dimension, revision, normalize, attention, batch size or max_seq_length: 0 hits each time; the encoder was called.
- A schema-1 style key (no identity, schema 1) planted with a vector: 0 hits, encoder called.
- Width mismatch: a 100-wide vector planted under the correct key: `hits=0 dimension_rejected=1`, encoder called; the bad entry is deleted. An encoder that returns width 100 for a 384 spec raises `RuntimeError` ("does not match the declared setup").
- Mixed widths in one result raise `RuntimeError` even without a declared dimension.
- Each profile has its own file: `profile_cache_path` gives `embeddings.sqlite3` for `cpu-default` and `embeddings-<profile>.sqlite3` otherwise; the pipeline uses it (`pipeline.py:305-309`).

### 3. Build sites (PROVEN by grep)
| Site | Status | Listed in docs/encoder-profiles.md |
|------|--------|------------------------------------|
| `opportunity_pairs/runner.py:96` (sentence-transformers) | routed via `make_encoder` | yes (routed) |
| `run/engines.py:249` | routed (spec path); the `spec is None` branch keeps the legacy direct call | yes (routed) |
| `doctor.py:126` `_default_encoder_loader` | routed, only when `--encoder-profile` is given | yes (routed) |
| `doctor.py:113-115` `_default_loader` (D8 probe) | NOT routed (direct `SentenceTransformer`) | no (W1) |
| `hsi_engine.py:99` | not routed | yes, with risk |
| `analogy_fitness.py:128` | not routed | yes, with risk |
| `pitch_analysis/algorithm.py:134` | not routed | yes, with risk |
| `hsi_reference.py:555` | not routed, not edited (hash recorded) | yes, with risk |
| `runner.py:81` `ReferenceBertEncoder` (AutoModel, reference-bert path) | not routed | no (W2) |

`hsi_reference.py` diff since 874f40b: empty. PROVEN.

### 4. Dependencies (PROVEN)
`[project] dependencies` = `jsonschema>=4.20,<5`, `numpy>=2.0,<3`, `scikit-learn>=1.6,<2` only. `uv lock --check` exits 0 ("Resolved 76 packages"). Extra `gpu-encoder = ["sentence-transformers>=5.4.1,<6", "transformers>=5.2,<6"]` exists. `git diff 874f40b..HEAD -- uv.lock` adds no `[[package]]` / top-level `name =` block; it adds only the extra lists and dependency entries (it also records the `bundle` extra from quick task 261107-wif, which is outside Phase 5). The lock and `pyproject.toml` changed together in commit 9e5b557.

### 5. MCP and doctor (PROVEN)
- `uv run --no-sync --offline --locked --no-python-downloads eureka-mcp < /dev/null`: exit 0, 0 bytes on stdout, 0 bytes on stderr.
- `server.list_tools()` returns 27 tools (run with `--extra mcp-server`).
- `eureka doctor` prints D1 to D7, no D8, no D9. JSON keys `checks`, `ok`, `schema_version` (shape unchanged); ids D1 to D7.
- `eureka doctor --encoder-profile gpu-nemotron` on this CPU-only machine: `[FAIL] D9 Encoder profile: Profile gpu-nemotron needs a CUDA device, but torch reports none.` with a fix line, exit 1. With `--encoder-profile cpu-default` the JSON ids are D1 to D7 plus D9.
- Note (W5): with a profile and `--load-model`, D9 replaces D8. The ids stay stable, but D8 is not printed in that case.

### 6. Spike script and comparison (PROVEN)
- `scripts/encoder-spike.py --dry-run --out-dir <repo>/docs/x`: refuses ("The output folder must be outside the repository"), exit 2, nothing created. With an outside folder it prints the 8 planned steps and writes a log whose every value is null.
- `trust_remote_code` appears in the script only as `trust_remote_code=False` (line 396) and in an error-text check (line 489). Never `True` anywhere in `src` or `scripts`.
- No GPU number exists: `grep` of `docs`, `evaluations` and the READMEs finds Nemotron only in the profile page, the spike page (all NOT RUN), the comparison page (NOT RUN), the READMEs (say "not run") and the owner's untracked `docs/research/` note. No `gpu-spike-log.json` or Nemotron `.npz` is tracked.
- Human steps (check package names on pypi.org, scratch venv outside the repo, CUDA torch, `nvidia-smi`, dry run, real run with `--allow-download`, copy log, `--render-doc`, return the log) are in `docs/encoder-spike-results.md` "How to run".
- `docs/encoder-comparison.md`: the mdbr-leaf-ir column says NOT RUN with its reason; every table cell (2.24, 30.90, 328, 256, 0.52, 0.52, 1.0000, 384) equals a field of `docs/encoder-evidence/cpu-compare-log.json` (30.8979 rounds to 30.90). The prose numbers (36, 200, 630) match the log (`records`, `top_k`, `pairs`). `tests/test_encoder_compare.py` and `tests/test_encoder_spike_record.py` pass and pin this.

### 7. README claims (criterion 7) (PROVEN)
| Claim | Check | Result |
|-------|-------|--------|
| Catalog holds 68 entries; 60 have CLI and MCP | `eureka capabilities` JSON: 68 entries; surfaces: 59 CLI+MCP and 1 CLI+loopback web+MCP = 60; 5 with no surface, 3 host-only | holds |
| Server registers 27 tools | `list_tools()` | holds |
| `eureka` commands run, doctor, hub, seed, check-example, capabilities | `eureka --help` | holds |
| Extras table (8 rows) | `pyproject.toml` optional-dependencies: bundle, hub-gate, modern-encoder, gpu-encoder, reference-encoder, mcp-server, hmm, neo4j | holds |
| `--encoder-profile` on run and doctor | `eureka run --help`, `eureka doctor --help` | holds |
| Named profile other than default needs `--model-path` | ran without it: exit 2 with a fix line | holds |
| gpu-approx run prints overlap and `Result: NO MATCH` | truth 4b | holds |
| Default run does not write `encoder_fingerprint` into pair files | `grep fingerprint` of reference run: 0; code `pipeline.py:437` | holds |
| README does not claim the spike ran | text says "not run yet" in three places | holds |
| Long dashes | zero U+2013, U+2014 or U+2015 in lines added to README.md, src/README.md, examples README, docs, and Phase 5 planning files since 874f40b. The only hits in all added lines are three test assertions that check a page has no such character. | holds |

### 8. No test weakened (PROVEN)
`git diff 6741585..HEAD -- tests` removes 6 lines (the range includes Phase 4.1 work):
- `tests/conftest.py`: import line widened (`replace`, `EMBED_DIM`); `_load(model_dir)` became `_load(model_dir, spec=None)`; the `hashing_encoder` fixture also sets the stub profile width to 64. Not weakened: needed because the stub is 64 wide and the real code now checks width.
- `tests/hashing_stub.py`: `__init__` gains `spec=None`. Not weakened.
- `tests/test_wrong_number_fixes.py`: the seeded cache key now passes `identity=custom_spec(...)`. Not weakened: it follows the new key shape; the test still seeds and reads the cache.
- `tests/test_partner_bundle.py`: `assert all("--extra-index-url" in call ...)` replaced by stricter per-call assertions. This belongs to Phase 4.1 (commit 811f19f), not Phase 5; it is a tightening.
Other changes are additions (`MANIFEST_KEYS` gains `encoder`; new MATCH-sentence assertions; new test files). 27 test files changed, 4513 insertions, 6 deletions.

### 9. Targeted tests (PROVEN)
- `PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder --with pytest python -m pytest tests/test_host_run_mcp.py tests/test_host_run_mcp_reach.py tests/test_mcp_start_stderr.py tests/test_encoder_docs.py -q`: 53 passed.
- Encoder suite (`test_encoder_spec`, `_factory`, `_extra`, `test_embedding_cache_key`, `test_doctor_encoder`, `test_example_check_encoder`, `test_encoder_compare`, `test_encoder_spike_script`, `test_encoder_spike_record`, `test_run_encoder`, `test_runner_encoder`, `test_readme_commands`, `test_public_example`, `test_hub_assets`): 257 passed, 1 skipped.
- `uv.lock` and `pyproject.toml` unchanged after these runs.

## Requirements coverage

| Req | Status | Evidence |
|-----|--------|----------|
| ENC-01 | SATISFIED | `EncoderSpec`, `Encoder` protocol, `make_encoder`, two profiles; default byte-identical. |
| ENC-02 | SATISFIED with W1, W2 | Pair engines and doctor profile probe routed; unrouted sites listed with risk; `hsi_reference.py` untouched. |
| ENC-03 | SATISFIED | Truth 2. |
| ENC-04 | SATISFIED (threshold deliberately None) | Manifest block; check-example overlap path; never MATCH. |
| ENC-05 | SATISFIED as worded in REQUIREMENTS.md | Library outputs, host `encoder` key, manifest; non-default pair files. See H3. |
| ENC-06 | SATISFIED | D9 with the flag; shape and ids unchanged. |
| ENC-07 | SATISFIED | Check 4. |
| ENC-08 | PARTIAL (script and page done; run is owner work) | Truth 5 and 6 of the hands-on section. |
| ENC-09 | SATISFIED in letter (CPU column ran, other columns NOT RUN with reasons); the three-way result is still missing | Truth 6. |
| ENC-10 | SATISFIED | `docs/encoder-profiles.md` has 10 hand-offs, each with source and mark. No plugin checkout touched. |
| ENC-11 | SATISFIED | Check 7. |
Orphaned requirements: none. All 11 IDs are claimed by plans.
Status marks in REQUIREMENTS.md and ROADMAP.md (Pending, "0 of 9 complete") are not updated yet; the orchestrator does that.

## Anti-patterns and warnings (none is a blocker)

| # | Severity | Finding |
|---|----------|---------|
| W1 | Warning | `doctor.py:113-115` (`_default_loader`, check D8) still builds `SentenceTransformer` directly. `docs/encoder-profiles.md` says `doctor.py` is routed without saying that only the `--encoder-profile` path is. Add one sentence to the "Build sites not routed yet" section or route D8. |
| W2 | Warning | `ReferenceBertEncoder` (AutoModel, `runner.py:81`) is a build site that is not routed and not listed in the follow-up table. Its cache key does include the spec identity, so cache safety holds. |
| W3 | Warning | `eureka run --encoder-profile gpu-nemotron --model-path <bad folder>` prints a fix text that names MiniLM and the MiniLM download command. The profile is Nemotron. Wrong hint for a GPU profile. |
| W4 | Warning | `model_digest` hashes `model.safetensors` and `pytorch_model.bin` only (05-05 summary). A sharded model could get a digest that does not cover all weights. The spike log records `model.sharded_weights`; check it before the owner pins a revision. |
| W5 | Info | `ranked-pairs.md` (the human report) carries the label but no encoder line for a non-default profile; the manifest and both pair files do. D8 is replaced by D9 when a profile and `--load-model` are combined. |
| W6 | Info | Bookkeeping: STATE.md says "Plan: 5 of 9", "Status: Ready to execute", "Progress 97%"; ROADMAP says "0 of 9 complete"; REQUIREMENTS table says Pending. Fix at close-out. Also `pyproject.toml` and docs say the `bundle` extra exists; the lock gained it in this phase's lock commit because the lock was stale (quick task 261107-wif left it out). Harmless. |

No TBD, FIXME or XXX debt marker found in the Phase 5 source files I opened. No stub that reaches user output was found. The `None` threshold and the `None` revision are deliberate, documented gates.

## Deferred and open items, and where each is recorded

| Item | Recorded in |
|------|-------------|
| GPU spike run (criterion 5) | `05-08-SUMMARY.md` "Next step"; `docs/encoder-spike-results.md`; STATE.md `stopped_at` |
| Revision pin, prefix strings, `GPU_APPROX_MIN_OVERLAP`, remote-code decision, keep-profile decision | `docs/encoder-spike-results.md` "Decisions that follow from the numbers"; `docs/encoder-profiles.md` |
| mdbr-leaf-ir column | `docs/encoder-comparison.md` reason text; `cpu-compare-log.json` |
| Fingerprint placement for default pair files | ENC-05 text in REQUIREMENTS.md; `docs/encoder-profiles.md`; README |
| Memory guard at 3,000 artifacts | REQUIREMENTS.md v2 LIM-01 (line 70) |
| Plugin routes and request field for the profile | REQUIREMENTS.md v2 PLG-01 (line 71); `docs/encoder-profiles.md` hand-offs 1-10 |
| Topic taxonomy | REQUIREMENTS.md v2 TAX-01 (line 72) |
| Local NIM | REQUIREMENTS.md v2 NIM-01 (line 73) |
| Unrouted build sites | `docs/encoder-profiles.md` (W1, W2 need one more row or sentence) |
| Phase 4.1 open items (Windows, macOS, ACL, release sign-off, O1) | `04.1-VERIFICATION.md` human items; STATE.md carry-over |

## Gaps summary

No gaps_found item: nothing that should exist in the code or the docs is missing. The phase is complete up to the owner checkpoint. Closing criterion 5, and the GPU and mdbr-leaf-ir parts of criterion 6, needs the owner (spike run and a model folder). I recommend the orchestrator marks the phase "complete pending owner checkpoint", fixes W1 to W3 in a quick task, and does not mark ENC-08 or ENC-09 fully done until a log returns.

---

_Verified: 2026-11-08 at HEAD ce5e7f3_
_Verifier: Claude (gsd-verifier)_
