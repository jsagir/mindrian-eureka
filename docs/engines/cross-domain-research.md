# Cross-domain mechanism research and testing

## User job

**Hire “Research and Test Cross-Domain Reframes” when** a user has a clear room-level objective, familiar approaches are not producing useful options, and they want mechanisms from other fields discovered, structurally mapped, and checked against external evidence before deciding what enters the opportunity portfolio.

This is an experimental staged workflow, not a claim that analogy scores prove transfer. It is designed to return a small set of traceable, reviewable candidate inferences that can accumulate as a portfolio across room work.

## End-to-end path

1. **Frame locally.** MindrianOS/Theo preserves the objective, constraints, in-scope room artifact IDs, and exclusions. The host creates a minimal target description group and records which room claims support each expression. Raw room documents remain in the room unless the user approves specific excerpts for search.
2. **Prepare mechanism discovery.** `scout_sme_prepare_research` (or `eureka-sme plan`) freezes exact search strings, providers, rationales, local source references, and hashes. The capability itself has no network access.
3. **Approve and retrieve in MindrianOS.** The host shows the exact strings and obtains its normal research approval. In the current beta 70 host, `research_run` has a plan/grant/run_quick route; quick search is described as public scholarly-index research, while deep research runs in Claude Code from an approved plan. The local source registry includes OpenAlex, arXiv, PubMed, Tavily, and Tavily Extract paths. Provider route, content depth, and approval semantics differ. The quick `research_run` perspective recall is a local graph/ICM operation, not the external literature search itself. See the checked-in host files listed under [beta 70 integration notes](../integrations/mindrianos.md).
4. **Return a traceable discovery bundle.** The host adapts its research result to `external-research-bundle.v1`: one outcome per approved exact query, including valid zero-hit vs failure; every included source has URL/provider/retrieval status; every used claim has exact text, locator, and SHA-256. `scout_sme_validate_research_bundle` checks query/source lineage and excerpt hashes. It cannot prove that the grant was actually approved; the host must enforce that.
5. **Encode and map locally.** Theo or a model converts useful discovered mechanisms into SME description groups and associates each expression with claim IDs. The host supplies those encodings plus target evidence to `scout_sme_map`. The deterministic Python SME maps the relations and emits candidate inferences as unverified hypotheses. The score is only an ordering aid.
6. **Prepare a separate verification pass.** The user selects which candidate inferences to investigate now; remaining ones can stay parked in the accumulating opportunity portfolio. For each selected inference, the host prepares exact searches for support, counterevidence, novelty, and analogy boundary. `scout_sme_prepare_research` binds this plan and its selected inference IDs to the mapping result ID. The user approves this second set of queries independently; approval for discovery is not reused.
7. **Review and decide.** MindrianOS returns the approved verification bundle. Theo/model or a human supplies a cited assessment for every inference. `scout_sme_finalize` checks citations and check coverage. MindrianOS then lets the user deepen, accept, park, or reject each opportunity and records the decision and rationale. Only MindrianOS writes to the room or opportunity portfolio.

The path can branch: a discovery search with no usable results can be revised; a strong source can be mapped before the batch completes; a candidate can be rejected without the verification pass; and a verified mechanism can be reused later only with its original room, source, date, and scope context attached.

## Components and boundaries

| Component | Owns | Does not own |
|---|---|---|
| MindrianOS room and Theo/framework layer | User objective, room scope, approval UX, research-provider calls, reviewer orchestration, persistence, portfolio decisions | None of the local SME algorithm internals |
| Eureka Scout host adapter (required integration work) | Translate MindrianOS research envelopes to/from these schemas; invoke local MCP/CLI; preserve stage/run lineage | Grant authority or unsupervised filing |
| Local Eureka SME worker | Exact-query canonicalization, bundle lineage checks, deterministic mapping, assessment record assembly | Network, model-provider calls, approval validation, room reads/writes |
| Research providers | External retrieval according to the enabled route | Room interpretation or opportunity acceptance |

This repository now contains the local engine workflow and transport contracts. It does **not** yet contain a beta 70 plugin adapter that calls `research_run`, converts its evidence cards to this bundle schema, or persists room/portfolio outcomes. That adapter is a required next integration deliverable; without it, this is end-to-end within the standalone repo only when a host/operator supplies the approved bundles and assessments.

## Beta 70 fit and constraints

The inspected MindrianOS beta 70 source is `/home/jsagi/dev/MindrianOS-Plugin` at version `2.0.0-beta.70`. `lib/mcp/tools/research.cjs` describes `research_run` operations for planning, grant request/status/revoke, quick runs, deep plans, review, and filing. Its quick-run description restricts searches to approved public scholarly-index terms. `lib/core/research-corpus.cjs` registers academic and web retrieval adapters, but their presence does not mean every `research_run` mode can invoke every adapter. Tavily Extract retrieves a URL's content; WebFetch is documented as a Claude-orchestrated fallback in `commands/research.md`. The host integration must choose a route that can produce the required claim-level bundle rather than infer uniform access from the registry.

## Operational usage

Install the package and optional local MCP dependencies in an isolated runtime. `eureka-sme` supports:

```text
eureka-sme plan request.json
eureka-sme validate-bundle discovery-plan.json approved-discovery-bundle.json
eureka-sme map mapping-input.json
eureka-sme validate-bundle verification-plan.json approved-verification-bundle.json
eureka-sme finalize mapping-result.json verification-plan.json approved-verification-bundle.json assessments.json
```

`assessments.json` follows `schemas/sme-assessments.v1.schema.json`. Each assessment must cite one or more claims in the verification bundle when marked supported or contradicted; an untested inference needs a concrete falsifier.

The same stages are exposed as MCP tools: `scout_sme_prepare_research`, `scout_sme_validate_research_bundle`, `scout_sme_map`, and `scout_sme_finalize`. The verification plan must include all four check intents for every inference ID. Host approval is always separate and external to these calls.

## Evidence and maturity

- **Observed in this repo:** deterministic standard-library SME module, ranking reference, plan hashing, exact-query/source lineage validation, local mapping entry point, CLI and MCP stage calls.
- **Observed in beta 70 source:** the `research_run` tool and its distinct quick/deep operations; academic and web source adapters in the corpus module; separate Tavily Extract and documented WebFetch fallback paths.
- **Not yet implemented:** beta 70 adapter, schema conversion from actual research results to claim records, Theo orchestration, persistent portfolio/feedback integration, and production evaluation.
- **Requires verification:** SME source fidelity against the shared PPTX/source archive, ownership/license status, algorithm edge cases, and evidence assessment quality. The two imported SME files are marked unresolved in `engine-source-ledger.md` and must not be distributed pending clearance.

## First user-facing experiment

Use one non-sensitive room snapshot with a bounded objective. Theo creates a target description and six diverse mechanism queries. The user reviews/approves those exact strings. The host supplies claim-linked results, local SME maps the best sourced mechanisms, and Theo drafts four verification queries per selected inference. The user approves that second batch and reviews the final source-linked assessments. Track: time from request to first reviewable candidate; percentage of candidates with complete source lineage; reviewer time per inference; and user's count of candidates worth keeping. Stop if source lineage is lost, query disclosure is broader than approved, or a candidate is presented as established fact without citations.
