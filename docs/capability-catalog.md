# Capability catalog

The catalog exposes user jobs, not package folder names. These methods serve an intelligence system built to explore uncertainty—especially wicked challenges—for opportunity. Capability calls are instruments in that exploration; none should force one problem frame or imply that a complex challenge has been solved. Each capability must have a manifest, input/output schema, runtime declaration, network/data classification, known limitations, provenance, and an evaluation plan before it is enabled. See [Engine jobs and when to use them](engine-jobs.md) for the method context, plain-language descriptions, and family-level readiness.

| Capability ID | User-facing name | Hire when | Initial status |
|---|---|---|---|
| `bottleneck.diagnose` | Find the Bottleneck | Progress is stalled and the limiting subsystem is unclear. | Planned as a host-owned job; not implemented in this repository. |
| `opportunity.find_cross_domain_pairs` | Find Cross-Domain Opportunity Pairs | The user has a scoped local collection and wants items whose structural and semantic similarity signals disagree, as leads for human investigation. | First implementation target; faithful RS baseline plus explicitly versioned modern encoder variant. |
| `opportunity.synthesize_discovery_signals` | Run the Local Opportunity Signal Scout | A catalog is ready and the user wants RS and HSI pair signals over one local snapshot. | Experimental durable job; shortlist union only, no fused score or opportunity verdict. |
| `opportunity.discover_breakthroughs` | Find and Challenge Breakthrough Leads | The user wants a room or portfolio explored for promising changes, with candidate evidence and assumptions made reviewable. | Blocked: Eureka source routines have not yet been migrated and evaluated as this user-facing job. |
| `portfolio.find_coverage_gaps` | Find Portfolio Coverage Gaps | The user wants to know which themes, populations, mechanisms, or evidence areas are thinly represented in a normalized portfolio. | Blocked: HSI runtime, domain taxonomy, and ranking validity require review. |
| `analogy.find_mechanisms` | Find Mechanisms from Other Fields | Current approaches are stuck or narrow and the user wants structurally relevant mechanisms from elsewhere. | Blocked pending verification of local recall and a host-approved external research path. |
| `analogy.map_structure` | Test a Structural Analogy | The user selected a source mechanism and wants to test whether its relationships map to the target problem. | Experimental; mapping/inference is not evidence validation. |
| `analogy.cross_domain_research` | Research and Test Cross-Domain Reframes | The user has a clearly framed problem and wants to discover source mechanisms, map them locally, then check each generated inference against external support and counterevidence. | Experimental end-to-end workflow; MindrianOS must broker both research passes and a reviewer must assess the evidence. |
| `claims.compare` | Compare Competing Explanations | Two explicit claims or plans need a structured comparison. | Planned; not implemented in this repository. |
| `deliberation.structure` | Structure a Governed Debate | A bounded decision has credible competing interpretations and needs arguments and disagreements made reviewable before a human ruling. | Blocked: BONO package is not yet reviewed or verified. |
| `evidence.fetch_for_question` | Gather Evidence for a Question | A specific candidate or bottleneck needs outside evidence. | Blocked until shared egress broker is verified. |
| `research.orchestrate_multidomain` | Plan Multi-Domain Research | The user has a scoped question that needs coordinated research across disciplines, with source-linked findings and explicit disagreement. | Planned: Genesis currently supports a research-planning role; verified execution, evidence-grounded domain selection, and ICM handoff are not shipped here. |
| `analysis.critique_pitch` | Challenge a Pitch or Proposed Solution | The user wants a source-traceable critique of a pitch, transcript, or solution and wants falsifiable next questions. | Blocked pending migration and verification of Jason's analysis module and its graph/research dependencies. |
| `experts.find_for_topic` | Find Relevant Experts | Evidence has produced relevant authors/experts that can be resolved against an authorized source. | Blocked pending transport/privacy verification. |
| `thesis.read_prior` | Read a Prior Bottleneck Thesis | The user needs to revisit a saved RS thesis. | Readback only. |
| `decision.compare_sequence_patterns` | OMM Decision-Sequence Pattern Explorer | The user has explicitly coded decision traces and competing HMM hypotheses, and wants relative fit and step-level state probabilities for research. | Experimental; this is not an opportunity finder or person score. |
| `graph.propose_relationships` | Propose Portfolio Relationships | The user wants explainable candidate links or pathways from an approved graph snapshot, before a human reviews any filing. | Blocked: read-only package exists, but ranking and backtest are not validated and no graph write is enabled. |

