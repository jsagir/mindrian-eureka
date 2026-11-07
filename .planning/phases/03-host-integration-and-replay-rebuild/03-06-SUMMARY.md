---
phase: 03-host-integration-and-replay-rebuild
plan: 06
subsystem: provenance
tags: [provenance-gap, replay, emit-script, golden-file, HOST-02]
requires: []
provides:
  - docs/jhtv-replay-record.md (the one record file for Phase 4; outcome provenance_gap, room_mark pending_approval)
  - evaluations/graph-derive-replay/record.v1.json (machine record, 9 labelled checks, count proof)
  - evaluations/graph-derive-replay/gap-list.v1.json (golden output of the emit script)
  - mindrian_eureka.provenance.gap_list (load_record, verify_arithmetic, build_list, render_json, render_text, main)
  - scripts/emit-provenance-gap-list
  - Schemas eureka.provenance-gap-record.v1 and eureka.provenance-gap-list.v1
affects: [04-03, 04-04, 03-07]
tech-stack:
  added: []
  patterns: ["byte-stable JSON list with a committed golden file and a --check mode", "front matter contract file read by a later phase"]
key-files:
  created:
    - docs/jhtv-replay-record.md
    - evaluations/graph-derive-replay/record.v1.json
    - evaluations/graph-derive-replay/gap-list.v1.json
    - src/mindrian_eureka/data/schemas/provenance-gap-record.v1.json
    - src/mindrian_eureka/data/schemas/provenance-gap-list.v1.json
    - src/mindrian_eureka/provenance/__init__.py
    - src/mindrian_eureka/provenance/gap_list.py
    - scripts/emit-provenance-gap-list
    - tests/test_graph_derive_provenance.py
  modified: []
key-decisions:
  - "Outcome stays provenance_gap. The count proof (2,130 vectors of 384 dimensions, 2,165 pairs at 0.55) shows the counts only and does not replay anything."
  - "The count proof is a top-level count_proof object in the machine record. The doc front matter holds only the 4 contract keys."
  - "The record schema allows outcome replayed with conditional required keys, and forbids claims, pairs and two_run_hashes_equal when the outcome is provenance_gap."
requirements-completed: []
duration: about 35 min
completed: 2026-11-07
---

# Phase 3 Plan 06: Replay provenance record, gap list and emit script Summary

HOST-02 is settled on the Eureka side as a recorded provenance gap: the graph-derive replay behind JHTV OPP-027 to OPP-031 cannot be rebuilt from this repo, so the repo holds one record file, a tested script that emits the list of the five candidates to mark, and a hand-off of the room mark to the host.

`room_mark` stays `pending_approval`. No room mark was written. HOST-02 was not marked complete in REQUIREMENTS.md by this plan (instruction of the orchestrator).

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Provenance record, list and script tests (RED) | 1749fda |
| 2 | Machine record, schemas, module, script and golden list (GREEN, part 1) | dcf059c |
| 3 | The one record file for Phase 4 (GREEN, part 2) | 8400d87 |

## RED output

`tests/test_graph_derive_provenance.py` before any source file: 15 failed, 1 passed in 0.30 s. The one pass is `test_cli_py_is_not_part_of_this_plan`, which holds because `cli.py` has no string `provenance` today. The file has 16 test functions.

## GREEN counts

- After Task 2: 13 passed, 3 failed. The 3 failures are the doc tests (`test_record_doc_front_matter_contract`, `test_record_doc_headings_and_content`, `test_house_style_of_every_new_text_file`); they need the doc of Task 3.
- After Task 3: `test_graph_derive_provenance.py`, `test_release_gate_record.py`, `test_room_seed_docs.py` and `test_readme_commands.py`: 45 passed, 0 failed.
- ruff `src tests`: 1465 errors (baseline 1465; the new files are clean). mypy `src`: 88 errors in 17 files (baseline 88; the new package is clean).

## Fact checks of 2026-11-07 (read only)

