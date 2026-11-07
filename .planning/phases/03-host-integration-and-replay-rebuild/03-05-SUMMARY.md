---
phase: 03-host-integration-and-replay-rebuild
plan: 05
subsystem: host-run
tags: [host-run, mcp, catalog, approval-gate, HOST-01]
requires:
  - phase: 03-01
    provides: limits.py caps in the MCP models
  - phase: 03-03
    provides: check_start, PlanReceipts, build_plan
  - phase: 03-04
    provides: build_job_request, the job branch for opportunity.run_pair_screen
provides:
  - MCP tools scout_plan_pair_screen and scout_start_pair_screen
  - host_run.api (plan_pair_screen, start_pair_screen)
  - Catalog entry opportunity.run_pair_screen (68 entries, 60 routed)
  - Host workflow text that names the two tools
affects: [03-07]
tech-stack:
  added: []
  patterns: ["plain-Python facade between the MCP models and the gate", "manager read at call time so tests swap it"]
key-files:
  created:
    - src/mindrian_eureka/host_run/api.py
    - tests/test_host_run_mcp.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/mcp_server.py
    - src/mindrian_eureka/data/capability-catalog.v1.json
    - src/mindrian_eureka/data/mos-opportunity-discovery.v1.json
    - tests/test_capability_cli.py
    - tests/test_graph_relations.py
    - docs/capability-catalog.md
    - docs/engine-jobs.md
    - docs/algorithm-origins-and-rationale.md
    - docs/integrations/mindrianos.md
    - docs/architecture.md
    - README.md
key-decisions:
  - "A start refusal is a dictionary with status refused; a failed job start raises and releases the receipt (unless it was a retry)."
  - "The approval block is echoed with verified_by_engine false; the reference is audit metadata."
requirements-completed: []
duration: about 40 min
completed: 2026-11-07
---

# Phase 3 Plan 05: MCP tools, catalog entry and workflow text Summary

A connected host can now call `scout_plan_pair_screen`, show the plan, get an approval, call `scout_start_pair_screen`, poll the existing job tools and read the ranked output. A start without a matching, live, unused plan receipt returns `status: refused` and starts no job.

HOST-01 is not complete. This plan finishes the Eureka side of the tools. Plan 03-07 and the plugin phase finish the rest. Do not mark HOST-01 complete before the last plan of the phase.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | End-to-end tests and count pin (RED) | 958daa3 |
| 2 | Facade, two tools, catalog entry, workflow text (GREEN) | bae4445 |
| 3 | Docs counts, catalog row, plugin note | 97e5499 |

## RED output

`tests/test_host_run_mcp.py` and `tests/test_capability_cli.py` before any source: 13 failed, 3 passed. The 3 passing items include `test_legacy_tool_caps_unchanged_by_this_plan`, a guard that holds from the start. Failures were AttributeError for the missing tools and the count pin (`67 == 68`).

## GREEN counts

- After Task 2: `test_host_run_mcp.py` 13 passed. With the capability, limits parity, all `test_host_run_*`, `test_graph_relations`, `test_hsi_rs_whitespace` and `test_decision_cli_mcp_parity` files: 148 passed, 3 skipped, 9 subtests passed, 0 failed.
- Guard set of Task 3 (`test_room_seed_docs`, `test_readme_commands`, `test_capability_cli`, `test_host_run_mcp`, `test_graph_relations`, `test_release_gate_record`, `test_hsi_rs_whitespace`): 79 passed, 9 subtests passed.
- New set (`test_mcp_limits_parity` plus the 7 `test_host_run_*` files): 110 passed, 0 failed.

## Tool signatures

- `scout_plan_pair_screen(request: PairScreenInput) -> dict`: starts nothing; returns a ready plan with `plan_digest`, a blocked plan, or a refusal.
- `scout_start_pair_screen(request: PairScreenInput, idempotency_key: str | None = None) -> dict`: returns the started job dictionary plus `capability_id`, `label`, `room_write`, `approval` (`verified_by_engine` false) and `next`, or a refusal dictionary.
- `PairScreenInput`: closed; `objective`, `scope_id`, `snapshot_id`, `artifacts` (2 to `MAX_ARTIFACTS`), `top_k` (default and maximum `MAX_TOP_K`), optional `approval`.
- `ApprovalInput`: closed; `plan_digest` (64 hex), `approval_ref` (the contracts pattern, anchored).
- `mcp_server.py` diff: 53 insertions, 0 deletions.

## Catalog

