---
phase: 03-host-integration-and-replay-rebuild
verified: 2026-11-07T00:00:00Z
status: human_needed
score: 3/3 roadmap success criteria verified on the Eureka side (1 branch of criterion 3, by design)
overrides_applied: 0
re_verification: false
gaps: []
human_verification:
  - test: "Read contract sections 4 (The approval step), 9 (How MindrianOS should wire the command), 10 (The provenance gap marks) and 13 (Open questions for the plugin phase) of docs/mos-eureka-engine-run-contract.md"
    expected: "They match what the plugin session should build"
    why_human: "Owner decision on a hand-off to another repo and another GSD rule"
  - test: "Run bash scripts/emit-provenance-gap-list --format text and read the 5 mark texts (OPP-027 to OPP-031)"
    expected: "The texts say what the owner accepts in the room"
    why_human: "Wording of a room mark is an owner decision"
  - test: "Approve and perform the room-side provenance gap mark (host-owned write)"
    expected: "The 5 candidates carry the mark in the room; then a Eureka quick task sets room_mark: done"
    why_human: "Room write needs approval; Eureka must not write a room"
  - test: "Release sign-off (Phase 1 open item, release decision is still draft no-go)"
    expected: "Owner signs or changes the go / no-go"
    why_human: "Owner decision"
---

# Phase 3: Host Integration and Replay Rebuild - Verification Report

**Phase goal:** A MindrianOS user can start the one-command run from `/mos:eureka`, and the five JHTV candidates that cite the graph-derive replay have either a repeatable script or an honest provenance-gap mark.
**Verified:** 2026-11-07
**Status:** human_needed
**Re-verification:** No (initial)

Scope note: the roadmap criteria were reworded on 2026-11-07. Criterion 1 covers the Eureka MCP tools only. The plugin wiring that makes `/mos:eureka` call them is a separate plugin phase and is out of scope here. Label of every result: candidate, not verified.

## Observable truths

| # | Truth | Status | Evidence (PROVEN = seen in code or a run by this verifier) |
|---|-------|--------|---------|
| 1 | The Eureka MCP server exposes a plan tool and a start tool, with an approval step and a result envelope that carries the host hand-off block | VERIFIED | `mcp_server.py` defines `scout_plan_pair_screen` and `scout_start_pair_screen` (diff 53 insertions, 0 deletions). `host_run/api.py` wires them to `build_plan`, `check_start`, `manager.start`. `host_run/envelope.py` builds schema `eureka.pair-screen.v1` with `host_handoff`; `jobs.py` branch calls `run_pair_screen_job` (7 added, 0 deleted). Catalog entry `opportunity.run_pair_screen` present (68 entries, 60 routed). Targeted tests pass. |
| 2a | The run does not start without the approval step | VERIFIED | Probe run by this verifier on `start_pair_screen` with a stub manager: no approval -> `approval_missing`; wrong digest -> `plan_mismatch`; correct digest but no plan receipt -> `plan_unknown`; first start with receipt -> `queued`, `room_write: not_performed`; second start -> `plan_consumed`. Refusals start no job (stub manager never called; tests check the jobs table has 0 rows). |
| 2b | Refusals for external corpus and more than 3,000 artifacts | VERIFIED | Probe: 3,001 artifacts -> `too_many_artifacts`; one artifact with `corpus: external` -> `external_corpus_refused`; 3,000 accepted. The MCP model also caps at `MAX_ARTIFACTS` (3,000) via `limits.py`. Refusal is never a truncation. |
| 2c | Eureka writes nothing to the room graph | VERIFIED | Grep of `host_run` and `provenance` for file operations: every write or mkdir is below the Eureka data directory (`plan-receipts.sqlite3`, `host-runs/<job id>/`), removed in a `finally` block. No room, registry or plugin path appears in the code. Envelope fixes `room_write` and `portfolio_write` to `not_performed` (schema const). `verified_by_engine` is const false. `MindrianOS-Plugin-release`: `git status --short` = 0 lines. |
| 3 | Replay script with equal hashes and counts, OR OPP-027 to OPP-031 marked provenance gap | VERIFIED (branch 2, Eureka side) | `docs/jhtv-replay-record.md` front matter has exactly 4 keys: `outcome: provenance_gap`, `room_mark: pending_approval`, `label`, `checked_on` (parsed by this verifier). `scripts/emit-provenance-gap-list --check` exit 0; text output lists OPP-027 to OPP-031 with a mark text each. Arithmetic: 2,130 x 2,129 / 2 = 2,267,385 (record C2). The replay data is not in the repo (search in record C1/C4), so no script is possible. The room-side mark is not done (host-owned write). |
| 4 | `cli.py` unchanged | VERIFIED | `git diff a88bff9..HEAD --stat -- src/mindrian_eureka/cli.py` is empty. |
| 5 | Limits parity (D-08) | VERIFIED | `tests/test_mcp_limits_parity.py` passes (8 items), including the guard that other families keep 2,500. |

**Score:** all truths VERIFIED for the reworded Eureka-side scope.

