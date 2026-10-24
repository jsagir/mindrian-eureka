# Public hub fixture

## Source

Source name: arXiv descriptive metadata, title and abstract fields only.
Source URL: https://export.arxiv.org/api/query
Metadata API terms: https://info.arxiv.org/help/api/tou.html
Retrieval date: 2026-10-24.

## License

License name: Creative Commons CC0 1.0 Universal Public Domain Dedication.
License statement: https://info.arxiv.org/help/license/index.html#metadata-license
Quoted statement: "A Creative Commons CC0 1.0 Universal Public Domain Dedication will apply to all metadata."

The official submission agreement at https://info.arxiv.org/help/policies/submission_agreement.html#metadata-license states: "Metadata includes title, author, abstract, and other information describing the Work."
These statements cover the extracted title and abstract metadata. No full paper, image, PDF, or source archive is copied.

## What was changed

- Kept only the title and abstract fields. Author, affiliation, and contact metadata are not included.
- Folded metadata title wrapping onto one front-matter line. Abstract line breaks are retained.
- Replaced U+2013, U+2014, and runs of two or more hyphens with a spaced plain hyphen.
- Preserved every abstract sentence, spelling, number, and claim. The fixture does not endorse those claims.
- Selected different documents where explicit personal attributions appeared. No private room export or partner record was consulted.

## Selection rule

The fixture contains 36 explicit versioned identifiers, six in each of six subject groups: computer science, biology, physics, mathematics, economics, and statistics. Subject queries were used only to discover candidates. The fixed identifiers below were curated for topic coverage and the final metadata request used this exact identifier list, without selecting by result order. Category cross-listings are allowed; each identifier occurs once. Shorter abstracts were retained intact where they add subject coverage.

## Documents

