# Cross-domain mechanism research and testing

## User job

**Hire “Research and Test Cross-Domain Reframes” when** a user has a clear room-level objective, familiar approaches are not producing useful options, and they want mechanisms from other fields discovered, structurally mapped, and checked against external evidence before deciding what enters the opportunity portfolio.

This is an experimental staged workflow, not a claim that analogy scores prove transfer. It is designed to return a small set of traceable, reviewable candidate inferences that can accumulate as a portfolio across room work.

## End-to-end path

1. **Frame locally.** MindrianOS/Theo preserves the objective, constraints, in-scope room artifact IDs, and exclusions. The host creates a minimal target description group and records which room claims support each expression. Raw room documents remain in the room unless the user approves specific excerpts for search.
2. **Prepare mechanism discovery.** `scout_sme_prepare_research` (or `eureka-structure-mapping plan`) freezes exact search strings, providers, rationales, local source references, and hashes. The capability itself has no network access.
3. **Approve and retrieve in MindrianOS.** The host shows the exact strings and obtains its normal research approval. The plugin's research planner provides its own plan/grant/run routes; available providers and approval semantics depend on the selected host route. The quick `research_run` perspective recall is a local graph/ICM operation, not the external literature search itself. This host research loop is separate from catalogued Eureka capabilities, which can be invoked independently.
4. **Return a traceable discovery bundle.** The host adapts its research result to `external-research-bundle.v1`: one outcome per approved exact query, including valid zero-hit vs failure; every included source has URL/provider/retrieval status; every used claim has exact text, locator, and SHA-256. `scout_sme_validate_research_bundle` checks query/source lineage and excerpt hashes. It cannot prove that the grant was actually approved; the host must enforce that.
5. **Encode and map locally.** Theo or a model converts useful discovered mechanisms into SME description groups and associates each expression with claim IDs. The host supplies those encodings plus target evidence to `scout_sme_map`. The deterministic Python SME maps the relations and emits candidate inferences as unverified hypotheses. The score is only an ordering aid.
6. **Prepare a separate verification pass.** The user selects which candidate inferences to investigate now; remaining ones can stay parked in the accumulating opportunity portfolio. For each selected inference, the host prepares exact searches for support, counterevidence, novelty, and analogy boundary. `scout_sme_prepare_research` binds this plan and its selected inference IDs to the mapping result ID. The user approves this second set of queries independently; approval for discovery is not reused.
7. **Review and decide.** MindrianOS returns the approved verification bundle. Theo/model or a human supplies a cited assessment for every inference. `scout_sme_finalize` checks citations and check coverage. MindrianOS then lets the user deepen, accept, park, or reject each opportunity and records the decision and rationale. Only MindrianOS writes to the room or opportunity portfolio.

The path can branch: a discovery search with no usable results can be revised; a strong source can be mapped before the batch completes; a candidate can be rejected without the verification pass; and a verified mechanism can be reused later only with its original room, source, date, and scope context attached.

## Components and boundaries

| Component | Owns | Does not own |
|---|---|---|
| MindrianOS room and Theo/framework layer | User objective, room scope, approval UX, research-provider calls, reviewer orchestration, persistence, portfolio decisions | None of the local SME algorithm internals |
| Optional MindrianOS composition | When a host chooses to combine this staged research process with Eureka capability calls, translate authorized evidence envelopes, invoke the relevant MCP/CLI stages, and preserve stage/run lineage | Grant authority or unsupervised filing; mandatory coupling between Theo and Eureka |
| Local Eureka SME worker | Exact-query canonicalization, bundle lineage checks, deterministic mapping, assessment record assembly | Network, model-provider calls, approval validation, room reads/writes |
| Research providers | External retrieval according to the enabled route | Room interpretation or opportunity acceptance |

This repository contains the local engine workflow and transport contracts. The MindrianOS adapter review worktree now exposes authorized graph projection and catalog dispatch, but it does not compose this entire multi-stage research workflow with `research_run` or persist its outcomes. That composition remains optional follow-up work; the CLI/MCP capabilities can be used independently with caller-prepared bundles and assessments.

## Beta 70 fit and constraints

The MindrianOS adapter review worktree is based on the beta.72 plugin checkout. Its graph-projection adapters call Eureka independently of the existing `/mos:eureka` research-planner flow. A future composition of the two must choose a host research route that produces the required claim-level bundle; capability registration alone does not establish provider availability, grant approval, or persistence behavior.

## Operational usage

Install the package and optional local MCP dependencies in an isolated runtime. `eureka-structure-mapping` supports (`eureka-sme` remains a compatibility alias):

```text
eureka-structure-mapping plan request.json
eureka-structure-mapping validate-bundle discovery-plan.json approved-discovery-bundle.json
eureka-structure-mapping map mapping-input.json
eureka-structure-mapping validate-bundle verification-plan.json approved-verification-bundle.json
eureka-structure-mapping finalize mapping-result.json verification-plan.json approved-verification-bundle.json assessments.json
```

Inspect the exact current request and result contracts before preparing the mapping JSON:

```text
eureka schema analogy.map_structure
```

The mapping contract requires a `document` with `run_id`, `scope_id`, target expression group and claim references, an evidence catalog, and one or more source mechanism bases with their own expression-to-claim references. The CLI and `scout_sme_map` MCP route validate the same typed contract and return the same result schema. An expression without an evidence claim reference is rejected; a returned candidate inference remains a hypothesis.

`assessments.json` follows `schemas/sme-assessments.v1.schema.json`. Each assessment must cite one or more claims in the verification bundle when marked supported or contradicted; an untested inference needs a concrete falsifier.

The same stages are exposed as MCP tools: `scout_sme_prepare_research`, `scout_sme_validate_research_bundle`, `scout_sme_map`, and `scout_sme_finalize`. The verification plan must include all four check intents for every inference ID. Host approval is always separate and external to these calls.

## Evidence and maturity

- **Observed in this repo:** deterministic standard-library SME module, ranking reference, plan hashing, exact-query/source lineage validation, local mapping entry point, CLI and MCP stage calls.
- **Observed in MindrianOS adapter review:** graph projection to local Eureka MCP calls, typed lineage-bound results, catalog dispatch, and separate start/status/result/cancel jobs.
- **Not yet implemented:** a combined `research_run` → claim-level bundle → SME map/verification → portfolio-write orchestration, plus production evaluation. The lack of that composition does not block independent engine calls.
- **Requires verification:** SME source fidelity against the shared PPTX/source archive, ownership/license status, algorithm edge cases, and evidence assessment quality. The two imported SME files are marked unresolved in `engine-source-ledger.md` and must not be distributed pending clearance.

## First user-facing experiment

Use one non-sensitive room snapshot with a bounded objective. Theo creates a target description and six diverse mechanism queries. The user reviews/approves those exact strings. The host supplies claim-linked results, local SME maps the best sourced mechanisms, and Theo drafts four verification queries per selected inference. The user approves that second batch and reviews the final source-linked assessments. Track: time from request to first reviewable candidate; percentage of candidates with complete source lineage; reviewer time per inference; and user's count of candidates worth keeping. Stop if source lineage is lost, query disclosure is broader than approved, or a candidate is presented as established fact without citations.
