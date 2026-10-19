# Eureka opportunity statement draft

**Capability:** `opportunity.prepare_statement`
**Readiness:** Experimental, local evaluation only
**Job:** Turn a source-linked candidate pair into a structured opportunity hypothesis for Theo and human review.

## Inputs and method

This method follows the LATEST Eureka Opportunity Statement emitter. MindrianOS supplies two distinct graph candidates with titles, primary problems, sections, dimension values, and source references; one or more cited shared-problem descriptions; the previous portfolio-priority signal and its source reference; and an ordinal rank plus a separate rank reference. The request includes MindrianOS scope and snapshot IDs.

The method derives weak dimensions using the LATEST Eureka floor of 0.4, then builds a statement containing both sides' unmet needs, a candidate combination, the shared gap, generic audience, shared weaknesses, next validation steps, a source-defined potential tier, and the supplied rank. The source cleans line breaks and en/em dashes in embedded text. It returns the component fields as well as the rendered statement and echoes all source references.

## Critic and banking gate

The source builder has a critic seam. This CLI/MCP capability deliberately pins that seam to unavailable: it never invokes a judge and asserts that `critic` is `pending` and `banked` is `false` before returning. It cannot create a banked opportunity. MindrianOS runs its approved local review, presents the draft to Theo/the user, and controls any later state transition or graph write.

The `priority_signal` and `rank` are host supplied. The prior portfolio assessment provides the signal; MindrianOS supplies the rank and its provenance. This stage does not calculate or validate either one.

## Use and limits

Use this after a candidate pair has been selected and its dimension signals and rank have inspectable sources. It can make an uncertain opportunity hypothesis easier to challenge by stating assumptions, weak dimensions, and next tests explicitly.

The template's audience and terms are technology-transfer oriented. Theo should edit or reject that framing when it does not fit the room, domain, or intended users. A fluent statement is not evidence of a real need, causal mechanism, technical transfer, market, novelty, or opportunity. This is not the full Eureka harvest or qualification lifecycle.

MindrianOS owns local graph access, authorization, source resolution, human review, persistence, and all writes. The capability only processes the supplied JSON request. The source headers identify Mindrian BSL 1.1; distribution remains subject to rights review.

## CLI and MCP

CLI:

```bash
eureka-workflow opportunity.prepare_statement request.json
```

MCP uses `scout_run_workflow` with capability ID `opportunity.prepare_statement`. Both surfaces use the same schemas, method, and draft-only gate.
