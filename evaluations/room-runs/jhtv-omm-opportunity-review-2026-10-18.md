# OMM-guided opportunity review — Oliver/JHTV

**Status:** exploratory, evidence-linked hypotheses for human review. This is not a calibrated HMM result, a novelty opinion, or a commercialization recommendation.

## Scope and method

Applied the four OMM stages (notice → connect → shape → resolve) as a transparent investigation scaffold to selected leads in the July 6, 2026 RS shortlist, then checked JHTV portfolio pages and external publications for consequential claims. The original shortlist came from a 2,117-row catalog, but the source CSV and reviewer traces are absent from this checkout. This review therefore does not claim to re-run the catalog search or validate all 2,117 records.

The HMM implementation was not used to score candidates. The OMM source does not provide calibrated initial/emission probabilities, and no observed reviewer sequence exists. Treat the opportunities below as hypotheses produced by human evidence review, not outputs of a validated OMM model.

## OMM investigation trace

| Stage | What surfaced in this room | Investigation result |
|---|---|---|
| Notice | Two delivery systems are close in the RS shortlist; two prosthetic signal interfaces also appear together; multiple IPV safety tools overlap. | Similarity is a lead, not proof of complementarity or novelty. |
| Connect | Local placement and sustained release may be distinct from tissue penetration; wearable surface EMG and implanted muscle interfaces may serve different reliability/clinical situations; safety decision aids depend on people and services around the app. | The potentially useful links are at system boundaries and handoffs, not shared keywords. |
| Shape | Form a delivery stack, an optional signal-acquisition pathway, and an app-to-support handoff. | Each is a testable architecture hypothesis. None is established as compatible or new. |
| Resolve | Rank by evidence, feasibility, downside, and cheap falsification. | Test human-review usefulness first; pursue lab/clinical work only after technical and stakeholder diligence. |

## Three opportunity hypotheses

### 1. Brain-local delivery with both controlled residence and tissue spread

**OMM move:** connect the nanofiber hydrogel record (C13285) for local sustained delivery with JHTV's brain-penetrating nanoparticle record (C15580), which reports 60–200 nm particles and animal-model distribution after convection-enhanced delivery. The hypothesis is that a local depot could address residence/release while the particles address distribution through tissue.

**Why investigate:** JHTV describes the nanoparticle penetration result and separately has a nanofiber-hydrogel local-treatment disclosure. A published 2023 JHTV-linked dual-arm local-delivery strategy is also reported for the particle platform. This creates a potentially useful *interface question* (can a depot preserve release and spread?) rather than a claim that the basic hydrogel-plus-nanoparticle combination is new.

**Critical mismatch / novelty warning:** JHTV already lists an mRNA-LNP nanofiber-hydrogel composite (C18197 / technology 56057), and C15580 has its own published local-delivery strategy. The payload, disease, mechanism, formulation, administration route, patent scope, and inventor overlap need diligence. No evidence reviewed establishes that the brain hydrogel and brain-penetrating particles are compatible.

**Smallest technical falsifier:** have the relevant formulation researchers assess compatibility, then compare free particles with particles released from hydrogel in a relevant tissue model. Measure particle integrity, release over time, and spatial distribution. Stop if the gel traps/aggregates particles or materially reduces distribution versus free particles. This is a proposed experiment; no lab data were generated here.

**Evidence status:** JHTV claims and publication existence verified; cross-platform compatibility and commercial whitespace are hypotheses.