| File name | Source identifier | Source URL | Title | Subject group |
|---|---|---|---|---|
| arxiv-cs-9311101v1.md | cs/9311101v1 | https://arxiv.org/abs/cs/9311101v1 | The Difficulties of Learning Logic Programs with Cut | computer-science |
| arxiv-cs-9312101v1.md | cs/9312101v1 | https://arxiv.org/abs/cs/9312101v1 | Decidable Reasoning in Terminological Knowledge Representation Systems | computer-science |
| arxiv-cs-9401101v1.md | cs/9401101v1 | https://arxiv.org/abs/cs/9401101v1 | Teleo-Reactive Programs for Agent Control | computer-science |
| arxiv-cs-9501102v1.md | cs/9501102v1 | https://arxiv.org/abs/cs/9501102v1 | A Domain-Independent Algorithm for Plan Adaptation | computer-science |
| arxiv-cs-9501101v1.md | cs/9501101v1 | https://arxiv.org/abs/cs/9501101v1 | Solving Multiclass Learning Problems via Error-Correcting Output Codes | computer-science |
| arxiv-cs-9608103v1.md | cs/9608103v1 | https://arxiv.org/abs/cs/9608103v1 | Spatial Aggregation: Theory and Applications | computer-science |
| arxiv-q-bio-0309024v1.md | q-bio/0309024v1 | https://arxiv.org/abs/q-bio/0309024v1 | Synchronization and oscillatory dynamics in heterogeneous mutually inhibited neurons | biology |
| arxiv-q-bio-0309025v1.md | q-bio/0309025v1 | https://arxiv.org/abs/q-bio/0309025v1 | Frequency control in synchronized networks of inhibitory neurons | biology |
| arxiv-q-bio-0309028v1.md | q-bio/0309028v1 | https://arxiv.org/abs/q-bio/0309028v1 | Analysis of Dynamic Brain Imaging Data | biology |
| arxiv-physics-9807059v1.md | physics/9807059v1 | https://arxiv.org/abs/physics/9807059v1 | Oligopeptides' frequencies in the classification of proteins' primary structures | biology |
| arxiv-q-bio-0309026v1.md | q-bio/0309026v1 | https://arxiv.org/abs/q-bio/0309026v1 | Coding Strategies in Monkey V1 and Inferior Temporal Cortices | biology |
| arxiv-cond-mat-9807121v2.md | cond-mat/9807121v2 | https://arxiv.org/abs/cond-mat/9807121v2 | Continuous and discrete models of cooperation in complex bacterial colonies | biology |
| arxiv-cond-mat-9610069v1.md | cond-mat/9610069v1 | https://arxiv.org/abs/cond-mat/9610069v1 | The Role of Bilayer Tilt Difference in Equilibrium Membrane Shapes | physics |
| arxiv-cond-mat-9610048v1.md | cond-mat/9610048v1 | https://arxiv.org/abs/cond-mat/9610048v1 | Instability and front propagation in laser-tweezed lipid bilayer tubules | physics |
| arxiv-cond-mat-9610070v1.md | cond-mat/9610070v1 | https://arxiv.org/abs/cond-mat/9610070v1 | Spontaneous Expulsion of Giant Lipid Vesicles Induced by Laser Tweezers | physics |
| arxiv-cond-mat-9610116v1.md | cond-mat/9610116v1 | https://arxiv.org/abs/cond-mat/9610116v1 | Long Range Moves for High Density Polymer Simulations | physics |
| arxiv-cond-mat-9611039v1.md | cond-mat/9611039v1 | https://arxiv.org/abs/cond-mat/9611039v1 | Macromolecular separation through a porous surface | physics |
| arxiv-cond-mat-9610098v1.md | cond-mat/9610098v1 | https://arxiv.org/abs/cond-mat/9610098v1 | Straightening of Thermal Fluctuations in Semi-Flexible Polymers by Applied Tension | physics |
| arxiv-1405-0585v2.md | 1405.0585v2 | https://arxiv.org/abs/1405.0585v2 | Evaluating gambles using dynamics | economics |
| arxiv-0906-4316v2.md | 0906.4316v2 | https://arxiv.org/abs/0906.4316v2 | Constructive Decision Theory | economics |
| arxiv-1405-0733v1.md | 1405.0733v1 | https://arxiv.org/abs/1405.0733v1 | Spatial interactions in agent-based modeling | economics |
| arxiv-1204-1846v3.md | 1204.1846v3 | https://arxiv.org/abs/1204.1846v3 | Approximate Revenue Maximization with Multiple Items | economics |
| arxiv-1405-2051v1.md | 1405.2051v1 | https://arxiv.org/abs/1405.2051v1 | Merchant Sharing Towards a Zero Marginal Cost Economy | economics |
| arxiv-1404-3167v1.md | 1404.3167v1 | https://arxiv.org/abs/1404.3167v1 | A Dynamical Model of the Industrial Economy of the Humber Region | economics |
| arxiv-1701-00554v2.md | 1701.00554v2 | https://arxiv.org/abs/1701.00554v2 | Exponential Convergence of a Distributed Algorithm for Solving Linear Algebraic Equations | mathematics |
| arxiv-1701-00558v2.md | 1701.00558v2 | https://arxiv.org/abs/1701.00558v2 | Successive Convexification of Non-Convex Optimal Control Problems with State Constraints | mathematics |
| arxiv-1701-00881v2.md | 1701.00881v2 | https://arxiv.org/abs/1701.00881v2 | Supervisory Control of Discrete-event Systems under Attacks | mathematics |
| arxiv-1701-01477v1.md | 1701.01477v1 | https://arxiv.org/abs/1701.01477v1 | Unconstrained inverse quadratic programming problem | mathematics |
| arxiv-1701-01768v1.md | 1701.01768v1 | https://arxiv.org/abs/1701.01768v1 | Multi-Haul Quasi Network Flow Model for Vertical Alignment Optimization | mathematics |
| arxiv-1701-01913v1.md | 1701.01913v1 | https://arxiv.org/abs/1701.01913v1 | Hierarchical Control Framework for Integrated Coordination between DERs and Demand Response | mathematics |
| arxiv-physics-0203002v2.md | physics/0203002v2 | https://arxiv.org/abs/physics/0203002v2 | Finding an Upper Limit in the Presence of Unknown Background | statistics |
| arxiv-math-0510276v3.md | math/0510276v3 | https://arxiv.org/abs/math/0510276v3 | An algorithmic and a geometric characterization of Coarsening At Random | statistics |
| arxiv-math-0609457v2.md | math/0609457v2 | https://arxiv.org/abs/math/0609457v2 | Defining and Estimating Intervention Effects for Groups that will Develop an Auxiliary Outcome | statistics |
| arxiv-math-0610518v1.md | math/0610518v1 | https://arxiv.org/abs/math/0610518v1 | Asymptotic Properties of Covariate-Adjusted Adaptive Designs | statistics |
| arxiv-0704-0744v1.md | 0704.0744v1 | https://arxiv.org/abs/0704.0744v1 | Quantifying social group evolution | statistics |
| arxiv-math-0702703v1.md | math/0702703v1 | https://arxiv.org/abs/math/0702703v1 | Can one estimate the conditional distribution of post-model-selection estimators? | statistics |

## Frozen run

Pending the two real-model runs and byte comparison.
