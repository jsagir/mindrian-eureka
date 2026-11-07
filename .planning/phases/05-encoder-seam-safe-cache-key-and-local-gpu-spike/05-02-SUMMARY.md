---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 02
subsystem: cache
tags: [embedding-cache, cache-key, schema-2, dimension-check, profile-cache]

requires:
  - phase: 05-01
    provides: encoder spec and profile names (not imported here; the cache takes a plain mapping)
provides:
  - "EmbeddingCache.SCHEMA_VERSION 2; key(..., identity=None) hashes the identity mapping"
  - "cached_encode(..., identity=None, expected_dimension=None) with width check and dimension_rejected meta"
  - "payload width header; a mismatch is a corrupt row"
  - "profile_cache_path and default_cache_path(profile): one private cache file per profile"
  - "eureka-rs-cache-clear --all-profiles"
affects: [05-03, 05-05]

tech-stack:
  added: []
  patterns: ["cache takes the identity as a plain mapping, no import of encoder_spec"]

key-files:
  created:
    - tests/test_embedding_cache_key.py
  modified:
    - src/mindrian_eureka/opportunity_pairs/cache.py
    - src/mindrian_eureka/opportunity_pairs/cli.py

key-decisions:
  - "BASE_PROFILE = cpu-default is a constant in cache.py; plan 05-03 adds the test that it equals encoder_spec.DEFAULT_PROFILE."
  - "The runner is not changed; it passes no identity yet (plan 05-03)."

requirements-completed: []

duration: 25min
completed: 2026-11-08
---

# Phase 5 Plan 02: Safe cache key Summary

**Schema 2 cache key that holds the full encoder identity, a width check on every hit and on every generated vector, a width header in each payload, and one private cache file per profile with an all-profiles clear option.**

Requirement ENC-03 is covered by this plan. It is not marked complete here; the orchestrator marks it at the end of the phase.

## Commits

| Task | Sha | Subject |
| ---- | --- | ------- |
| 1 RED | 0981d4c | test(05-02): add failing tests for the schema 2 cache key, width check and profile files |
| 2 GREEN | be03ec0 | feat(05-02): schema 2 cache key with encoder identity, width check and one cache file per profile |
| Summary | see git log | docs(05-02): record the safe cache key plan |

## RED output (Task 1)

`tests/test_embedding_cache_key.py`: 27 failed, 0 passed (14 of the failures are the parametrized identity-field test). Causes: schema version 1, no `identity` keyword, no `profile_cache_path`, no `--all-profiles` flag, no `dimension_rejected` meta.

## GREEN counts

- `tests/test_embedding_cache_key.py`: 27 passed.
- Guard and pinning set on system Python (`test_embedding_cache_key`, `test_wrong_number_fixes`, `test_rs_hybrid_2026`, `test_rs_engine_parity`, `test_run_pipeline`, `test_run_engines`, `test_mcp_start_stderr`, `test_hub_assets`, `test_partner_bundle`, `test_readme_commands`, `test_public_example`, `test_example_check`, `test_release_gate_record`, `test_room_seed_docs`, `test_host_handoff_docs`): 296 passed, 4 skipped, 0 failed. `test_partner_bundle.py` passed; no launcher test failed.
- Locked environment (`PYTHONPATH=src:tests uv run --offline --extra mcp-server --extra modern-encoder --with pytest`): `test_mcp_start_stderr`, `test_run_engines`, `test_embedding_cache_key`, `test_wrong_number_fixes`: 94 passed.
- Acceptance one-liner prints `2 embeddings.sqlite3 embeddings-gpu-nemotron.sqlite3`. `grep -c encoder_spec cache.py` prints 0. No em dash or en dash in `cache.py`.

## Lint counts

- `ruff check src tests`: 1454 errors (baseline 1456 after plan 05-01; the gain comes from the new test file being clean and from the removal of old findings in the touched code).
- `ruff check` on `cache.py`, `cli.py` and the new test file: 17 errors; the two source files held 19 before the change.
- `mypy src`: 87 errors in 16 files (baseline 87 in 16).

## Deviations from Plan

**1. [Rule 1 - Bug] `EmbeddingCache.clear()` failed when the cache held rows.** Root cause: `DELETE` opens an implicit transaction, and `PRAGMA wal_checkpoint(TRUNCATE)` and `VACUUM` cannot run inside an open transaction, so SQLite raised `database table is locked`. PROVEN on Python 3.12.3 and 3.12.12 on the unchanged code with one stored row. The existing command `eureka-rs-cache-clear` was therefore broken for any non-empty cache, and the new `--all-profiles` test could not pass. Fix: commit the delete in a `with db:` block, then run the checkpoint and the vacuum, then close the connection. Commit be03ec0. The new clear test covers it (before and after rows).

**2. [Info] Test file formatting.** Six long lines in the new test file were wrapped before the RED commit so `ruff check` is clean.

No existing test was weakened, deleted or changed.

## Behavior notes

- A rejected hit counts as a miss and is deleted before the new vector is stored.
- The width check reads `shape[-1]`, so a chunked result of shape (chunks, width) is checked by its width.
- Mixed widths in one result raise `RuntimeError` with the words `different widths`; this check runs even when `expected_dimension` is None.
- `--all-profiles` skips links and non-regular files, does not recurse, and leaves other files (for example `notes.txt`) untouched.

## Known Stubs

None.

## UNVERIFIED

- Real-model byte identity of the default path. Plan 05-05 proves it. The runner passes no identity yet, so the old key shape (now under schema 2) is the only one in use; a real run will miss the cache once, then hit.
- The MCP server cache path `data_dir / "embeddings.sqlite3"` is not changed.
- Full-suite count after this plan (the orchestrator runs it).
- The opt-in fresh-checkout test was not run (plan rule).

## Threat flags

None. T-05-06 to T-05-09 mitigated as the plan states (full identity in key, schema bump, width checks, name pattern, all-profiles clear, modes 0o700 and 0o600 tested). `git diff` of this plan lists no `pyproject.toml` or `uv.lock` change.

## Self-Check: PASSED

- `tests/test_embedding_cache_key.py`, `cache.py`, `cli.py` exist.
- Commits 0981d4c and be03ec0 exist in `git log`.
- No `story/`, `docs/research/`, `.gitkeep` or quick-folder file staged or committed.
