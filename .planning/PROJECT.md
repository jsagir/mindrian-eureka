# MindrianOS Eureka

## What This Is

MindrianOS Eureka is a local Python engine (CLI + stdio MCP server) that finds candidate opportunity pairs in a collection of documents. It ranks pairs where meaning-similarity and vocabulary-structure similarity disagree (the unusual-pairs engine, the wording-and-meaning pairs engine, graph services). It returns leads for human review. It never claims novelty, evidence, or value.

Repo: `mindrian-eureka`. Runtime: Python 3.11+ with `uv`. Used by MindrianOS (`/mos:eureka`) and by direct CLI.

## Core Value

A user who is not the author can install Eureka, run it on their own collection with one command, and get the same ranked candidates every time, with hashes and settings that prove it. Output stays labeled "candidate, not verified".

## Why Now

The JHTV Fast Forward partner room ran the unusual-pairs engine (formerly called RS), the wording-and-meaning pairs engine (formerly called HSI), five graph services and a graph-derive replay on a 2,117-technology catalog (2026-10-18 to 2026-10-21). Review on 2026-10-23 found the run is only partly reproducible:

- Unusual-pairs engine: reproducible. Settings in the result file match `rs-engine.py --mode internal --topk 200 --threshold 0.0 --no-thesis` with `RS_EMBEDDING_MODEL=minilm`.
- Wording-and-meaning pairs engine: settings recorded (`top_k 200`, `min_percentile 0.0`) but `compute-hsi.py --help` shows no top-k flag. The exact command is not on record.
- Graph services (Oct 19): request JSONs saved; exact `eureka-workflow` syntax unconfirmed.
- Graph-derive replay (Oct 21, 2,130 claims, 2,267,385 pairs): no script and no `derive_results.json` found. OPP-027 to OPP-031 cite it.
- Two unusual-pairs implementations exist (plugin `rs-engine.py`, repo `eureka-pair-scout`). No test shows they agree.

## Requirements

### Validated

- ✓ CLI and stdio MCP server install and run via `uv sync`, `uv run eureka capabilities` — existing
- ✓ Capability catalog (21 summarized entries on 2026-10-23, mostly experimental) with JTBD, status, limitations — existing
- ✓ Unusual-pairs engine in repo (`eureka-pair-scout`), hybrid scoring, local-only models, embedding cache — existing
- ✓ Graph services (`eureka-graph`, `eureka-workflow`) over caller-supplied snapshots — existing
- ✓ Host handoff block telling MindrianOS the next review step — existing
- ✓ Dockerfile, tests, SECURITY.md, CONTRIBUTING.md — existing

### Active

See `.planning/REQUIREMENTS.md`.

### Out of Scope

- Claiming novelty, demand, or commercial value from any score — scores are screening signals only
- Fetching web research inside the engine — MindrianOS owns approved research and grants
- Writing to a MindrianOS room graph — host owns graph and portfolio writes
- Model downloads inside the MCP server — local models only, by design

## Context

- Owner rule: all dev work runs through GSD. Executors never push; main session reviews every commit ahead of origin before any push.
- Working tree already holds peer uncommitted edits under `story/`. GSD commits use `--only` / explicit file lists. Never revert or stage them.
- Unusual-pairs source: derived from a PowerPoint method analysis. The original `similarity_code` package is not in the repo. Bit-for-bit fidelity, author attribution and licensing are unresolved. The repo docs say this must be settled before production distribution.
- Theo (MindrianOS teaching graph) guides method choice. Room content never goes to Theo or Brain calls.
- Style: plain English, hyphens not em-dashes, Feynman-simple explanations.

## Constraints

- **Offline by default**: engine makes no network calls; models must already be on disk.
- **Determinism**: ranking is code, no LLM; seeds and versions are recorded in result provenance.
- **Honest labels**: every output keeps "candidate, not verified" wording.
- **Privacy**: embeddings are derived sensitive data; cache and job data stay local with owner-only permissions.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Make the first milestone "operational by other users" | JHTV review showed reproducibility gaps and no one-command path | — Pending |
| Licensing/attribution check goes first | Only item that can block public release | — Pending |
| One unusual-pairs implementation, or a proven match | Two code paths with no agreement test is a trust hole | — Pending |
| Skip domain research at init | Domain is internal and already documented in repo docs | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-23 after initialization*
