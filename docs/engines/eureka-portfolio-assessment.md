# Eureka portfolio dimension assessment

**Capability:** `portfolio.assess_candidate_dimensions`
**Readiness:** Experimental, local evaluation only
**Engine job:** Inspect a candidate pair's distinct portfolio dimensions before human review.

## What it does

The capability applies the LATEST Eureka portfolio dimension map to two candidate nodes and the host-supplied comparable cohort. It computes strategic fit, cohort-relative demand, and technical-economic feasibility separately for each node, maps the supplied RS signal into a pair-feasibility value, identifies weak dimensions and complementarity, then combines the pair dimensions using the geometric-mean AHP weights from a caller-supplied 3×3 judgment matrix.

The matrix is rejected when its consistency ratio exceeds 0.1. The method never compares one candidate against another in the AHP matrix. The output contains a `portfolio_priority_signal` for this pair, separate dimension values, weights, consistency diagnostics, source references, the host scope/snapshot IDs, and an exact input fingerprint.

## When to hire it

Use it after MindrianOS has selected a source-linked RS pair and can provide comparable cohort fields (`primary_tier`, `pair_count`, and `degree`) from one authorized local-graph snapshot. Use the result to see which dimensions contribute to a candidate's portfolio signal and where validation work may be needed.

Do not use it to qualify an opportunity, claim market demand, determine truth, or write a graph relation. The component is a portfolio heuristic from the LATEST Eureka lifecycle; the full harvest, critic, calibration, and qualification workflow remains blocked.

## CLI and MCP

Both surfaces use the same `eureka-workflow` handler and packaged schemas. The MCP call is `scout_run_workflow` with capability ID `portfolio.assess_candidate_dimensions`. CLI example:

```bash
eureka-workflow portfolio.assess_candidate_dimensions request.json
```

The request needs `scope_id`, `snapshot_id`, cohort `items`, a `pair` containing endpoint IDs plus the supplied RS direction / absolute difference / pass flag and its source reference, and a reciprocal `criteria_matrix`. Each cohort item has a stable node ID, the three host-projected measurements, and source references. The schemas cap the cohort at 10,000 items; execution is local and makes no external call.

Example criteria order:

```json
[
  [1, 0.5, 0.25],
  [2, 1, 0.5],
  [4, 2, 1]
]
```

The required order is `strategic_fit`, `validated_demand`, `tech_econ_feasibility`.

## MindrianOS graph boundary

MindrianOS owns the graph and must prepare the authorized cohort and source references. Eureka reads only the supplied request. It does not access `.mindrian/room.db`, retrieve sources, verify the supplied RS result, or persist output. `scope_id` and `snapshot_id` bind lineage; they do not grant access. MindrianOS resolves the references, judges whether the cohort values are comparable, and decides whether any result merits follow-up.

## Method and limits

- `strategic_fit`: `1 / primary_tier`, with the source's below-tier-3 floor for missing/invalid tiers (request schema requires an explicit positive tier).
- `validated_demand`: the pair-count percentile within the supplied cohort.
- Node-level `tech_econ_feasibility`: degree percentile within the same cohort.
- Pair feasibility: the LATEST source's fixed piecewise map of the supplied RS direction, absolute difference, and pass state.
- Pair-level strategic fit is the larger endpoint value; pair demand is the endpoint mean.
- AHP uses the source's geometric-mean weighting and Saaty consistency ratio. It weights three criteria, not technologies.
- Complementarity is true only when both endpoints have nonempty, disjoint weak-dimension sets under the source floor.

These are heuristic signals, not validated probabilities. An internally consistent AHP matrix does not prove its judgments are correct. The historical Eureka ranking method has not been validated against human outcome labels, so this signal must not be used as an opportunity verdict or accepted graph knowledge. Source headers identify Mindrian BSL 1.1; distribution remains pending rights review.
