# Baseline whitespace analysis

**Capability:** `portfolio.analyze_baseline_whitespace`
**Hire when:** MindrianOS can provide an authorized artifact projection, vectors generated with a named shared embedding model, and source-linked Brain or domain baseline frameworks. Use it to identify baseline concepts that are comparatively underrepresented in the current room.
**Interfaces:** `eureka-workflow portfolio.analyze_baseline_whitespace request.json` and MCP `scout_run_workflow`.

## What MindrianOS supplies

The request includes the room artifacts, source references, optional artifact text for lexical coverage, each artifact's vector, baseline framework records and vectors, `embedding_model`, and the graph `scope_id`/`snapshot_id`. All vectors must use the same model and preprocessing. MindrianOS authorizes and projects the local graph; this engine does not open the room database or resolve source references.

## Method

The adapted LATEST HSI hybrid gap detector uses its deterministic PCA fallback and scores each baseline framework using relative KDE sparsity, k-nearest-neighbor distance, dense cosine distance, and lexical coverage when artifact text is supplied. It returns the most sparse frameworks with nearest artifact references, signal percentiles, and an input fingerprint. The selection threshold and resource bounds are explicit in the capability schema.

## Interpretation limits

- This measures sparsity relative to the supplied room projection and baseline corpus. It does not establish that the idea is novel, missing from external research, demanded by a market, or worth pursuing.
- The source's UMAP path is not run. The deterministic PCA fallback is recorded in the result.
- Baseline selection, vector model, corpus size, and text quality can change rankings. Validate against human-rated cases before raising readiness.
- MindrianOS resolves evidence and owns review, persistence, and all graph writes.
- Upstream source reuse rights remain under review.

Input contract: [`hsi-baseline-whitespace-input.v1.json`](../../src/mindrian_eureka/data/schemas/hsi-baseline-whitespace-input.v1.json). Result contract: [`hsi-baseline-whitespace-output.v1.json`](../../src/mindrian_eureka/data/schemas/hsi-baseline-whitespace-output.v1.json).