Entry `opportunity.run_pair_screen`, status `experimental`, after `opportunity.synthesize_discovery_signals`. Counts: 68 entries (was 67), 60 routed (was 59), 8 blocked or planned (unchanged). `counts_by_status.experimental` is 55 (was 54). `scout_capability_contract` returns both schemas. Docs that state the numbers were updated: `engine-jobs.md`, `algorithm-origins-and-rationale.md`, `integrations/mindrianos.md`, `architecture.md`, `README.md`.

## Refusal codes seen in the tests

`approval_missing`, `plan_mismatch` (two cases), `plan_unknown` (two cases), `plan_expired`, `plan_consumed` (two cases), `local_model_unavailable` (as a blocked plan). The jobs table keeps 0 rows after the five start refusals, the expiry case and the blocked plan. A bad `approval_ref` is refused by the model (`ValidationError`).

## Lint counts

- `ruff check` on `host_run` and `tests/test_host_run_mcp.py`: All checks passed.
- `ruff check src tests`: 1465 errors (baseline 1465; one new long line was found and fixed).
- `mypy src`: 88 errors in 17 files (baseline 88).

## Plugin checkout (information only)

`git status --short | wc -l` of `/home/jsagi/dev/MindrianOS-Plugin-release`: 0 at the start and 0 at the end. No plugin file was read for edit or edited.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Guard tests pinned the old catalog**
- **Found during:** Task 2
- **Issue:** `tests/test_graph_relations.py` pins 59 runnable entries and holds two route tables (MCP tool and CLI script per capability). The new entry failed 3 tests. `tests/test_capability_cli.py` also pins `counts_by_status.experimental` at 54.
- **Fix:** 59 to 60; added `opportunity.run_pair_screen` to `direct_routes` (`scout_start_pair_screen`) and to `direct_cli` (`eureka`); `experimental` 54 to 55 (in the RED commit).
- **Files modified:** `tests/test_graph_relations.py`, `tests/test_capability_cli.py`
- **Commits:** 958daa3, bae4445

**2. [Rule 1 - Bug in own test] Blocked-plan test used a digest that cannot match**
- **Issue:** `test_blocked_plan_without_a_model` sent digest `a` x 64 and got `plan_mismatch`. The plan states `plan_unknown` for "any digest", but the gate checks the digest against the request first.
- **Fix:** The test sends the real digest of the request; the result is `plan_unknown`. Fixed in the GREEN commit, not amended into RED.
- **Commit:** bae4445

**3. [Rule 2 - Missing] Stale count statements outside the planned files**
- **Issue:** `docs/architecture.md` and `README.md` state 59 routed entries. The `67` grep did not find them.
- **Fix:** `architecture.md` says 60. `README.md` says 60 runnable entries and that live verification of 2026-10-20 covered the first 59. `integrations/mindrianos.md` keeps its verification claim honest the same way.
- **Commit:** 97e5499

**4. [Plan addendum] Plugin Phase 387 note**
- Added a short section to `docs/integrations/mindrianos.md`: plugin Phase 387 owns adoption, doctor and typed refusals (base commits 173a5b1e9 and 25838bb02); the two routes need entries in `ALLOWED_MCP_ROUTES`, `ASYNC_ROUTES` and `routeGate` of `lib/mcp/eureka-tool-contract.cjs`; the plugin adapter caps (`top_k` 100, `node_ids` 2,500) must lift to 200 and 3,000. Also added two tool bullets and corrected the stale "2,500 artifacts" bound of the RS bundle to 3,000 (plan 03-01 limit).

**5. [Tool path]** Used `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`, and `ruff` and `mypy` from `/home/jsagi/.local/bin`, as the orchestrator set.

### Commit file counts

The RED commit lists 2 files as planned. The GREEN commit lists 6 files (plan: 4) because of deviations 1 and 2. The docs commit lists 6 files (plan: 4) because of deviations 3 and 4.

## Known Stubs

None.

## Threat Flags

None. T-03-27 to T-03-34 mitigations are in place and tested: `check_start` runs before `manager.start`; the corpus rule refuses `external`; `verified_by_engine` is false; single use with a key rule (same key, other key, no key); release on a failed start; the home tree changes only below the data directory and a fake room tree keeps its hash; `routes.mcp.tool` names a real function and the contract returns both schemas.

## Self-Check: PASSED

- Files `host_run/api.py`, `tests/test_host_run_mcp.py`: FOUND
- Commits 958daa3, bae4445, 97e5499: FOUND
- Nothing from `story/` or `docs/research/` staged; `cli.py` untouched; nothing pushed.
