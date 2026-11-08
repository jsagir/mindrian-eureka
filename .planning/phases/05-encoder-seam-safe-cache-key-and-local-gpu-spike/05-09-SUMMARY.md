---
phase: 05-encoder-seam-safe-cache-key-and-local-gpu-spike
plan: 09
subsystem: readme-refresh
tags: [readme, encoder-profile, docs, check-table]
status: DONE (plan 05-08 stays open at its owner-run checkpoint)

requires:
  - phase: 05-06
    provides: docs/encoder-profiles.md, encoder key of the host result
  - phase: 05-07
    provides: docs/encoder-comparison.md (MiniLM column only)
  - phase: 05-08
    provides: docs/encoder-spike-results.md (all values NOT RUN)
provides:
  - "README.md section 'Choose an encoder profile', extras row, readiness row, MCP note"
  - "src/README.md and examples/public-example/README.md Phase 5 text"
  - "five new assertions in tests/test_readme_commands.py"
affects: []

key-files:
  modified:
    - README.md
    - src/README.md
    - examples/public-example/README.md
    - tests/test_readme_commands.py

key-decisions:
  - "The public example README gets the gpu-approx text as plain paragraphs, not a new heading, because tests/test_public_example.py pins the heading list and this plan may not edit that test."
  - "No speed number is quoted in the READMEs. The MiniLM CPU speed stays on the comparison page only."

requirements-completed: []

duration: about 35min
completed: 2026-11-08
---

# Phase 5 Plan 09: README refresh for the encoder profiles Summary

STATUS: DONE. The three README files match the code and a run. `gpu-nemotron` is described as a spike profile, unproven, "not run yet". No GPU number is written anywhere.

## Commits

| Step | Commit | Subject |
| ---- | ------ | ------- |
| Task 1 | db19325 | docs(05-09): refresh the READMEs for the encoder profiles |
| Summary | see git log | docs(05-09): record the README refresh |

## README check table

Every row is a claim, the command that checked it, the result and whether the README changed. Commands ran with `uv run --no-sync --offline` unless noted.

| Claim | Command | Result | Changed |
| ----- | ------- | ------ | ------- |
| Catalog size "68 entries" | `eureka capabilities`, count `capabilities` | 68 (55 experimental, 5 host_brokered, 4 blocked, 4 planned) | No (still true) |
| Routed count "60 have a CLI and MCP route" and "All 60 runnable entries" | same output, count entries with `routes` | 60 | No (still true) |
| MCP tool count "27 tools" | `asyncio.run(server.list_tools())` on `mcp_server.server` (system mcp, locked env) and `grep -c "@server.tool"` | 27 and 27 | No (still true) |
| `eureka` commands in Development list | `eureka --help` | capabilities, capability, schema, workflow, run, doctor, hub, seed, check-example | No (still true) |
| `eureka run` flags | `eureka run --help` | `--encoder-profile NAME` and `--model-path P` exist; "another profile needs --model-path" | Added the flag, the table and the example command |
| `eureka doctor` flags | `eureka doctor --help` and `eureka doctor --encoder-profile gpu-nemotron` | flag exists; on this computer check D9 fails (no CUDA in torch), as designed; 6 passed, 1 warning, 1 failed | Added the flag and the sentence in the doctor paragraph |
| Unknown profile name | `eureka run /nonexistent --encoder-profile nope` | "The encoder profile 'nope' is not known. The names are: cpu-default, gpu-nemotron." | Names in README equal this list |
| Profile table (model ids, 384 and 2048) | `docs/encoder-profiles.md`, `encoder_spec.PROFILES` | `cpu-default` MiniLM 384; `gpu-nemotron` Nemotron-3-Embed-1B-BF16 2048 | Added; a test compares the model ids with `PROFILES` |
| Extras list | `pyproject.toml` optional-dependencies | bundle, hub-gate, modern-encoder, gpu-encoder, reference-encoder, mcp-server, hmm, neo4j | Added the row `gpu-encoder`; a test checks every extra has a row |
| `gpu-encoder` extra content | `pyproject.toml` | `sentence-transformers>=5.4.1,<6`, `transformers>=5.2,<6`; no CUDA torch (CPU index pinned) | Added the install line and the note |
| Manifest `encoder` block | `example/contracts.ENCODER_KEY`, `docs/encoder-profiles.md`, grep of `encoder_fingerprint` in `run/pipeline.py` and `run/project.py` | key `encoder`, schema `eureka.encoder-block.v1`; `encoder_fingerprint` written to the pair files only for a named (non-default) profile | Added |
| Reference run has no encoder block | `manifest.json` keys of `examples/public-example/reference-run` | no `encoder` key (the reference run predates Phase 5) | Not claimed in the README |
| `check-example` on the reference run | `eureka check-example examples/public-example/reference-run --expected examples/public-example/expected-hashes.json` | 7 PASS lines, `Result: MATCH.` | No change needed; ran again after the edits: MATCH |
| `check-example` for a `gpu-approx` run | scratch copy of the reference run with `encoder.determinism_class` set to `gpu-approx` (scratchpad, not in the repository), then `check-example` | X6 FAIL: overlap 1.0000 of 63 and 1.0000 of 200 reference pairs, "no overlap threshold has been measured yet, so a gpu-approx run is not a match"; the note text of `GPU_APPROX_NOTE`; `Result: NO MATCH.` | Added: overlap numbers printed, NO MATCH, never a match while `GPU_APPROX_MIN_OVERLAP` is None (read in `example/contracts.py`) |
| Threshold unset | `example/contracts.py` line 87 | `GPU_APPROX_MIN_OVERLAP: float | None = None` | Described as "not measured yet" |
| Spike state | `docs/encoder-spike-results.md` front matter and table; `docs/encoder-evidence/` listing | `status: not_run`; no `gpu-spike-log.json` in the folder | Written as "not run yet", no GPU number |
| Comparison page state | `docs/encoder-comparison.md` table; `cpu-compare-log.json` | MiniLM column run; `mdbr-leaf-ir` and Nemotron columns NOT RUN | README says only the MiniLM column was measured |
| Partner bundle command and `bundle` extra | `scripts/build-partner-bundle --help`; `pyproject.toml` | targets linux-x86_64, windows-x86_64, macos-arm64 (and host); `--out`, `--online`; extra `bundle = ["packaging>=26.3"]`; the script passes `--extra bundle` | No (still true) |
| Windows launcher note | grep `start.ps1` in `partner_bundle/launchers.py`; `docs/partner-run-guide.md` line 123 | `start.ps1` exists; launchers on three systems stay ASSUMED | No (still true) |
| `requires-python` "Python 3.11+" | `pyproject.toml` | `>=3.11` | No (still true) |
| `reference-encoder` is the default encoder of `eureka-pair-scout` | `opportunity_pairs/encoders.py` line 163 | install text names the extra `reference-encoder` | No |
| Pair-screen result carries the encoder block | `docs/mos-eureka-engine-run-contract.md`, plan 05-06 summary | optional key `encoder`; no request field for a profile (hand-off 2 not built) | Added one note to the MCP section |
| Links in the new section | test `test_profile_section_does_not_overclaim_the_spike` | all targets exist | Added |
| Style: no long dash in added lines | `git diff HEAD -- <4 files> | grep '^+' | grep -cP "\x{2014}|\x{2013}"` | 0 | |

