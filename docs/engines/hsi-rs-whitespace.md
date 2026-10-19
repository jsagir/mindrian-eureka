# RS-seeded downstream whitespace

**Capability:** `portfolio.discover_rs_whitespace`
**Status:** Experimental; callable through `eureka-workflow` and MCP over host-supplied data.

## Job to be done

After MindrianOS has identified a reverse salient or bottleneck, inspect the section it affects for concepts underrepresented in the supplied framework baseline. Return downstream whitespace leads so Theo can investigate what the bottleneck may be preventing the team from seeing.

Use `portfolio.discover_hsi_whitespace` for the region between a surprising HSI pair. Use `portfolio.discover_rs_whitespace` when an RS result identifies a source section and a downstream target section. The methods answer different questions and should not be collapsed into one generic gap score.

## MindrianOS graph boundary

MindrianOS supplies the authorized bottleneck records, target-section artifacts, source references, same-model vectors, and framework baseline vectors. The engine does not read `.mindrian/room.db`, search the graph, read room paths, generate embeddings, retrieve literature, or write graph state. It preserves `scope_id`, `snapshot_id`, artifact IDs, reverse-salient IDs, and baseline IDs so MindrianOS can resolve every lead against its canonical graph and evidence.

The source script read local room files and Brain data. This adaptation replaces those reads with a bounded JSON contract and accepts artifact text explicitly from the host for its lexical second signal. Do not provide room paths or unrestricted graph properties.

## Method

For each unique target section, the engine:

1. Computes that section's embedding centroid and finds the three nearest supplied framework vectors.
2. Measures framework coverage as the mean best cosine match from a section artifact to each selected framework.
3. Compares coverage with all supplied artifact sections. With at least four sections, it uses the source percentile rule; with fewer sections or `signal_method: fixed`, it uses the source fixed cutoffs.
4. Checks whether the supplied section text uses the nearest framework name's vocabulary.
5. Returns a source-linked hypothesis and the reverse-salient/target-section relationship.

These are relative signals. They do not validate the bottleneck or establish opportunity, demand, or literature novelty.

## Limits

- Up to 2,500 artifacts, 1,000 frameworks, and 500 reverse salients.
- Vectors must share a model, preprocessing, and dimensionality (up to 4,096 dimensions).
- MCP/workflow request payloads are limited to 20 MiB.
- One output zone is emitted per unique target section represented in the artifact bundle.
- MindrianOS retains authorization, source resolution, Theo review, human qualification, and any graph write.

## Example

```bash
eureka-workflow portfolio.discover_rs_whitespace request.json
```

The same capability is available through MCP `scout_run_workflow`. Retrieve the exact schemas with `eureka schema portfolio.discover_rs_whitespace` or `scout_capability_contract`.

## Source and readiness

Adapted from LATEST `engines/hsi/scripts/discover-rs-whitespace.py` (SHA-256 `e36e81c4ed9ffdc42bb26f6339a1658632bbdf63bdae4f9e20fc4752ab05ab22`). Local source-function comparisons match framework coverage, percentile, and signal class on a fixed four-section fixture. Authorship/redistribution rights and real-room value remain unverified; see the [engine source ledger](../engine-source-ledger.md).
