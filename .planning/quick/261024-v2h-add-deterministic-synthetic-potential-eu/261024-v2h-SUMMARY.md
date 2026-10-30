---
quick: 261024-v2h
status: complete
implementation_commit: 0398f90
---

# Synthetic Potential eureka fixture

Added `build_run_folder_with_potential_eureka` using the existing HashingEncoder stub. Its 21 visible synthetic records produce two neighborhoods and two Potential eureka records under unchanged model rules. Stable bridge ID order is `synthetic-b-000`, `synthetic-z-connector`. Every record identifies itself as synthetic test fixture, not a finding. The helper stays under tests and never supplies package or public example data.

Two builds in different parent folders and with different output names contain exactly the same five files and bytes. Payload checks bind each Potential eureka to candidate, not verified and source links, and reject missing status or source data.

The real public fixture remains unchanged. The page now renders the existing Gr09 tour-empty copy when there are no bridges. Tests check Gr09, B05's actual 0.90 cut-off fragment, and B06. P06.hidden means Hidden by default; the real fixture has zero weak pairs, so the test correctly checks its absence rather than manufacturing a hidden row.

The 12-line addendum assigns positive chip, tour, panel, and yellow sphere with ink shell checks to plans 13, 15, 18, and 16 using the helper. The real example keeps honest none-state checks.

Verification: 32 focused tests passed. Full suite: 1016 passed, 27 skipped, 45 subtests passed in 129.03 seconds. Ruff passed for the helper, new test module, and page. Strict mypy passed for hub_support.py and page.py. Browser behavior for later UI features remains unverified until their plans run.

Deviation: added a dedicated regression test module and a minimal page empty-state change to meet the explicit test and rendering requirements. No existing PLAN, model threshold, production scorer, or public fixture was edited. No push. Next: execute Plan 09.
