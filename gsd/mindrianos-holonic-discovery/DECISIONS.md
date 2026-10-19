# Decisions and open questions

## D1 — Preserve MindrianOS as the graph authority

**Status:** Verified from accepted ADR 0001. Eureka may analyze supplied authorized data; MindrianOS owns permission, approval, canonical graph, and portfolio writes.

## D2 — Add graph-relations as an experimental capability

**Status:** Implemented as a planning decision in this seed. CLI uses explicit local Neo4j read-only mode or snapshot mode; MCP receives snapshot data. No mutation API is provided.

**Alternatives:** Keep graph-relations as standalone scripts; add Neo4j writeback; wait for a fully validated ranking method. Direct script-only use does not provide stable package contracts; writeback violates current repository boundary; waiting blocks readiness work that can be safely performed read-only.

## D3 — Do not model Holon as every graph node

**Status:** Proposed; defer final semantics until MindrianOS ICM/DataRoom schema is inspected. Holon identity, containment, membership, and portal relations may map to existing concepts.

## D4 — Keep MCP host supplied and CLI local connection distinct

**Status:** Proposed. MCP receives authorized snapshot content; CLI can use explicit local connection credentials and source-supplied read-only Cypher. This avoids teaching MCP to resolve room identity or paths.

## D5 — Keep the MindrianOS adapter wave out of the active release

**Status:** The adapter wave remains untouched in `stash@{0}` in the MindrianOS Plugin checkout and is held out of the beta.73 cut while its release suite completes. The active plugin checkout has no current Eureka graph bridge; the held stash is not deployable evidence. Resume adapter review after beta.73 is cut, then land it through the host repository's review and readiness gates.

**Alternatives:** Pop the stash before the release, or ship the adapter without review. Both conflict with the release hold and skip the previously established review gate.

## Unresolved decisions

- Are graph nodes/edges or DataRoom records canonical, and how are they synchronized?
- What are the exact Holon boundary and shared-membership semantics?
- Which timestamps represent event time versus ingestion time?
- What host mechanism authorizes graph export and enforces cross-room filtering?
- Which read-only graph role and local connection transport are supported in deployment?
- Which research algorithms are legally redistributable and faithful to their sources?
- What evidence threshold and reviewers are required before accepting a connection?
