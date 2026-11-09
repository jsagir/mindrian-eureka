---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 5 verified human_needed; quick task 261108-37h closed warnings W1 to W4; 05-08 open at the owner-run GPU spike
last_updated: "2026-11-08T09:32:20.640Z"
last_activity: 2026-11-09 -- Phase 02.3.1 wave 4 closed (gap plan 11 done; full suite green); plan 08 starting
progress:
  total_phases: 10
  completed_phases: 8
  total_plans: 71
  completed_plans: 63
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-23)

**Core value:** A user who is not the author can install Eureka, run it on their own collection with one command, and get the same ranked candidates every time, with hashes and settings that prove it. Output stays labeled "candidate, not verified".
**Current focus:** Phase 02.3.1 — Hub look matches the live JHTV site

## Current Position

Phase: 02.3.1 (Hub look matches the live JHTV site) — EXECUTING
Plan: 10 of 11 (9 done: 01 to 07, 10, 11; next 08 pages and router, then 09 owner brand stop)
Status: Executing Phase 02.3.1
Last activity: 2026-11-08 -- Phase 02.3.1 execution started

Progress: Phase 5 plans 8/9 (05-08 awaits the owner spike). Phase 5 is not marked complete.

## Performance Metrics

**Velocity:**

- Total plans completed: 30
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 02.1 P01 | 22min | 3 tasks | 11 files |
| Phase 02.1 P02 | 35min | 3 tasks | 7 files |
| Phase 02.1 P03 | 15min | 2 tasks | 8 files |
| Phase 02.1 P04 | 37min | 3 tasks | 8 files |
| Phase 02.1 P05 | about 13min | 2 tasks | 5 files |
| Phase 02.1 P06 | recorded in summary | 3 tasks | 27 files |
| Phase 02.1 P07 | recorded in summary | 2 tasks | 43 files |
| Phase 02.1 P08 | recorded in summary | 3 tasks | 5 files |
| Phase 02.1 P09 | recorded in summary | 3 tasks | 11 files |
| Phase 02.1 P10 | recorded in summary | 3 tasks | 8 files |
| Phase 02.1 P11 | recorded in summary | 2 tasks | 8 files |
| Phase 02.1 P12 | recorded in summary | 2 tasks | 4 files |
| Phase 02.1 P13 | recorded in summary | 2 tasks | 6 files |
| Phase 02.1 P14 | recorded in summary | 3 tasks | 12 files |
| Phase 02.1 P15 | recorded in summary | 2 tasks | 5 files |
| Phase 02.1 P18 | recorded in summary | 3 tasks | 9 files |
| Phase 02.1 P16 | recorded in summary | 2 tasks | 7 files |
| Phase 02.1 P19 | 1265 passed; 27 skipped; 45 subtests; 454.33 s |
| Phase 03 P01 | 15min | 2 tasks | 7 files |
| Phase 03 P02 | 25min | 3 tasks | 8 files |
| Phase 03 P06 | 35 min | 3 tasks | 9 files |
| Phase 03 P03 | 20min | 3 tasks | 4 files |
| Phase 03 P04 | 35min | 3 tasks | 5 files |
| Phase 03 P05 | 40 min | 3 tasks | 13 files |
| Phase 03 P07 | 45min | 3 tasks | 7 files |
| Phase 04 P01 | 40min | 2 tasks | 9 files |
| Phase 04 P02 | 10min | 3 tasks | 11 files |
| Phase 04 P03 | 25min | 3 tasks | 4 files |
| Phase 04 P04 | 20min | 2 tasks | 3 files |
| Phase 05 P01 | 55min | 3 tasks | 9 files |
| Phase 05 P02 | 25min | 2 tasks | 3 files |
| Phase 05 P03 | 40min | 3 tasks | 6 files |
| Phase 5 P04 | 35min | 2 tasks | 5 files |
| Phase 5 P05 | 75min | 3 tasks | 8 files |
| Phase 05 P06 | 40min | 3 tasks | 8 files |
| Phase 05 P08 | about 40min (PARTIAL, checkpoint pending) | 2 tasks | 4 files |
| Phase 05 P07 | 45min | 2 tasks | 5 files |
| Phase 05 P09 | 35min | 1 tasks | 4 files |
| Phase 02.3.1 P02 | 10min | 2 tasks | 5 files |
| Phase 02.3.1 P01 | about 20min | 3 tasks | 17 files |
| Phase 02.3.1 P04 | about 25min | 4 tasks | 18 files |
| Phase 02.3.1 P03 | about 34 min | 3 tasks | 21 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Suggested order kept (REL/ENG, then RUN/DOC, then HOST, then EXM). No dependency forced a change.
- [Roadmap]: REL-01 go / no-go gates public shipping in Phase 4 only. Phases 2 and 3 proceed either way.
- [Roadmap]: Domain research skipped on purpose at init. Domain is internal and documented in repo docs.
- [Phase 02.1-01]: D-14 owner ruling 2026-10-24: keep, label Potential eureka. D-17 password gate kept as drafted.
- [Phase 02.1-03]: Hub JS data file escapes characters inside JSON strings only (and also < and >); the word eureka is allowed only as the product name, Potential eureka, and the command eureka hub; the reader refuses unknown reading sentences and files whose hash differs from the manifest.
- [Phase 02.1-04]: CSP decision = default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none' (Firefox does not enforce a meta CSP on local file loads, so the static scan stays a required control). cryptography becomes the optional extra hub-gate. 3d-force-graph@1.79.1 passes the 14 day rule (MIT, 262 days old). Browser tests skip without tools; EUREKA_REQUIRE_BROWSER=1 makes them fail.
- [Phase 03]: 03-05: a refused start returns status refused with a reason code; a failed job start raises and releases the plan receipt unless it was a retry — Refusals are data for the host; a failed start must not burn the approval
- [Phase 04-02]: Example reference run uses all-MiniLM-L6-v2 (JHTV replay used mdbr-leaf-ir); recorded in example.model_note. Example status: Internal only, per docs/rs-release-gate.md.
- [Phase 04]: 04-03: the replay block of the reproduction guide holds a fixed pending text until plan 04-04 derives it from docs/jhtv-replay-record.md — One record file is the only source of the replay statement
- [Phase 04]: 04-04: the guide replay block holds the statement derived from docs/jhtv-replay-record.md (provenance gap); example hashes did not drift; release status stays internal only
- [Phase 05]: 05-01: factory not wired into runner/engines yet; gpu-nemotron revision unpinned until spike 05-08
- [Phase 05]: 05-04: GPU_APPROX_MIN_OVERLAP stays None; a gpu-approx run is never a MATCH until the spike (05-08) sets it

