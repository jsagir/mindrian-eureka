# HSI-seeded room whitespace

**User-facing capability:** Find HSI-Seeded Room Whitespace  
**Hire when:** HSI has surfaced an unusual pair and you want to locate the embedding region between them, then see whether that region is sparse in this room relative to supplied reference frameworks.  
**Interface:** `scout_run_workflow` with capability `portfolio.discover_hsi_whitespace`, or `eureka-workflow portfolio.discover_hsi_whitespace request.json`.

## What the user or MindrianOS supplies

Provide one snapshot of artifacts with stable IDs, source references and vectors; the HSI pairs from that same snapshot; and reference-framework vectors. Every vector must have the same dimension and must come from the same embedding model and preprocessing. Include the model name in `embedding_model`. The host owns embedding generation and baseline selection; this MCP does not read room paths or contact a model provider.

The method averages each pair's vectors to estimate a connecting region, then compares the region's nearest-framework density with its room-artifact density after excluding the pair's two seed artifacts. It ranks the resulting density signals against distributions computed from the supplied room vectors. A result is a hypothesis about what this room may not articulate, not a validated gap.

## What it does not claim

- Sparse in this room does not mean absent from research or the market.
- Similarity to a reference framework does not establish that the framework is relevant.
- HSI pair quality, embedding choice, baseline choice and small sample size can distort the result.
- External source gathering requires a separate approved MindrianOS research workflow; this capability performs none.
- No output is written to a room, graph, or opportunity bank.

Input contract: [`hsi-whitespace-input.v1.schema.json`](../../schemas/hsi-whitespace-input.v1.schema.json). The original HSI implementation and its redistribution rights remain under review; this is an independently integrated, host-bundle adaptation for local evaluation.
