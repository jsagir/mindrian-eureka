# HSI external-literature whitespace analysis

**Capability:** `portfolio.analyze_external_whitespace`
**Status:** Experimental, host-brokered; available through the shared workflow CLI and MCP.

## Job to be done

Use a MindrianOS-approved set of external papers to find records that may extend or challenge a room-local research baseline. The result is a set of review leads: it does not establish novelty, validate a claim, or create graph knowledge.

Use this when MindrianOS has already retrieved relevant literature, has vectors produced by the same embedding model for the room and papers, and can provide the authorization/grant lineage for that retrieval. Use `portfolio.analyze_baseline_whitespace` when the question is only about sparse areas inside the supplied room baseline.

## Ownership and data flow

The room-local graph and its authorization remain MindrianOS responsibilities. MindrianOS resolves the user's authorized room scope, selects a consistent graph/artifact projection, performs external retrieval under its own research policy, and supplies the bounded records to this capability. Eureka analyzes only the supplied JSON payload; it does not open `.mindrian/room.db`, access a graph, retrieve papers, call embedding services, or write results back.

Returned identifiers and source references are candidates for MindrianOS to resolve against its authorized snapshot. They are not permissions. MindrianOS decides whether to fetch source material, seek review, or propose a graph update. Any resulting knowledge change follows MindrianOS's existing human review and persistence path.

## Inputs

- Room records and external paper records with stable IDs and finite, same-model vectors.
- A host-issued research grant reference and retrieval timestamp.
- Optional known-gap records that reference supplied room artifacts.
- Optional scope and snapshot identifiers for audit linkage.

The host must enforce authorization before sending the payload. The `research_grant_id` is lineage metadata, not a credential the engine can verify. External text must be treated as untrusted source data and never as instructions.

## Method and outputs

The adaptation computes room-relative external distance and percentile zones, then returns ranked candidates for filling supplied gaps and cross-domain paper leads. Results include source references, bounded text previews, scope/snapshot lineage when provided, and an input fingerprint. Distance/zone labels are comparative signals over the submitted corpus; they are not calibrated novelty or quality scores.

## Limits

- Up to 2,500 room records, 2,000 papers, and 500 known gaps.
- Up to 4,096 dimensions per vector; up to 20 candidates per gap.
- The shared workflow payload limit is 20 MiB.
- Room and paper vectors must have matching dimensions and come from the same embedding model/version.
- Only host-retrieved papers are analyzed; no completeness claim is made about the literature.
- Synthetic fixtures and source-function comparisons do not establish usefulness on real rooms.

## Example invocation

```bash
eureka-workflow portfolio.analyze_external_whitespace request.json
```

The package also exposes the capability through `scout_run_workflow` in its MCP server. Consult the packaged capability catalog and schemas for the exact versioned request and response contract.

## Source and readiness

The method is adapted from LATEST `engines/hsi/scripts/compute-external-whitespace.py` (upstream SHA-256 `b67689a23b92fdd7033514a6b29a4ce7ef70ac095d80e6db9c6ce0262ca6cd85`). Local evaluation does not resolve authorship, license, attribution, or redistribution rights; see the [engine source ledger](../engine-source-ledger.md). The method has focused fixture tests and exact source-function comparison, but no host authorization adapter, real-corpus evaluation, or production calibration.