## Required artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/mindrian_eureka/host_run/{contracts,bundle,gate,plan,execute,envelope,api}.py` | VERIFIED | Substantive (1,915 lines with provenance package), wired from `mcp_server.py` and `jobs.py`. |
| `src/mindrian_eureka/data/schemas/pair-screen-{input,output}.v1.json` | VERIFIED | Published through `scout_capability_contract`. |
| `src/mindrian_eureka/provenance/gap_list.py`, `scripts/emit-provenance-gap-list` | VERIFIED | `--check` exit 0, output sha256 `23eb2c2c...3e11` equals the golden file. |
| `docs/jhtv-replay-record.md`, `evaluations/graph-derive-replay/{record,gap-list}.v1.json` | VERIFIED | Front matter contract met. |
| `docs/mos-eureka-engine-run-contract.md` | VERIFIED (content awaits owner read) | 14 headings (1 title + 13 numbered sections) pinned in order by `tests/test_host_handoff_docs.py`. Sections 4, 9, 10 and 13 are: The approval step, How MindrianOS should wire the command, The provenance gap marks, Open questions for the plugin phase. |

## Behavioral spot-checks and tests

| Check | Command | Result |
|-------|---------|--------|
| Targeted tests | `PYTHONPATH=src:tests pytest tests/test_host_run_*.py tests/test_graph_derive_provenance.py tests/test_host_handoff_docs.py tests/test_mcp_limits_parity.py -q` | 142 passed |
| Refusal probe | scratchpad script on `start_pair_screen`, `normalize_request` | all 6 refusal paths as expected (see truths 2a, 2b) |
| Emit script | `bash scripts/emit-provenance-gap-list --check` | exit 0 |
| Full suite | run by orchestrator | at the time of this check the output file had no `EXIT=` line (still running, about 19 percent). UNVERIFIED by this report. |

## Key links

| From | To | Status |
|------|----|--------|
| `scout_start_pair_screen` | `check_start` before `manager.start` | WIRED (claim happens first; a failed start releases the receipt) |
| `jobs.py` `_execute` | `run_pair_screen_job` -> `run_pipeline` (use_cache False) | WIRED |
| `run_pair_screen_job` | `build_result` envelope with sha256 per file | WIRED |
| Catalog entry | `scout_capability_contract` schemas | WIRED |

## Requirements coverage

| Requirement | Status | Reason |
|-------------|--------|--------|
| HOST-01 (`/mos:eureka` calls the Eureka MCP server for the run, room scope and approval respected) | Eureka side SATISFIED; requirement NOT complete as worded | The Eureka tools, gate and envelope exist and work. The wording of HOST-01 says `/mos:eureka` in MindrianOS calls the server. That wiring is in the plugin repo and is a separate plugin phase. Recommendation: do not mark HOST-01 complete. Mark it "Eureka side complete; plugin wiring pending" in REQUIREMENTS.md, or reword HOST-01 to the Eureka tool surface (as ROADMAP criterion 1 was reworded) and then mark it complete. This is an owner decision. |
| HOST-02 (replay rebuilt as script, or the five candidates marked "provenance gap" in the room) | Eureka side SATISFIED; requirement NOT complete | The record, list and script exist. The mark "in the room" is not written (`room_mark: pending_approval`). HOST-02 can be marked complete only after the host session writes the mark with approval and a Eureka quick task sets `room_mark: done`. Alternative: reword HOST-02 to "record and list" (owner decision). |

No orphaned requirement: REQUIREMENTS.md maps only HOST-01 and HOST-02 to Phase 3.

## Anti-patterns

Grep of `host_run` and `provenance` for TBD, FIXME, XXX: not run as a separate listing; the 142 passing tests include house-style tests. No stub found in the reading of `api.py`, `gate.py`, `execute.py`. No blocker.

## Boundaries

| Check | Result |
|-------|--------|
| `cli.py` | unchanged since BASE a88bff9 |
| Plugin checkout `MindrianOS-Plugin-release` | 0 changed files |
| Plugin checkout `MindrianOS-Plugin` | 1 untracked file `.planning/debug/379-1-1-10-large-room-drain-clock-breach.md`. It is not from this phase (no Phase 3 commit touches the plugin; summaries recorded 0). Information only, belongs to the plugin session. |
| Room, registry write by code | none found |
| Files changed BASE..HEAD outside `.planning` | all inside Eureka repo (src, tests, docs, evaluations, scripts, schemas) |
| Network words in `host_run`, `provenance` | 0 per the 03-07 check |

## Human items (list)

1. Owner reads contract sections 4, 9, 10 and 13 and confirms the plugin hand-off.
2. Owner reads the five provenance-gap mark texts (`bash scripts/emit-provenance-gap-list --format text`).
3. Room-side mark: host-owned write with approval; then a Eureka quick task sets `room_mark: done`.
4. Release sign-off (release decision still draft no-go; Phase 4 ships internal only until changed).
5. Decision on HOST-01 and HOST-02 completion wording (see Requirements coverage).

## Gaps summary

No gap against the reworded roadmap criteria. The two requirements are only complete on the Eureka side, by design. No deferred item is hidden as a failure: the plugin wiring and the room mark are named in the contract and in the roadmap scope notes.

---

_Verified: 2026-11-07_
_Verifier: Claude (gsd-verifier)_
