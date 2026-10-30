# Eureka graph-event opportunity harvest

**Capability:** `opportunity.harvest_graph_events`
**Readiness:** Experimental, local evaluation only
**Job:** Surface connected graph events that deserve an evidence-led opportunity investigation.

## What the source method does

The LATEST Eureka harvest scans five event lanes in a graph: bridges, whitespace zones, contradictions, candidate opportunity nodes, and meeting filings. It keeps only events with at least one typed connection (Q2), excludes high-degree bridge hubs, deduplicates already rejected/banked candidates where host state is available, classifies a Gibson Four-Lens label, applies the source Q1–Q8 rubric, and returns a candidate score/band plus a component bag and `HarvestIndex_v1`.

The Q1/Q3/Q4/Q5/Q6/Q7/Q8 values and the HarvestIndex weights are source-defined heuristics. In particular, timing, actor fit, and desirability use fixed defaults; they are not measured facts. `HarvestIndex_v1` is explicitly advisory and experimental. An `unknown` component remains unknown rather than becoming zero. These candidate scores are not probabilities or opportunity qualification.

## MindrianOS projection contract

MindrianOS owns the local graph and supplies a **complete projection of the authorized scope** with zero omitted nodes or edges. The projection includes stable node IDs, node types, the small property whitelist defined in the input schema, and all relevant typed edges. It also supplies a complete current opportunity-bank name list for Q7 deduplication and may supply prior portfolio-dimension rows for D-18 components.

Incomplete projections, missing bank dedup state, duplicate IDs/edges, and dangling endpoints are rejected. The engine does not open `room.db`, resolve source files, read prior reports, write the legacy side channel, or mutate graph state. Results contain stable handles, enums, and numeric signals; they omit node names, titles, and hypothesis text. MindrianOS resolves evidence and presents candidates to Theo/humans through its existing review path.

The completeness requirement is scoped to the authorized projection, not permission to expose the whole room. `scope_id` and `snapshot_id` bind lineage; they are not authorization tokens.

## CLI and MCP

CLI:

```bash
eureka-workflow opportunity.harvest_graph_events request.json
```

MCP uses `scout_run_workflow` with capability ID `opportunity.harvest_graph_events`. Both use the same request/result schemas and source method. Limits: 10,000 nodes, 50,000 edges, 10,000 portfolio rows, and 100,000 bank names.

## Limitations and handoff

- Candidate generation does not verify evidence, causality, novelty, desirability, or real-world demand.
- A high or low band is method-relative and uncalibrated. Historical ranking evidence elsewhere in this repo failed to beat its baseline.
- Results are candidate handles only. A selected pair can be passed to dimension assessment and then to statement drafting, but those later steps remain distinct and require host-supplied evidence/rank.
- Only MindrianOS can approve, persist, or write graph relationships. The full harvest-to-critic-to-human qualification lifecycle is not implemented by this capability.
- LATEST source headers identify Mindrian BSL 1.1; distribution remains subject to rights review.
