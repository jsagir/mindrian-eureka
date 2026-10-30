---
phase: 01-release-gate-and-engine-parity
plan: 06
subsystem: docs-fidelity
status: complete
tags: [REL-02, fidelity, readme, metadata, consistency-test]
requirements: [REL-02]
requires: ["01-01", "01-02", "01-04", "01-05"]
provides:
  - README section "Fidelity of the unusual-pairs engine" and extended readiness row
  - pyproject readme key and fidelity clause in description (no license key)
  - same phrase "not verified bit-for-bit" in manifest, catalog, run limitations, engine guide, parity record
  - docs/rs-engine-parity.md section 3.1 with after-fix numbers
  - tests/test_rs_fidelity_statement.py
affects: [phase-04-release]
key-files:
  modified:
    - README.md
    - pyproject.toml
    - capabilities/opportunity.find_cross_domain_pairs/manifest.json
    - src/mindrian_eureka/data/capability-catalog.v1.json
    - src/mindrian_eureka/opportunity_pairs/runner.py
    - docs/engines/opportunity-pairs.md
    - docs/rs-engine-parity.md
    - tests/test_rs_engine_parity_record.py
  created:
    - tests/test_rs_fidelity_statement.py
commits:
  - 68732ac docs(01-06): state fidelity of the unusual-pairs engine in README and package metadata
  - d495962 docs(01-06): same fidelity phrase in manifest, catalog, run limitations and engine guide
  - f56a893 docs(01-06): after-fix numbers in the parity record and a fidelity consistency test
metrics:
  tasks: 3
  completed: 2026-10-23
---

# Phase 1 Plan 06: Fidelity statement Summary

The phrase "not verified bit-for-bit" now appears in the README (twice), the package description, the capability manifest, the catalog entry, the run result limitations, the engine guide and the parity record. One test keeps them equal.

## What changed

- README: the readiness row is renamed to "Opportunity-pair discovery (the unusual-pairs engine)" and ends with the phrase. A new section "Fidelity of the unusual-pairs engine" names "Find Unusual Pairs Across a Research Collection" once with its job. It states the fixed statement, the canonical path (`eureka-pair-scout`, `hybrid_2026`, owner decision 2026-10-23), the newer fact (same ranking logic, different dense-input rule; 0.74 shared pairs and rank correlation 0.62 on the fixtures; 0.423 on the 40-file JHTV smoke; does not reproduce the JHTV ranking at the meaning-signal level), the JHTV provenance to an earlier reference script version by sha256, and links to the three records. It does not state a release decision.
- pyproject: `readme = "README.md"` and a clause in `description`. No `license` key, no license classifier, no urls table.
- Manifest: the old "has not been proven bit-for-bit" item is replaced by the new sentence, plus one item on the dense-input rule.
- Catalog: the old item is kept; one new item with the phrase is added.
- Runner: one item added to the result `limitations`; no item removed.
- Engine guide: states the original package and deck are not in this repo but the package files exist on the maintainer machine (paths and sha256 in `rs-release-gate.md`). Adds a paragraph on the dense-input rule and a table D1 to D9 in our own words. D8 is FIXED (tight LSA limit passes without xfail in plan 01-04). D4 is marked INFERRED.
- Parity record: section 3.1 holds the 16 metric rows from `report_after_tie_break_fix.json` (`.4g`). Section 3 rows are unchanged. The tie-break row in section 7 is now "Fixed in plan 01-04; evidence in section 3.1 (LSA max abs delta 3.371e-08, at most 1e-6)". The section 5 tie-break row and the section 3 intro sentence were updated. One fidelity line was added to section 1.
- Tests: `test_rs_engine_parity_record.py` gained 3 tests (section 3.1 drift, tamper guard, tie-break status vs the after-fix delta) and its old assertion "pending, scheduled in plan 01-04" now asserts the row has a final status. `test_rs_fidelity_statement.py` has 9 tests.

## Verification (PROVEN)

- Full suite before the plan: 180 passed, 25 skipped, 45 subtests passed.
- Full suite after the plan: 192 passed, 25 skipped, 45 subtests passed, 0 failed.
- `PYTHONPATH=src pytest tests/test_rs_fidelity_statement.py tests/test_rs_engine_parity_record.py`: 21 passed.
- Surname check (read at run time from the CJS comment) found no hit in README, parity record, engine guide or the two test files. No em-dash in the added lines.
- No test pinned the old catalog or limitations text, so no expected value of an existing test was edited (searched `tests/` for "bit-for-bit", "Reference equivalence", "has not been proven").

## Deviations from Plan

**1. [Owner naming rule] No bare "RS" in prose I wrote.**
- The plan fixed statement says "Eureka's RS ranking is ...". It was adapted to "Eureka's unusual-pairs engine is a reimplementation ... It is not verified bit-for-bit ...". The plan line for the parity record "RS fidelity: ..." became "Fidelity of the unusual-pairs engine: ...". The readiness row label was renamed. The phrase "not verified bit-for-bit" is exact everywhere.
- Existing text that I did not touch still has bare RS (for example the catalog item "Reference equivalence to the original RS package ..." which the plan says to keep, and other README rows).

**2. [Plan wording] Manifest item replaced and one item added.** The plan said replace; I replaced it and added a second item on the dense-input rule (newer fact).

**3. [Plan wording] Fidelity line in the parity record sits in section 1** (as the plan says), not in the preamble.

**4. [Detail] Test of the README release text.** `test_readme_does_not_state_a_release_decision` is an extra check for T-01-27.

## Auth gates

None.

## Known Stubs

None.

## Threat Flags

None.

## Open items

- The release decision (plan 01-01 task 3, owner sign-off) is still open. The README links to the record and does not state it.
- Overlap of the repo path with the JHTV file at 2117 files and top 200 is UNVERIFIED. The wording uses the 40-file figure.
- `top_k` cap of 100 stays; Phase 2 must lift it.
- The wheel was not rebuilt (as planned).

## Self-Check: PASSED

- Files exist: README.md, pyproject.toml, manifest, catalog, runner.py, engine guide, parity record, both test files.
- Commits exist: 68732ac, d495962, f56a893.
