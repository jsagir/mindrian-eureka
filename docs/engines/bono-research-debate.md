# BONO Research/Debate Engine: migration and host contract

**Readiness:** Not implemented as a full Eureka capability. The current `deliberation.prepare_six_hat_review` capability only organizes supplied perspectives for human review.

## Job to be done

Hire BONO when a wicked, uncertain question needs a governed argument across several domains and perspectives, rather than a single answer or a one-pass Six Thinking Hats review. The full job assembles a bounded research grid, gathers source-linked readings in parallel, debates those readings sequentially under hat-specific rules, and presents a synthesis for a human ruling.

BONO is especially relevant to opportunity discovery: it should help explore uncertain future states, surface tensions and candidate opportunities, and make the assumptions and evidence inspectable. It must not treat a plausible what-if as a validated opportunity or as a resolved wicked problem.

## Verified source shape

The current LATEST package contains 11 files under `engines/bono/`: a command definition, persona instructions, a HITL fixture, and eight implementation modules. The command describes a larger MindrianOS workflow assembled from these BONO modules plus shared host modules. Those shared modules are not included in the BONO directory. In particular, the command depends on MindrianOS decomposition, expert assembly, research dispatch and egress controls, local graph/navigation, run-chain execution, persistence/resume, close-loop filing, supersession, and interactive decision gates.

The source flow declares three decision gates: confirm topic/scope, confirm the what-if hypothesis, and approve the final ruling/synthesis. The work between gates includes a parallel `(subdomain × hat)` cell fan-out followed by sequential inter-hat debate. Cells must cite their wired evidence, and each cell's allowed research scope is constrained. The terminal output files only after approval through MindrianOS's close-loop path. These are material parts of the behavior, not interface details that can be dropped in a standalone port.

The package is MindrianOS Plugin code by its file headers, but authorship/release authority and redistribution terms have not been established. Source hashes and this review boundary are recorded in the [engine source ledger](../engine-source-ledger.md). No source code has been copied into Eureka.

## MindrianOS graph boundary

MindrianOS owns the canonical local graph, room scope, authorization, source resolution, human approval, persistence, and all graph writes. Eureka must not open `room.db`, decide which room records are authorized, or write accepted graph state.

For graph-aware BONO execution, MindrianOS should prepare one bounded, versioned projection containing stable node/source IDs, the selected evidence, typed relations, and explicit scope/snapshot metadata. Eureka can return debate cells, cited evidence references, candidate claims/relations, dissent, residual tensions, and a proposed synthesis, all bound to that same scope and snapshot. MindrianOS resolves those references and runs its existing human-gated review and filing workflow. A returned proposal is not an accepted graph fact.

External research and local judge/model calls also remain host-brokered. The engine contract should receive authorized findings or host-produced responses rather than room paths, credentials, or permission-bearing identifiers. Scope and snapshot fields are lineage metadata, never authorization tokens.

## Required engine interfaces before the capability can be unblocked

1. **Open run:** accept an authorized projection, objective, candidate what-if, allowed source policy, resource budget, and run idempotency key; return a run ID and explicit requirements for the topic-confirm gate.
2. **Confirm scope/hypothesis:** record host-confirmed values and the projection version. Refuse to proceed when the projection or candidate IDs are stale or unresolved.
3. **Build research grid:** accept host-confirmed domains and allowed hat lenses; bound the cell count and per-cell resource limits before any research starts.
4. **Collect cells:** accept host-brokered, source-linked findings per cell; validate citation IDs, cell identity, allowed domain/lens, and completeness. Preserve failed or thin cells as explicit failures rather than silently treating them as evidence.
5. **Debate sequentially:** consume the fixed collected-cell set exactly once; return each hat's argument, cited sources, challenges, and residual tensions with governance diagnostics. No fan-out or new external calls inside the debate loop.
6. **Ruling and review:** return candidate dispositions and a synthesis for host presentation. Do not write or promote graph records; filing remains unavailable until MindrianOS approval is recorded.
7. **Resume and audit:** persist run cursor and cell/debate outputs in Eureka's job store; support idempotent resume without repeating completed cells or human gates; expose an inspectable run trace.

The future MCP surface should be job-oriented (start, supply host results, advance after gate, inspect, resume/cancel) rather than one monolithic call that hides human pauses. The CLI must expose the same state machine for prepared fixtures and operator-supplied host results. Both surfaces should share typed request/result schemas and job semantics.

## Migration sequence

1. Keep `deliberation.prepare_six_hat_review` callable as the current lightweight, preparation-only method.
2. Add a BONO capability manifest and schema only when the host-brokered state machine and job transitions are defined; do not change `deliberation.structure` from blocked based on a planning stub.
3. Implement and fixture-test the pure, bounded grid/debate composition seams against the exact LATEST modules where their dependencies are available and rights permit.
4. Add host adapters for research dispatch, local judge/model execution, decision gates, and result review. Keep graph projection and filing in MindrianOS.
5. Verify the full lifecycle with an end-to-end fixture that pauses at every gate, tests rejection/resume, citation failures, resource caps, stale snapshots, duplicate delivery, and confirms no graph write occurs before MindrianOS approval.

Until those steps pass, report BONO as **blocked for full research/debate execution**, while the six-hat preparation sub-capability remains experimental and usable.
