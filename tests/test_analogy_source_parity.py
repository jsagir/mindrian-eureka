"""Golden parity checks against the pinned LATEST analogy-whitespace source.

The expected digests were produced by
engines/analogies/scripts/discover-analogy-whitespace.py at SHA-256
e5a5d58e867189df9df2c6155ea8d4009a8c0b10e9754eadee2f55c1c9b4bc3d.
They cover the comparable source output fields after excluding timestamps and
host-specific envelope metadata.
"""

import hashlib
import json

import numpy as np

from mindrian_eureka.analogy_whitespace import analyze


SOURCE_FIELDS = (
    "source_artifact", "target_artifact", "source_section", "target_section",
    "transfer_type", "nearest_brain_frameworks", "articulation_gap", "gap_signal",
    "articulation_gap_percentile", "articulation_gap_z", "brain_mean_similarity",
    "nearest_brain_similarities", "endpoints_excluded_from_gap",
    "nearest_other_artifact", "structural_fitness",
)

SOURCE_DIGESTS = {
    "fixed": "ef463cf1123c1ca0563932a749eae9bb0e8dd0ea539aa3703a1e442b9dd0172e",
    "percentile": "70db8dc6db8a3b2f316d0706ae4dc02154543f6c09fc3dd8ce118e2c7edd8e7a",
    "small_corpus_fallback": "3e4dc99797839d88e8b773d9736569d7a4fda26d1bde42ff3a58f2912479ceed",
    "hsi_fallback": "4a412ce216ff8975e9e87d30abecad6fde69b0021ac01e4074c3b669b1bf624e",
}


def _fixture():
    rng = np.random.default_rng(7)
    artifacts = [
        {"id": f"a{i}", "section": f"s{i % 3}", "title": f"T{i}", "vector": rng.normal(size=8).tolist()}
        for i in range(14)
    ]
    baselines = [
        {"id": f"f{i}", "name": f"fw{i}", "vector": rng.normal(size=8).tolist()}
        for i in range(6)
    ]
    edges = [
        {"source_id": f"a{i}", "target_id": f"a{(i * 3 + 5) % 14}",
         "analogy_distance": ["near", "far", "cross-domain"][i % 3], "structural_fitness": 0.5}
        for i in range(10)
    ]
    hsi_pairs = [
        {"left_id": f"a{i}", "right_id": f"a{i + 1}",
         "semantic_sim": 0.3 + 0.02 * i, "lsa_sim": 0.6 - 0.015 * i}
        for i in range(10)
    ]
    return artifacts, baselines, edges, hsi_pairs


def _digest(result):
    rows = [{field: zone.get(field) for field in SOURCE_FIELDS} for zone in result["zones"]]
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_analogy_whitespace_matches_pinned_latest_core_outputs():
    artifacts, baselines, edges, hsi_pairs = _fixture()
    cases = {
        "fixed": {"mode": "fixed", "analogy_edges": edges, "hsi_pairs": []},
        "percentile": {"mode": "percentile", "analogy_edges": edges, "hsi_pairs": []},
        "small_corpus_fallback": {"mode": "percentile", "analogy_edges": edges[:2], "hsi_pairs": []},
        "hsi_fallback": {"mode": "percentile", "analogy_edges": [], "hsi_pairs": hsi_pairs},
    }
    for label, case in cases.items():
        result = analyze({
            "scope_id": "fixture", "snapshot_id": label, "min_corpus": 5,
            "artifacts": artifacts, "baselines": baselines, **case,
        })
        assert _digest(result) == SOURCE_DIGESTS[label], label
