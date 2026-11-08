# Encoder profiles

## What this page is

Phase 5 put the choice of the meaning model in one place. One module builds each encoder, a vector of one setup is never used for another setup, the small CPU model stays the default, and a GPU profile exists as a spike. Plans 05-01 to 05-08 built this. The measured numbers live in two other pages:
`docs/encoder-spike-results.md` (the spike record, plan 05-08) and `docs/encoder-comparison.md` (the comparison, plan 05-07). This page holds no measured number. Every result of every profile is a lead and keeps the label candidate, not verified. Marks used here: PROVEN (seen in code, a test or a
run), INFERRED (read from a source by someone else), UNVERIFIED (not run or not read at source), ASSUMED (a design choice without a check).

## The two profiles

A profile is a named list of every setting that changes a vector. The table below equals `encoder_spec.PROFILES`, `PROFILE_STATUS` and `PROFILE_EXTRA`. A test compares each cell with the code.

| Profile | Model id | Dimension | Device | Dtype | Maximum tokens | Query prefix | Document prefix | Status | Extra | Source |
|---------|----------|-----------|--------|-------|----------------|--------------|-----------------|--------|-------|--------|
| `cpu-default` | `sentence-transformers/all-MiniLM-L6-v2` | 384 | cpu | none | model default | `(empty)` | `(empty)` | default | `modern-encoder` | `src/mindrian_eureka/encoder_spec.py`, `models.py` (D-04, D-07), PROVEN: this is the setup of the shipped reference run |
| `gpu-nemotron` | `nvidia/Nemotron-3-Embed-1B-BF16` | 2048 | cuda | bfloat16 | 4096 | `query: ` | `passage: ` | spike | `gpu-encoder` | model card as read in 05-RESEARCH.md Q3, INFERRED; not loaded yet |

For `gpu-nemotron`, three values are UNVERIFIED until the spike record `docs/encoder-spike-results.md` states them: the prefix whitespace, the attention setting (`sdpa`) and the revision pin. The string form of the dtype is UNVERIFIED for the same reason. The revision is None until the spike pins
it, and no hash is invented here. The profile is a spike profile: it is selectable, and it is not a recommendation (D-04). The 4096 token limit is the NVIDIA evaluation length (INFERRED, 05-RESEARCH.md Q3). It bounds memory on a card with 12 GB (ASSUMED; no VRAM run yet).

License: the model card names OpenMDW-1.1. That was read from excerpts only (UNVERIFIED in full; no legal review). If weights are ever redistributed, keep the license text and the notices.

## The one rule: never mix

A vector means something only next to vectors of the same setup. So vectors of two setups never meet in one cache file or in one room store.

The cache key holds the full identity of the setup: 14 fields (profile, model id, revision, model digest, dimension, dtype, attention, device, query prefix, document prefix, normalize, chunking, batch size, maximum tokens). The cache schema version is 2 (PROVEN, `opportunity_pairs/cache.py`). The
revision field holds the name of the model snapshot. The model digest is a hash over the hashes of the model files. Two model folders that carry one profile name get two different keys, unless no model file can be hashed. In that case the digest is None and the manifest says that the weights are not
pinned (PROVEN, plan 05-05).

Each profile has its own cache file: `embeddings.sqlite3` for `cpu-default`, and `embeddings-<profile>.sqlite3` for any other profile (PROVEN, `profile_cache_path`). The command `eureka-rs-cache-clear --all-profiles` clears all of them.

A room store follows the same rule. It needs one `vec0` table for each profile, with the width of the profile: 384 and 2048. The partner room store holds 2,130 vectors of 384 dimensions. They were made by `MongoDB/mdbr-leaf-ir`, not by MiniLM (PROVEN, Phase 3 record
`.planning/phases/03-host-integration-and-replay-rebuild/03-06-SUMMARY.md` and the run contract page). Do not put 2048-dimension vectors in that table.

## How a run records its encoder

Every run writes the manifest key `encoder` (schema `eureka.encoder-block.v1`, PROVEN, plan 05-05). It holds the profile, the determinism class, and for each pair engine a fingerprint and the identity of 14 fields. A profile that runs on CUDA adds a `gpu` block with the device name and the CUDA
version. The block holds no path. The host run result copies the block as the optional key `encoder` (PROVEN, plan 05-06; see `docs/mos-eureka-engine-run-contract.md`).

The determinism class has two values:

- `cpu-exact`: the device is the CPU, the dtype is float32 or not set, and no attention setting is set.
- `gpu-approx`: every other setup.

Bit-exact output is shown for one CPU setup only (PROVEN, 05-CONTEXT fact F2). A GPU or another dtype can differ slightly. A non-default profile adds `encoder_fingerprint` to both pair files. The default profile does not add it, so the shipped hashes keep holding (PROVEN, plan 05-05).

