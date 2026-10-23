#!/usr/bin/env python3
"""Regenerate the parity fixtures for the unusual-pairs engine (maintainer tool).

The normal test run never calls this file. It builds a fully synthetic corpus
and seeded dense vectors, then runs two outside reference scripts on them and
stores their output as golden files. Neither reference script is copied into
this repo. Each one is named by an environment variable and is refused unless
its sha256 matches the expected full hash.

Environment variables (both required):
  EUREKA_RS_REFERENCE_SCRIPT  path to path B, the LATEST reference rs-engine.py
  EUREKA_RS_PLUGIN_SCRIPT     path to path A, the shipped plugin rs-engine.py

Run with the system python3 (numpy 2.2.6, scikit-learn 1.8.0 are the versions
of the recorded run):

  EUREKA_RS_REFERENCE_SCRIPT=... EUREKA_RS_PLUGIN_SCRIPT=... \\
      python3 scripts/generate_rs_parity_golden.py

Output: tests/fixtures/rs_parity/{corpus,reference_vectors,golden_reference,
golden_plugin_legacy}.json. Running it twice gives byte-identical corpus and
vector files (only generated_on in the golden headers changes).

Safety: the temp room lives outside the repo, holds no .mindrian/room.db, and
the scripts run offline (HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1). The scripts
are run as subprocesses. Only path B is also loaded by file path, after the
sha256 check, to read its own matrix functions.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np

REFERENCE_SHA256 = "044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45"
PLUGIN_SHA256 = "57c18df558d83fbffc8e9f7fda905729d0c0fbfe18a1c370b1db816efa3937f1"
SEED = 256
N_DOCS = 32
DIM = 64
CASES = {
    "nonneg": "parity-stub-nonneg-v1",
    "signed": "parity-stub-signed-v1",
}
FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "rs_parity"
SECTION = "synthetic"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_script(env_name: str, expected: str) -> Path:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        sys.exit(f"{env_name} is not set. Set it to the path of the reference script.")
    path = Path(raw)
    if not path.is_file():
        sys.exit(f"{env_name} does not name a file: {path}")
    actual = sha256_file(path)
    if actual != expected:
        sys.exit(
            f"Refusing to run {path}: sha256 {actual} does not equal the expected {expected}."
        )
    return path


# ---------------------------------------------------------------- corpus --

_SYLLABLES = ["ka", "mo", "ri", "ve", "tu", "sa", "lo", "ne", "pi", "zu", "da", "fe", "go", "hi", "bu", "wa"]


def _pseudo_words(rng: random.Random, count: int, used: set[str], syllables: int = 3) -> list[str]:
    words: list[str] = []
    while len(words) < count:
        word = "".join(rng.choice(_SYLLABLES) for _ in range(syllables))
        if word in used:
            continue
        used.add(word)
        words.append(word)
    return words


def build_corpus() -> list[dict]:
    """32 synthetic documents: 4 topic vocabularies, 8 documents per topic.

    Every document mixes words of its own topic with words of a second topic,
    and carries 3 to 5 rare tokens that occur once in the whole corpus. The rare
    tokens of one document have identical TF-IDF columns, which creates exact
    ties in the SVD loadings and exposes the top-7 term tie-break.
    """
    rng = random.Random(SEED)
    used: set[str] = set()
    topics = [_pseudo_words(rng, 14, used) for _ in range(4)]
    docs = []
    for i in range(N_DOCS):
        own = i // 8
        other = (own + 1 + (i * 7 + i // 3) % 3) % 4
        words = [rng.choice(topics[own]) for _ in range(rng.randint(16, 20))]
        words += [rng.choice(topics[other]) for _ in range(rng.randint(5, 9))]
        rare = _pseudo_words(rng, rng.randint(3, 5), used, syllables=4)
        # Alternate rare tokens are written with a capital letter. TF-IDF folds
        # case, so the columns stay tied. The membership count uses raw
        # whitespace tokens, so only the plain form matches a topic keyword.
        # This makes the tie order change the structural matrix, as it does on
        # real text with mixed case and punctuation.
        words += [w.capitalize() if k % 2 else w for k, w in enumerate(rare)]
        rng.shuffle(words)
        docs.append({
            "id": f"syn-{i + 1:03d}",
            "title": f"Syn {i + 1:03d}",
            "text": " ".join(words),
            "source_ref": f"syn://{i + 1:03d}",
        })
    return docs


def build_vectors() -> dict:
    """Seeded float32 vectors, dimension 64, for two cases.

    The cluster assignment is independent of the text topics, so the dense
    signal disagrees with the lexical signals on some pairs. 'nonneg' has no
    negative component. 'signed' has both signs, so some cosines are negative.
    """
    rng = np.random.default_rng(SEED)
    centers = rng.normal(size=(5, DIM))
    out: dict = {"dimension": DIM, "cases": {}}
    for case, model in CASES.items():
        vectors = {}
        for i in range(N_DOCS):
            cluster = (i * 3 + i // 4) % 5
            noise = rng.normal(scale=0.6, size=DIM)
            if case == "nonneg":
                vec = np.abs(centers[cluster]) + np.abs(noise)
            else:
                vec = centers[cluster] + noise
            vec = (vec / np.linalg.norm(vec)).astype(np.float32)
            # Shortest float32 text, so a reader gets the same float32 back.
            vectors[f"syn-{i + 1:03d}"] = [float(str(x)) for x in vec]
        out["cases"][case] = {"model": model, "vectors": vectors}
    return out


def dump_stable(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, sort_keys=True, indent=1) + "\n", encoding="utf-8")


# ------------------------------------------------------------ reference runs --

def make_room(root: Path, corpus: list[dict], vectors: dict[str, list[float]]) -> Path:
    room = root / "room"
    (room / SECTION).mkdir(parents=True)
    cache = {}
    for item in corpus:
        (room / SECTION / f"{item['id']}.md").write_text(
            f"{item['text']}\n", encoding="utf-8")
        body = item["text"].strip()
        cache[f"{SECTION}/{item['id']}"] = {
            "hash": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            "model": "all-MiniLM-L6-v2",
            "vector": np.asarray(vectors[item["id"]], dtype=np.float32).astype(np.float32).tolist(),
        }
    (room / ".rs-engine-cache.json").write_text(
        json.dumps({"version": "1", "model": "all-MiniLM-L6-v2", "embeddings": cache}),
        encoding="utf-8")
    return room


def run_script(script: Path, room: Path, out: Path, extra: list[str], cwd: Path) -> dict:
    env = dict(os.environ, RS_EMBEDDING_MODEL="minilm", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    cmd = [sys.executable, str(script), "--mode", "internal", "--room", str(room),
           "--topk", "100", "--threshold", "0.0", "--no-thesis", *extra, "--output", str(out)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"Reference run failed ({result.returncode}): {result.stderr[-600:]}")
    return {"command": cmd, "output": json.loads(out.read_text(encoding="utf-8"))}


def strip_id(artifact_id: str) -> str:
    return artifact_id.split("/", 1)[1] if "/" in artifact_id else artifact_id


def load_reference_module(path: Path):
    old_argv = sys.argv
    sys.argv = [str(path)]
    try:
        spec = importlib.util.spec_from_file_location("eureka_parity_reference_b", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.argv = old_argv
    return module


def rounded(matrix) -> list[list[float]]:
    return np.round(np.asarray(matrix, dtype=np.float64), 8).tolist()


def versions() -> dict:
    import sklearn
    return {"python": sys.version.split()[0], "numpy": np.__version__, "scikit_learn": sklearn.__version__}


def main() -> None:
    reference = require_script("EUREKA_RS_REFERENCE_SCRIPT", REFERENCE_SHA256)
    plugin = require_script("EUREKA_RS_PLUGIN_SCRIPT", PLUGIN_SHA256)

    corpus = build_corpus()
    vectors = build_vectors()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    corpus_path = FIXTURE_DIR / "corpus.json"
    vectors_path = FIXTURE_DIR / "reference_vectors.json"
    dump_stable({"artifacts": corpus}, corpus_path)
    dump_stable(vectors, vectors_path)

    header_common = {
        "generated_on": date.today().isoformat(),
        "corpus_sha256": sha256_file(corpus_path),
        "vectors_sha256": sha256_file(vectors_path),
        **versions(),
    }

    ref_module = load_reference_module(reference)
    texts = [f"{item['title']}\n{item['text'].strip()}" for item in corpus]
    lsa = ref_module.build_lsa_matrix(texts)
    bm25 = ref_module.bm25_similarity_matrix(texts)

    reference_golden = {"header": {
        **header_common,
        "reference_script_sha256": sha256_file(reference),
        "command": ["python3", "rs-engine.py", "--mode", "internal", "--room", "<temp room>",
                    "--topk", "100", "--threshold", "0.0", "--no-thesis", "--no-verify",
                    "--output", "<temp file>"],
        "env": {"RS_EMBEDDING_MODEL": "minilm", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    }, "cases": {}}
    plugin_golden = {"header": {
        **header_common,
        "reference_script_sha256": sha256_file(plugin),
        "command": ["python3", "rs-engine.py", "--mode", "internal", "--room", "<temp room>",
                    "--topk", "100", "--threshold", "0.0", "--no-thesis", "--output", "<temp file>"],
        "env": {"RS_EMBEDDING_MODEL": "minilm", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        "scoring": "legacy (path A supports legacy scoring only)",
    }, "cases": {}}

    with tempfile.TemporaryDirectory(prefix="eureka-parity-") as tmp:
        tmp_root = Path(tmp)
        for case, info in vectors["cases"].items():
            case_dir = tmp_root / case
            case_dir.mkdir()
            room = make_room(case_dir, corpus, info["vectors"])
            run = run_script(reference, room, case_dir / "b_out.json", ["--no-verify"], tmp_root)
            pairs = []
            for rank, pair in enumerate(run["output"]["pairs"], start=1):
                pairs.append({
                    "rank": rank,
                    "left": strip_id(pair["source_artifact_id"]),
                    "right": strip_id(pair["target_artifact_id"]),
                    "hybrid_signed_gap": pair["hybrid_signed_gap"],
                })
            dense_vectors = np.asarray(
                [np.asarray(info["vectors"][item["id"]], dtype=np.float32) for item in corpus])
            dense = ref_module.cosine_matrix(dense_vectors, clip=True)
            reference_golden["cases"][case] = {
                "model": info["model"],
                "metadata": {k: run["output"]["metadata"].get(k) for k in (
                    "scoring", "min_percentile", "lex_weight", "schema", "artifact_count")},
                "pairs": pairs,
                "matrices": {"lsa": rounded(lsa), "bm25": rounded(bm25), "dense_clipped": rounded(dense)},
            }
            if case == "nonneg":
                plugin_room_dir = tmp_root / "plugin"
                plugin_room_dir.mkdir()
                plugin_room = make_room(plugin_room_dir, corpus, info["vectors"])
                plugin_run = run_script(plugin, plugin_room, plugin_room_dir / "a_out.json", [], tmp_root)
                plugin_pairs = [{
                    "rank": rank,
                    "left": strip_id(pair["source_artifact_id"]),
                    "right": strip_id(pair["target_artifact_id"]),
                    "abs_diff": pair["abs_diff"],
                    "signed_diff": pair["signed_diff"],
                } for rank, pair in enumerate(plugin_run["output"]["pairs"], start=1)]
                plugin_golden["cases"][case] = {"model": info["model"], "pairs": plugin_pairs}

    dump_stable(reference_golden, FIXTURE_DIR / "golden_reference.json")
    dump_stable(plugin_golden, FIXTURE_DIR / "golden_plugin_legacy.json")
    print("wrote", ", ".join(sorted(p.name for p in FIXTURE_DIR.glob("*.json"))))


if __name__ == "__main__":
    main()
