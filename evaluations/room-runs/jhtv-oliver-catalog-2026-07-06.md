# JHTV Fast Forward: first RS capability run

**Run status:** completed exploratory run; candidates have not been reviewed by Oliver/JHTV or validated as opportunities.

## Scope and method

- **Room:** `jhtv-oliver-kuntz` (source materials were read only).
- **Corpus:** all 2,117 rows in `research/2026-07-06-jhu-tech-csv-source/technologies.csv`, the room’s July 6, 2026 catalog snapshot.
- **Preparation:** removed leading Telerik/CSS formatting blocks from descriptions and appended the separately listed unmet need when present. Excluded contact fields, inventor lists, category labels, prior opportunity cards, and prior generated reports.
- **Objective:** surface unexpected pairs for human investigation of transferable mechanisms, combinations, or new applications. The current RS score does not use this objective.
- **Encoder:** local `sentence-transformers/all-MiniLM-L6-v2`, cached revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; model download and research-network access were disabled.
- **Method:** 80-topic TF-IDF/SVD structural profile plus modern sentence-transformer cosine similarity; ranked top 20 by absolute global-normalized signal disagreement.
- **Scope snapshot:** `sha256:f0b72ca4f4e3108f52f60396c9450640986ccb9a872eb2423e42fcb299df6425`.
- **Job:** `eureka-a5448339bf814134b6365131b73c4dd1`; duration reported by runner: 245562 ms.
- **Warning:** 10 of 2,117 artifact profiles had no membership in the selected LSA topic keywords; inspect candidates involving those records carefully.

Scores are method-relative ranking signals, not probabilities, confidence, proof of transfer, or commercial value. The result’s `structural_transfer` direction means semantic similarity exceeded structural similarity; it is a review cue only.

## Ranked pairs

