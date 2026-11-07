# Requirements: MindrianOS Eureka

**Defined:** 2026-10-23
**Core Value:** A user who is not the author can install Eureka, run it on their own collection with one command, and get the same ranked candidates every time, with hashes and settings that prove it.

## v1 Requirements

### Release readiness (REL)

- [x] **REL-01**: Maintainer has a written record of the unusual-pairs engine source origin, author attribution and license status, with a go / no-go for public distribution.
- [x] **REL-02**: README and package metadata state the unusual-pairs engine fidelity status (not verified bit-for-bit) in plain words.

### Engine parity (ENG)

- [x] **ENG-01**: A test runs plugin `rs-engine.py` and repo `eureka-pair-scout` on the same fixed input and reports the rank overlap and score differences.
- [x] **ENG-02**: The project records one chosen unusual-pairs engine path as canonical, or documents why both stay, with the parity result as evidence.
- [x] **ENG-03**: The exact wording-and-meaning pairs engine command and settings that produced `top_k 200` on the JHTV run are found, or rebuilt and recorded.

### One-command run (RUN)

- [x] **RUN-01**: User runs one command (`eureka run`) with a folder of CSV or Markdown sources and gets ranked pairs from the unusual-pairs engine and the wording-and-meaning pairs engine.
- [x] **RUN-02**: The command first builds a clean corpus with stable IDs, as `prepare_engine_corpus.py` does for JHTV.
- [x] **RUN-03**: The command writes a run manifest: input file hashes, record counts, settings, seeds, library and model versions, output hashes.
- [x] **RUN-04**: Running the command twice on the same input gives identical ranked output, and a test proves it.
- [x] **RUN-05**: Every output file keeps "candidate, not verified" labels and score-meaning notes.

### First-run experience (DOC)

- [x] **DOC-01**: `eureka doctor` checks Python, `uv`, local model presence, cache directory and data directory permissions, and prints the exact fix for each failure.
- [x] **DOC-02**: A missing model gives a clear message, never a silent failure.

### Host integration (HOST)

- [ ] **HOST-01**: `/mos:eureka` in MindrianOS calls the Eureka MCP server for the one-command run, with room scope and approval rules respected.
- [ ] **HOST-02**: The graph-derive replay used for JHTV OPP-027 to OPP-031 is rebuilt as a recorded, repeatable script, or the five candidates are marked "provenance gap" in the room.

### Hub (HUB)

