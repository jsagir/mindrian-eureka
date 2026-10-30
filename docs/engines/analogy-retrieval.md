# Analogy source recall and transfer review

## Retrieve candidate mechanisms

`analogy.retrieve_mechanism_candidates` searches a local or MindrianOS-approved mechanism corpus with transparent lexical overlap. Each item needs a stable ID, domain, mechanism description, and source reference. The retrieval ratio and matched terms only show why a record was recalled; they are not semantic or structural fit.

Hire this stage when the user has a framed target problem and wants to inspect source mechanisms from other domains. If remote research is needed, Genesis/SME query planning prepares exact questions; MindrianOS's approved broker performs retrieval and returns cited records.

## Test a selected structure

After a mechanism is selected, encode source and target relationships as seven structural fields and attach evidence reference IDs to every populated field. The fitness stage returns those expressions and references alongside its layer comparisons. Then call `scout_sme_map` for a relational mapping. Candidate inferences go through source/counterevidence/boundary review. SME output is still a hypothesis until the evidence stage and human decision.

The supporting `analogy.assess_structural_fitness` stage compares seven SAPPhIRE fields using a local sentence-transformer model. It reports layer cosines, corpus-relative correspondence thresholds when at least five candidates are available, a band, a restatement warning, and the source references attached to each populated layer. Set `MINDRIAN_EUREKA_ANALOGY_MODEL_PATH` or reuse `MINDRIAN_EUREKA_RS_MODEL_PATH`. The thresholds and bands are exploratory heuristics, not calibrated judgments. Hire this stage to prioritize which sourced mappings to inspect; use SME to evaluate relational mappings and candidate inferences.

The reviewed embedding-based Analogies recall and fitness stack is not fully ported. Do not substitute lexical recall for the original method, SAPPhIRE structure fitness, or SME adjudication.
