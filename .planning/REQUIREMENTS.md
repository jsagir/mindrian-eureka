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

- [ ] **EXM-01**: A small public dataset example runs end to end with `eureka run` and ships with expected output hashes.
- [ ] **EXM-02**: A "reproduce the JHTV method" guide for a non-author, in plain English, states what is reproducible and what is not.

## v2 Requirements

- **CAT-01**: Promote experimental capabilities to supported, one at a time, with benchmark evidence.
- **EVAL-01**: Bundle a benchmark corpus and reviewer rubric so method variants can be compared.
- **DEDUP-01**: Near-duplicate and same-family record handling before ranking.
- **DOM-01**: Domain-aware filtering so "cross-domain" pairs really cross domains.

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
| HOST-01 | Phase 3 - Host Integration and Replay Rebuild | Pending |
| HOST-02 | Phase 3 - Host Integration and Replay Rebuild | Pending |
| HUB-01 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-02 | Phase 2.1 - Opportunity Hub in the mos-brand format | Complete |
| HUB-03 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-04 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| HUB-05 | Phase 2.1 - Opportunity Hub in the mos-brand format | Pending |
| EXM-01 | Phase 4 - Public Example and Reproduction Guide | Pending |
| EXM-02 | Phase 4 - Public Example and Reproduction Guide | Pending |

**Coverage:**

- v1 requirements: 21 total
- Mapped to phases: 21 (Phase 1: 5, Phase 2: 7, Phase 2.1: 5, Phase 3: 2, Phase 4: 2)
- Unmapped: 0

---
*Requirements defined: 2026-10-23*
*Last updated: 2026-10-23 after adding Phase 2.1 (Hub)*