| Rank | Pair | Structural | Semantic | Disagreement | Source records |
|---:|---|---:|---:|---:|---|
| 1 | [C03882 · Beta-Secretase (BACE1) Knockout Fibroblast Cells](https://jhu.technologypublisher.com/technology/16215) ↔ [C04556 · BACE2 Knockout Mice](https://jhu.technologypublisher.com/technology/16357) | 0.000 | 1.238 | 1.238 | room catalog |
| 2 | [C03774 · Beta - Secretase (BACE1) Knockout Mice](https://jhu.technologypublisher.com/technology/16193) ↔ [C03882 · Beta-Secretase (BACE1) Knockout Fibroblast Cells](https://jhu.technologypublisher.com/technology/16215) | 0.000 | 1.236 | 1.236 | room catalog |
| 3 | [C12143 · Developing an Interactive, Personalized Safety Decision Smart Phone Application to Prevent and Respond to Intimate Partner Violence in College Women](https://jhu.technologypublisher.com/technology/26280) ↔ [C12105 · Danger Assessment app for Young Women with OneLove Foundation](https://jhu.technologypublisher.com/technology/42095) | 0.000 | 1.188 | 1.188 | room catalog |
| 4 | [C11372 · DNA Constructs to Make Papillomavirus Pseudovirions for HPV Types](https://jhu.technologypublisher.com/technology/24237) ↔ [C10218 · Novel HPV Vaccine](https://jhu.technologypublisher.com/technology/60515) | 0.000 | 1.170 | 1.170 | room catalog |
| 5 | [C15791 · Semi-supervised end-to-end speech recognition using text-to-speech and autoencoders](https://jhu.technologypublisher.com/technology/38587) ↔ [C15375 · Semi-Supervised End-to-End Speech Recognition](https://jhu.technologypublisher.com/technology/39160) | 0.190 | 1.347 | 1.157 | room catalog |
| 6 | [C05024 · Biocompatible "smart" nanogels as carriers for hydrophobic drugs](https://jhu.technologypublisher.com/technology/24629) ↔ [C13285 · Therapeutic Nanofiber Hydrogels for Local Treatment of Brain-related Diseases](https://jhu.technologypublisher.com/technology/24722) | 0.000 | 1.141 | 1.141 | room catalog |
| 7 | [C12105 · Danger Assessment app for Young Women with OneLove Foundation](https://jhu.technologypublisher.com/technology/42095) ↔ [C14493 · myPlan app: Empowering decisions for a safe path forward](https://jhu.technologypublisher.com/technology/56314) | 0.000 | 1.134 | 1.134 | room catalog |
| 8 | [C03882 · Beta-Secretase (BACE1) Knockout Fibroblast Cells](https://jhu.technologypublisher.com/technology/16215) ↔ [C03929 · Beta-Secretase (BACE1) Polyclonal Antisera](https://jhu.technologypublisher.com/technology/16223) | 0.114 | 1.245 | 1.131 | room catalog |
| 9 | [C10970 · Compact High Efficient Multispectral LED Based Endoscopic Illumination System](https://jhu.technologypublisher.com/technology/16803) ↔ [C11386 · Dark Field Illuminated Reflectance Fiber Bundle Endoscopic Microscope](https://jhu.technologypublisher.com/technology/16919) | 0.026 | 1.155 | 1.130 | room catalog |
| 10 | [C17030 · A Method of Post-synthetic Modification of Metal-organic Frameworks for Enhancing Hydrophilicity and Water Stability of Metal-organic Frameworks in Water Sorption](https://jhu.technologypublisher.com/technology/48586) ↔ [C17480 · Organo-phosphate Modified Metal Organic Frameworks and Applications](https://jhu.technologypublisher.com/technology/54919) | 0.032 | 1.159 | 1.126 | room catalog |
| 11 | [C10220 · N-Hydroxylsulfonamide Derivatives as New Physiologically Useful Nitroxyl Donors](https://jhu.technologypublisher.com/technology/50277) ↔ [C10812 · N-Acyloxysulfonamide and N-Hydroxy-N-acylsulfonamide Derivatives as Stabilized HNO Donors](https://jhu.technologypublisher.com/technology/50279) | 0.125 | 1.248 | 1.123 | room catalog |
| 12 | [C04822 · Process for Polarized-gate Semiconductor Device](https://jhu.technologypublisher.com/technology/16421) ↔ [C10436 · Easily Processed Tetracarboxylic Diimide Semiconductors](https://jhu.technologypublisher.com/technology/16665) | 0.103 | 1.222 | 1.119 | room catalog |
| 13 | [P05418 · Novel Poly (propylene glycol) Based Passivation Coatings for High Performance Aqueous Lithium Ion Batteries](https://jhu.technologypublisher.com/technology/53590) ↔ [P05406 · Deep Eutectic Solvent Based Gel Polymer Electrolytes for Lithium Ion Batteries](https://jhu.technologypublisher.com/technology/53591) | 0.000 | 1.111 | 1.111 | room catalog |
| 14 | [C03088 · Human Blood Samples that Contain the Human Granulocytic Ehrlichia](https://jhu.technologypublisher.com/technology/16102) ↔ [C03087 · Plasmids Encoding the 16S rRNA Genes of Ehrlichia Equi and Human Granulocytic Ehrlichia](https://jhu.technologypublisher.com/technology/16101) | 0.000 | 1.109 | 1.109 | room catalog |
| 15 | [C11921 · Layered Reactive Particles with Controlled Geometries, Energies and Ignition Thresholds and Methods for Making the Same](https://jhu.technologypublisher.com/technology/17099) ↔ [C14575 · Reactive Multilayer Foils with Controlled, Discontinuous Structures for Chemical Time Delays](https://jhu.technologypublisher.com/technology/38107) | 0.030 | 1.133 | 1.103 | room catalog |
| 16 | [C13046 · System for Stereo Reconstruction from Monoscopic Endoscope Images](https://jhu.technologypublisher.com/technology/24723) ↔ [C14165 · An Inexpensive technique to Conduct High-Resolution 3D for use in Surgical Guidance](https://jhu.technologypublisher.com/technology/24898) | 0.000 | 1.102 | 1.102 | room catalog |
| 17 | [C01753 · TechTours](https://jhu.technologypublisher.com/technology/16087) ↔ [C11084 · PDQuests](https://jhu.technologypublisher.com/technology/28843) | 0.000 | 1.100 | 1.100 | room catalog |
| 18 | [C13514 · WeCareAdvisor Tool](https://jhu.technologypublisher.com/technology/31651) ↔ [C16447 · Keystone Dashboard](https://jhu.technologypublisher.com/technology/45263) | 0.000 | 1.097 | 1.097 | room catalog |
| 19 | [C12890 · Electrode Assemblies for Detecting Muscle Signals in a Prosthetic Liner](https://jhu.technologypublisher.com/technology/23325) ↔ [C16260 · 3D Printed Neural Port](https://jhu.technologypublisher.com/technology/43245) | 0.087 | 1.181 | 1.094 | room catalog |
| 20 | [C11587 · Grants Management Database](https://jhu.technologypublisher.com/technology/16985) ↔ [C16447 · Keystone Dashboard](https://jhu.technologypublisher.com/technology/45263) | 0.000 | 1.092 | 1.092 | room catalog |

## First-pass quality observations (not human ratings)

- All 20 top-ranked pairs were in the `semantic similarity > structural similarity` direction.
- 15 of 20 pairs have identical broad `domain` labels in the separate room catalog. The engine was not given or asked to filter on `domain`, so its capability name currently overstates cross-domain enforcement.
- The shortlist contains several obvious near-duplicate or adjacent records (for example BACE1/BACE2 knockout materials, two semi-supervised speech-recognition disclosures, and multiple intimate-partner-violence decision-support apps). These may be useful as portfolio consolidation/relatedness signals, but they do not by themselves demonstrate a new opportunity.
- None of the 40 endpoint IDs in this shortlist appear in the current opportunity-bank Markdown files. That is only “not currently referenced by these files”; it is not a novelty or value check.
- A full room/opportunity review is still needed. No usefulness judgments were recorded, and top-20 results may be affected by duplicated disclosures, uneven source text, the raw-token structural profile, and this July snapshot’s active-catalog scope.

## Conclusion

The end-to-end local job path completed over the full room catalog and produced source-linked results without downloading a model or sending the corpus to a research service. This validates execution on this input size. It does **not** establish that RS alone finds high-quality, genuinely cross-domain opportunities. The immediate product gap is to test de-duplication/known-pair handling and domain-aware filtering as explicit, separately evaluated steps before exposing this as a “breakthrough” shortlist.

## OMM fit for this room

The room snapshot has 2,117 technology-disclosure records and the RS run produced 20 candidate pairs. Those are not ordered observations of a reviewer's decision process, which is what the Opposable Mind HMM requires. No valid OMM score or comparison can be computed over the disclosure corpus itself, and this package checkout does not contain the source CSV or reviewer traces.

The companion HTML page now documents that data mismatch and connects a human-recorded candidate investigation trace to the local pomegranate HMM API. Its toy-model button is only a technical UI demonstration. A substantive run still needs consented reviewer traces, a reviewed coding rubric, and reviewed parameter sets; the method's source provides no calibrated emissions or initial distribution. OMM does not score the opportunity or validate the RS shortlist.
