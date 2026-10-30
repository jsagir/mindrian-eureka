# MindrianOS Holonic Focus and Discovery

**Status:** Seeded for architecture audit and implementation planning. The architecture in the initiating brief is proposed, not an approved MindrianOS design.

## Problem

MindrianOS knowledge can be connected and nested while Theo still lacks a reliable way to focus on the relevant context, navigate across boundaries, preserve evidence and uncertainty, and find potentially useful relationships in wicked, uncertain problem spaces. Excess context can obscure evidence; overly narrow context can hide opportunities. The discovery engine must support both bounded analysis and deliberate cross-boundary search.

## Mission

Prepare Mindrian Eureka engines to analyze an authorized local MindrianOS graph and return traceable, reviewable discovery candidates through CLI and MCP. The objective is to extract opportunities hidden in plain sight, especially in uncertainty and wicked problems, while preserving the host's authority over access, accepted knowledge, and graph changes.

## Intended users

- MindrianOS / Theo orchestration calling a bounded engine capability.
- Researchers and operators running reproducible CLI analyses against an authorized local graph.
- Human reviewers evaluating evidence-backed proposals.

## Expected outcomes

- A source-grounded inventory of existing engines and latest research algorithms.
- A runnable local graph analysis entry point with explicit read-only behavior.
- Typed handoff outputs that distinguish candidate signals from evidence and accepted knowledge.
- A sequenced plan for Holonic focus, projections, navigation, discovery, and human review that reuses MindrianOS services.

## Scope

- Audit Eureka code, docs, tests, capability catalog, and latest research package.
- Add a read-only graph analysis slice to CLI and snapshot-based MCP dispatch.
- Specify the MindrianOS adapter contract for authorization and graph snapshot supply.
- Plan research algorithm evaluation and future integration across the remaining engine families.

## Non-goals

- Replacing ICM, DataRoom, Theo, Genesis, Neo4j, or MindrianOS authorization.
- Creating a second canonical graph, portfolio, or truth store.
- Automatically accepting hypotheses or writing graph relations.
- Claiming graph ranking, novelty, or opportunity quality is validated.
- Implementing every proposed Holon concept before the repository audit establishes the existing equivalent.

## Key assumptions

- **Verified:** ADR 0001 assigns room permissions, approval, and canonical portfolio records to MindrianOS; Eureka must not write MindrianOS graph state.
- **Verified:** the existing graph-relations research source operates on JSON snapshots and includes a Neo4j read-only export path.
- **Verified in the MindrianOS Plugin checkout:** room-local graph state is stored in `<room>/.mindrian/room.db`; the existing `/mos:eureka` reads its bound room graph and ICM through the research-planner perspective. The visualization graph export is a limited display projection, not an engine data contract.
- **Verified in this repo:** selected graph engines accept bounded snapshot data through MCP; a development CLI can read a separately configured Neo4j store.
- **Proposed:** MindrianOS navigation will prepare authorized graph projections for Eureka MCP and resolve engine-returned stable IDs through the existing review/write workflow. Direct Neo4j CLI access is a development/replay path, not the production integration.
- **Unknown:** the canonical MindrianOS Holon, membership, temporal, provenance, and authorization schemas and current graph labels/types.
- **Reported:** ICM, DataRoom, Theo, Genesis, and OM-HMM are host concepts/capabilities described in the supplied brief; exact live contracts must be verified in the MindrianOS repository.