### Pending Todos

None yet.

### Carry-over items

- Owner sign-off on the release decision (draft no-go) in `docs/rs-release-gate.md`. Only the owner sets `decided_on`.
- `top_k` cap 100 to 200 and artifact cap 2500 to 3000: DONE in plan 02-01 (`limits.py`). The MCP schemas still cap at 2,500 artifacts and 100 pairs (Phase 3 item).
- Engine version must be recorded in the run manifest (the tie-break change in plan 01-04 changes the top-7 term order).
- Open item O1: older comments in `rs-differential-scorer.cjs` still cite the original author. Editing the file changes its sha256 in the ledger. Owner decides later.

### Quick Tasks Completed

| ID | Task | Status |
|----|------|--------|
| 261023-py1 | File the JHTV market-signal record | complete |
| 261023-q2c | Cleanup (names, paths, engine names) and Phase 1 close-out | complete |
| 261024-v2h | [Synthetic Potential eureka coverage](quick/261024-v2h-add-deterministic-synthetic-potential-eu/261024-v2h-SUMMARY.md), implementation 0398f90 | complete |
| 261029-184 | [Fix BM25 vocab cap so rare identifiers are kept](quick/261029-184-fix-bm25-vocab-cap-so-rare-identifiers-a/261029-184-SUMMARY.md), implementation 5165aba | complete |
| 261029-bfm | [Equal-spread lexical fusion so LSA and BM25 each hold half the vote](quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md), implementation b405fe7 | complete |
| 261107-vk6 | [Fix partner bundle online wheel download for the three targets](quick/261107-vk6-fix-partner-bundle-online-wheel-download/261107-vk6-SUMMARY.md), implementation 5357443 4f79e3f 05f8bbd | complete |
| 261107-w6v | [Silence the HSI start warning, add the macOS 14 note, declare packaging](quick/261107-w6v-silence-the-hsi-start-warning-add-the-ma/261107-w6v-SUMMARY.md), implementation 2065d46 f4acbf9 | complete |
| 261107-wif | [Move packaging to an optional bundle extra](quick/261107-wif-move-packaging-to-an-optional-bundle-ext/261107-wif-SUMMARY.md), implementation 727dc23 2b86358 | complete |
| 261107-wuy | [Windows launcher: pass the uv sync arguments as an array](quick/261107-wuy-windows-launcher-pass-the-uv-sync-argume/261107-wuy-SUMMARY.md), implementation 4be74df | complete |
| 261108-0ur | [Verify the MCP reach table and tests on the locked mcp 2.3.0](quick/261108-0ur-verify-the-mcp-reach-table-and-tests-on-/261108-0ur-SUMMARY.md), implementation 67617cb 7840888 | complete |
| 261108-37h | [Close the Phase 5 verifier warnings W1 to W4 and the bookkeeping](quick/261108-37h-close-the-phase-5-verifier-warnings-and-/261108-37h-SUMMARY.md), implementation 89b55b5 (RED) 59540a2 (fix) | complete |

### Blockers/Concerns

- [Phase 1] Unusual-pairs engine original `similarity_code` package is not in the repo. REL-01 may stay open if the source cannot be traced.
- [Phase 1] The JHTV wording-and-meaning pairs engine command may not be recoverable. ENG-03 allows a rebuild with recorded settings.
- [Phase 3] HOST-01 needs edits in the MindrianOS plugin repo. That repo is GSD-only and has its own commit rules.
- [Phase 3] The graph-derive replay input and script were not found. HOST-02 may end as a provenance-gap mark.
- [All] Peer uncommitted edits exist under `story/`. Use `--only` or explicit file lists for every commit. Never stage or revert them.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-11-08T09:32:20.631Z
Stopped at: Phase 5 verified human_needed; quick task 261108-37h closed warnings W1 to W4; 05-08 open at the owner-run GPU spike
Resume file: None

### Roadmap Evolution

- Phase 5 added 2026-11-07: Encoder seam, safe cache key and local GPU spike (source: fan-out research on local embedding, NVIDIA open models and plugin fit; owner chose in-process on the user's own computer now, local NIM later)