Sources: [JHTV C15580](https://jhu.technologypublisher.com/technology/36712), [JHTV nanofiber-hydrogel/LNP composite C18197](https://jhu.technologypublisher.com/technology/56057), [JHTV smart nanogels C05024](https://jhu.technologypublisher.com/technology/24629), [brain-penetrating nanoparticles paper](https://pubs.acs.org/doi/10.1021/nn504210g).

### 2. User-chosen escalation path for prosthetic control signals

**OMM move:** connect replaceable electrodes embedded in a prosthetic liner (C12890) with the implantable muscle interface / neural port (C16260), but treat them as distinct acquisition options rather than one assumed integrated product. The opportunity hypothesis is a modular pathway that starts with a low-burden surface interface and considers implanted signals only for people whose needs and preferences justify added intervention.

**Why investigate:** the JHTV records address signal acquisition at different levels of invasiveness. External literature describes practical limitations in surface EMG/socket use, while small human studies report promising implanted muscle-signal performance. These findings justify examining the user-choice and transition problem, not claiming superiority across users.

**Critical mismatch:** the devices may use incompatible signal formats, target different users, and follow different clinical and regulatory pathways. Implantation adds surgical risk and care burden; a common decoder or transition route has not been demonstrated. Adoption, reimbursement, long-term reliability, and user preference remain open.

**Smallest technical falsifier:** first compare de-identified, consented signal datasets or bench outputs using the same task/decoder protocol. Measure usable-control time, recalibration burden, error rate, and signal dropout by modality. Do not propose implantation as the first experiment. Stop the integration hypothesis if the interfaces cannot produce comparable data or if no user-defined need supports escalation.

**Evidence status:** technology descriptions and selected peer-reviewed evidence verified; pathway, interface compatibility, and user value are hypotheses.

Sources: [JHTV liner electrode assembly](https://jhu.technologypublisher.com/technology/23325), [JHTV 3D Printed Neural Port](https://jhu.technologypublisher.com/technology/43245), [surface EMG/prosthesis review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8694273/), [long-term implanted muscle-interface study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10126717/), [2025 RPNI/iEMG study](https://pubmed.ncbi.nlm.nih.gov/40470247/).

### 3. Safety-tool-to-human-support handoff, not another safety app

**OMM move:** treat the overlapping IPV decision-aid records as a service-system signal. The candidate is a survivor-controlled, privacy-aware handoff from a digital decision aid to a trusted advocate or community service, with the survivor controlling whether any information is shared.

**Why investigate:** myPlan is a functioning, evidence-backed decision aid, and research has evaluated context adaptation and delivery with trained community health volunteers. That suggests the research question is about implementation, continuity, and user-controlled support—not whether to build a generic new app.

**Critical mismatch:** this may already be substantially addressed by the product and its implementation partners. A handoff can create serious exposure risks if a device or account is monitored, and careless data retention could harm users. Any exploration requires IPV specialists and survivor co-design; no real survivor data should be used in an initial prototype.

**Smallest practical falsifier:** conduct a paid design review with IPV advocates and survivor advisors using fictional scenarios only. Ask whether the proposed handoff fills a real gap, preserves user control, and can be made safer than existing referral practice. Stop if stakeholders see no unmet need or cannot identify a safe, voluntary data boundary.

**Evidence status:** product features and trial evidence verified; a remaining service handoff gap is only a hypothesis.

Sources: [JHTV myPlan](https://jhu.technologypublisher.com/technology/56266), [myPlan Kenya randomized trial](https://gh.bmj.com/content/5/7/e002091), [college-women myPlan trial](https://pubmed.ncbi.nlm.nih.gov/33576291/).

## Triage

| Candidate | Structural fit | Potential impact | Feasibility now | Novelty vs current portfolio | Cheap to test | Risk if wrong |
|---|---|---|---|---|---|---|
| Brain-local residence + spread | Strong mechanism complement, compatibility unknown | High if a real delivery gap exists | Low–medium; specialist formulation work | Low until a specific unmet payload/use is shown; substantial overlap warning | Medium | High biomedical/IP risk |
| Prosthetic signal pathway | Moderate; related user outcome but different modalities | Meaningful for a defined user subgroup | Medium for non-invasive data review; low for clinical integration | Unclear; likely portfolio adjacency | Medium | Medium–high clinical and adoption risk |
| Safety-tool handoff | Strong system-level connection | High social value if a gap remains | High for stakeholder review, low for deployment | Low as a new app; possible implementation opportunity | High | High user-safety/privacy risk |

Ratings are qualitative judgment, not measured scores. The safety-handoff idea is easiest to test but should not be treated as a product opportunity until advocates and survivor advisors validate the gap. The brain-delivery idea has the highest technical upside and the clearest overlap/compatibility risks. The prosthetic pathway is the best next opportunity for a bounded, non-invasive evidence check.

## First experiment for MindrianOS / OMM

Run a one-week evidence-review pilot on these three candidate dossiers with two independent reviewers. Give each reviewer the same linked source packet and the OMM stage prompts; ask them to record evidence, assumptions, mismatches, and the next falsifying test. Compare whether reviewers independently identify the same bottleneck and whether a domain expert rates each proposed next test as actionable. Continue the OMM workflow if at least two of three dossiers yield a shared, source-linked bottleneck and a feasible falsifier, with no unsupported claim carried as fact; otherwise revise the stage prompts and handoff schema.

This tests whether OMM improves investigation structure and decision usefulness. It does not validate the HMM, establish individual reasoning types, or prove an opportunity is novel or valuable.

## Important source gap

This checkout contains the ranked run report but not the 2,117-row source CSV or actual reviewer decision traces. Reproduce the RS run and conduct a full portfolio/claim review only after those source artifacts are restored. Patent status and scope here are surfaced from JHTV pages, not legal advice or freedom-to-operate analysis.
