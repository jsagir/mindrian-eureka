# Roadmap: MindrianOS Eureka

## Overview

The first milestone makes Eureka operational by other users. The JHTV review on 2026-10-23 showed that the run is only partly reproducible and that no one-command path exists. The work goes in four steps. First, settle the one item that can block a public release (licensing and attribution of the unusual-pairs engine, formerly called RS) and prove which unusual-pairs and wording-and-meaning paths are trustworthy. Second, build the one-command run (`eureka run`) and the first-run check (`eureka doctor`) on top of those proven paths. Third, connect the run to MindrianOS (`/mos:eureka`) and close the graph-derive replay gap. Fourth, ship a small public example and a plain-English guide so a non-author can reproduce the method and knows what is not reproducible.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Release Gate and Engine Parity** (completed 2026-10-23, one open owner item) - Settle unusual-pairs engine licensing and attribution, prove or choose its canonical path, recover the wording-and-meaning pairs engine command
- [ ] **Phase 2: One-Command Run and Doctor** - `eureka run` builds a clean corpus, ranks unusual pairs and wording-and-meaning pairs, writes a manifest; `eureka doctor` checks the setup
- [ ] **Phase 2.1: Opportunity Hub in the mos-brand format** - One local page shows the opportunity bank, the connection graph and the full catalogue of an analyzed collection, styled by the mos-brand book
- [ ] **Phase 3: Host Integration and Replay Rebuild** - `/mos:eureka` calls the run through the MCP server; the graph-derive replay is rebuilt or marked as a provenance gap
- [ ] **Phase 4: Public Example and Reproduction Guide** - Small public dataset with expected hashes, plus a "reproduce the JHTV method" guide

## Phase Details

### Phase 1: Release Gate and Engine Parity
**Goal**: The maintainer knows whether Eureka may ship publicly, which unusual-pairs engine path is canonical, and which wording-and-meaning pairs engine command produced the JHTV `top_k 200` result.
**Depends on**: Nothing (first phase)
**Requirements**: REL-01, REL-02, ENG-01, ENG-02, ENG-03
**Success Criteria** (what must be TRUE):
  1. The maintainer can open one written record that states the unusual-pairs engine source origin, author attribution and license status, and ends with a go / no-go for public distribution.
  2. Running the parity test on one fixed input prints the rank overlap and the score differences between plugin `rs-engine.py` and repo `eureka-pair-scout`.
  3. The project docs name one canonical unusual-pairs engine path, or explain why both stay, and cite the parity result as evidence.
  4. A reader can copy the exact wording-and-meaning pairs engine command and settings that produced `top_k 200` on the JHTV run, either found in the room history or rebuilt and recorded.
  5. The README and the package metadata state in plain words that unusual-pairs engine fidelity is not verified bit-for-bit.
**Plans**: 6 plans, all complete
- [x] 01-01: Release-gate record (decision stays draft no-go; owner sign-off pending)
- [x] 01-02: Reproduction record for the JHTV pair results
- [x] 01-03: Parity test for the unusual-pairs engine
- [x] 01-04: Stable top-7 term order
- [x] 01-05: Canonical path record for the unusual-pairs engine
- [x] 01-06: Fidelity statement
**Open owner item**: sign-off on the release decision (draft no-go). Phases 2 and 3 proceed; Phase 4 ships internal only until the owner changes it.
**Scope notes**: The go / no-go gates public shipping in Phase 4 only. Phases 2 and 3 can proceed on a no-go. REL-02 wording depends on the REL-01 record and the ENG-01 result.

### Phase 2: One-Command Run and Doctor
**Goal**: A non-author can check their setup, run one command on a folder of their own sources, and get the same ranked pairs every time, with a manifest that proves it.
**Depends on**: Phase 1 (canonical unusual-pairs engine path and wording-and-meaning pairs engine command decide what `eureka run` calls)
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. User runs `eureka run` on a folder of CSV or Markdown sources and gets ranked pair files from both engines, built on a clean corpus with stable record IDs.
  2. Each run writes a manifest with input file hashes, record counts, settings, seeds, library and model versions, and output file hashes.
  3. Running the command twice on the same input gives identical ranked output, and a test in the suite proves it.
  4. Every output file carries the "candidate, not verified" label and a score-meaning note.
  5. `eureka doctor` checks Python, `uv`, local model presence, and cache and data directory permissions, and prints the exact fix for each failure. A missing model produces a clear message, never a silent failure.
