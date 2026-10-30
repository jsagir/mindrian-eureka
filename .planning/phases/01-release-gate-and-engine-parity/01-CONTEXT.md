# Phase 1: Release Gate and Engine Parity - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning
**Source:** Owner decisions at plan-phase (AskUserQuestion) plus 01-RESEARCH.md

<domain>
## Phase Boundary

Settle RS licensing and attribution status, prove or choose the canonical RS path, recover the HSI command that produced the JHTV result, and state fidelity in plain words. No plugin-repo edits.
</domain>

<decisions>
## Implementation Decisions (LOCKED by owner, 2026-10-23)

- **Canonical dense rule:** the repo path (`eureka-pair-scout`: title plus body, chunk-mean) is canonical going forward. JHTV candidates keep provenance to the r-and-d RS script (path B) by sha256. Document JHTV results as a different method version. Record the measured overlap (0.42 on a 40-file smoke test) as evidence, not as a defect to fix by matching B.
- **REL-01 record:** `decided_by` is the owner (Jonathan Sagir). The record does NOT name the original source author. Use wording such as "original author, name held privately" with a pointer outside the repo. Attribution wording must be settled with the author before any public release. Default decision stays no-go, status draft, until the owner changes it.
- **Do not vendor** the r-and-d script or the original similarity_code files into the repo. Use env vars and a golden file.
- **Tests** run as `PYTHONPATH=src pytest` with a tmp embedding cache path in every test. Use scratch copies of any room.
- **Plan split** follows 01-RESEARCH.md: six plans, three waves.

### Claude's Discretion
Fixture sizes, exact thresholds (use the reasoning in 01-RESEARCH.md), file names inside the phase.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/01-release-gate-and-engine-parity/01-RESEARCH.md` - three RS paths, HSI command, REL-01 evidence, parity design, plan split
- `.planning/ROADMAP.md` - Phase 1 success criteria
- `.planning/REQUIREMENTS.md` - REL-01, REL-02, ENG-01, ENG-02, ENG-03
- `docs/engines/opportunity-pairs.md` - current RS docs
</canonical_refs>

<deferred>
## Deferred Ideas

- Optional `--dense-rule jhtv-v1` switch (owner chose repo-canonical; revisit only if users need JHTV reruns).
- Plugin-repo fixes for rs-engine.py legacy-only scoring.
</deferred>

---
*Phase: 01-release-gate-and-engine-parity*
*Context gathered: 2026-10-23*
