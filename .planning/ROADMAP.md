# Roadmap: MindrianOS Eureka

## Overview

The first milestone makes Eureka operational by other users. The JHTV review on 2026-10-23 showed that the run is only partly reproducible and that no one-command path exists. The work goes in four steps. First, settle the one item that can block a public release (licensing and attribution of the unusual-pairs engine, formerly called RS) and prove which unusual-pairs and wording-and-meaning paths are trustworthy. Second, build the one-command run (`eureka run`) and the first-run check (`eureka doctor`) on top of those proven paths. Third, connect the run to MindrianOS (`/mos:eureka`) and close the graph-derive replay gap. Fourth, ship a small public example and a plain-English guide so a non-author can reproduce the method and knows what is not reproducible.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Release Gate and Engine Parity** (completed 2026-10-23, one open owner item) - Settle unusual-pairs engine licensing and attribution, prove or choose its canonical path, recover the wording-and-meaning pairs engine command
- [x] **Phase 2: One-Command Run and Doctor** - `eureka run` builds a clean corpus, ranks unusual pairs and wording-and-meaning pairs, writes a manifest; `eureka doctor` checks the setup
- [ ] **Phase 2.1: Opportunity Hub in the mos-brand format** - One local page shows the opportunity bank, the connection graph and the full catalogue of an analyzed collection, styled by the mos-brand book
- [x] **Phase 3: Host Integration and Replay Rebuild** - `/mos:eureka` calls the run through the MCP server; the graph-derive replay is rebuilt or marked as a provenance gap
- [x] **Phase 4: Public Example and Reproduction Guide** - Small public dataset with expected hashes, plus a "reproduce the JHTV method" guide
- [x] **Phase 04.1: Fix the review findings** (INSERTED) - Fix the defects the Codex review and the independent code review confirm, starting with Windows launcher paths with spaces
- [ ] **Phase 5: Encoder seam, safe cache key and local GPU spike** (human_needed: waits for the owner GPU spike log) - One place builds every encoder, the cache never mixes setups, and one local GPU encoder is proven on the owner's computer; MiniLM stays the default

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
- [x] 02-02: Corpus builder with CSV mapping file and flags
- [x] 02-03: Typed engine facade for both engines
- [x] 02-04: Projection, canonical writer, manifest and console
- [x] 02-05: Model discovery, `eureka doctor` and offline install note
- [x] 02-06: Pipeline, CLI wiring, run-twice (RUN-04) and label (RUN-05) tests

### Phase 02.3: Room seed hand-off to MindrianOS (INSERTED)

**Goal:** A candidate intersection from a Eureka run becomes a seed bundle (`eureka.room-seed.v1`) that MindrianOS can open as a room through its own birth chokepoint: `eureka seed <run> --pair <id>` and `--cluster <record-id>` write the statement draft, the evidence with hashes, "what we know" and "what to feed next" per room section from the filled and blank columns, and `eureka seed --list` ranks candidates by pair class and node degree. The plugin-side `/mos:ignite --from-seed` is specified in a contract doc for its own phase in the plugin repo. Offline, deterministic, no model, no room write.
**Requirements**: SEED-01 (seed contract and schema), SEED-02 (column-to-section map and not-in-export list as mapping data), SEED-03 (pair and cluster seeds with known and feed-next lists), SEED-04 (candidate list by class and degree), SEED-05 (hub action naming the seed command), SEED-06 (plugin consumption contract doc with the model boundary stated)
**Depends on:** Phase 2.2 (pair_class, carried columns, mapping schema, hub chip row)
**Context:** .planning/phases/02.3-room-seed-hand-off-to-mindrianos/02.3-CONTEXT.md
**Plans:** 5/5 plans executed (verification: human_needed)

Plans:

- [x] 02.3-01: Room-section map in the mapping file, room cell states in runs, hub reader fields
- [x] 02.3-02: Seed contract, closed schema, pair seed builder and `eureka seed --pair`
- [x] 02.3-03: Pair graph, `--cluster` and `--list`
- [x] 02.3-04: Seed command row in the hub bank
- [x] 02.3-05: Plugin hand-off contract doc `docs/room-seed-contract.md`

### Phase 02.3.1: Hub look matches the live JHTV site: cobalt, red and yellow accents, sticky header, finding rows, black pattern band (INSERTED)

