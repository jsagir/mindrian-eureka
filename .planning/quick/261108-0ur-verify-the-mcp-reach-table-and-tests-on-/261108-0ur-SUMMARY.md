---
phase: quick
plan: 261108-0ur
subsystem: host-run-mcp
tags: [mcp, tests, contract, lock]
requires: [HOST-01]
provides: [reach tests that pass on mcp 1.25.0 and mcp 2.3.0, contract table verified on the locked mcp]
affects: [tests/test_host_run_mcp_reach.py, docs/mos-eureka-engine-run-contract.md, tests/test_host_handoff_docs.py]
key-files:
  modified:
    - tests/test_host_run_mcp_reach.py
    - docs/mos-eureka-engine-run-contract.md
    - tests/test_host_handoff_docs.py
decisions:
  - "No table cell differs between mcp 1.25.0 and mcp 2.3.0. Only the result shape differs. The contract table keeps its cells and gains a sentence naming the verified versions."
metrics:
  completed: 2026-11-08
---

# Quick 261108-0ur: MCP reach table verified on the locked mcp

The reach tests now read both the mcp 1.x list result and the mcp 2.x `CallToolResult`. All 18 original cells give the same class on both versions, so the contract table is unchanged except for one new sentence that names the verified versions.

## Library versions

| Environment | mcp | pydantic |
|-------------|-----|----------|
| System Python (PROVEN) | 1.25.0 | 2.12.4 |
| Locked: `uv run --offline --extra mcp-server --extra modern-encoder` (PROVEN) | 2.3.0 | 2.14.1 |

## Root cause

The `call` helper read `out[0].text`. On mcp 1.25.0 `call_tool` returns a list of content items. On mcp 2.3.0 it returns a `CallToolResult` object (fields `content`, `structured_content`, `is_error`), which has no index. Before the fix, 12 of the 18 reach tests failed on 2.3.0 with `TypeError: 'CallToolResult' object is not subscriptable`. The 6 that passed were the "tool error" cells, which raise before the result is read.

## Fix

`classify()` in `tests/test_host_run_mcp_reach.py` reads: an exception as "tool error"; a result with `is_error` true as "tool error"; a result otherwise through `structured_content` or the first text item as JSON; a list, tuple or dict as before. Expectations were not changed. Added `test_reader_handles_each_result_shape` and `test_a_tool_error_never_repeats_the_value_that_was_sent`.

## Per-cell table (route and class)

Route PROVEN with a probe plugin that logged each call on both versions (the probe lives in the scratchpad, not in the repo). In every refused or blocked or ready cell, mcp 1.25.0 returns a `list` and mcp 2.3.0 returns a `CallToolResult` with `is_error` false. In every tool error cell, both versions raise `ToolError` from the argument check. No cell returned `is_error` true on either version.

| Cell | mcp 1.25.0 | mcp 2.3.0 | Pinned (locked) |
|------|------------|-----------|-----------------|
| plan call, valid request | ready | ready | ready |
| blank objective | refused bad_request | refused bad_request | refused bad_request |
| id with no usable character | refused bad_request | refused bad_request | refused bad_request |
| missing key | tool error (raised) | tool error (raised) | tool error |
| unknown key | tool error (raised) | tool error (raised) | tool error |
| lone surrogate in text | tool error (raised) | tool error (raised) | tool error |
| lone surrogate in objective | tool error (raised) | tool error (raised) | tool error |
| more than 3000 artifacts | tool error (raised) | tool error (raised) | tool error |
| one text above 1000000 characters | tool error (raised) | tool error (raised) | tool error |
| duplicate id | refused duplicate_artifact_id | refused duplicate_artifact_id | same |
| id collision after sanitizer | refused id_collision | refused id_collision | same |
| wrong sha256 | refused artifact_hash_mismatch | refused artifact_hash_mismatch | same |
| external corpus | refused external_corpus_refused | refused external_corpus_refused | same |
| total text above 20 MiB | refused bundle_too_large | refused bundle_too_large | same |
| start, no approval | refused approval_missing | refused approval_missing | same |
| start, digest "zz" | tool error | tool error | tool error |
| start, reference "bad ref" | tool error | tool error | tool error |
| start, key of 129 characters | refused bad_request | refused bad_request | same |
| start, unknown plan | refused plan_unknown | refused plan_unknown | same |
| start, wrong digest | refused plan_mismatch | refused plan_mismatch | same |
| start, expired receipt | refused plan_expired | refused plan_expired | same |
| start, second start on one receipt | refused plan_consumed | refused plan_consumed | same |
| plan call, too few records | blocked too_few_usable_records | blocked too_few_usable_records | same |
| plan call, no local model | blocked local_model_unavailable | blocked local_model_unavailable | same |

Cells that differ between the versions: NONE. No version-guarded expectation was needed.

Extra claim checked on both versions (PROVEN): the contract sentence "A tool error also hides the input" holds. For an unknown key, a wrong type and a lone surrogate, the error text names the field and rule, not the value. It is now pinned by a test.

## Contract change

`docs/mos-eureka-engine-run-contract.md`: added one paragraph under "Refusals and errors" that says the table was verified on mcp 2.3.0 with pydantic 2.14.1 (the lock the plugin runs), gave the same cells on mcp 1.25.0, that a library change can move a cell, and that `tests/test_host_run_mcp_reach.py` fails when a cell moves. `tests/test_host_handoff_docs.py` gained three assertions for the sentence. No existing assertion changed.

## Results

- Reach, MCP and doc tests (tests/test_host_handoff_docs.py plus tests/test_host_run_mcp_reach.py), after the final commit: 37 passed on system Python and 37 passed on the locked environment (PROVEN).
- Whole suite, locked environment (PROVEN): `1813 passed, 8 skipped, 45 subtests passed` in 487 s. 0 failures. Total 1821 tests = 1819 (system baseline 1790 + 29) + 2 new tests. The locked run skips 21 fewer tests because the modern-encoder extra is installed.
- The whole suite was not re-run on system Python after the 2 new tests (UNVERIFIED); the touched files pass there.
- Pinning set on system Python (10 files, PROVEN): 195 passed.
- ruff on the two edited test files: All checks passed. mypy and the full ruff count were not re-run (UNVERIFIED); the edits are test files with typed signatures and add no new errors found by ruff.

## Locked-only failures

NONE. The only locked-environment failures were the 12 reach tests, fixed in Task 1.

## Deviations from Plan

None. No `src/` file changed. No real defect found. Added two tests beyond the plan (reader test, tool-error-hides-value test); neither weakens an existing test.

## Commits

- 67617cb test(quick-261108-0ur): read both mcp result shapes in the reach tests
- 7840888 docs(quick-261108-0ur): verify the MCP reach table on the locked mcp

## Self-Check: PASSED
