# Compare Decision-Sequence Models

**Capability IDs:** `decision.compare_sequence_patterns`, `decision.fit_sequence_patterns`
**Engine:** pomegranate 1.1.2, MIT licensed, backed by PyTorch  
**Method source:** *The Opposable Mind Algorithmic Framework Using Hidden Markov Models* (user-provided research package, revised 2026-10-08)  
**Status:** executable local inference and exploratory Baum–Welch fitting; OMM construct, feature rubric, and parameters are not empirically validated.

## Hire this capability when

A user has already recorded a sequence of decision steps and wants to compare how explicit HMM hypotheses account for that trace, inspect step-level posterior probabilities, or explore fitting parameters from multiple coded sequences. It is a downstream process-reflection tool. It does not scout opportunities, evaluate a technology, or score a person's intelligence or ability.

## What it does

Each trace step has four binary observations: complex features, multidirectional causation, holistic view, and creative synthesis. Each configured model supplies a four-state initial distribution, 4×4 transition matrix, and four independent Bernoulli emission probabilities for each state. pomegranate supplies the HMM implementation:

A one-step trace is supported. Since there is no transition to evaluate in that case, Eureka computes the equivalent initial-state, emission, and uniform terminal likelihood directly; traces with two or more steps use pomegranate's forward/backward implementation.

- `log_probability`: whole-sequence log likelihood.
- `predict_proba`: forward–backward posterior probabilities by step and state.
- `predict`: posterior-MAP state label per step. This is **not** a globally optimal Viterbi path.
- Baum–Welch / EM fitting from a declared seed model, over multiple independently coded sequences.
- SHA-256 fingerprint on each caller-supplied parameter set.

The source names states as salience recognition, causality mapping, architecture building, and resolution creation. These labels do not establish that the states can be reliably observed or distinguished.

## Run the Oliver–JHTV local page

From the repository root (the `hmm` extra selects CPU-only PyTorch wheels, avoiding unnecessary CUDA downloads for this small local model):

```bash
uv sync --extra hmm
uv run eureka-decision-sequences-web
```

Open the URL printed by the server (default `http://127.0.0.1:4173/jhtv-theo-larry-review.html`). The page records a trace in browser memory and sends it only to the loopback API on your computer. It does not call an external model provider. To exercise the UI, choose **Load toy example models**; the output is fabricated technical-demo data, not an analysis of the JHTV candidates. For research use, upload your reviewed model JSON.

The web service refuses non-loopback bind addresses and limits request bodies to 1 MB. Stop it with Ctrl+C.

The adapter disables Numba JIT by default before loading pomegranate because the current Linux runtime aborts in Numba/LLVM during import otherwise. This model is small; the HMM calculations themselves use pomegranate/PyTorch. An explicit `NUMBA_DISABLE_JIT` environment setting is respected.

## MCP and command line

Install `hmm` alongside the desired MCP dependencies, then start `eureka-mcp`. The tools are `decision_compare_sequence_patterns` for inference and `decision_fit_sequence_patterns` for explicitly requested exploratory fitting. Each is catalogued separately and publishes its own request and result schemas.

Inspect the exact inference request/result contract with `eureka schema decision.compare_sequence_patterns`. The input schema types each step's four Boolean features and each model's 4-state distribution, 4×4 transition matrix, and 4×4 Bernoulli emission matrix. Probability ranges and dimensions are schema-checked; vector and matrix row sums are checked by the engine. CLI and MCP apply the same published contracts.

```bash
uv run eureka-decision-sequences analyze examples/decision-patterns/illustrative-only.json --output result.json
uv run eureka-decision-sequences fit training-bundle.json --output exploratory-fit.json
```

The fit command requires `training_mode: "exploratory_unlabeled_baum_welch"`, a fully specified `seed_model`, at least two sequences, and at least 32 coded steps in total. Thirty-two steps is an input guard only; it does **not** mean the dataset is statistically sufficient. The fit output is explicitly unvalidated. Unsupervised fitting can permute the state identities, so retaining the source's state names in the output does not mean their semantic identity has been preserved.

## Evidence, rights, and safeguards

- **Observed source:** the research markdown describes a four-state HMM, names four binary feature contrasts, provides two transition matrices, and labels classification, accuracy, likelihood-ratio, and learning-progression figures unsourced.
- **Observed gap:** a described 4×8 categorical emission matrix conflicts with the four binary contrasts. This implementation uses independent Bernoulli emissions because the library supports them directly; that is an implementation hypothesis, not a source-validated choice.
- **Library choice:** pomegranate's official documentation describes multivariate Bernoulli emissions with independent features, dense HMM likelihood/posterior inference, and Baum–Welch fitting. The PyPI package is MIT-licensed; installing the HMM extra also installs PyTorch and associated dependencies.
- **Rights boundary:** the pomegranate software license does not grant rights to the OMM paper, framework, slide deck, or underlying content. Confirm permission to use and redistribute those materials separately before publishing or shipping derived content.
- **Not established:** validity, reliability, construct meaning, fairness, clinical or employment suitability, or usefulness for opportunity discovery.
- **Before substantive use:** obtain informed consent for process traces; establish a coding rubric and provenance; recruit enough independent sequences for the intended inference; test inter-rater agreement, identifiability, state stability, bias, and held-out performance with qualified reviewers.

An analogy between named stages and fitted latent states is a hypothesis, not evidence. Do not use these outputs to rank, diagnose, or make decisions about individuals or teams.
