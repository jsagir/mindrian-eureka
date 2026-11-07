---
phase: 03-host-integration-and-replay-rebuild
plan: 01
subsystem: mcp-limits
tags: [mcp, limits, schemas, parity, HOST-01]
requires: []
provides:
  - MCP pair tools and published input schemas that follow limits.py (3,000 artifacts, 200 pairs)
  - A parity test that fails when limits.py and the contract drift apart
affects: [03-05]
tech-stack:
  added: []
  patterns: ["caps imported from limits.py, never written as literals in a model"]
key-files:
  created:
    - tests/test_mcp_limits_parity.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/mcp_server.py
    - src/mindrian_eureka/opportunity_discovery.py
    - src/mindrian_eureka/data/schemas/cross-domain-pairs-input.v1.json
    - src/mindrian_eureka/data/schemas/discovery-signals-input.v1.json
    - src/mindrian_eureka/data/schemas/hsi-pairs-input.v1.json
    - src/mindrian_eureka/data/capability-catalog.v1.json
key-decisions:
  - "D-08: only the three pair-engine routes lift to 3,000 and 200. graph.prepare_artifact_bundle stays at 2,500 and a test pins it."
requirements-completed: [HOST-01]
duration: about 15 min
completed: 2026-11-07
---

# Phase 3 Plan 01: MCP limits parity Summary

The MCP models, three input schemas, one engine check and one catalog sentence for the pair routes now read 3,000 artifacts and 200 pairs, the same as `limits.py`. One parity test pins this.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Parity tests (RED) | 208c6fd |
| 2 | Lift the stale caps (GREEN) | cdd8d46 |

## RED output

`tests/test_mcp_limits_parity.py` before the change: 7 failed, 1 passed. The passing test is `test_other_families_keep_their_caps`, as planned. (`test_mcp_models_*` are parametrized over 2 models, so the file holds 8 test items.)

## GREEN counts

- Parity file: 8 passed.
- Guard set (parity, graph_relations, hsi_latest_integration, hsi_rs_whitespace, rs_engine_parity, capability_cli, wrong_number_fixes, eureka_opportunity_harvest, decision_cli_mcp_parity): 72 passed, 25 skipped, 9 subtests passed, 0 failed.
- `tests/test_graph_relations_hardening.py` (it mentions 2500): 26 passed, 36 subtests passed.
- No guard test pinned an old number. No test was edited.

## Old and new numbers per file

| File | Old | New |
|------|-----|-----|
| `opportunity_pairs/mcp_server.py` (2 models) | artifacts max 2500, top_k le 100 | `MAX_ARTIFACTS`, `MAX_TOP_K` (import added) |
| `opportunity_discovery.py` | `> 2500`, message `at most 2500 artifacts` | `> MAX_ARTIFACTS`, f-string message |
| `cross-domain-pairs-input.v1.json` | artifacts maxItems 2500, top_k maximum 100 | 3000, 200 |
| `discovery-signals-input.v1.json` | artifact_count 2500, max_artifacts 2500, artifacts maxItems 2500, top_k maximum 100 | 3000, 3000, 3000, 200 |
| `hsi-pairs-input.v1.json` | artifacts maxItems 2500, top_k maximum 100 | 3000, 200 |
| `capability-catalog.v1.json` | `2..2500 source-linked local artifacts` | `2..3000 ...` (1 insertion, 1 deletion) |

The catalog count of the string `2500` went from 12 to 11. The other families keep their caps.

## Lint counts

- `ruff check src tests`: 1465 errors before and after. The new test file is clean.
- `mypy src`: 88 errors in 17 files before and after.

## Deviations from Plan

Tool path only: the plan used `uv run --offline`; the orchestrator prompt set `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest`, and the `ruff` and `mypy` binaries ran directly. The counts match the planned baselines. No other deviation.

Note on an acceptance check: `grep -c "le=100" mcp_server.py` prints 1. The match is `le=1000` of an unrelated `max_iterations` field (line 141). No `le=100` cap of a pair model remains.

## Plugin checkout (information only)

`git status --short | wc -l` of `/home/jsagi/dev/MindrianOS-Plugin-release`: 1 before and after. `/home/jsagi/MindrianOS-Plugin` is not a git repository (fatal error, so no count). No plugin file was edited.

## Known Stubs

None.

## Threat Flags

None. T-01 to T-03 mitigations are in place: the model, schema and engine cap share one source, the parity test compares with the imported constants, and the catalog diff is one line.

## Self-Check: PASSED

- tests/test_mcp_limits_parity.py: FOUND
- Commits 208c6fd and cdd8d46: FOUND
- Nothing from `story/` staged; nothing pushed.