| Check | Value observed |
|-------|----------------|
| C1 repo search | `derive_results` and `2,267,385` appear only in `.planning` files and the files of this plan. No script, claim table, vector table or `derive_results.json` in the repo. PROVEN |
| C2 arithmetic | 2130*2129/2 = 2267385; 2117*2116/2 = 2239786. PROVEN |
| C3 partner room store | Opened with `mode=ro&immutable=1`. `eureka_vec_rowids` 2130 rows, `eureka_vec_metadatatext00` 2130 rows. The table definition reads `vec0(node_id TEXT, embedding float[384])`. Store file dated 2026-10-29. No vector value and no text read. PROVEN |
| C4 file search | `find -maxdepth 8 -iname 'derive_results*'` in the dev folder, the rooms folders, the repo, the partner room, and the work, output, research, tmp and Downloads folders: no hit. PROVEN for those folders |
| Model on disk | No `mdbr` entry in the Hugging Face cache or under the repo. `model_on_disk` is false. PROVEN |
| C6 plugin code | `lib/core/graph-derive-classifier.cjs` at `MindrianOS-Plugin` commit cd6879a98: `DERIVE_CONVERGES_FLOOR_DEFAULT = 0.55`, `sem >= floors.converges` gives CONVERGES, `countAllPairs` returns n*(n-1)/2. PROVEN |
| C7 plugin history | Commit e2e819d43, 2026-10-21, `feat(379.1-04)` (the oldest commit that touches `buildCandidatePairs`, `countAllPairs`). PROVEN |
| 2,165 pairs at 0.55 | Taken from fact F14 of the phase context (feasibility check of the same date). Not repeated in this plan, because it needs a read of vector values. The record says so in `count_proof.basis`. |

No value differed from the plan facts.

## Script output

Two runs gave equal bytes that equal the golden file. The script printed this line on stderr: `sha256 23eb2c2c0073e095487fcc44fdb8c83f8b323aede1903d73286304b55cc83e11`. `scripts/emit-provenance-gap-list --check` exits 0.

## Boundaries

- Plugin checkout `git status --short | wc -l`: 0 before and 0 after (`MindrianOS-Plugin-release`). The main plugin checkout also shows 0 (information only).
- `src/mindrian_eureka/cli.py` is unchanged; no `eureka` subcommand was added.
- No room database was opened for writing; the one read was a row count and a table definition, read only and immutable. No push.
- No `story/` file and no `docs/research/` file was staged.

## Front matter of the record

```
outcome: provenance_gap
room_mark: pending_approval
label: candidate, not verified
checked_on: 2026-11-07
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Addendum] Count proof block in the machine record**
- **Found during:** Task 2
- **Issue:** The addendum asks the record and its machine twin to state the count proof. The plan fixed the 9 checks C1 to C9 and gave no field for it.
- **Fix:** Added a required top-level `count_proof` object to `record.v1.json` and its schema (vectors, dimensions, all pairs, pairs at floor, model on disk, store and replay dates, same-set label INFERRED, the Phase 3.1 deferral). The doc carries the same facts in prose. The test file has one extra test for it (16 tests, plan asked for 13 or more). The doc front matter has no extra key.
- **Files modified:** `evaluations/graph-derive-replay/record.v1.json`, `provenance-gap-record.v1.json`, `tests/test_graph_derive_provenance.py`
- **Commit:** 1749fda, dcf059c

**2. [Rule 3 - Blocking] Docstring line length in the test file**
- **Found during:** Task 1
- **Issue:** ruff E501 on the module docstring (108 characters).
- **Fix:** Shortened the line before the RED commit.
- **Commit:** 1749fda

## Known Stubs

None.

## Threat Flags

None. The only outside read was a row count of the partner room store (read only, immutable), as the threat model T-03-35 allows.

## Self-Check: PASSED

- Files found: all 9 created files exist.
- Commits found: 1749fda, dcf059c, 8400d87.
