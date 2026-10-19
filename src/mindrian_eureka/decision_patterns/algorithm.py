"""Opposable Mind decision-process HMM powered by pomegranate.

The source document supplies transition hypotheses but no initial or emission
parameters. All parameters are therefore caller-provided or fitted from coded
sequences and remain research hypotheses until independently validated.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any

import numpy as np

STATE_NAMES = (
    "salience_recognition",
    "causality_mapping",
    "architecture_building",
    "resolution_creation",
)
FEATURE_NAMES = (
    "complex_features",
    "multidirectional_causation",
    "holistic_view",
    "creative_synthesis",
)
MAX_STEPS = 2000


def _pomegranate():
    # pomegranate's optional KMeans initializer imports apricot/numba. On some
    # CPU toolchains numba's generated LLVM schedule aborts the Python process;
    # this four-state model is tiny and does not need that JIT initializer.
    # Respect an explicit operator setting if one is already present.
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
    try:
        from pomegranate.distributions import Bernoulli
        from pomegranate.hmm import DenseHMM
    except ImportError as exc:
        raise RuntimeError(
            "OMM needs the optional HMM engine. Install with: uv sync --extra hmm"
        ) from exc
    return Bernoulli, DenseHMM


def _probability(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number between 0 and 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{label} must be a finite number between 0 and 1")
    return number


def _probability_vector(value: Any, size: int, label: str, *, total: bool = True) -> list[float]:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"{label} must contain exactly {size} probabilities")
    vector = [_probability(item, f"{label}[{i}]") for i, item in enumerate(value)]
    if total and not math.isclose(sum(vector), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(f"{label} must sum to 1")
    return vector


def _validate_model(model: dict[str, Any]) -> tuple[list[float], list[list[float]], list[list[float]]]:
    if not isinstance(model, dict) or not isinstance(model.get("id"), str) or not model["id"].strip():
        raise ValueError("Each model needs a non-empty id")
    initial = _probability_vector(model.get("initial_distribution"), 4, f"{model['id']}.initial_distribution")
    transitions = model.get("transition_matrix")
    emissions = model.get("emission_probabilities")
    if not isinstance(transitions, list) or len(transitions) != 4:
        raise ValueError(f"{model['id']}.transition_matrix must have 4 rows")
    if not isinstance(emissions, list) or len(emissions) != 4:
        raise ValueError(f"{model['id']}.emission_probabilities must have 4 rows")
    transition_rows = [
        _probability_vector(row, 4, f"{model['id']}.transition_matrix[{i}]")
        for i, row in enumerate(transitions)
    ]
    emission_rows = []
    for i, row in enumerate(emissions):
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"{model['id']}.emission_probabilities[{i}] must contain 4 Bernoulli probabilities")
        emission_rows.append([_probability(p, f"{model['id']}.emission_probabilities[{i}][{j}]") for j, p in enumerate(row)])
    return initial, transition_rows, emission_rows


def _build_model(model: dict[str, Any], *, max_iter: int = 100, tol: float = 1e-3):
    Bernoulli, DenseHMM = _pomegranate()
    initial, transitions, emissions = _validate_model(model)
    distributions = [Bernoulli(probs=row) for row in emissions]
    # A uniform end probability gives each state the same sequence-termination
    # factor, preserving the source algorithm's no-terminal-preference model.
    hmm = DenseHMM(distributions, edges=transitions, starts=initial, ends=[0.25] * 4, max_iter=max_iter, tol=tol)
    return hmm


def _observation_matrix(sequence: Any) -> tuple[list[str], np.ndarray]:
    if not isinstance(sequence, list) or not 1 <= len(sequence) <= MAX_STEPS:
        raise ValueError(f"observations must contain between 1 and {MAX_STEPS} steps")
    ids: list[str] = []
    rows: list[list[int]] = []
    seen: set[str] = set()
    for index, step in enumerate(sequence):
        if not isinstance(step, dict) or not isinstance(step.get("step_id"), str) or not step["step_id"].strip():
            raise ValueError(f"observations[{index}] needs a non-empty step_id")
        if step["step_id"] in seen:
            raise ValueError(f"Duplicate step_id: {step['step_id']}")
        seen.add(step["step_id"])
        features = step.get("features")
        if not isinstance(features, dict) or set(features) != set(FEATURE_NAMES):
            raise ValueError(f"observations[{index}].features must contain exactly: {', '.join(FEATURE_NAMES)}")
        if any(not isinstance(features[name], bool) for name in FEATURE_NAMES):
            raise ValueError(f"observations[{index}].features values must be booleans")
        ids.append(step["step_id"])
        rows.append([int(features[name]) for name in FEATURE_NAMES])
    return ids, np.asarray(rows, dtype=np.float32)


def _parameter_hash(model: dict[str, Any]) -> str:
    payload = {key: model[key] for key in ("initial_distribution", "transition_matrix", "emission_probabilities")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def analyze_sequence(document: dict[str, Any]) -> dict[str, Any]:
    """Compare one observed sequence under two or more configured HMMs."""
    if not isinstance(document, dict):
        raise ValueError("Input must be an object")
    step_ids, observations = _observation_matrix(document.get("observations"))
    models = document.get("models")
    if not isinstance(models, list) or not 2 <= len(models) <= 5:
        raise ValueError("models must contain between 2 and 5 configured models")
    ids = [model.get("id") if isinstance(model, dict) else None for model in models]
    if any(not isinstance(model_id, str) or not model_id.strip() for model_id in ids):
        raise ValueError("Every model needs a non-empty id")
    if len(set(ids)) != len(ids):
        raise ValueError("Model ids must be unique")

    sequence = observations[None, :, :]
    results = []
    posteriors = {}
    for spec in models:
        if len(observations) == 1:
            # pomegranate's DenseHMM forward/backward implementation cannot
            # reshape the empty transition axis for a one-step sequence. With
            # no transitions to evaluate, compute the equivalent initial ×
            # Bernoulli-emission × terminal likelihood directly.
            initial, _, emissions = _validate_model(spec)
            bits = observations[0].astype(bool)
            initial_array = np.asarray(initial, dtype=np.float64)
            emission_array = np.asarray(emissions, dtype=np.float64)
            with np.errstate(divide="ignore", invalid="ignore"):
                state_log_weights = np.log(initial_array) + np.log(
                    np.where(bits[None, :], emission_array, 1.0 - emission_array)
                ).sum(axis=1) + math.log(0.25)
            max_log_weight = float(np.max(state_log_weights))
            if not math.isfinite(max_log_weight):
                raise ValueError(f"The one-step observation has zero probability under model {spec['id']}")
            log_likelihood = max_log_weight + math.log(float(np.exp(state_log_weights - max_log_weight).sum()))
            posterior = np.exp(state_log_weights - log_likelihood)[None, :]
            predicted = np.asarray([int(np.argmax(posterior[0]))])
        else:
            hmm = _build_model(spec)
            log_likelihood = float(hmm.log_probability(sequence)[0].item())
            posterior = hmm.predict_proba(sequence)[0].detach().cpu().numpy()
            predicted = hmm.predict(sequence)[0].detach().cpu().numpy()
        posterior_rows = [
            {STATE_NAMES[state]: float(row[state]) for state in range(4)} for row in posterior
        ]
        posteriors[spec["id"]] = posterior_rows
        results.append({
            "model_id": spec["id"],
            "label": str(spec.get("label", spec["id"])),
            "parameter_sha256": _parameter_hash(spec),
            "log_likelihood": log_likelihood,
            "mean_log_likelihood_per_step": log_likelihood / len(observations),
            "posterior_map_state_sequence": [STATE_NAMES[int(state)] for state in predicted],
            "posterior_state_probabilities": posterior_rows,
        })
    ranked = sorted(results, key=lambda result: result["mean_log_likelihood_per_step"], reverse=True)
    return {
        "schema_version": "eureka.decision-sequence-result.v1",
        "capability_id": "decision.compare_sequence_patterns",
        "method_version": "pomegranate-1.1.2-four-state-bernoulli-hmm-v1",
        "engine": {"name": "pomegranate", "version": "1.1.2", "license": "MIT"},
        "status": "completed_unvalidated_model_comparison",
        "scope": {"scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id"), "sequence_id": document.get("sequence_id")},
        "observation_count": len(observations),
        "feature_names": list(FEATURE_NAMES),
        "state_names": list(STATE_NAMES),
        "model_results": results,
        "relative_fit_leader": ranked[0]["model_id"],
        "mean_log_likelihood_difference_per_step": ranked[0]["mean_log_likelihood_per_step"] - ranked[1]["mean_log_likelihood_per_step"],
        "step_posteriors": [
            {"step_id": step_id, "models": {model_id: rows[i] for model_id, rows in posteriors.items()}}
            for i, step_id in enumerate(step_ids)
        ],
        "interpretation_limit": (
            "Relative fit is conditional on the supplied parameters and draft feature coding. "
            "It is not a validated measure, diagnosis, ability score, or opportunity finding. "
            "Posterior-MAP labels are per-step labels, not a globally optimal Viterbi path."
        ),
        "warnings": [
            "The source document provides no initial distribution or numeric emission parameters.",
            "Independent Bernoulli emissions are an explicit modeling assumption, not validated by the source.",
            "No result from this engine has been empirically validated for the JHTV room or for individual assessment.",
        ],
    }


def fit_model(document: dict[str, Any]) -> dict[str, Any]:
    """Run exploratory Baum-Welch updates from a declared seed model."""
    if not isinstance(document, dict):
        raise ValueError("Input must be an object")
    if document.get("training_mode") != "exploratory_unlabeled_baum_welch":
        raise ValueError("Set training_mode to 'exploratory_unlabeled_baum_welch' to enable parameter fitting")
    seed = document.get("seed_model")
    if not isinstance(seed, dict):
        raise ValueError("seed_model is required")
    _validate_model(seed)
    raw_sequences = document.get("sequences")
    if not isinstance(raw_sequences, list) or not 2 <= len(raw_sequences) <= 500:
        raise ValueError("sequences must contain between 2 and 500 independently coded sequences")
    arrays: list[np.ndarray] = []
    total_steps = 0
    for index, raw in enumerate(raw_sequences):
        _, matrix = _observation_matrix(raw.get("observations") if isinstance(raw, dict) else None)
        arrays.append(matrix)
        total_steps += len(matrix)
    if total_steps < 32:
        raise ValueError("Exploratory fitting requires at least 32 coded steps; this is a software guard, not a statistical sufficiency guarantee")
    try:
        max_iter = int(document.get("max_iterations", 100))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_iterations must be an integer from 1 to 1000") from exc
    if not 1 <= max_iter <= 1000:
        raise ValueError("max_iterations must be an integer from 1 to 1000")

    tolerance = float(document.get("tolerance", 1e-3))
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a finite non-negative number")
    hmm = _build_model(seed, max_iter=max_iter, tol=tolerance)
    hmm.fit(arrays)
    trained = {
        "id": str(document.get("model_id", f"{seed['id']}-exploratory-fit")),
        "label": str(document.get("label", f"Exploratory fit from {seed.get('label', seed['id'])}")),
        "parameter_status": "exploratory_unvalidated",
        "parameter_origin": "pomegranate Baum-Welch from caller-provided seed_model",
        "states": list(STATE_NAMES),
        "features": list(FEATURE_NAMES),
        "initial_distribution": hmm.starts.detach().cpu().exp().tolist(),
        "transition_matrix": hmm.edges.detach().cpu().exp().tolist(),
        "emission_probabilities": [distribution.probs.detach().cpu().tolist() for distribution in hmm.distributions],
    }
    return {
        "schema_version": "eureka.decision-sequence-fit-result.v1",
        "capability_id": "decision.fit_sequence_patterns",
        "engine": {"name": "pomegranate", "version": "1.1.2", "algorithm": "Baum-Welch / expectation-maximization"},
        "status": "exploratory_unvalidated_fit",
        "sequence_count": len(arrays),
        "observation_count": total_steps,
        "max_iterations": max_iter,
        "model": trained,
        "warnings": [
            "A low data-volume guard does not establish statistical sufficiency or identifiability.",
            "Unlabeled fitting may permute state identities; the familiar names are not guaranteed to retain their source meaning.",
            "The seed values, feature rubric, missing-data handling, independence assumptions, and learned model need expert review and held-out evaluation before substantive use.",
            "Do not use this exploratory model to assess, rank, or diagnose people.",
        ],
    }