## How to pick a profile

Use a flag. Run `eureka run <folder> --encoder-profile NAME --model-path <folder of that model>`. A named profile other than the default needs an explicit `--model-path`. To check a setup first, run `eureka doctor --encoder-profile NAME` and add `--load-model` to load the model and compare the vector width.

There is no environment variable for the profile. The MindrianOS plugin passes an allowlisted environment to the engine, so a new variable would be dropped (INFERRED, 05-RESEARCH.md lane `repo-mcp-and-plugin-contract`). A host that wants a profile needs a request field in the pair-screen input. That field is not built in this phase (hand-off 2).

## How a non-exact run is checked

The command `eureka check-example` reads `encoder.determinism_class` from the manifest of the run (PROVEN, plan 05-04). A run without a block, or with `cpu-exact`, gets the byte check against the shipped reference run. A `gpu-approx` run gets two checks: `corpus/records.jsonl` is compared by bytes,
and the two pair files are compared by ranking overlap with the shipped reference run.

The overlap threshold is the constant `GPU_APPROX_MIN_OVERLAP` in `example/contracts.py`. Its value is None, so the threshold is not measured yet. Until the GPU spike records the drift (plan 05-08), a `gpu-approx` run is never reported as a match. The check prints the overlap numbers and says so. The label stays candidate, not verified.

## Install for the GPU profile

The extra `gpu-encoder` (`uv sync --extra gpu-encoder`) holds `sentence-transformers` 5.4.1 or newer and `transformers` 5.2 or newer (PROVEN, `pyproject.toml`). A CUDA build of torch is not part of the lock. The project pins torch to the CPU index (PROVEN, `pyproject.toml`). The user installs a CUDA build for the computer.

The owner computer is a Windows machine with WSL and an RTX 3060 with 12 GB (D-11). The model is about 2.3 GB in BF16 (INFERRED from the model card size in 05-RESEARCH.md; no VRAM run yet, so a fit in 12 GB is UNVERIFIED). The run that proves the load, or shows that it fails, is recorded in `docs/encoder-spike-results.md`.

## Build sites not routed yet

Three sites that build a sentence-transformers model are routed through the encoder factory: `runner.py` (the sentence-transformers path), `run/engines.py` and `doctor.py` (PROVEN, plans 05-03 and 05-05).

The `doctor.py` route holds only for the `--encoder-profile` path (`_default_encoder_loader`). The plain model probe D8 (`_default_loader`) still builds `SentenceTransformer` directly.

Six sites are not routed in this phase. Each one is a row of the table. Line numbers are from 05-RESEARCH.md (lane `repo-encoder-seams`) and may have moved.

| Site | What it does | Why not routed now | Risk when it is routed |
|------|--------------|--------------------|------------------------|
| `hsi_engine.py` line 99 | `SentenceTransformerEncoder`; the model path comes from `MINDRIAN_EUREKA_HSI_MODEL_PATH`; it also accepts dense vectors from the host | out of the scope of the first spike; a host may send its own vectors | a host vector and an engine vector of different setups can meet in one score (PROVEN, read at hsi_engine.py lines 90 to 92) |
| `analogy_fitness.py` line 128 | `SentenceTransformerEncoder`; fixed cosine thresholds 0.5, 0.8 and 0.3 | tests patch the name `analogy_fitness.SentenceTransformerEncoder` | each threshold is tuned to the 384-dimension model; another encoder moves the scores and the classes (PROVEN, 05-RESEARCH.md) |
| `pitch_analysis/algorithm.py` line 134 | a module-level model with `local_files_only=True`; rule: meaning at least 0.6 and wording at most 0.2 | the model loads at import, so a profile cannot change it without a larger edit | the two cutoffs are encoder-sensitive; a new encoder can flip a verdict (PROVEN, 05-RESEARCH.md) |
| `hsi_reference.py` line 555 | `SentenceTransformer(model_name)` without `local_files_only` | its sha256 is recorded in manifests, so the file is not edited; the pipeline reaches it only through an injected `encoder` | an edit changes the recorded hash and breaks the replay proof; a load without `local_files_only` can try the network (PROVEN for the hash record) |
| `doctor.py` lines 113 to 115 (`_default_loader`, check D8) | `SentenceTransformer(model_dir, local_files_only=True)`; encodes one sentence to report the width | the D8 probe has no profile; the profile probe D9 is routed | the probe can pass for a setup that a profile run does not use; it stores no vector, so no cache risk (PROVEN, doctor.py lines 113 to 115) |
| `runner.py` line 81 (`ReferenceBertEncoder`) | an `AutoModel` encoder for the `reference-bert` path | it is not a sentence-transformers encoder; the factory builds that path only | cache safety holds: its cache key already holds the spec identity (`identity=spec.identity()`); the open risk is that dtype, device and prefix do not come from a profile (PROVEN, runner.py lines 81 to 88) |

