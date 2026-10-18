# Capability catalog

The catalog exposes user jobs, not package folder names. Each capability must have a manifest, input/output schema, runtime declaration, network/data classification, known limitations, provenance, and an evaluation plan before it is enabled.

| Capability ID | User-facing name | Hire when | Initial status |
|---|---|---|---|
| `bottleneck.diagnose` | Find the Bottleneck | Progress is stalled and the limiting subsystem is unclear. | Existing MindrianOS route; behavior equivalence audit required. |
| `coverage.find_gaps` | Find Portfolio Gaps | The user needs to find thinly covered themes or evidence areas. | Experimental. |
| `opportunity.find_pairs` | Find Breakthrough Pairs | The user has a collection of items and wants a bounded candidate shortlist of potentially valuable pairings. | Current MindrianOS perspective is baseline; legacy implementation is not presumed equivalent. |
| `opportunity.find_cross_domain_pairs` | Find Cross-Domain Opportunity Pairs | The user has a scoped local collection and wants items whose structural and semantic similarity signals disagree, as leads for human investigation. | First implementation target; faithful RS baseline plus explicitly versioned modern encoder variant. |
| `analogy.find_mechanisms` | Find Mechanisms from Other Fields | Current approaches are stuck or narrow and the user wants structurally relevant mechanisms from elsewhere. | Experimental; separate local recall and external retrieval. |
| `analogy.map_structure` | Test a Structural Analogy | The user selected a source mechanism and wants to test whether its relationships map to the target problem. | Prototype; mapping/inference is not evidence validation. |
| `claims.compare` | Compare Competing Explanations | Two explicit claims or plans need a structured comparison. | Experimental. |
| `deliberation.structure` | Structure a Decision Debate | A bounded what-if needs multiple perspectives and a human ruling. | Use existing governed MindrianOS BONO route initially. |
| `evidence.fetch_for_question` | Gather Evidence for a Question | A specific candidate or bottleneck needs outside evidence. | Disabled until shared egress broker is verified. |
| `experts.find_for_topic` | Find Relevant Experts | Evidence has produced relevant authors/experts that can be resolved against an authorized source. | Blocked pending transport/privacy verification. |
| `thesis.read_prior` | Read a Prior Bottleneck Thesis | The user needs to revisit a saved RS thesis. | Readback only. |

