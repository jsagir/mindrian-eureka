# Using MindrianOS Eureka capabilities

MindrianOS is the user-facing host. It resolves the active room, scope, permissions, Theo guidance, and research approvals, then sends a bounded JSON bundle. Eureka never accepts a room directory path and never writes the MindrianOS portfolio.

## Pick a job by user need

MindrianOS should first classify the user's question as undefined (explore possible futures), ill-defined (find opportunity areas), or well-defined (test a solution against clear criteria). Theo can guide method choice; the user confirms the objective and scope. Then select only the supporting capability whose inputs are ready. See [the engine jobs guide](engine-jobs.md) for the full process and readiness.

| User-facing job | Capability | Use it when |
|---|---|---|
| Find technical bottlenecks and unusual connections | `opportunity.find_cross_domain_pairs` | A scoped, source-linked collection is ready and you want cross-field leads to explore. |
| Screen one collection for opportunity leads | `opportunity.synthesize_discovery_signals` | You want RS and HSI shortlists over the same local snapshot before choosing candidates for review. |
| Find similarities and surprising differences | `portfolio.find_hybrid_similarity_pairs` | A scoped collection is ready for a portfolio-relative pair scan. |
| Find mechanisms from other fields | `analogy.retrieve_mechanism_candidates` | You have a target problem and a source-linked mechanism corpus supplied by the host. |
| Compare a mechanism with the target problem | `analogy.assess_structural_fitness` | Both are represented in sourced relational layers and a local model is configured; use results as hypotheses to review. |
| Map a mechanism to a problem | `analogy.map_structure` | A source mechanism is selected and you want possible relational transfers made explicit for testing. |
| Turn confirmed fields into research tasks | `research.prepare_multidomain_plan` | The user or Theo has confirmed relevant fields and the host will run approved research. |
| Check claims for restatement or overlap | `analysis.compare_text_differences` | Descriptions may repeat existing claims and you need comparison leads for human inspection. |
| Challenge claims against evidence | `analysis.audit_claim_traceability` | A candidate needs its evidence, counterevidence, assumptions, and falsifiers checked for completeness. |
| Prepare a review of competing views | `deliberation.prepare_six_hat_review` | Source-linked arguments exist and the human needs open questions organized before deciding. |
| Validate and package proposed portfolio links | `graph.package_relationship_proposals` | Another process has proposed links and they need reference checks before human review. |

The packaged catalog (`eureka capabilities` or MCP `scout_capabilities`) is authoritative about prerequisites and maturity. `experimental`, `blocked`, and `planned` are materially different states.

## CLI

Install the package in the repo's locked environment, then pass a JSON file to the named stage:

```bash
eureka-scout input.json --output result.json
eureka-workflow portfolio.find_hybrid_similarity_pairs input.json --output result.json
eureka-workflow analysis.compare_text_differences input.json --output result.json
eureka-workflow analogy.assess_structural_fitness input.json --output result.json
eureka-workflow research.prepare_multidomain_plan input.json --output result.json
```

The CLI reads only the explicit input file and writes only the requested result path. For HSI, supply `dense_vectors` in the request or set `MINDRIAN_EUREKA_HSI_MODEL_PATH` to a local model. Jason accepts `MINDRIAN_EUREKA_JASON_MODEL_PATH`; without one, its text similarity field is explicitly a character n-gram proxy.

## MCP

- `scout_capabilities` lists maturity, JTBD, and requirements.
- `scout_capability(capability_id)` returns one job contract.
- `scout_start_opportunity_signal_scout(request)` runs the durable local RS+HSI signal job, with status/result/cancel via its returned `job_id`.
- `scout_run_workflow(capability_id, request)` runs one named local stage synchronously.
- `scout_find_hybrid_similarity_pairs(request)` and `scout_compare_text_differences(request)` are direct, typed MCP entry points.
- `scout_assess_analogy_fitness(request)` compares sourced SAPPhIRE-layer structures with the configured local encoder.
- `scout_start/status/result/cancel` provide durable job lifecycle for RS pair discovery and the RS+HSI signal scout; other supporting stages are synchronous.

External sources must be retrieved by MindrianOS's approved broker and returned with their source IDs/URLs, retrieval date, and claim locators. Research plans are not search results. None of the local stages approves a transfer, validates market demand, resolves licensing, or files a graph relationship.

## Example MindrianOS user journey

1. **Frame with Theo.** MindrianOS asks Theo for method guidance using the generic problem class, then confirms the user's decision, scope, and exclusions.
2. **Prepare a local snapshot.** The host exports only authorized records with stable IDs, text, titles, source references, and hashes. It does not send room paths.
3. **Scout selectively.** Start `scout_start_opportunity_signal_scout` for the local RS+HSI pair shortlist. If only one method is needed, call its specific capability instead. The shortlist preserves the original engine ranks; it does not merge them into an opportunity score.
4. **Choose a candidate for deeper work.** The user selects a pair. MindrianOS runs `/mos:find-connections` for prior-art and room-graph context and records any match or conflict.
5. **Broaden only when needed.** Ask Theo/Genesis for user-confirmed domains, run `research.prepare_multidomain_plan`, and obtain approval for exact outside queries. MindrianOS's broker performs those queries and returns source-linked claims.
6. **Test the transfer.** Retrieve source mechanisms with `analogy.retrieve_mechanism_candidates`, encode the selected source and target with claim provenance, then use `scout_sme_map` and `scout_sme_finalize` to test inferences against support, counterevidence, novelty, and boundary evidence.
7. **Challenge and decide.** Use Jason's text-difference diagnostic when restatement/overlap is a concern, or the Six-Hat review-preparation stage when evidence-backed positions disagree. Ask Theo to review only through an operation that accepts the authorized case context. The human decides whether to qualify, park, reject, or continue research.
8. **Accumulate the portfolio.** MindrianOS writes an approved candidate with its sources, unresolved questions, status, and relationships to the room opportunity bank. Eureka returns proposals and never writes to that bank itself.

The host skips irrelevant stages, stops on missing evidence or approval, and can keep multiple candidates in the portfolio. It should not force every pair through all methods.