The wording-and-meaning engine does not use the embedding cache today (PROVEN, 05-RESEARCH.md). This phase does not add it.

## Hand-offs for the MindrianOS plugin session

This list is for the plugin session. This repository does not edit the plugin. The plugin facts are cited from 05-RESEARCH.md and the Phase 3 run contract, with the mark of the source.

1. The environment allowlist drops new `MINDRIAN_*` variables, so any profile switch needs a request field.
   Why: the plugin passes an allowlisted child environment.
   Source: 05-RESEARCH.md lane `repo-mcp-and-plugin-contract`. Mark: INFERRED for the full list, PROVEN that a variable the plugin does not list is dropped.
2. Add a request field `encoder_profile` to the pair-screen input, and pass the matching model path through `MINDRIAN_EUREKA_RS_MODEL_PATH`. Eureka builds the field in a later engine phase.
   Why: the flag `--encoder-profile` exists for the command line only.
   Source: this page, section "How to pick a profile". Mark: ASSUMED.
3. Use the block schema id `eureka.encoder-block.v1` as the contract version marker. The plugin checks the project name `mindrian-eureka` and the `eureka-mcp` script only, with no version and no tool list check.
   Why: the check does not tell the plugin which encoder rules the engine follows.
   Source: 05-RESEARCH.md lane `repo-mcp-and-plugin-contract`. Mark: PROVEN for the check, INFERRED for the use of the schema id.
4. Keep one `vec0` table for each profile, with the width of the profile: 384 for the partner store, 2048 for `gpu-nemotron`. Never put a second encoder in one table.
   Why: vectors of two setups are not comparable.
   Source: Phase 3 record `03-06-SUMMARY.md` and `docs/mos-eureka-engine-run-contract.md`. Mark: PROVEN for the 384 table.
5. The 0.55 CONVERGES floor lives in the plugin file `graph-derive-classifier.cjs`. Tune it again for each profile. On the 384-dimension vectors, 2,165 of 2,267,385 pairs reach 0.55.
   Why: cosine values of another encoder have another spread.
   Source: Phase 3 record `03-06-SUMMARY.md`. Mark: PROVEN.
6. Keep the failure reasons. A missing model is `local_model_unavailable`. The text `Install the optional extra: ... mindrian-eureka[gpu-encoder]` is new for the GPU profile. The plugin pattern accepts the name `gpu-encoder`, but its list of allowed extras may not.
   Why: a host that shows the wrong install text sends the user to a dead end.
   Source: 05-RESEARCH.md lane `repo-mcp-and-plugin-contract` (the pattern was checked by the verifier). Mark: INFERRED for the allowed extras list.
7. Show `determinism_class` next to every pair, and keep the label candidate, not verified.
   Why: a `gpu-approx` result is compared by ranking overlap, not by bytes (D-12).
   Source: `docs/mos-eureka-engine-run-contract.md`, key `encoder`. Mark: PROVEN for the key, ASSUMED for the display.
8. Check Canon Part 8 at its source. This page read it only from a summary in a plugin CLAUDE.md file.
   Why: the rule that room content never enters a Brain call limits what the plugin may send for a profile.
   Source: plugin CLAUDE.md summary. Mark: UNVERIFIED at source.
9. Capture the stderr of a start of `eureka-mcp` once. A healthy start writes 0 bytes to stderr (pinned by `tests/test_mcp_start_stderr.py`). The warning of the reference script was silenced by quick task 261107-w6v (recorded in STATE.md).
   Why: a plugin that reads stderr as a failure signal must see nothing on a healthy start.
   Source: the test and STATE.md in this repository. Mark: INFERRED for the plugin side, because the research never captured it.
10. The doctor does not check that the `mcp` package imports or that Node.js is present, so a green doctor does not prove that the server starts. Phase 5 adds only the encoder check D9. A later phase may add the other checks.
   Why: a host may trust a green doctor too much.
   Source: 05-RESEARCH.md lane `repo-mcp-and-plugin-contract`. Mark: PROVEN.

## Parked and later

A local NIM server stays a later option that the owner wants to keep (D-01). NIM does not support the RTX 3060, and a tunnel to a shared host breaks the rule that room text stays on the user's computer (05-RESEARCH.md Q2).

The topic taxonomy idea, with OpenAlex Topics as a soft signal, is parked (D-02).

The first comparison uses the public example of 36 records only. The JHTV corpus waits until the owner says so (D-03).

The default encoder changes only by a decision of the owner after the measured comparison (D-04). Nothing on this page changes it.

No GGUF weights, no NVFP4 weights and no loopback HTTP client are part of this phase.
