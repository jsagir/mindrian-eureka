---
phase: 01-release-gate-and-engine-parity
plan: 01
status: partial
subsystem: docs-provenance
tags: [release-gate, provenance, licensing]
requirements: [REL-01]
requires: []
provides:
  - docs/rs-release-gate.md (draft record, decision no-go)
  - tests/test_release_gate_record.py (12 checks)
affects: [phase-04-release]
key-files:
  created:
    - docs/rs-release-gate.md
    - tests/test_release_gate_record.py
  modified:
    - docs/licensing-and-provenance.md
decisions:
  - "Record stays status draft, decision no-go. Task 3 (owner sign-off) is not done."
metrics:
  tasks_done: 2
  tasks_total: 3
  completed: 2026-10-23
---

# Phase 1 Plan 1: Release-gate record Summary

One record, `docs/rs-release-gate.md`, states the source origin, author attribution status and license facts of the unusual-pairs engine ("Find Unusual Pairs Across a Research Collection", formerly called RS), and ends with decision no-go, status draft.

## What was done

- Task 1: re-ran the evidence commands on 2026-10-23. The 5 original files are byte-identical in both locations (sha256 recorded in section 2, 434 lines measured). A search for license, copyright and author lines found no rights statement. The PowerPoint deck was not found on disk (depth 6 search). The plugin LICENSE is BSL 1.1 with licensor Jonathan Sagir. Script hashes 044b9ae6... and 57c18df5... match the research file. No fact changed since research. The record has the 9 front matter keys, 8 sections, gaps G1 to G6 and open item O1. It does not name the original author. It uses the phrase "name held privately" and points to the private plugin planning files.
- Task 2: one link line added to `docs/licensing-and-provenance.md` (insertions only). `tests/test_release_gate_record.py` has 12 checks. It reads repo files only and adds no dependency. It rejects: a missing key, a bad enum, a decided record without a date, a draft record with decision other than no-go, and decision go with open gaps.
- Task 3 (checkpoint:decision) was NOT run. The owner has not answered.

## Task commits

| Task | Commit | Files |
|------|--------|-------|
| 1 | 4809f8b | docs/rs-release-gate.md |
| 1 (wording follow-up) | e8ed73e | docs/rs-release-gate.md |
| 2 | 631a879 | docs/licensing-and-provenance.md, tests/test_release_gate_record.py |

## Deviations from Plan

**1. [Owner rule from coordinator] Catalog names in prose.** The coordinator ordered that prose use the catalog names instead of the short names RS and HSI. Task 1 was committed first with the short name in places. Commit e8ed73e fixes the prose of the record. The subject line of commit 4809f8b still carries the short name (history not rewritten). Literal names (`rs-engine.py`, `eureka-pair-scout`, `rs-release-gate.md`, the id `rs-source-release-gate`) stay as they are.

**2. Link line placement.** The link line sits directly after the second paragraph, in the same markdown block, so the diff shows 1 insertion and 0 deletions.

No other deviation.

## Verification

- `PYTHONPATH=src pytest tests/test_release_gate_record.py -q -p no:cacheprovider`: 12 passed (PROVEN).
- Task 1 automated check, including the run-time surname grep: passed (PROVEN). The surname and the first name are absent from the three files.
- No em-dash in the three files (PROVEN). No path starting with /home or /mnt in the test file (PROVEN).
- Full suite not run in this plan (UNVERIFIED).

## Open checkpoint (Task 3)

The owner must decide the status of the record. Question: Keep the release record as draft no-go, or decide now (no-go, internal-only, go)? The draft default stays valid for Phases 2 and 3. A go is valid only if G1, G2, G3 and G5 are closed.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- docs/rs-release-gate.md: found
- tests/test_release_gate_record.py: found
- commits 4809f8b, e8ed73e, 631a879: found in git log
