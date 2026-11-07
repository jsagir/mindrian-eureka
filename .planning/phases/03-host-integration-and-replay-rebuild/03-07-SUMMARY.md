---
phase: 03-host-integration-and-replay-rebuild
plan: 07
subsystem: docs
tags: [hand-off-contract, plugin-phase, docs, HOST-01, HOST-02]
requires:
  - phase: 03-05
    provides: MCP tools scout_plan_pair_screen and scout_start_pair_screen, catalog entry
  - phase: 03-06
    provides: docs/jhtv-replay-record.md, gap list, emit script
provides:
  - docs/mos-eureka-engine-run-contract.md (14 headings, schema-key and refusal-code parity tested)
  - tests/test_host_handoff_docs.py (16 tests)
  - Linked docs: host integration section, engine doc limit, usage and architecture bullets, README sentences
affects: [plugin-phase, 04-03, 04-04]
tech-stack:
  added: []
  patterns: ["contract doc pinned to code by parity tests (schema keys, refusal codes, tool names)"]
key-files:
  created:
    - docs/mos-eureka-engine-run-contract.md
    - tests/test_host_handoff_docs.py
  modified:
    - docs/integrations/mindrianos.md
    - docs/engines/opportunity-pairs.md
    - docs/using-capabilities.md
    - docs/architecture.md
    - README.md
key-decisions:
  - "The third plugin table entry (F15, routeGate) is documented as the capability id in PAIR_IDS of eureka-engine-requirements.cjs, which routeGate reads. routeGate itself is a function."
requirements-completed: []
duration: about 45 min
completed: 2026-11-07
---

# Phase 3 Plan 07: Hand-off contract and phase checks Summary

The plugin phase can now plan the `/mos:eureka` wiring and the provenance gap marks from `docs/mos-eureka-engine-run-contract.md` alone. The doc is tied to the code by tests: every schema key, every refusal code and every `scout_` name.

HOST-01 and HOST-02 are not marked complete in REQUIREMENTS.md (instruction of the orchestrator). The plugin wiring and the room mark are not done by this phase.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Hand-off document tests (RED) | 7132c7c |
| 2 | Contract document (GREEN, part 1) | 25c4d25 |
| 3 | Linked docs and limits (GREEN, part 2) | 9dfc252 |

## RED output

`tests/test_host_handoff_docs.py` before any doc change: 16 failed in 1.92 s. ruff on the file: All checks passed. `def test_` count: 16.

## GREEN counts

- After Task 2, `-k contract`: 11 passed, 1 failed (`test_readme_points_to_the_contract`, expected until Task 3), 4 deselected.
- After Task 3, guard set (`test_host_handoff_docs`, `test_room_seed_docs`, `test_readme_commands`, `test_partner_bundle`, `test_release_gate_record`, `test_hub_decisions`, `test_graph_derive_provenance`, `test_host_run_mcp`): 97 passed, 0 failed.

## Phase-level checks

| Check | Result |
|-------|--------|
| (a) Full suite | Not run by this executor. The orchestrator runs it (instruction of the run). |
| (b) `ruff check src tests` | 1465 errors (baseline 1465) |
| (b) `mypy src` | 88 errors in 17 files (baseline 88) |
| (c) `grep -rn "candidate, not verified" src/ \| wc -l` | 10 |
| (d) `wording_params_hash(200)` | `bea4c100c2013300` |
| (e) BASE (parent of first `(03-01)` commit) | `a88bff9d643064ac72e9266a2b4d58edb093a575` |
| (e) `git diff BASE..HEAD --stat -- tests/fixtures \| wc -l` | 0 |
| (e) `story/` files in the diff | 0 |
| (e) `cli.py` in the diff | 0 |
| (e) `jobs.py` numstat | `7 0` (7 added, 0 deleted) |
| (f) network words in `host_run` and `provenance` | 0 |
| (g) plugin `git status --short \| wc -l` | 0 before and 0 after (information only) |
| (h) Phase 4 front matter of `docs/jhtv-replay-record.md` | `outcome: provenance_gap`, `room_mark: pending_approval`, `label`, `checked_on: 2026-11-07` |
| (i) `bash scripts/emit-provenance-gap-list --check` | `exit=0` |
| (j) uncommitted files outside `story/` | only `docs/research/` (untracked, pre-existing, not staged) |
| Dash check on added doc lines | 0 en or em dashes |

## Requirement coverage

