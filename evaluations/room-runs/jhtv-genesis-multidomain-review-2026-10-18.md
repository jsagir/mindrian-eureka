# Genesis multi-domain research review — Oliver/JHTV

**Run type:** local execution of the legacy Genesis code for Stages 1–4, followed by source research using explicitly selected human research lenses. The actual code produced four text segments, a “LOW” complexity label, no domains, and zero personas for this JHTV brief. Stage 4 still returned generic phases with no research lenses. The empty map was not treated as an answer: the research lenses below were selected from the actual technologies and claims under review. Stages 5–6 were not invoked because the pipeline can substitute synthetic findings when Tavily is unavailable and its synthesis uses unvalidated heuristic scores.

**Scope limitation:** the 2,117-row source CSV is not in this checkout. Inputs were the July 6 RS run report (20 candidate pairs) and public JHTV/external sources. This is not a re-run of all 2,117 records or an exhaustive novelty, market, or IP search.

## 1. Context decomposition

**User decision:** Which JHTV portfolio leads deserve the next expert diligence step because they could address a concrete unmet need or support a credible translation path?

- **Function:** turn technology disclosures into a small set of evidence-backed, falsifiable opportunity hypotheses.
- **Actors:** JHTV/technology owners, researchers, clinicians or users, prospective licensees/partners, regulators, and funders.
- **Resources:** disclosed technologies, public literature, prototypes, clinical/workflow access, and investigator/partner time.
- **Bottleneck:** moving from a ranked text pair to proof of a real need, technical fit, user value, rights position, and feasible next experiment.
- **Fixed for this review:** public-only external research; no access to the source CSV, confidential room contents, devices, or lab results.
- **Not fixed:** RS ranking, number of domains, whether two technologies must be combined, or the requirement to call an item a “breakthrough.”

**How might we identify a defensible JHTV translation opportunity from a partial shortlist, despite missing full-catalog and experimental data, without mistaking semantic proximity or generated confidence for novelty or value?**

## 2. Domain map and perspectives

The legacy classifier did not identify any domains or generate personas on this input. The following lenses were selected manually to continue the investigation; they are not outputs of the domain classifier.

| Research lens | Question assigned | Why it belongs |
|---|---|---|
| Endoscopic imaging and optical engineering | What does each visualization asset actually measure or reconstruct, and what hardware/channel constraints apply? | Candidate #16 joins two 3D visualization disclosures. |
| Surgical robotics and safety control | What event triggers the safety mechanism, what does it physically do, and can it coexist with an imaging add-on? | JHTV has a motion-triggered endoscope retraction system in ENT/neurosurgery. |
| ENT/neurosurgery workflow and human factors | Where could depth cues help, and what trade-offs or usability costs could erase the benefit? | The technologies target clinical procedures where workflow fit matters. |
| Prosthetic control and rehabilitation | Are surface and implanted EMG complementary for different users, and what non-invasive evidence can discriminate? | Candidate #19 suggests two signal-acquisition modalities. |
| Survivor-centered IPV services and digital safety | Is there a user-controlled support handoff gap beyond the existing decision aid and partner-delivery model? | Candidate #3 shows overlapping safety-decision tools; exposure risk is consequential. |
| Drug delivery, formulation, and neuro-oncology | Is there a target-specific gap left after existing local gel/nanoparticle systems and related JHTV assets? | Candidate #6 suggests brain-local delivery convergence. |
| Technology transfer, regulation, and adoption | Is a technical connection distinct from a licensable, adoptable, rights-clear opportunity? | All candidates need translation and overlap checks. |

These lenses were used to define questions and source checks; no fictional experts or consensus vote were used. The actual run artifact is [jhtv-genesis-planning-run-2026-10-18.json](./jhtv-genesis-planning-run-2026-10-18.json). It preserves the exact code outputs and run scope.

## 3. Research findings and disagreements

### A. Endoscopic visualization + motion-triggered safety