## Test results

- Task 1 set (`test_readme_commands`, `test_room_seed_docs`, `test_release_gate_record`, `test_public_example`, `test_reproduction_guide`, `test_host_handoff_docs`, `test_encoder_docs`): 88 passed.
- Wider pinning set (adds `test_hub_assets`, `test_partner_bundle`, `test_example_check`, `test_host_run_mcp_reach`) on system Python with `PYTHONPATH=src:tests`: 209 passed.
- First run of the Task 1 set had one failure: `tests/test_public_example.py::test_readme_structure_and_wording` pins the heading list of the example README, and my first draft added a heading. Fix: the new text became plain paragraphs under "What you should see". This is the recorded deviation below.
- `ruff check src tests`: 1452 errors (baseline 1452, no rise). `ruff check tests/test_readme_commands.py`: All checks passed.
- `mypy src`: 87 errors in 16 files (baseline 87, no rise).
- Full suite: not run (the orchestrator runs it).

## New assertions in tests/test_readme_commands.py

Five new tests, no existing assertion changed or removed:
- `test_profile_section_commands_and_flags_exist_in_the_parser_help`: the commands in the README exist; `--encoder-profile` is in the help text of `run` and `doctor`; `--model-path` is in the help of `run`; the `gpu-encoder` install line is present.
- `test_profile_section_names_the_profiles_the_code_defines`: both profile names and both model ids equal `encoder_spec.PROFILES`.
- `test_profile_section_does_not_overclaim_the_spike`: "unproven", "not run yet", "MiniLM stays the default encoder.", "Result: NO MATCH", the schema id, no long dash, links exist.
- `test_extras_table_lists_every_extra_of_the_project`: every extra of `pyproject.toml` has a row.
- `test_public_example_readme_names_the_gpu_approx_behavior`.

## Deviations from Plan

**1. [Rule 3 - Blocking] No new heading in the example README**
- **Found during:** Task 1 verify
- **Issue:** `tests/test_public_example.py` pins the heading list; a new heading failed it. The plan does not allow an edit of that test.
- **Fix:** The text sits in two plain paragraphs before "Where it was checked".
- **Commit:** db19325

No stale claim was found in the Phase 4.1 items (counts, commands, partner bundle, launcher note). The only stale item was the missing `gpu-encoder` extra row.

## Not done and why

- The GPU spike (plan 05-08) is not run. The READMEs say so.
- No MiniLM speed is quoted in the READMEs (the plan allows it only if indicated; it stays on the comparison page).
- STATE.md pointer stays at "Plan: 5 of 9" because 05-08 is open.

## Known Stubs

None.

## Threat Flags

None. Documentation and tests only.

## Self-Check: PASSED

- README.md, src/README.md, examples/public-example/README.md, tests/test_readme_commands.py: FOUND, changed in db19325
- Commit db19325: FOUND in git log