**Goal:** The hub page that `eureka hub` writes looks like the live JHTV hub site the owner named (cobalt, red and yellow accents, sticky header with section navigation, large cobalt numerals, finding rows, a black pattern band), while it stays offline, accessible and honest, and the brand stop is re-recorded on the new look.
**Requirements**: HUB-02 (re-opened by the owner's NOT APPROVED verdict, 2026-11-08), HUB-06, HUB-07, HUB-08, HUB-09, HUB-10, HUB-11 (plus HUB-01, HUB-03, HUB-04)
**Depends on:** Phase 2.3
**Success Criteria** (what must be TRUE):

  1. The page built from the public fixture matches the target's look at 320, 390, 768, 1280 and 1600 px: the same colour roles, type scale, header and navigation, eyebrow plus heading, finding rows, and black band. A side-by-side check against the target stylesheet tokens passes.
  2. The owner's ruling (D-01) is recorded with its date, and each UI decision cites a mos-brand book segment where the book speaks, or an owner ruling of 2026-11-08 (R-01: the session decisions overrule the book where they conflict) with a proposed book segment. The book review is advisory: it is recorded "not run, lock not reconciled, by owner ruling" and is not a gate.
  3. The hub stays offline and keeps its behavior: no network request, the locked page, the data check, the reading panel, all three views, keyboard routes, 44 px targets, reduced motion honoured. The black band is generated from run data with sourced numbers only.
  4. Every test and hash that pinned the old look is updated on purpose with the reason recorded; the full suite stays green (baseline 1941 passed, 0 failed); ruff 1452 and mypy 87 errors do not rise.
  5. No name from the target site is committed. Close-out: READMEs refreshed (owner rule 2026-11-07) and plan 02.1-17 re-opened as pending the owner's look at the new page.
  6. The page has a light and a dark theme with a header toggle. The first load follows the system setting, the choice persists across reload, there is no flash, and every text and graphic pair passes contrast in both themes (HUB-10).
  7. Every pair and every record opens as a page with a breadcrumb, a Back knob, Previous and Next knobs with a position, working arrow keys and Escape, focus on the heading and a document title. The unknown-route notice and the old routes keep working (HUB-11).
  8. Each pair has a picture that shows the core of that lead from the words of its two records, deterministic and generated by the hub's own code, with a real-text version for narrow screens and screen readers (HUB-06).

**Plans:** 0 of 9 complete

Plans:

- [ ] 02.3.1-01: Run reading band (black band from sourced numbers) (wave 1)
- [ ] 02.3.1-02: Distinctive words (tf-idf rule, goldens, rules file) (wave 1)
- [ ] 02.3.1-03: Shell look, look contract, owner ruling, deck parts (wave 2)
- [ ] 02.3.1-04: Figures in the payload (card and detail, terms, legend) (wave 2)
- [ ] 02.3.1-05: Light and dark theme with a toggle (wave 3)
- [ ] 02.3.1-06: Bank finding rows, stretched links, target parity test (wave 3)
- [ ] 02.3.1-07: Graph, catalogue and panel look, header wiring, Open links, thumbnails (wave 3)
- [ ] 02.3.1-08: Page routes, Back, Previous and Next knobs, pair and record pages, twin (wave 4)
- [ ] 02.3.1-09: Evidence in both themes, READMEs, owner decision (wave 5; owner checkpoint)

**Scope notes**: Owner-requested urgent insert after the Phase 2.1 brand stop (2026-11-08). Evidence and decisions: `.planning/phases/02.3.1-*/02.3.1-CONTEXT.md`.

### Phase 02.2: Partner export profile and package (INSERTED)

**Goal:** A partner who holds a technology-portfolio CSV export (one row per case number, outcome flags and dates, abstract possibly blank) runs `eureka run` on their own offline machine with a shipped mapping, gets cross pairs (an open technology next to one with a commercial outcome) and open-open bundle candidates, sees the outcome columns beside every pair in the run output and the hub, fills thin text from a case-number side-car with the coverage stated in numbers, and installs it all from a one-page partner guide. The owner's ruling on partner-internal distribution is recorded in the release gate.
**Requirements**: PKG-01 (mapping for the export, outcome and people columns never in text), PKG-02 (corpus rule from outcome columns, cross-corpus run, open-open list), PKG-03 (carry columns on pair payloads and in the hub, additive contract), PKG-04 (case-number text side-car with a coverage line and manifest hash), PKG-05 (partner run guide plus MINDRIAN_EUREKA_ROOT hookup), PKG-06 (owner ruling recorded in docs/rs-release-gate.md: partner-internal approved 2026-10-29, public stays no-go, G1 G2 G3 G5 open), PKG-07 (carry-in bundle and launcher: one folder per target with uv, wheels, model, source, mapping, guide, hashed manifest, start.sh and start.ps1 running doctor, run, hub, open; optional Docker-load variant)
**Depends on:** Phase 2 (eureka run, mapping, doctor, offline install), Phase 2.1 (hub reader and contracts)
**Context:** .planning/phases/02.2-partner-export-profile-and-package/02.2-CONTEXT.md
**Plans:** 4 plans in 3 waves (wave 1: 02.2-01; wave 2: 02.2-02, 02.2-03 in parallel; wave 3: 02.2-04)

Plans:

- [x] 02.2-01: Mapping schema (`outcome_rule`, `carry_columns`), outcome class on every pair at the projection layer, carried cells, per-engine class counts, manifest keys, conditional Class column, shipped mapping `examples/mappings/technology-audit-export.json`
- [x] 02.2-02: `--text-sidecar` join by raw id with the coverage line and manifest hash, `docs/partner-run-guide.md`, the dated partner-internal ruling in `docs/rs-release-gate.md`, host cross-link
- [x] 02.2-03: Brand token sheet refresh, hub contracts and reader (additive, unknown class refused), class chips and filter, 2,000-record scale check
- [x] 02.2-04: Carry-in bundle builder (`scripts/build-partner-bundle`, hashed manifest, uv and optional Docker variants) and the `start.sh` / `start.ps1` launchers

### Phase 2.1: Opportunity Hub in the mos-brand format

**Goal**: A user who ran `eureka run` can open one local page that shows the opportunity bank, the connection graph and the full catalogue of the analyzed collection, styled by the mos-brand book.
**Depends on**: Phase 2 (the hub reads the `eureka run` output and its manifest)
**Requirements**: HUB-01, HUB-02, HUB-03, HUB-04, HUB-05
**Success Criteria** (what must be TRUE):

  1. After `eureka run` on a folder of sources, one command writes a single local hub page with three views (opportunity bank, connection graph, full catalogue). The catalogue has search and filter. A check shows the page makes no network call and loads only local files.
  2. A design-decisions file lists every choice for colour, type, layout, motion and the Theo face, and cites the mos-brand ruling (`mos-brand context`, `mos-brand review`) for each. The review passes on the hub page.
  3. Every claim and every opportunity on the hub shows the label "candidate, not verified" and a link to its source record. A test fails when an item lacks either.
  4. The hub can be password-gated by an option, and the page reads from a local file only. The public-data example reproduces the existing JHTV hub (opportunity bank, idea graph, October leads page) in the new format, with no private room data in the repo.

**Plans**: 19 plans in 10 waves (wave 1: 02.1-01 to 02.1-04 in parallel; wave 2: 02.1-05, 02.1-06, 02.1-07 in parallel; wave 3: 02.1-08; wave 4: 02.1-09; wave 5: 02.1-10; wave 6: 02.1-11 to 02.1-15 in parallel; wave 7: 02.1-18; wave 8: 02.1-16; wave 9: 02.1-19; wave 10: 02.1-17)

- [x] 02.1-01: Brand intake with mos-brand (init, owner checkpoint, configure, adopt), decisions file and silent-item register
- [x] 02.1-02: Phase 2 touch-ups: W1 engine note fix, staged-run hook for the hub, W2 README run and doctor section
- [x] 02.1-03: Hub package base: contracts, copy deck, run reader, run-folder test helper
- [x] 02.1-04: Browser test harness and recorded probes (WebCrypto, CSP, WebGL, library facts, crypto dependency)
- [x] 02.1-05: Hub model: neighborhoods, cut-offs, bridges, data check, payload, label and source link guard
- [x] 02.1-06: Packaged book assets, vendored 3d-force-graph, package data and hub-gate extra (package legitimacy checkpoint)
- [x] 02.1-07: Public-data fixture with license record and a frozen real run (HUB-05 input)
- [x] 02.1-08: Page shell with server-side lists, locked form of the page, and tests
- [x] 02.1-09: Hub writer, hub manifest, source links and the `eureka hub` command, static no-network scanners
- [x] 02.1-10: Front-end core: stylesheet, HubApp API, routing, shell behavior, static rule tests, browser tests
- [x] 02.1-11: Opportunity bank view
- [x] 02.1-12: Catalogue view
- [x] 02.1-13: Reading panel
- [x] 02.1-14: Password gate (`--password-env`): encryption, unlock script, gate record
- [x] 02.1-15: Connection graph view: guide, legend, Find, small-collection diagram, pair list, bridge tour, fallbacks
- [x] 02.1-16: HUB-05 reproduction on the public fixture, JHTV view mapping, README section, copy and close tests
- [ ] 02.1-17: Owner decision (brand stop) and its record
- [x] 02.1-18: Connection graph 3D stage: loader, camera player, labels, CSP check with the library, 3,000-record scale test
- [x] 02.1-19: `mos-brand review`, screenshots and measurements, review record, return of the gaps to the book

**Scope notes**: The mos-brand book (`~/mos-brand`, CLI `bin/mos-brand.cjs`) is the design authority. A brand intake runs as the first plan. The JHTV reference files live in the partner room's solution-design folder; use them as a visual and structural reference only. The example must come from public data.

### Phase 3: Host Integration and Replay Rebuild

**Goal**: A MindrianOS user can start the one-command run from `/mos:eureka`, and the five JHTV candidates that cite the graph-derive replay have either a repeatable script or an honest provenance-gap mark.
**Depends on**: Phase 2 (the MCP server calls the one-command run; the replay script reuses the manifest pattern)
**Requirements**: HOST-01, HOST-02
**Success Criteria** (what must be TRUE):

  1. The Eureka MCP server exposes a plan tool and a start tool for the one-command run, with the approval step and the result envelope that carries the host handoff block. The plugin wiring that makes `/mos:eureka` call them is a separate plugin phase under the plugin's own GSD rule (reworded 2026-11-07 after the feasibility check).
  2. The run respects room scope and approval rules: it does not start without the approval step, and Eureka writes nothing to the room graph.
  3. Either a recorded script rebuilds the graph-derive replay and two runs give the same output hashes, with its claim and pair counts compared to the cited 2,130 claims and 2,267,385 pairs, or OPP-027 to OPP-031 are marked "provenance gap" in the room.

**Plans**: 7 plans

Plans:

- [x] 03-01 to 03-07, complete 2026-11-07 (verification: human_needed; see `.planning/phases/03-host-integration-and-replay-rebuild/`)

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

**Plans**: 4 plans

Plans:

- [x] 04-01 to 04-04, complete 2026-11-07 (verification: human_needed; see `.planning/phases/04-public-example-and-reproduction-guide/`); 04-04 waits for the Phase 3 record `docs/jhtv-replay-record.md`

**Scope notes**: The dataset license must allow redistribution. If REL-01 ends in no-go, ship the example and guide as internal only and record the reason.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 2.1 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Release Gate and Engine Parity | 6/6 | Complete (owner sign-off open) | 2026-10-23 |
| 2. One-Command Run and Doctor | 6/6 | Complete (verification: human_needed) | 2026-10-24 |
| 2.1. Opportunity Hub in the mos-brand format | 18/19 | In progress | - |
| 2.2. Partner export profile and package | 4/4 | Complete (verification: human_needed) | 2026-10-29 |
| 2.3. Room seed hand-off to MindrianOS | 5/5 | Complete (verification: human_needed) | 2026-11-07 |
| 3. Host Integration and Replay Rebuild | 7/7 | Complete (verification: human_needed) | 2026-11-07 |
| 4. Public Example and Reproduction Guide | 4/4 | Complete (verification: human_needed) | 2026-11-07 |
| 4.1. Fix the review findings | 3/3 | Complete (verification: human_needed) | 2026-11-08 |
| 5. Encoder seam, safe cache key and local GPU spike | 8/9 (05-08 awaits the owner spike) | Verified: human_needed | - |

### Phase 04.1: Fix the review findings (Codex and code review): Windows launcher paths with spaces and anything the reviews confirm (INSERTED)

**Goal:** Every defect that a review of the Phase 3 and Phase 4 work confirms is fixed, tested and recorded, starting with the one the Codex adversarial review found on 2026-11-07, so the committed capabilities will work for a MindrianOS user.
**Requirements**: PKG-07, HOST-01, EXM-01 (fixes to delivered work; no new requirement)
**Depends on:** Phase 4
**Success Criteria** (what must be TRUE):

  1. Windows launcher: the `uv sync` command is built as a PowerShell argument array, so a bundle path with spaces stays one argument. A text test pins it. It stays ASSUMED until a Windows machine runs it, because PowerShell is not installed on the build machine.
  2. Each finding of the independent code review (requested 2026-11-07 over the range 874f40b..6741585) that this phase confirms as Critical or Important is fixed with a failing test first, or is recorded as declined with the reason.
  3. No finding is fixed by weakening a test. The full suite stays at or above 1701 passed with 0 failed; ruff 1465 and mypy 88 errors do not rise.
  4. Close-out: the READMEs (README.md, examples/public-example/README.md, src/README.md and any doc index that lists counts or commands) are refreshed and checked against the code and a run (owner rule 2026-11-07: refresh the READMEs after each version).

**Plans:** 3 of 3 complete (verification: human_needed, 04.1-VERIFICATION.md)

Plans:

- [x] 04.1-01: Windows launcher passes the `uv sync` arguments as an array (delivered as quick task 261107-wuy, commit 4be74df)
- [x] 04.1-02: Code fixes confirmed by the independent code review (receipt replay after delete, lone surrogates, extra index scope, quiet import order, hidden input in tool errors, envelope leak test)
- [x] 04.1-03: Contract and guide honesty fixes, README refresh against the code

**Scope notes**: Urgent insert at the owner's request ("add a phase to fix what codex found, asap now"). Do not edit `hsi_reference.py`. No plugin checkout edits.

### Phase 5: Encoder seam, safe cache key and local GPU spike

**Goal:** Eureka builds every encoder in one place, never reuses a vector made by a different encoder setup, and can run one named local GPU encoder on the user's own computer, while MiniLM stays the default and every default result stays byte-identical.
**Requirements**: ENC-01, ENC-02, ENC-03, ENC-04, ENC-05, ENC-06, ENC-07, ENC-08, ENC-09, ENC-10, ENC-11 (research source: the 2026-11-07 fan-out research, 8 lanes, 18 agents)
**Depends on:** Phase 4
**Success Criteria** (what must be TRUE):

  1. One `EncoderSpec` and one `make_encoder` build every encoder. The two pair engines use it first. The other build sites follow; at least seven exist today (runner.py, run/engines.py, hsi_engine.py, analogy_fitness.py, hsi_reference.py, pitch_analysis/algorithm.py, doctor.py). `hsi_reference.py` is not edited, because its hash is recorded in manifests.
  2. The embedding cache key holds the model revision, dimension, dtype, device, prefixes and normalization. A vector made by one setup is never returned for another. Old cache entries are ignored, not misread.
  3. The default run on the public example still gives `Result: MATCH`, and the full suite stays green with MiniLM defaults unchanged.
  4. The manifest and every ranked result carry an encoder fingerprint and the label "candidate, not verified". A non-CPU run is compared by ranking overlap, not by bytes.
  5. A recorded spike shows whether `Nemotron-3-Embed-1B-BF16` loads and embeds on the owner's RTX 3060 (dimension, load time, peak memory, prefixes, whether remote code is needed), with every number from a run log.
  6. A measured comparison of MiniLM, `mdbr-leaf-ir` and the Nemotron profile on the 36-record public example gives top-200 pair overlap and texts per second. The owner decides any change of default from it.
  7. Close-out: the READMEs are refreshed and checked against the code and a run (owner rule 2026-11-07: refresh the READMEs after each version).

**Plans:** 8 of 9 complete (05-08 awaits the owner spike)

Plans:

- [x] 05-01: EncoderSpec, Encoder protocol, make_encoder, `gpu-encoder` extra (wave 1)
- [x] 05-02: Cache key with full encoder identity, schema 2, one cache file per profile (wave 1)
- [x] 05-03: Pair engine runner and doctor route through the factory (wave 2)
- [x] 05-04: `check-example` compares `gpu-approx` runs by ranking overlap (wave 2)
- [x] 05-05: Wording engine, `--encoder-profile`, manifest encoder block (wave 3)
- [x] 05-06: Host result key, profiles page, plugin hand-offs (wave 4)
- [x] 05-07: CPU comparison harness on the 36-record example (wave 4)
- [ ] 05-08: Self-contained GPU spike script and results template; ends at an owner-run checkpoint (wave 4) (built and tested; waits for the owner-run spike on the RTX 3060)
- [x] 05-09: README refresh close-out (wave 5)

**Scope notes**: In-process on the user's own computer only. No sockets, no loopback HTTP client, no NIM and no tunnel in this phase; local NIM stays a later option the owner wants to keep. No ontology work (OpenAlex Topics is parked as an optional later layer). Never mix vectors from two encoders in one store. The partner room store holds 2,130 vectors of 384 dimensions made by `mdbr-leaf-ir`; a 2048-dimension profile needs its own table. Keep stable for the MindrianOS plugin: the `eureka-mcp` script, the tool names, the `eureka.doctor.v1` shape, and a `uv.lock` in sync (the plugin starts with `--locked`). A new device or backend setting needs a plugin allowlist entry, which is a hand-off to the plugin session.