- The RS run paired a monoscopic-endoscope 3D reconstruction disclosure with an inexpensive high-resolution 3D surgical-guidance disclosure (rank 16). JHTV describes one 3D method as inexpensive and potentially disposable for minimally invasive measurement; its search listing describes the other as a cost-effective structured-light endoscope.
- JHTV separately describes a robotically manipulated endoscope safety feature: a head-motion sensor causes a latch to release and retract the scope. The page identifies ENT and neurosurgery applications and reports a developed system.
- Clinical evidence about 3D endoscopy is mixed. A randomized multicentre study of 80 patients found better depth perception and detail recognition with 3D but worse overall image quality/usability, and no statistically significant procedure-time difference. A clinical training study found no significant performance improvement for inexperienced participants despite better subjective ratings. Other preclinical evidence reports task-specific benefits. The implication is not “3D is better”; utility depends on task, user, and setup.
- **Potential convergence:** low-cost depth cues and a motion-responsive safety mechanism could be evaluated as parts of an endoscopic guidance/safety workflow for selected ENT/neurosurgery tasks.
- **Critical technical mismatch:** the monoscopic reconstruction concept uses a light-patterning component in the endoscope’s working channel; the safety technology uses a robot-held endoscope, a head-motion sensor, a controller, and a mechanical latch. The two may compete for space, interfaces, or workflow. No compatibility evidence was found.

