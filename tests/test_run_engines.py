"""Tests for the engine facade of `eureka run` (engines.py)."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import CORPUS_FIXTURE, InputSet
from hashing_stub import hashing_encode
from mindrian_eureka.run import engines
from mindrian_eureka.run.contracts import Record, RunError, UsageError, sha256_text

SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")
OFFLINE_NAMES = (
    "HSI_NO_AUTO_INSTALL",
    "HF_HUB_OFFLINE",
    "TRANSFORMERS_OFFLINE",
    "HF_HUB_DISABLE_TELEMETRY",
    "TOKENIZERS_PARALLELISM",
)
THREAD_NAMES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


def make_records(count: int = 32, *, titles: bool = True) -> list[Record]:
    """Build Record objects from the synthetic corpus fixture."""
    data = json.loads(CORPUS_FIXTURE.read_text(encoding="utf-8"))
    records: list[Record] = []
    for item in data["artifacts"][:count]:
        text = item["text"].strip()
        records.append(
            Record(
                id=f"synthetic/{item['id']}",
                title=item["title"] if titles else "",
                text=text,
                source_ref=f"synthetic/{item['id']}.md",
                source_file=f"synthetic/{item['id']}.md",
                text_sha256=sha256_text(text),
            )
        )
    return records


def _restorable_env(monkeypatch: pytest.MonkeyPatch, names: tuple[str, ...]) -> None:
    """Record the current value of each variable so monkeypatch restores it at teardown."""
    for name in names:
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


# --- Environment helpers ----------------------------------------------------


def test_prepare_offline_environment_assigns_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    monkeypatch.setenv("HSI_NO_AUTO_INSTALL", "0")
    monkeypatch.setenv("TOKENIZERS_PARALLELISM", "true")
    engines.prepare_offline_environment()
    assert os.environ["HSI_NO_AUTO_INSTALL"] == "1"
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    # setdefault: an existing value stays.
    assert os.environ["TOKENIZERS_PARALLELISM"] == "true"


def test_prepare_offline_environment_sets_missing_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    engines.prepare_offline_environment()
    assert os.environ["TOKENIZERS_PARALLELISM"] == "false"
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"


def test_prepare_offline_environment_quiets_model_libraries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = ("TRANSFORMERS_VERBOSITY", "HF_HUB_DISABLE_PROGRESS_BARS", *OFFLINE_NAMES)
    _restorable_env(monkeypatch, names)
    engines.prepare_offline_environment()
    assert os.environ["TRANSFORMERS_VERBOSITY"] == "error"
    assert os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] == "1"


def test_apply_thread_limits_none_changes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _restorable_env(monkeypatch, THREAD_NAMES)
    engines.apply_thread_limits(None)
    assert not any(name in os.environ for name in THREAD_NAMES)


def test_apply_thread_limits_rejects_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _restorable_env(monkeypatch, THREAD_NAMES)
    with pytest.raises(UsageError):
        engines.apply_thread_limits(0)
    assert not any(name in os.environ for name in THREAD_NAMES)


def test_apply_thread_limits_sets_three_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    _restorable_env(monkeypatch, THREAD_NAMES)
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    engines.apply_thread_limits(3)
    assert [os.environ[name] for name in THREAD_NAMES] == ["3", "3", "3"]


def test_apply_thread_limits_calls_torch_only_when_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restorable_env(monkeypatch, THREAD_NAMES)
    calls: list[int] = []

    class FakeTorch:
        @staticmethod
        def set_num_threads(count: int) -> None:
            calls.append(count)

    monkeypatch.setitem(sys.modules, "torch", FakeTorch())
    engines.apply_thread_limits(2)
    assert calls == [2]


def test_importing_engines_loads_no_heavy_library() -> None:
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import mindrian_eureka.run.engines;"
        "bad = {'numpy', 'sklearn', 'torch', 'sentence_transformers'} & set(sys.modules);"
        "sys.exit(1 if bad else 0)"
    )
    done = subprocess.run([sys.executable, "-I", "-c", code, SRC_DIR], capture_output=True)
    assert done.returncode == 0, done.stderr.decode()


def test_source_never_uses_the_reference_encoder_factory() -> None:
    source = Path(engines.__file__).read_text(encoding="utf-8")
    code_lines = [line for line in source.splitlines() if not line.lstrip().startswith("#")]
    assert not any("make_sentence_transformer_encoder" in line for line in code_lines)


# --- Local model load -------------------------------------------------------


def test_load_local_encode_fails_cleanly_and_never_opens_a_socket(
    tmp_path: Path,
    no_network: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("sentence_transformers")
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    with pytest.raises(RunError) as caught:
        engines.load_local_encode(tmp_path / "no-such-model-folder")
    assert caught.value.fix == "Check the model folder with: eureka doctor --load-model"
    assert no_network == []


def test_load_local_encode_on_a_stub_folder_never_opens_a_socket(
    fake_model_dir: Path,
    no_network: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("sentence_transformers")
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    try:
        engines.load_local_encode(fake_model_dir)
    except RunError:
        pass
    assert no_network == []


def test_load_local_encode_names_the_fix_when_the_package_is_missing(
    fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(RunError) as caught:
        engines.load_local_encode(fake_model_dir)
    assert caught.value.fix == "uv sync --extra modern-encoder"


# --- Unusual-pairs call -----------------------------------------------------


def test_unusual_pairs_call_shape(
    monkeypatch: pytest.MonkeyPatch, fake_model_dir: Path, tmp_path: Path
) -> None:
    from mindrian_eureka.opportunity_pairs import runner

    _restorable_env(monkeypatch, OFFLINE_NAMES)
    order: list[str] = []
    seen: dict[str, Any] = {}

    def fake_validate(document: dict[str, Any], **kwargs: Any) -> None:
        order.append("validate")
        seen["validate_document"] = copy.deepcopy(document)
        seen["validate_kwargs"] = kwargs

    def fake_run(document: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        order.append("run")
        seen["run_document"] = document
        seen["run_kwargs"] = kwargs
        return {"status": "completed", "outputs": []}

    monkeypatch.setattr(runner, "validate_document", fake_validate)
    monkeypatch.setattr(runner, "run_document", fake_run)
    records = make_records(5)
    stages: list[str] = []
    cache_path = tmp_path / "cache.sqlite"
    outcome = engines.run_unusual_pairs(
        records,
        model_dir=fake_model_dir,
        top_k=50,
        max_artifacts=4000,
        cache_path=cache_path,
        objective="find leads",
        progress=stages.append,
    )
    assert order == ["validate", "run"]
    assert seen["validate_kwargs"] == {"max_artifacts": 4000}
    document = seen["run_document"]
    assert document["objective"] == "find leads"
    assert document["mode"] == "local"
    assert document["scoring"] == "hybrid_2026"
    assert [item["id"] for item in document["artifacts"]] == [r.id for r in records]
    first = document["artifacts"][0]
    assert first == {
        "id": records[0].id,
        "title": records[0].title,
        "text": records[0].text,
        "source_ref": records[0].source_ref,
        "corpus": "room",
    }
    kwargs = seen["run_kwargs"]
    assert kwargs["encoder_name"] == "sentence-transformers"
    assert kwargs["model_path"] == str(fake_model_dir)
    assert kwargs["allow_model_download"] is False
    assert kwargs["top_k"] == 50
    assert kwargs["scoring"] == "hybrid_2026"
    assert kwargs["lex_weight"] == 0.5
    assert kwargs["min_percentile"] == 0.90
    assert kwargs["cache_path"] == cache_path
    assert kwargs["stage_callback"] == stages.append
    assert outcome.settings.top_k == 50
    assert outcome.capability_version == runner.CAPABILITY_VERSION


def test_unusual_pairs_value_error_becomes_run_error(
    monkeypatch: pytest.MonkeyPatch, fake_model_dir: Path, tmp_path: Path
) -> None:
    from mindrian_eureka.opportunity_pairs import runner

    _restorable_env(monkeypatch, OFFLINE_NAMES)

    def reject(document: dict[str, Any], **kwargs: Any) -> None:
        raise ValueError("Input needs at least two artifacts")

    monkeypatch.setattr(runner, "validate_document", reject)
    with pytest.raises(RunError) as caught:
        engines.run_unusual_pairs(
            make_records(1),
            model_dir=fake_model_dir,
            top_k=10,
            max_artifacts=3000,
            cache_path=tmp_path / "cache.sqlite",
        )
    assert caught.value.message == "Input needs at least two artifacts"


def _strip_volatile(result: dict[str, Any]) -> dict[str, Any]:
    clean = copy.deepcopy(result)
    clean["runner"].pop("started_at")
    clean["runner"].pop("finished_at")
    clean["resource_use"].pop("duration_ms")
    return clean


def test_unusual_pairs_end_to_end_with_stub_encoder(
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_path: Path,
    tmp_inputs: Callable[..., InputSet],
    monkeypatch: pytest.MonkeyPatch,
    no_network: list[object],
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    tmp_inputs("markdown")
    records = make_records(32)
    first = engines.run_unusual_pairs(
        records,
        model_dir=fake_model_dir,
        top_k=20,
        max_artifacts=3000,
        cache_path=tmp_path / "one" / "cache.sqlite",
    )
    second = engines.run_unusual_pairs(
        records,
        model_dir=fake_model_dir,
        top_k=20,
        max_artifacts=3000,
        cache_path=tmp_path / "two" / "cache.sqlite",
    )
    assert first.result["status"] == "completed"
    assert first.result["outputs"]
    assert _strip_volatile(first.result) == _strip_volatile(second.result)
    assert no_network == []


def test_unusual_pairs_follows_record_order(
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    records = make_records(12)
    outcome = engines.run_unusual_pairs(
        records,
        model_dir=fake_model_dir,
        top_k=5,
        max_artifacts=3000,
        cache_path=tmp_path / "cache.sqlite",
    )
    assert outcome.result["scope"]["read_artifact_ids"] == [r.id for r in records]


def test_hashing_encode_is_the_stub_used_by_the_fixture(
    stub_encoders: None, fake_model_dir: Path
) -> None:
    assert engines.load_local_encode(fake_model_dir) is hashing_encode


# --- Wording-and-meaning call -----------------------------------------------

PAIR_FIELDS = (
    "left_id",
    "right_id",
    "rank",
    "hsi_score",
    "lsa_sim",
    "semantic_sim",
    "lexical_sim",
    "bm25_sim",
)
ENGINE_CODES = re.compile(r"\b(R" + r"S|H" + r"SI)\b")


def _fields(pairs: Any) -> list[tuple[Any, ...]]:
    return [tuple(pair[name] for name in PAIR_FIELDS) for pair in pairs]


def test_wording_params_hash_equals_the_recorded_rebuild() -> None:
    assert engines.RECORDED_PARAMS_HASH == "7affae3c94c6bed9"
    assert engines.wording_params_hash(200) == engines.RECORDED_PARAMS_HASH


def test_wording_params_hash_matches_other_recorded_values() -> None:
    assert engines.wording_params_hash(20).startswith("5b4b370a")
    assert engines.wording_params_hash(100).startswith("0b2948b9")


def test_wording_params_has_the_recorded_settings() -> None:
    params = engines.wording_params(200)
    assert params["tier"] == 1
    assert params["threshold"] is None
    assert params["ranking"] == "percentile"
    assert params["lexical"] == "hybrid"
    assert params["top_k"] == 200
    assert params["min_percentile"] == 0.0
    assert params["confirm_percentile"] == 0.75
    assert params["seed"] == 42
    assert params["model"] == "all-MiniLM-L6-v2"
    assert params["chunking"] is True
    assert params["dense_vectors"] is None
    assert params["pinecone"] is False


def test_wording_call_order_and_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np

    reference = engines._reference()
    order: list[str] = []
    args_seen: dict[str, tuple[Any, dict[str, Any]]] = {}
    returned: dict[str, Any] = {}

    def wrap(name: str) -> None:
        original = getattr(reference, name)

        def recorder(*args: Any, **kwargs: Any) -> Any:
            order.append(name)
            args_seen[name] = (args, kwargs)
            value = original(*args, **kwargs)
            returned[name] = value
            return value

        monkeypatch.setattr(reference, name, recorder)

    for name in (
        "compute_lsa_similarity",
        "compute_bm25_similarity",
        "compute_semantic_similarity_tier1",
        "compute_hsi_matrix",
    ):
        wrap(name)
    records = make_records(12)
    outcome = engines.run_wording_and_meaning(records, encode=hashing_encode, top_k=200)
    assert order == [
        "compute_lsa_similarity",
        "compute_bm25_similarity",
        "compute_semantic_similarity_tier1",
        "compute_hsi_matrix",
    ]
    texts = [record.model_text for record in records]
    assert args_seen["compute_lsa_similarity"][0][0] == texts
    assert args_seen["compute_lsa_similarity"][1] == {"seed": 42}
    assert args_seen["compute_bm25_similarity"][0][0] == texts
    tier1_args, tier1_kwargs = args_seen["compute_semantic_similarity_tier1"]
    assert tier1_args[0] == texts
    assert tier1_kwargs == {"encoder": hashing_encode, "chunk_words": 200}
    matrix_args, matrix_kwargs = args_seen["compute_hsi_matrix"]
    artifacts = matrix_args[0]
    assert [item["id"] for item in artifacts] == [record.id for record in records]
    assert [item["text"] for item in artifacts] == texts
    assert artifacts[0]["section"] == ""
    assert artifacts[0]["path"] == records[0].source_ref
    assert artifacts[0]["content_hash"] == records[0].text_sha256
    assert matrix_kwargs["threshold"] is None
    assert matrix_kwargs["ranking"] == "percentile"
    assert matrix_kwargs["top_k"] == 200
    assert matrix_kwargs["min_percentile"] == 0.0
    assert matrix_kwargs["confirm_percentile"] == 0.75
    assert matrix_kwargs["computed_at"] == "1970-01-01T00:00:00+00:00"
    expected_lexical = 0.5 * (
        returned["compute_lsa_similarity"] + returned["compute_bm25_similarity"]
    )
    assert np.allclose(matrix_kwargs["lexical_matrix"], expected_lexical)
    assert matrix_kwargs["bm25_matrix"] is returned["compute_bm25_similarity"]
    assert outcome.settings.top_k == 200
    assert outcome.params_hash == engines.RECORDED_PARAMS_HASH
    assert len(outcome.pairs) == 66


def test_wording_pairs_follow_engine_order_and_are_deterministic() -> None:
    records = make_records(16)
    first = engines.run_wording_and_meaning(records, encode=hashing_encode, top_k=30)
    second = engines.run_wording_and_meaning(records, encode=hashing_encode, top_k=30)
    assert first.pairs == second.pairs
    assert [pair["rank"] for pair in first.pairs] == list(range(1, 31))
    assert first.pairs[0]["source_trail"][0]["retrieved_at"] == "1970-01-01T00:00:00+00:00"


def test_wording_needs_two_records() -> None:
    with pytest.raises(RunError):
        engines.run_wording_and_meaning(make_records(1), encode=hashing_encode, top_k=10)


def test_wording_rejects_top_k_above_the_shared_limit() -> None:
    with pytest.raises(UsageError):
        engines.run_wording_and_meaning(make_records(4), encode=hashing_encode, top_k=201)


def test_wording_progress_lines_are_plain_and_nothing_reaches_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lines: list[str] = []
    engines.run_wording_and_meaning(
        make_records(8), encode=hashing_encode, top_k=5, progress=lines.append
    )
    assert capsys.readouterr().err == ""
    assert lines
    assert all(line.startswith("Wording-and-meaning engine: ") for line in lines)
    assert not any(ENGINE_CODES.search(line) for line in lines)


def test_import_time_note_is_captured_not_printed() -> None:
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]);"
        "from mindrian_eureka.run import engines;"
        "engines._reference();"
        "json.dump(list(engines._reference_notes), sys.stdout)"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-c", code, SRC_DIR], capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    notes = json.loads(done.stdout)
    assert all(note.startswith("Wording-and-meaning engine: ") for note in notes)
    assert not any(ENGINE_CODES.search(note) for note in notes)


# --- Reference parity guard --------------------------------------------------


def test_reference_parity_with_hsi_reference_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = engines._reference()
    data = json.loads(CORPUS_FIXTURE.read_text(encoding="utf-8"))["artifacts"][:20]
    room = tmp_path / "room"
    section = room / "synthetic"
    section.mkdir(parents=True)
    for item in data:
        (section / f"{item['id']}.md").write_text(item["text"], encoding="utf-8")
    out_json = tmp_path / "out" / "hsi.json"
    out_json.parent.mkdir()
    monkeypatch.setattr(
        reference, "make_sentence_transformer_encoder", lambda model_name=None: hashing_encode
    )
    try:
        reference.main([str(room), "--tier", "1", "--top-k", "200", "--output", str(out_json)])
    except SystemExit as stop:
        assert stop.code in (None, 0)
    expected = json.loads(out_json.read_text(encoding="utf-8"))["hsi_pairs"]
    records = [
        Record(
            id=f"synthetic/{item['id']}",
            title="",
            text=item["text"].strip(),
            source_ref=f"synthetic/{item['id']}.md",
            source_file=f"synthetic/{item['id']}.md",
            text_sha256=sha256_text(item["text"].strip()),
        )
        for item in data
    ]
    outcome = engines.run_wording_and_meaning(records, encode=hashing_encode, top_k=200)
    assert len(expected) == 190
    assert _fields(outcome.pairs) == _fields(expected)
    assert tmp_path in room.parents


# --- Manifest sections --------------------------------------------------------


def test_manifest_engine_sections(
    stub_encoders: None, fake_model_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _restorable_env(monkeypatch, OFFLINE_NAMES)
    records = make_records(20)
    unusual = engines.run_unusual_pairs(
        records,
        model_dir=fake_model_dir,
        top_k=10,
        max_artifacts=3000,
        cache_path=tmp_path / "cache.sqlite",
    )
    wording = engines.run_wording_and_meaning(records, encode=hashing_encode, top_k=10)
    sections = engines.manifest_engine_sections(unusual, wording)
    assert set(sections) == {"engines", "settings", "seeds", "engine_notes"}
    assert set(sections["engines"]) == {"unusual_pairs", "wording_and_meaning"}
    assert sections["engines"]["unusual_pairs"]["tie_break"] == engines.TIE_BREAK
    assert sections["engines"]["unusual_pairs"]["scoring"] == "hybrid_2026"
    unusual_engine = sections["engines"]["unusual_pairs"]
    assert unusual_engine["capability_id"] == "opportunity.find_cross_domain_pairs"
    wording_engine = sections["engines"]["wording_and_meaning"]
    assert wording_engine["reference"] == "hsi_reference.py"
    assert wording_engine["params_hash"] == engines.wording_params_hash(10)
    assert len(wording_engine["reference_sha256"]) == 64
    assert sections["settings"]["unusual_pairs"]["top_k"] == 10
    assert sections["settings"]["unusual_pairs"]["svd_random_state"] == 256
    assert sections["settings"]["wording_and_meaning"]["chunk_words"] == 200
    assert sections["settings"]["wording_and_meaning"]["max_chunks"] == 12
    assert sections["seeds"] == {
        "unusual_pairs_svd_random_state": 256,
        "wording_and_meaning_lsa_seed": 42,
    }
    notes = sections["engine_notes"]
    assert notes == sorted(set(notes))
    json.dumps(sections)