- [ ] **HUB-01**: The hub is generated from `eureka run` output (opportunity bank, connection graph and catalogue views, with search and filter on the catalogue). It makes no network call and no data leaves the machine.
- [x] **HUB-02**: Every design choice (colour, type, layout, motion, Theo face) is ruled by the mos-brand book through its CLI (`mos-brand context`, `mos-brand review`), with the ruling cited in a design-decisions file.
- [ ] **HUB-03**: Every claim and opportunity on the hub shows its "candidate, not verified" status and its source link.
- [ ] **HUB-04**: The hub can be password-gated by an option, and the page reads from a local file only (enclave-safe).
- [ ] **HUB-05**: The existing JHTV hub (opportunity bank, idea graph, October leads page; reference files live in the partner room's solution-design folder) is reproduced in the new format from a public-data example, not from private room data.

### Public example (EXM)

- [x] **EXM-01**: A small public dataset example runs end to end with `eureka run` and ships with expected output hashes.
- [x] **EXM-02**: A "reproduce the JHTV method" guide for a non-author, in plain English, states what is reproducible and what is not.

### Encoder seam (ENC)

- [ ] **ENC-01**: One `EncoderSpec`, one `Encoder` protocol and one `make_encoder` factory build every encoder, with two named profiles (`cpu-default` with MiniLM at 384 dimensions, `gpu-nemotron` as a spike profile); MiniLM stays the default and every default result stays byte-identical.
- [ ] **ENC-02**: The two pair engines (`runner.py`, `run/engines.py`) and `doctor.py` load their encoder through the factory; the build sites that are not routed in this phase are listed with their risk, and `hsi_reference.py` is not edited.
- [ ] **ENC-03**: The embedding cache key holds the full encoder identity (model id, revision, model digest, dimension, dtype, attention, device, prefixes, normalization, chunking, batch size, token cap); the cache schema version is raised so old entries are ignored; a stored vector of the wrong width is rejected on a hit; each profile has its own cache file.
- [ ] **ENC-04**: The run manifest has an `encoder` block with the profile, the determinism class (`cpu-exact` or `gpu-approx`) and an encoder fingerprint for each engine; `eureka check-example` compares a `gpu-approx` run by ranking overlap and not by bytes, and never reports a match while no overlap threshold has been measured.
- [ ] **ENC-05**: Every ranked result carries the label "candidate, not verified" and an encoder fingerprint in a stable field: on each output of the library runner, in the optional `encoder` key of the host run result, and in the manifest; the pair files of a non-default profile also carry the fingerprint.
- [ ] **ENC-06**: `eureka doctor --encoder-profile NAME` adds one encoder check (profile name, libraries, device, model folder, and with `--load-model` the vector width) without changing the `eureka.doctor.v1` shape or any existing check id.
- [ ] **ENC-07**: GPU-related packages live in the optional extra `gpu-encoder`; the core dependencies stay `jsonschema`, `numpy` and `scikit-learn`; `uv.lock` is regenerated in the same commit as `pyproject.toml`.
- [ ] **ENC-08**: A self-contained spike script and a results page let the owner run `nvidia/Nemotron-3-Embed-1B-BF16` on the RTX 3060 in a scratch environment outside the repository; every number on the page comes from the run log; until the owner returns a log, every value is NOT RUN.
- [ ] **ENC-09**: A measured comparison of MiniLM, `mdbr-leaf-ir` and the Nemotron profile on the 36-record public example reports the dense top-200 pair overlap and the texts per second; the CPU part runs on this computer, a column that cannot run is marked NOT RUN with its reason, and the owner decides any change of the default encoder.
- [ ] **ENC-10**: The hand-offs for the MindrianOS plugin session (environment allowlist, request field for the profile, contract version marker, one `vec0` table for each profile, re-tuned 0.55 floor, failure reasons, start stderr, doctor checks that are not added) are written in `docs/encoder-profiles.md` with a source and a mark for each; no plugin checkout is edited.
- [ ] **ENC-11**: The READMEs (README.md, examples/public-example/README.md, src/README.md) are refreshed for the encoder profiles, `--encoder-profile`, `doctor --encoder-profile`, the `gpu-encoder` extra and the `cpu-exact` / `gpu-approx` classes, and every claim is checked against the code and a run (owner rule 2026-11-07).

## v2 Requirements

- **CAT-01**: Promote experimental capabilities to supported, one at a time, with benchmark evidence.
- **EVAL-01**: Bundle a benchmark corpus and reviewer rubric so method variants can be compared.
- **DEDUP-01**: Near-duplicate and same-family record handling before ranking.
- **DOM-01**: Domain-aware filtering so "cross-domain" pairs really cross domains.
- **LIM-01**: A memory guard for the pair-screen job at 3,000 artifacts (about 3.4 GB is ASSUMED in limits.py; a long-lived MCP process could be OOM-killed). Source: independent code review 2026-11-07, finding 10b; recorded in docs/mos-eureka-engine-run-contract.md.
- **PLG-01**: Plugin-side wiring for the pair-screen routes (ALLOWED_MCP_ROUTES, ASYNC_ROUTES, routeGate needs, caps 100 to 200 and 2,500 to 3,000), owned by the MindrianOS plugin repo (nearest fit: plugin Phase 374).
- **TAX-01**: Optional topic taxonomy layer for graph typing (OpenAlex Topics, CC0) as a soft signal; parked by the owner on 2026-11-07.
- **NIM-01**: Local NIM hosting of the embedding model, kept as a later option by the owner on 2026-11-07 (research: docs/research/mindrian-eureka-local-nim-hosting.md).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Novelty, demand or value scoring | Scores are screening signals, never proof |
| Web research inside the engine | MindrianOS owns approved research and grants |
| Writing to room graphs or portfolios | Host owns those writes |
| Downloading models in MCP server | Local-only by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REL-01 | Phase 1 - Release Gate and Engine Parity | Complete (record exists; decision draft no-go; owner sign-off pending) |
| REL-02 | Phase 1 - Release Gate and Engine Parity | Complete |
| ENG-01 | Phase 1 - Release Gate and Engine Parity | Complete |
| ENG-02 | Phase 1 - Release Gate and Engine Parity | Complete |
| ENG-03 | Phase 1 - Release Gate and Engine Parity | Complete |
| RUN-01 | Phase 2 - One-Command Run and Doctor | Complete |
| RUN-02 | Phase 2 - One-Command Run and Doctor | Complete |
| RUN-03 | Phase 2 - One-Command Run and Doctor | Complete |
| RUN-04 | Phase 2 - One-Command Run and Doctor | Complete |
| RUN-05 | Phase 2 - One-Command Run and Doctor | Complete |
| DOC-01 | Phase 2 - One-Command Run and Doctor | Complete |
| DOC-02 | Phase 2 - One-Command Run and Doctor | Complete |
| HOST-01 | Phase 3 - Host Integration and Replay Rebuild | Eureka side complete; plugin wiring open |
| HOST-02 | Phase 3 - Host Integration and Replay Rebuild | Eureka side complete (provenance gap recorded); room mark open |
| HUB-01 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-02 | Phase 2.1 - Opportunity Hub in the mos-brand format | Complete |
| HUB-03 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-04 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-05 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| EXM-01 | Phase 4 - Public Example and Reproduction Guide | Complete |
| EXM-02 | Phase 4 - Public Example and Reproduction Guide | Complete (owner check: non-author run) |
| ENC-01 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-02 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-03 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-04 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-05 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-06 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-07 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-08 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-09 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-10 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-11 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |

**Coverage:**

- v1 requirements: 32 total
- Mapped to phases: 32 (Phase 1: 5, Phase 2: 7, Phase 2.1: 5, Phase 3: 2, Phase 4: 2, Phase 5: 11)
- Unmapped: 0

---
*Requirements defined: 2026-10-23*
*Last updated: 2026-11-08 after adding Phase 5 (Encoder seam, ENC-01 to ENC-11)*