Sources: [JHTV monoscopic endoscope reconstruction](https://jhu.technologypublisher.com/technology/24723), [JHTV high-resolution 3D surgical guidance](https://jhu.technologypublisher.com/technology/24898), [JHTV motion-triggered endoscope safety](https://jhu.technologypublisher.com/technology/28852), [multicentre 3D endoscopy study](https://pubmed.ncbi.nlm.nih.gov/33373011/), [randomized endoscopic training study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7027512/), [preclinical neuroendoscopy crossover study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4053590/).

### B. Prosthetic signal modality pathway

- The RS shortlist pairs liner-mounted muscle electrodes with an implantable muscle interface. JHTV pages confirm these are different acquisition approaches, one external and one implanted.
- Reviews and small human studies support investigating surface-interface reliability and implanted-signal performance, but do not show these two JHTV assets share a decoder, are interchangeable, or can form a clinical pathway.
- **Unresolved disagreement:** a modality continuum could help a subset of users, but it could also be a category error that adds surgery and cost without improving control. User preference and unmet need must lead the question.

Sources: [JHTV liner electrodes](https://jhu.technologypublisher.com/technology/23325), [JHTV neural port](https://jhu.technologypublisher.com/technology/43245), [surface EMG/socket review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8694273/), [2025 implanted-signal study](https://pubmed.ncbi.nlm.nih.gov/40470247/).

### C. Survivor-controlled safety decision support

- The room includes overlapping IPV safety-decision technologies. Current myPlan materials describe a functioning app with user-safety features; research has evaluated contextual adaptation and delivery with trained community health volunteers.
- **Unresolved disagreement:** an app-to-advocate handoff may address continuity for some settings, but may duplicate existing practice. Any information transfer can create safety risk if a partner monitors devices or accounts.
- No survivor or advocate interviews were conducted. This is not ready to be called a product gap.

Sources: [JHTV myPlan](https://jhu.technologypublisher.com/technology/56266), [myPlan Kenya randomized trial](https://gh.bmj.com/content/5/7/e002091), [myPlan safety and privacy features](https://myplanapp.org/en/our-story).

### D. Brain-local hydrogel/nanoparticle delivery: prior-art correction

- The room’s RS pair linked a smart nanogel disclosure and a local brain-treatment nanofiber hydrogel.
- Broader search found a 2023 paper, *Intracranial nanomedicine-gel with deep brain-penetration for glioblastoma therapy*, describing a nanoparticle reservoir in an injectable gel that provides sustained release and deep drug penetration. JHTV also lists a nanofiber-hydrogel/LNP composite and a separate brain-penetrating particle platform.
- This materially weakens the generic “combine hydrogel and nanoparticles for sustained deep-brain delivery” hypothesis. A narrower payload, mechanism, patient/use case, or unmet formulation constraint might remain, but it needs specific prior-art and IP review before being advanced.
- FDA has a formal Office of Combination Products and a classification pathway for products mixing regulated components. This does not assign a classification to this hypothetical system, but reinforces that modality combinations carry regulatory planning work.

Sources: [2023 intracranial nanomedicine-gel study](https://doi.org/10.1016/j.jconrel.2023.01.085), [JHTV hydrogel/LNP composite](https://jhu.technologypublisher.com/technology/56057), [JHTV brain-penetrating particles](https://jhu.technologypublisher.com/technology/36712), [FDA combination products](https://www.fda.gov/combination-products).

## 4. Opportunity triage

Qualitative judgments only; not numeric opportunity scores.

| Candidate | Structural fit | Potential impact | Feasibility to investigate | Distinctness / novelty | Cheap falsifier | Risk if wrong | Decision |
|---|---|---|---|---|---|---|---|
| Endoscopic depth + motion-triggered safety workflow | Moderate; common setting and purpose, interfaces unverified | Potentially high for specific procedures | Medium for benchtop fit check | Unclear; multiple related JHTV assets and existing 3D systems | High | Medium–high clinical/device risk | **Advance to technical fit screen** |
| Choice-aware prosthetic signal pathway | Moderate; same control need, different invasiveness | Potentially meaningful for a subgroup | Medium for data/decoder review | Unclear; likely portfolio adjacency | Medium | High if it encourages unnecessary implantation | **Keep as second candidate** |
| Survivor-controlled app-to-human-support handoff | Strong service-system relation | High social value if gap exists | High for a fictional-scenario workshop | Low as a new app; gap unverified | High | Very high privacy/safety consequence | **Stakeholder validation only** |
| Generic brain hydrogel + nanoparticle delivery | Strong mechanism similarity | Potentially high | Low | **Weak after direct prior-art and portfolio overlap check** | Medium | High biomedical/IP/regulatory | **Reject as a generic opportunity** |

The endoscopic workflow is the strongest next investigation because multiple JHTV assets converge around a shared operative context and there is a clear, cheap compatibility question. That is not evidence of a market opportunity or a claim that the parts should be combined.

## 5. Proposed concept and hybrid

### Depth-aware, motion-safe endoscopic guidance

Use a low-cost 3D/depth cue for tasks where depth information helps, alongside a motion-triggered safe-retraction mechanism where sudden head movement creates a hazard. Imaging contributes spatial information; the safety subsystem contributes a physical response to motion. The combination is only useful if it does not obstruct the endoscope channel, degrade image quality, delay ordinary operation, or introduce unsafe false releases.

**Critical mismatch:** the technologies may require incompatible endoscope form factors, working-channel space, control hardware, and clinical workflow. The clinical literature does not establish universal benefit from 3D viewing; several studies show mixed performance or usability results.

**Smallest experiment:** before a patient or cadaver study, conduct a benchtop fit-and-failure review with the inventors/engineering leads using the intended monoscopic scope and the actual component geometry. In a dry anatomical model, test depth-calibration error, image quality, channel clearance, motion-trigger latency, and unintended release under ordinary handling. Stop if the optics cannot fit with the safety hardware, if image quality degrades beyond a predefined task-specific limit, or if ordinary head/hand motion causes false release.

## 6. Genesis handoff

- **To Theo:** accept or revise the endoscopic workflow question and define the exact procedure and intended user before more search.
- **To SME:** map the depth-sensing and motion-safe control mechanisms separately; test whether their interfaces can coexist and whether the causal chain from depth cue to safer action is evidenced.
- **To Builder:** do not build a combined prototype until a bench geometry/interface review confirms a feasible test article. If feasible, build an inert simulator fixture, not a clinical device.
- **To ICM:** record this report as a versioned research finding; store each technology, source, claim, counterclaim, review status, and experiment result separately. Keep the brain-delivery generic combination marked rejected for now, with the 2023 prior-art link as the reason.

## 7. First experiment

**We will test** whether the low-cost 3D/endoscope concept can physically coexist with the motion-triggered scope safety mechanism **with** a dry benchtop endoscopic setup, **over** a two-week engineering feasibility sprint, measuring channel clearance, depth-calibration error, image quality, motion-trigger latency, and false-release rate. **Continue** to an inert simulator study only if the components fit, image quality stays within a pre-agreed task threshold, and no false release occurs during the defined normal-motion set. **Revise or stop** if the hardware is incompatible or the motion-safety behavior is unreliable.

This is a proposed feasibility experiment, not a completed test. Have the relevant inventors and clinical safety experts set the task-specific image-quality and latency thresholds before testing; do not invent them after seeing results.
