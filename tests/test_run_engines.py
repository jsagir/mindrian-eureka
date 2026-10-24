"""Tests for the engine facade of `eureka run` (engines.py)."""

from __future__ import annotations

import copy
import json
import os
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
