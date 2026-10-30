# HSI whitespace interpretation

**Capability:** `portfolio.interpret_whitespace`
**Status:** Experimental. Available through `eureka-workflow` and MCP when MindrianOS supplies an authorized graph projection.

## Job to be done

After the HSI whitespace stage identifies candidate gaps, use this method to connect each gap to the problem type of its nearest mapped framework and select a short `FEEDS_INTO` framework chain for Theo's next investigation.

This distinction is central to MindrianOS opportunity discovery:

- **Un-Defined:** open an unexplored territory with a generative question.
- **Ill-Defined:** explore what might be next in a field or market; the result is an opportunity set, not a directly solvable specification.
- **Well-Defined:** use falsifiable criteria to frame a problem that can be solved and evaluated.
- **Wicked:** investigate interacting systems, feedback loops, stakeholders, and unintended consequences. Do not collapse this category into generic uncertainty.

The method does not infer a type from raw question text. It inherits the type from a MindrianOS framework mapping, preserving that provenance. If a relevant mapping is missing, it returns `Un-Defined` with zero confidence and the fallback exploration chain.

## Graph and runtime boundary

MindrianOS owns the room-local graph, authorization, and canonical framework relations. It supplies the HSI gaps, projection coordinates, `ADDRESSES_PROBLEM_TYPE` mappings, and `FEEDS_INTO` edges as bounded input. Include stable framework IDs as well as display names; results return both chain labels and resolvable framework IDs. Eureka does not query the graph, read `.mindrian/room.db`, write interpretation results, retrieve research, or call a model. Outputs preserve host `scope_id` and `snapshot_id`; they are proposals for Theo's workflow, not graph mutations.

The source interpretation stage's Brain reads and room-file writes were removed from this adapter. The source anchor and framework-consensus gates are retained over host-supplied records. `offline_validate` can accept anchor-only results when no framework mapping is supplied; the response records that basis explicitly. The capability does not need a second brokered research or judge call once the host has prepared the projection.

## Output

Each zone receives a problem type, mapping confidence, voting framework, selected framework chain, anchor/consensus gate results, and a type-specific next question. Validated zones can be returned as hypothesis candidates, prioritized by the source's gap-percentile ordering. Those candidates do not contain generated hypotheses and do not assert that a gap is an opportunity.

The `Wicked` route asks Theo to inspect unexamined feedback loops and unintended consequences. Its availability depends on MindrianOS's framework graph containing a relevant Wicked mapping.

## Limits

- Up to 500 gaps, 5,000 edges per relation family, 2,500 projection points, and 50 returned candidates.
- The 2D anchor gate is a heuristic; it does not demonstrate that a gap is useful or actionable.
- Effectiveness defaults to the source's host-query fallback of `1.0` when omitted; the response marks the mapping source. Prefer supplying the graph's measured value when available.
- Semantic coherence checking is deferred; no embeddings or LLM are used here.
- MindrianOS remains responsible for authorization, evidence resolution, Theo orchestration, human review, and graph writes.

## Example

```bash
eureka-workflow portfolio.interpret_whitespace request.json
```

For exact request/result contracts, use `eureka schema portfolio.interpret_whitespace` or the MCP `scout_capability_contract` tool.

## Source and readiness

Adapted from LATEST `engines/hsi/scripts/interpret-whitespace.cjs` (upstream SHA-256 `f0c5a71678f57c53d9c0821b98f382bbbacdb48c74578e932bce389ee4432d7b`). The file-based room IO and direct Brain queries were replaced by host-supplied JSON. Authorship and distribution rights remain unresolved; see the [engine source ledger](../engine-source-ledger.md). Local tests verify the Wicked mapping route, fallback, gates, source chain selection, CLI/MCP parity, and schemas. Host graph mapping quality and real-room usefulness remain untested.
