# JHTV Opportunity Leads — Fresh Full-Catalog Pass

**Run:** 2026-10-18  
**Catalog snapshot:** JHTV extraction dated 2026-07-06, 2,117 technology records  
**Discovery inputs:** fresh local HSI and RS runs recorded in the room's `solution-design/full-catalog-run-2026-10-18/`  
**Decision status:** leads for diligence; none is a qualified opportunity or approved portfolio entry.

## Lead 1 — Partner the C15631 controlled-release formulation

**Source record:** [C15631, Compositions and methods for controlled release suprachoroidal drug delivery](https://jhu.technologypublisher.com/technology/43809). The July extraction describes biodegradable polymeric microparticles for suprachoroidal (SCS) delivery, reports at least eight weeks of controlled release in rodent models and therapeutic efficacy for at least 18 weeks, marks the stage preclinical, and explicitly seeks partners to develop and commercialize the formulation. These are technology-office-reported claims, not independently reproduced results.

**Why it is a lead:** this is a concrete, stated partnering need attached to a defined asset, a named delivery route, preclinical data, and a translation gap. A viable next step is an asset-specific diligence package for ophthalmic formulation or drug-delivery partners.

**What weakens it:** controlled release in the SCS is an established research direction, not an empty field. A 2020 peer-reviewed paper from the same JHU group reported sustained delivery of acriflavine from the SCS and long-term suppression of choroidal neovascularization in an animal model ([paper record](https://pubmed.ncbi.nlm.nih.gov/32172031/)). A review describes multiple polymeric and implant-based controlled-release approaches, including months-long persistence in preclinical work ([review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8309112/)). A 2024 review discusses newer devices, formulations, and clinical work ([review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11357265/)). The diligence question is therefore specific performance and IP differentiation, not whether SCS sustained release is possible.

**Next discriminating work:** retrieve the current patent family and prosecution status; identify the exact lead formulation, active agents, release profile and comparator; review complete animal data and safety endpoints; clarify whether the 2023 Celanese–JHU collaboration ([company announcement](https://www.celanese.com/news-and-media/2023/february/celanese-announces-research-agreement-with-johns-hopkins)) overlaps this asset or its rights; and confirm current licensing availability with JHTV.

**Smallest useful test:** a host-approved JHTV diligence request plus a blinded comparison of the asset's claims, patent claims, and published SCS sustained-release prior art. Continue only if the specific formulation has a defensible technical or IP distinction and rights are available.

## Lead 2 — Assess a modality-spanning SCS portfolio around C14402 and C15631

**Source records:** [C14402, Nonviral gene transfer to the suprachoroidal space](https://jhu.technologypublisher.com/technology/28645) and C15631 above. The fresh HSI run ranked the pair second. C14402 concerns polymer-particle delivery of expression constructs and reports preclinical transfection; C15631 concerns biodegradable drug-loaded microparticles for controlled release. They share the same anatomical delivery compartment, while their payloads and intended mechanisms differ.

**Why investigate:** if the assets remain independently available and their formulation/IP boundaries are compatible, they could support a portfolio or partner conversation spanning nonviral gene transfer and sustained small-molecule delivery through one SCS-focused development capability. The useful opportunity may be coordinated evaluation and partnering, not physically combining the formulations.

**Critical mismatch and evidence:** the records have overlapping inventors and institutional origin, so the semantic connection may be an existing program or related IP family rather than an unexpected cross-domain insight. External reviews already describe SCS delivery across small molecules, particles, gene therapy, and other modalities ([review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7926337/)); thus “one route, multiple payloads” is not itself novel. C14402 has a granted US patent and a pending continuation according to its JHTV listing; the SCS route also has established clinical use for at least one drug, XIPERE ([FDA label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/211950s002lbl.pdf)). Neither fact establishes that the two JHU assets can be combined, licensed together, or clinically translated.

**Next discriminating work:** compare patent claims, ownership, license status, shared inventorship, formulation compatibility, and intended partner/customer. Ask whether the current opportunity is (a) licensing C15631 alone, (b) a coordinated SCS platform portfolio, or (c) a technically integrated formulation. Keep (c) out of the plan unless payload stability, release kinetics, transfection, and safety support it.

**Smallest useful test:** request the two current nonconfidential technology briefs and patent-family summaries; produce a claim-overlap and rights map; then ask one ophthalmic delivery partner to assess which distinct asset-specific problem they would fund. Stop the “platform” framing if the partner sees no advantage beyond a shared anatomical route.

## Fresh signal versus qualified opportunity

The HSI pair is a fresh discovery signal from the October run; it is not proof that the opportunity is new to JHTV, new to the market, or absent from prior art. The underlying C15631 record and 2020 publication predate this run. RS returned no edges in its fresh full-catalog run, so it contributed no new RS-ranked pair to this lead set. No outside research was fetched by the local engines, no native `/mos:find-connections` or `/mos:qualify-opportunity` operation was run, no Theo case evaluation was performed, and no graph/portfolio write occurred.

## Theo MCP boundary

Theo MCP is available to MindrianOS for framework, concept, and review guidance. The available Theo calls do not accept this JHTV bundle or execute the room's `/mos:find-connections` workflow. Theo was not asked to review these case records. A general Theo review guide may inform the host's checklist, but it is not evidence for either lead and does not make the leads Theo-reviewed.

## SME structural review — C15631 compared with C14402

**Question:** does the high-level relationship between these HSI-neighbor records carry a transferable mechanism, or only a shared route and delivery vocabulary?

**What SME received:** a source-linked description of C15631 as a drug payload carried by polymeric microparticles, administered to the SCS, and released over time; and C14402 as expression-construct cargo in polymeric particles, administered to the SCS, then acting through transfection and transgene expression. The input claims point to exact excerpts in the July catalog's `description_full` / `value_prop` fields. This is an analyst-prepared representation of those records, not automatic extraction by SME.

**Observed run:** the literal role-and-mechanism encoding found only a small, awkward correspondence and no candidate inferences. A second, explicitly normalized role encoding represented only the operations stated in both records: cargo in a carrier, administration to SCS, and targeting the posterior eye. Under that encoding, SME returned two mappings (AN and MA) with fit 0.8834 and 0.862, surface distance 0.3333, zero novelty, and zero candidate inferences. The scores are ranking diagnostics for this encoding, not probabilities or evidence of opportunity quality. SME did not identify a transferable new mechanism.

**Interpretation:** the structural overlap supports a portfolio question—whether distinct payload modalities could be evaluated or partnered under an SCS-focused program. It does not support combining the formulations. The causal paths diverge after delivery: C15631 depends on release kinetics and local drug exposure; C14402 depends on construct integrity, cellular uptake/transfection, and expression. A combined product would require evidence on compatibility, potency, release, biodistribution, and safety that these records do not supply.

**Assessment:** SME is useful here as a disciplined challenge to the HSI signal. The shared route and carrier-level framing explain why the pair can be related, while the absence of candidate inferences and zero novelty caution against treating that relation as an “Eureka” transfer. This is a comparison within the same institutional and therapeutic domain, not a distant-domain analogy search. External base discovery remains a separate next step.

**Encoding limitation:** SME implements symbolic structural mapping. It does not decide that “drug” and “expression construct” occupy the same abstract role, or that “release” and “transfection” are equivalent. An analyst must choose the abstraction. The normalized map intentionally encoded their shared delivery roles while preserving their different effect-producing mechanisms; its result should be read alongside the literal encoding, not as an objective discovery independent of representation.

**Artifacts:** `evaluations/room-runs/jhtv-sme-2026-10-18/structure-mapping-input.json`, `structure-mapping-result.json`, and the explicitly normalized `structure-mapping-input-shared-mechanism-roles.json` / `structure-mapping-result-shared-mechanism-roles.json`.