The machine-readable version of this catalog is packaged at `src/mindrian_eureka/data/capability-catalog.v1.json` and is served through the top-level `eureka` CLI and `scout_capabilities`. A catalog entry can be blocked or planned; it does not imply that a corresponding runnable engine is present.



## Runnable supporting stages added

These are narrow workflow components. The machine-readable catalog is authoritative for schemas and limitations. Their presence does not mean the legacy engine's full end-to-end behavior has been migrated.

| Capability ID | User-facing name | Hire when | Readiness |
|---|---|---|---|
| `opportunity.synthesize_discovery_signals` | Run the Local Opportunity Signal Scout | The user wants RS and HSI pair leads from the same local snapshot. | Experimental durable job; source-linked shortlist union, no score fusion or qualification. |
| `portfolio.find_hybrid_similarity_pairs` | Find Hybrid-Similarity Pair Leads | A scoped collection needs a local lexical/semantic differential-pair scan. | Experimental HSI scoring. |
| `portfolio.discover_hsi_whitespace` | Find HSI-Seeded Room Whitespace | HSI surfaced a surprising pair and the user wants to check whether the connecting region is sparse in this room relative to supplied reference frameworks. | Experimental host-bundle adaptation; room-relative only. See [HSI whitespace](engines/hsi-whitespace.md). |
| `portfolio.inventory_taxonomy_coverage` | Inventory Portfolio Taxonomy Coverage | A taxonomy has already been supplied and the user wants to see which categories are represented or thin. | Counts only; no demand/market claim. |
| `analogy.retrieve_mechanism_candidates` | Retrieve Candidate Mechanisms | A source-linked mechanism corpus is available for recall before SME mapping. | Lexical recall; no structural-fit score. |
| `analogy.assess_structural_fitness` | Assess a Selected Structural Analogy | The user has source-linked source/target SAPPhIRE structures and needs to prioritize mappings for SME review. | Experimental local embedding fit; not evidence adjudication. |
| `research.prepare_multidomain_plan` | Prepare a Multi-Domain Research Plan | Theo/user confirmed the domains and needs bounded research questions. | Planning only; host broker executes searches. |
| `research.group_multidomain_findings` | Group Multi-Domain Findings | Host supplied source-linked findings and needs exact claim repeats/disagreements grouped. | Exact normalized claim grouping, not verification or consensus. |
| `analysis.compare_text_differences` | Compare Text Claims and Detect Restatements | The user needs descriptive text comparison and paraphrase/restatement leads. | Jason v3.1 descriptive analysis; not an innovation score. |
| `analysis.audit_claim_traceability` | Audit Claim and Evidence Coverage | A proposal's claim/evidence/counterevidence/falsifier links need a completeness pass. | Completeness audit; not Jason's original critique flow. |
| `deliberation.prepare_six_hat_review` | Prepare a Six-Hat Decision Review | Source-linked perspectives need organization before a human ruling. | Preparation only; BONO fan-out/debate remains blocked. |
| `graph.package_relationship_proposals` | Package Evidence-Linked Relationship Proposals | Candidate links need reference validation and a human-review envelope. | Packaging only; no discovery/ranking/write. |
| `discovery.plan_opportunity_scout` | Plan an Opportunity-Discovery Run | The user wants a selective, dependency-aware method sequence. | Planning only; it does not run every engine. |