**Plans**: 6 plans in 3 waves (wave 1: 02-01; wave 2: 02-02, 02-03, 02-04, 02-05 in parallel; wave 3: 02-06)
- [x] 02-01: Caps lift (top_k 200, 3,000 artifacts), shared contracts and test scaffold
- [ ] 02-02: Corpus builder with CSV mapping file and flags
- [ ] 02-03: Typed engine facade for both engines
- [ ] 02-04: Projection, canonical writer, manifest and console
- [ ] 02-05: Model discovery, `eureka doctor` and offline install note
- [ ] 02-06: Pipeline, CLI wiring, run-twice (RUN-04) and label (RUN-05) tests

### Phase 2.1: Opportunity Hub in the mos-brand format
**Goal**: A user who ran `eureka run` can open one local page that shows the opportunity bank, the connection graph and the full catalogue of the analyzed collection, styled by the mos-brand book.
**Depends on**: Phase 2 (the hub reads the `eureka run` output and its manifest)
**Requirements**: HUB-01, HUB-02, HUB-03, HUB-04, HUB-05
**Success Criteria** (what must be TRUE):
  1. After `eureka run` on a folder of sources, one command writes a single local hub page with three views (opportunity bank, connection graph, full catalogue). The catalogue has search and filter. A check shows the page makes no network call and loads only local files.
  2. A design-decisions file lists every choice for colour, type, layout, motion and the Theo face, and cites the mos-brand ruling (`mos-brand context`, `mos-brand review`) for each. The review passes on the hub page.
  3. Every claim and every opportunity on the hub shows the label "candidate, not verified" and a link to its source record. A test fails when an item lacks either.
  4. The hub can be password-gated by an option, and the page reads from a local file only. The public-data example reproduces the existing JHTV hub (opportunity bank, idea graph, October leads page) in the new format, with no private room data in the repo.
**Plans**: TBD
**Scope notes**: The mos-brand book (`~/mos-brand`, CLI `bin/mos-brand.cjs`) is the design authority. A brand intake runs as the first plan. The JHTV reference files live in the partner room's solution-design folder; use them as a visual and structural reference only. The example must come from public data.

### Phase 3: Host Integration and Replay Rebuild
**Goal**: A MindrianOS user can start the one-command run from `/mos:eureka`, and the five JHTV candidates that cite the graph-derive replay have either a repeatable script or an honest provenance-gap mark.
**Depends on**: Phase 2 (the MCP server calls the one-command run; the replay script reuses the manifest pattern)
**Requirements**: HOST-01, HOST-02
**Success Criteria** (what must be TRUE):
  1. In MindrianOS, `/mos:eureka` starts the one-command run through the Eureka MCP server and returns the ranked output with the host handoff block.
  2. The run respects room scope and approval rules: it does not start without the approval step, and Eureka writes nothing to the room graph.
  3. Either a recorded script rebuilds the graph-derive replay and two runs give the same output hashes, with its claim and pair counts compared to the cited 2,130 claims and 2,267,385 pairs, or OPP-027 to OPP-031 are marked "provenance gap" in the room.
**Plans**: TBD
**Scope notes**: HOST-01 touches the MindrianOS plugin repo, which has its own GSD-only rule. Plan-phase must split the Eureka side (MCP tool surface) from the plugin side (command wiring). Room marks for HOST-02 are host-owned writes and need approval.

### Phase 4: Public Example and Reproduction Guide
**Goal**: A stranger can reproduce a documented run from public data and knows exactly what is and is not reproducible about the JHTV method.
**Depends on**: Phase 2 (`eureka run` and manifest), Phase 3 (the guide reports the replay outcome), Phase 1 (public shipping needs a go decision)
**Requirements**: EXM-01, EXM-02
**Success Criteria** (what must be TRUE):
  1. A small public dataset ships in the repo, and `eureka run` on it finishes end to end on a fresh checkout.
  2. The output hashes of that run match the shipped expected hashes, and a check fails when they differ.
  3. A "reproduce the JHTV method" guide in plain English walks a non-author through the steps from install to ranked pairs.
  4. The guide states what is reproducible (the unusual-pairs and wording-and-meaning pairs engines, per the Phase 1 record), what is not (the replay outcome from Phase 3, unusual-pairs engine bit-for-bit fidelity), and keeps the "candidate, not verified" wording.
**Plans**: TBD
**Scope notes**: The dataset license must allow redistribution. If REL-01 ends in no-go, ship the example and guide as internal only and record the reason.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 2.1 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Release Gate and Engine Parity | 6/6 | Complete (owner sign-off open) | 2026-10-23 |
| 2. One-Command Run and Doctor | 1/6 | In progress | - |
| 2.1. Opportunity Hub in the mos-brand format | 0/TBD | Not started | - |
| 3. Host Integration and Replay Rebuild | 0/TBD | Not started | - |
| 4. Public Example and Reproduction Guide | 0/TBD | Not started | - |
