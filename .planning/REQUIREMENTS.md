# Requirements: MindrianOS Eureka

**Defined:** 2026-10-23
**Core Value:** A user who is not the author can install Eureka, run it on their own collection with one command, and get the same ranked candidates every time, with hashes and settings that prove it.

## v1 Requirements

### Release readiness (REL)

- [ ] **REL-01**: Maintainer has a written record of the RS source origin, author attribution and license status, with a go / no-go for public distribution.
- [ ] **REL-02**: README and package metadata state the RS fidelity status (not verified bit-for-bit) in plain words.

### Engine parity (ENG)

- [ ] **ENG-01**: A test runs plugin `rs-engine.py` and repo `eureka-pair-scout` on the same fixed input and reports the rank overlap and score differences.
- [ ] **ENG-02**: The project records one chosen RS path as canonical, or documents why both stay, with the parity result as evidence.
- [ ] **ENG-03**: The exact HSI command and settings that produced `top_k 200` on the JHTV run are found, or rebuilt and recorded.

### One-command run (RUN)

- [ ] **RUN-01**: User runs one command (`eureka run`) with a folder of CSV or Markdown sources and gets RS and HSI ranked pairs.
- [ ] **RUN-02**: The command first builds a clean corpus with stable IDs, as `prepare_engine_corpus.py` does for JHTV.
- [ ] **RUN-03**: The command writes a run manifest: input file hashes, record counts, settings, seeds, library and model versions, output hashes.
- [ ] **RUN-04**: Running the command twice on the same input gives identical ranked output, and a test proves it.
- [ ] **RUN-05**: Every output file keeps "candidate, not verified" labels and score-meaning notes.

### First-run experience (DOC)

- [ ] **DOC-01**: `eureka doctor` checks Python, `uv`, local model presence, cache directory and data directory permissions, and prints the exact fix for each failure.
- [ ] **DOC-02**: A missing model gives a clear message, never a silent failure.

### Host integration (HOST)

- [ ] **HOST-01**: `/mos:eureka` in MindrianOS calls the Eureka MCP server for the one-command run, with room scope and approval rules respected.
- [ ] **HOST-02**: The graph-derive replay used for JHTV OPP-027 to OPP-031 is rebuilt as a recorded, repeatable script, or the five candidates are marked "provenance gap" in the room.

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
| REL-01 | Phase 1 - Release Gate and Engine Parity | Pending |
| REL-02 | Phase 1 - Release Gate and Engine Parity | Pending |
| ENG-01 | Phase 1 - Release Gate and Engine Parity | Pending |
| ENG-02 | Phase 1 - Release Gate and Engine Parity | Pending |
| ENG-03 | Phase 1 - Release Gate and Engine Parity | Pending |
| RUN-01 | Phase 2 - One-Command Run and Doctor | Pending |
| RUN-02 | Phase 2 - One-Command Run and Doctor | Pending |
| RUN-03 | Phase 2 - One-Command Run and Doctor | Pending |
| RUN-04 | Phase 2 - One-Command Run and Doctor | Pending |
| RUN-05 | Phase 2 - One-Command Run and Doctor | Pending |
| DOC-01 | Phase 2 - One-Command Run and Doctor | Pending |
| DOC-02 | Phase 2 - One-Command Run and Doctor | Pending |
| HOST-01 | Phase 3 - Host Integration and Replay Rebuild | Pending |
| HOST-02 | Phase 3 - Host Integration and Replay Rebuild | Pending |
| EXM-01 | Phase 4 - Public Example and Reproduction Guide | Pending |
| EXM-02 | Phase 4 - Public Example and Reproduction Guide | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16 (Phase 1: 5, Phase 2: 7, Phase 3: 2, Phase 4: 2)
- Unmapped: 0

---
*Requirements defined: 2026-10-23*
*Last updated: 2026-10-23 after roadmap creation*
