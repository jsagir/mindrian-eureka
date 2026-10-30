# Requirements and acceptance criteria

## Functional requirements

- FR-1: Production engine runs accept only a MindrianOS-authorized projection from the room-local graph; snapshot JSON is its transport shape. Explicit Neo4j CLI configuration remains development/replay only and is not a reader for room.db.
- FR-2: Discover candidate relations from the source algorithms: open triads, induced 4-cycles, bridges, semantic gaps, and atypical category pairs.
- FR-3: Return method-specific scores/details and stable endpoint identifiers.
- FR-4: Identify likely duplicate/suspect names separately from relationship proposals.
- FR-5: Preserve reproducibility inputs (snapshot metadata, seed, analysis options) in results or run metadata.
- FR-6: Support future MindrianOS Focus and projection inputs without taking ownership of their data model.
- FR-7: Keep CLI and MCP workflow dispatch backed by one shared handler registry and advertise only capabilities with a real route on the named surface.
- FR-8: Publish versioned JSON input/output schemas and explicit runtime/resource bounds for graph capabilities.
- FR-9: Expose each migrated algorithm or method as its own discoverable, independently invocable CLI/MCP service with a stable capability ID and typed contract; compositions may call multiple services but are optional and do not replace the individual service surfaces.

## Epistemic invariants

- EI-1: Stable endpoint identifiers are retained through analysis.
- EI-2: New relations remain proposals; no implicit promotion.
- EI-3: Evidence is never fabricated; missing evidence is explicit.
- EI-4: Contradictory assertions remain representable in the host graph.
- EI-5: Human authority and rollback remain in MindrianOS.
- EI-6: Graph candidates do not imply truth, novelty, utility, or causality.
- EI-7: Context omission and unavailable source retrieval are disclosed.

## Security and traceability requirements

- SR-1: Any direct Neo4j development query is read-only; production room graph access goes through MindrianOS navigation, and no Eureka mutation capability is available.
- SR-2: MindrianOS authorizes and filters graph scope before MCP snapshot submission.
- SR-3: No room path, credentials, or unrestricted room directory is accepted as MCP input.
- SR-4: Label and relationship type filters bound Neo4j export.
- SR-5: Results identify input snapshot where available, engine capability/version, method signals, and limitations.
- SR-6: Cross-room leakage and sensitive metadata must be tested by the host before enabling graph integration.

## Testable acceptance criteria

- AC-1: A graph snapshot fixture produces deterministic proposal IDs and ordering for a fixed seed.
- AC-2: Existing edges are excluded from proposed additions.
- AC-3: Candidate rows remain `proposed`, have no evidence added by the engine, and disclose unknown direction.
- AC-4: Malformed snapshots and invalid bounds fail explicitly.
- AC-5: Neo4j adapter uses read access and rejects a query that fails the read-only guard.
- AC-6: MCP invocation accepts snapshot content only and never resolves a room or path.
- AC-7: A host integration test verifies authorization filtering before snapshot construction and confirms no unauthorized metadata appears. **Not met in the active plugin checkout:** the referenced bridge test is absent; no active-tree test verifies the real session resolver.
- AC-11: The host projection uses the navigation boundary, omits content outside its explicit node-ID scope, preserves stable node/edge IDs and selected source references, and reports omissions/caps; it does not reuse the visualization-only `getGraphExport` shape. **Not met in the active plugin checkout:** no Eureka graph-projection operation is present. Eureka's caller-supplied snapshot schema does not prove the host projection.
- AC-12: MindrianOS MCP operations project the bound local graph, invoke the local Eureka MCP engine, and return results bound to the same capability, scope, and snapshot while leaving graph bytes unchanged. **Not met in the active plugin checkout:** no graph-to-Eureka bridge operation or referenced end-to-end test is present.
- AC-13: The host can transform an authorized graph projection into the published source-linked artifact bundle contract without losing MindrianOS source references or scope/snapshot identity. **Engine half verified:** Eureka accepts a correctly shaped graph artifact bundle. Host-side authorized projection and transformation are not verified in the active plugin checkout.
- AC-14: MindrianOS can feed the verified artifact bundle into the local Genesis planner and receive a plan bound to the original scope/snapshot, with external research still unexecuted and room graph unchanged. **Engine half verified:** Genesis plans over caller-supplied artifacts. Host composition, session binding, and unchanged-room integration are not verified in the active plugin checkout.
- AC-8: No capability maturity upgrade occurs until temporal backtest and blinded human review succeed against baselines.
- AC-9: Every catalog capability advertising CLI or MCP resolves to a registered command/tool route; shared workflow stages use the same handler on both surfaces.
- AC-10: Every runnable graph capability's packaged input/output schemas parse and its catalog version, runtime, and resource limits are present.
- AC-15: For every source-ledger algorithm marked migrated, the capability catalog identifies its service ID, maturity, prerequisites, input/output schemas, and CLI/MCP routes; an inventory check reports unmapped algorithms separately from workflows that are intentionally blocked or planned.
