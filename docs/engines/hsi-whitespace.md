# Innovation-pair gap analysis

**User-facing capability:** Check Whether an Innovation Pair Sits in an Underexplored Area
**Hire when:** A pair scan has surfaced an unusual pair and MindrianOS can supply room and reference-framework vectors from the same snapshot; compare the pair’s surrounding concept coverage and return room-relative gaps for further investigation. This does not establish a literature or market gap.
**Interface:** `scout_run_workflow` with capability `portfolio.discover_hsi_whitespace`, or `eureka-workflow portfolio.discover_hsi_whitespace request.json`.

## What the user or MindrianOS supplies

Provide one snapshot of artifacts with stable IDs, source references and vectors; the HSI pairs from that same snapshot; and reference-framework vectors. Every vector must have the same dimension and must come from the same embedding model and preprocessing. Include the model name in `embedding_model`. The host owns embedding generation and baseline selection; this MCP does not read room paths or contact a model provider.

The method first chooses the supplied pairs using `hsi_ranking.method: "percentile"` when the upstream ranking is percentile-based, an explicit `threshold` when requested, or the legacy `hsi_score > 0.4` fallback. It averages each selected pair's vectors to estimate a connecting region, then compares the region's nearest-framework density with its room-artifact density after excluding the pair's two seed artifacts. With at least four room artifacts, it ranks both densities against per-artifact room reference distributions; smaller rooms use the source's fixed density cutoffs. It also carries the pair's lexical-similarity signal when supplied. A result is a hypothesis about what this room may not articulate, not a validated gap.

## What it does not claim

- Sparse in this room does not mean absent from research or the market.
- Similarity to a reference framework does not establish that the framework is relevant.
- HSI pair quality, embedding choice, baseline choice and small sample size can distort the result.
- External source gathering requires a separate approved MindrianOS research workflow; this capability performs none.
- No output is written to a room, graph, or opportunity bank.

Input contract: [`hsi-whitespace-input.v1.schema.json`](../../schemas/hsi-whitespace-input.v1.schema.json). It adapts LATEST `engines/hsi/scripts/discover-hsi-whitespace.py`; numeric pair selection, densities, percentiles, and nearest records match its source functions on a fixed fixture. Source authorship and redistribution rights remain under review. The host-bundle adaptation is experimental and does not access the MindrianOS graph directly.