| Requirement | Plans | State |
|-------------|-------|-------|
| HOST-01 | 03-01 to 03-05, 03-07 | Eureka side done (success criteria 1 and 2): tools, gate, schemas, catalog entry, limits, contract. The plugin wiring is handed off in the contract. Not done by this phase. |
| HOST-02 | 03-06, 03-07 | Second branch of success criterion 3: the provenance gap record and the list are done. `room_mark` is `pending_approval`. The room mark is a host-owned write and is not done by this phase. |

## Plugin commit read

Repository `MindrianOS-Plugin` (checkout of the release line), branch main, HEAD `cd6879a98`. Phase 387 base commits `173a5b1e9` and `25838bb02` (both ancestors of HEAD, PROVEN). Facts read: `commands/eureka.md`, `lib/mcp/tools/eureka-capability-run.cjs`, `lib/mcp/tools/eureka-capability-jobs.cjs`, `lib/mcp/tools/eureka-graph-opportunity-scout.cjs`, `lib/mcp/eureka-tool-contract.cjs`, `lib/core/eureka/eureka-engine-requirements.cjs`, `lib/mcp/gate-ledger.cjs`, `lib/core/graph-derive-classifier.cjs`. Nothing was written there.

## Open questions copied from the contract

(a) Subcommand name, and does it replace the default `run`. (b) Card shape for the plan, and the gate id as `approval_ref`. (c) Lift the plugin caps to 3,000 and 200, or pass the Eureka limits through. (d) Blocking wait or job tools for the poll. (e) Where the manifest and file hashes live in the room run record. (f) Show `ranked-pairs.md` or write the answer from `outputs`. (g) Who writes the provenance gap marks, and in which phase. (h) Whether the plan call needs its own entry in the plugin connector registry.

## Human checks pending (not marked done)

1. **Contract sections 4, 9, 10 and 13.** The owner reads the approval step, the wiring steps, the provenance gap marks and the open questions, and confirms they match what the plugin session should build. PENDING.
2. **The five mark texts.** The owner runs `bash scripts/emit-provenance-gap-list --format text`, reads the five texts for OPP-027 to OPP-031, and confirms they say what the owner will accept in the room. PENDING.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan fact] Limits sentence was already corrected**
- **Found during:** Task 3
- **Issue:** The plan expects the old sentence `Input is bounded at 2,500 artifacts and 20 MiB ...` in `docs/integrations/mindrianos.md`. Plan 03-05 had already changed it to `3,000 artifacts and 20 MiB`, without the pair count and without the tool list.
- **Fix:** Replaced the 3,000 sentence by the planned wording: the four pair tools accept 3,000 artifacts, 200 pairs and 20 MiB; other families keep the catalog limits; the graph projection stays at 2,500.
- **Commit:** 9dfc252

**2. [Rule 1 - Plan fact differs from code] The routeGate table**
- **Found during:** Task 2
- **Issue:** Fact F15 says the routes need an entry in "the routeGate table of `lib/mcp/eureka-tool-contract.cjs`". `routeGate` there is a function. It reads the needs of a call from `needsForCall` in `lib/core/eureka/eureka-engine-requirements.cjs`, where `PAIR_IDS` lists capability ids; an unlisted id gets the default cell with unknown needs.
- **Fix:** The contract keeps the name `routeGate` and says the capability id goes into the needs table that `routeGate` reads. The plugin facts table records both files as PROVEN. The existing 03-05 section in `docs/integrations/mindrianos.md` keeps its shorter wording; it was not rewritten.
- **Commit:** 25c4d25

**3. [Rule 3 - Blocking] Tool bullets already present in the host doc**
- **Issue:** Plan 03-05 had already added the two tool bullets and a plugin side subsection to `docs/integrations/mindrianos.md`.
- **Fix:** Did not add them twice. Added only the limits sentence change and the new section.
- **Commit:** 9dfc252

**4. [Process] Full suite not run**
- The orchestrator runs the full suite (instruction of this run). Only the guard set above was run.

### Commit file counts

RED 1 file, contract 1 file, docs 5 files, as planned.

## Known Stubs

None.

## Threat Flags

None. T-03-41 to T-03-47 mitigations are in place: PROVEN and ASSUMED labels with a commit hash (test), parity tests for schema keys, refusal codes and tool names, approval limits and the silent-retry rule pinned by phrase tests, the house-style test for names, institution words and machine paths, and the plugin status count of 0 before and after.

## Self-Check

- Files `docs/mos-eureka-engine-run-contract.md`, `tests/test_host_handoff_docs.py`: FOUND
- Commits 7132c7c, 25c4d25, 9dfc252: FOUND
- Nothing from `story/` or `docs/research/` staged; `cli.py` untouched; nothing pushed; plugin checkout unchanged.

## Self-Check: PASSED
