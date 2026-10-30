# Roadmap

## Phase 0 — Architecture audit (in progress)

- Inventory current repo capabilities, workflows, tests, interfaces, and decisions.
- Verify source package versions and latest research inventory.
- Map MindrianOS Holon/DataRoom/ICM/authorization schemas from the host repo.
- Deliver gap matrix and ADRs for unresolved boundaries.
- Exit: each proposed layer maps to a verified host or Eureka component, or is explicitly unknown.

## Phase 1 — Graph algorithm CLI and snapshot workflow (engine-side slice complete)

- Package latest graph-relations methods.
- Add local Neo4j read-only and JSON snapshot CLI input.
- Support bounded focal-node projections and explicit omission metadata.
- Project authorized graph nodes into the established RS/HSI source-linked bundle and verify it against the Scout validator.
- Expose bounded snapshot execution through existing MCP workflow dispatcher.
- Run focused adapted source tests; document failed validation and provenance.
- **Verified complete for the Eureka engine side:** caller-supplied snapshots run read-only through CLI/MCP; graph-to-RS/HSI projection validates against the existing Scout contract; SME neighborhood mapping uses the bundled core; proposals remain unevidenced and pending. The full repository suite passes 106 tests, 1 skipped test, and 4 subtests with the HMM extra enabled (2026-10-19), including the RS domain-analysis, differential-scoring, and pair-set quality and query-matrix stages, plus critic Stage A graph-neighbor and Stage B local-judge handoffs, analogy-whitespace parity against four LATEST fixtures, real OM-HMM and SME CLI/MCP parity, and the RS classifier, breakthrough score, thesis, and expert extraction stages. SAPPhIRE fusion and restatement ranking are covered as local contract behavior; model-spine numerical parity remains unknown.
- **Still required in MindrianOS:** the active `MindrianOS-Plugin` checkout does not contain `eureka_graph_project`, the graph-to-Eureka bridge tools, or the referenced `test-eureka-live-bridge.cjs`; an adapter-related change set remains stashed separately. It was applied only in `/tmp/mos-eureka-review` for isolated review, where all 8 focused adapter tests passed, including graph projection through Eureka stdio MCP and the live opportunity scout. This does not put the wave in the active checkout or establish release readiness. After the beta.73 release hold, integrate the reviewed adapter, test session authorization against a real bound room, call the separate Eureka MCP from `/mos:eureka`, resolve results through the existing review flow, and keep writes host-owned.

## Phase 1b — Capability contract delivery (in progress)

- [x] Expose packaged schemas through `eureka schema <capability-id>` and MCP `scout_capability_contract`.
- [x] Publish input/output schemas for all 58 experimental or host-brokered catalog entries that advertise CLI/MCP surfaces.
- [x] Enforce request and result schemas through shared `eureka-workflow` and `scout_run_workflow` dispatch.
- [x] Enforce published catalog schemas through generic dispatch and the mapped dedicated CLI/MCP routes: RS/combined scout, graph CLI, SME, OMM CLI/MCP/loopback, Jason, HSI, and analogy fitness.
- [x] Verify all 58 experimental/host-brokered capabilities are discoverable through `eureka capability`, `eureka schema`, and MCP `scout_capability_contract`, with matching packaged input/output schemas.
- [x] Split the five bundled graph signals into independently named services with individual JTBDs, strict request/result schemas, and generic CLI/MCP routes; preserve `graph.explore_local_relationships` as the optional composite.
- [ ] Exercise real MindrianOS input/result pairs for every advertised capability and close the remaining host integration gaps.
- [x] Expose the LATEST Eureka critic's deterministic Stage A over MindrianOS-prepared local embeddings and graph neighbors, with source-defined variant hashes and shared CLI/MCP dispatch.
- [x] Expose Stage B prompt preparation and verdict evaluation over MindrianOS-approved local judge responses; keep calibration and qualification separate.
- Exit: every callable capability exposes a discoverable, versioned contract and both surfaces enforce it.

## Phase 2 — Host snapshot contract

- Treat each room's `<room>/.mindrian/room.db` as MindrianOS's canonical graph; preserve the existing `/mos:eureka` research-planner workflow and add this engine service as a selected method provider.
- [ ] Add a purpose-bound explicit-ID graph projection through MindrianOS navigation, reusing its canonical read-only navigation boundary. Active-checkout symbol audit found no Eureka graph projection handler.
- [ ] Include stable IDs, typed nodes/edges, selected source-linked text, hashes, focal scope, snapshot identity, and explicit completeness/omission metadata.
- [ ] Validate minimal and extended node schemas in a synthetic room database; test selected text hashes, stable node URIs, induced typed edges, snapshot hash, and omission counts.
- [ ] Test session authorization and cross-room leakage against real MindrianOS room binding and identity resolution.
- [ ] Configure and wire the projection result to Eureka MCP from `/mos:eureka`; direct `eureka-graph --neo4j` remains an unrelated development/replay path for a separately configured Neo4j store.
- Exit: authorized snapshot input is auditable, omissions are explicit, and Eureka engine results can be resolved against the canonical MindrianOS graph without bypassing its review/write path.

## Phase 3 — Algorithm evaluation

- Establish temporal baselines and negative controls on authorized snapshots.
- Evaluate structural, semantic, bridge, atypicality, surprise, BTM, and persistent-homology methods independently.
- Blind human assessment for useful leads, false connections, evidence traceability, latency, and resource use.
- Exit: define evidence-backed maturity per algorithm; retire methods that fail.

## Phase 4 — Focus and projection mapping

- Inspect current ICM/room investigation records and Theo context assembly.
- Reuse host structures for focus sessions and projection metadata where available.
- Prototype bounded projections with source references, omissions, and reproducible snapshot/version data.
- Exit: host and Eureka ownership and exact interfaces are documented; projection completeness tested.

## Phase 5 — Navigation and discovery workflow

- Map existing graph relations to semantic membership and possible boundaries; do not equate every node with a Holon.
- Add authorized, auditable navigation and candidate generation beyond known edges.
- Integrate candidate review through existing human approval and graph write paths.
- Exit: an unapproved candidate cannot become accepted knowledge and all source/decision lineage is recoverable.

## Phase 6 — Theo and PWS orchestration

- Map Theo, PWS, Genesis, and OM-HMM contracts; choose methods per wicked/undefined/ill-defined/well-defined problem framing.
- [x] Expose LATEST HSI whitespace interpretation through CLI/MCP, preserve MindrianOS framework IDs, and route Wicked separately to a feedback-loop question and framework chain.
- [x] Expose LATEST RS-seeded downstream whitespace over host-projected bottlenecks, target sections, and framework vectors.
- [ ] Wire the method-routing stage to authorized framework mappings from the MindrianOS local graph; the Eureka engine only accepts the host-supplied projection.
- Run selected methods only, preserve uncertainty and competing futures, and ask host to prepare the next instrument/evidence bundle.
- Exit: reproducible end-to-end workflow, host tests, measured value against current baseline.

## Dependencies and risks

- Phase 2 depends on MindrianOS graph schema and authorization access.
- Phase 3 depends on dated snapshots, labels, source lineage, and evaluators.
- Holon semantics depend on identifying current canonical ICM/DataRoom structures.
- Upstream source ownership/license remains unresolved for several engines.
- Graph-relations backtest failed to validate ranking quality; this is a gating risk.
