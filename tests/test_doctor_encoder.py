"""The optional encoder profile check D9 of `eureka doctor` (--encoder-profile)."""

from __future__ import annotations

import io
import json
import os
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from mindrian_eureka.cli import main
from mindrian_eureka.doctor import (
    CheckResult,
    Probes,
    Status,
    doctor_command,
    format_report,
    report_json,
    run_checks,
)


def _probes(
    *,
    find_spec: Callable[[str], object | None] | None = None,
    encoder_loader: Callable[[Any, Path], int] | None = None,
    cuda_available: Callable[[], bool] | None = None,
    loader: Callable[[Path], int] | None = None,
) -> Probes:
    uid = os.geteuid() if os.name == "posix" else -1
    return Probes(
        python_version=(3, 12, 3),
        which=lambda name: f"/usr/bin/{name}",
        find_spec=find_spec or (lambda name: object()),
        run_command=lambda args: "uv 0.9.4\n",
        is_posix=True,
        geteuid=lambda: uid,
        loader=loader or (lambda path: 384),
        encoder_loader=encoder_loader or (lambda spec, path: spec.dimension or 0),
        cuda_available=cuda_available or (lambda: True),
    )


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "MINDRIAN_EUREKA_CACHE_DIR": str(tmp_path / "cache"),
        "MINDRIAN_EUREKA_DATA_DIR": str(tmp_path / "data"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }


def _checks(
    tmp_path: Path,
    probes: Probes,
    *,
    model: Path | None = None,
    load_model: bool = False,
    **extra: Any,
) -> list[CheckResult]:
    return run_checks(
        model_path=model,
        load_model=load_model,
        env=_env(tmp_path),
        home=tmp_path / "home",
        probes=probes,
        **extra,
    )


def _d9(
    tmp_path: Path,
    profile: str,
    probes: Probes | None = None,
    *,
    model: Path | None = None,
    load_model: bool = False,
) -> CheckResult:
    results = _checks(
        tmp_path, probes or _probes(), model=model, load_model=load_model, encoder_profile=profile
    )
    found = [item for item in results if item.id == "D9"]
    assert len(found) == 1
    assert results[-1].id == "D9"
    return found[0]


def test_default_report_is_unchanged(tmp_path: Path, fake_model_dir: Path) -> None:
    probes = _probes()
    plain = _checks(tmp_path, probes, model=fake_model_dir)
    none = _checks(tmp_path, probes, model=fake_model_dir, encoder_profile=None)
    assert format_report(plain) == format_report(none)
    assert report_json(plain) == report_json(none)
    assert [item.id for item in none] == ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
    document = json.loads(report_json(none))
    assert sorted(document) == ["checks", "ok", "schema_version"]
    assert document["schema_version"] == "eureka.doctor.v1"
    for check in document["checks"]:
        assert sorted(check) == ["fix", "id", "message", "name", "status"]


def test_unknown_profile_is_a_fail(tmp_path: Path) -> None:
    result = _d9(tmp_path, "nope")
    assert result.status is Status.FAIL
    assert result.message.startswith("Unknown encoder profile")
    assert "cpu-default" in result.message and "gpu-nemotron" in result.message
    assert result.fix == "Use one of: cpu-default, gpu-nemotron"


def test_missing_libraries_for_the_profile(tmp_path: Path) -> None:
    no_transformers = _probes(find_spec=lambda name: None if name == "transformers" else object())
    gpu = _d9(tmp_path, "gpu-nemotron", no_transformers)
    assert gpu.status is Status.FAIL
    assert gpu.fix is not None and "uv sync --extra gpu-encoder" in gpu.fix
    no_st = _probes(find_spec=lambda name: None if name == "sentence_transformers" else object())
    cpu = _d9(tmp_path, "cpu-default", no_st)
    assert cpu.status is Status.FAIL
    assert cpu.fix is not None and "uv sync --extra modern-encoder" in cpu.fix


def test_missing_cuda_device_is_a_fail(tmp_path: Path, fake_model_dir: Path) -> None:
    gpu = _d9(tmp_path, "gpu-nemotron", _probes(cuda_available=lambda: False), model=fake_model_dir)
    assert gpu.status is Status.FAIL
    assert "needs a CUDA device" in gpu.message
    assert gpu.fix is not None
    assert "CUDA build of torch" in gpu.fix
    assert "does not lock" in gpu.fix

    def _never() -> bool:
        raise AssertionError("the cuda probe must not run for a cpu profile")

    cpu = _d9(tmp_path, "cpu-default", _probes(cuda_available=_never))
    assert cpu.status is not Status.FAIL


def test_non_default_profile_needs_a_model_path(tmp_path: Path) -> None:
    loaded = _d9(tmp_path, "gpu-nemotron", load_model=True)
    assert loaded.status is Status.FAIL
    assert loaded.fix is not None and "--model-path" in loaded.fix
    unloaded = _d9(tmp_path, "gpu-nemotron")
    assert unloaded.status is Status.WARN
    assert unloaded.fix is not None and "--model-path" in unloaded.fix
    cpu = _d9(tmp_path, "cpu-default")
    assert cpu.status is Status.PASS


def test_load_checks_the_width(tmp_path: Path, fake_model_dir: Path) -> None:
    ok = _d9(
        tmp_path, "gpu-nemotron", _probes(encoder_loader=lambda spec, path: 2048),
        model=fake_model_dir, load_model=True,
    )
    assert ok.status is not Status.FAIL
    assert "2048" in ok.message and "bfloat16" in ok.message and "cuda" in ok.message

    wrong = _d9(
        tmp_path, "gpu-nemotron", _probes(encoder_loader=lambda spec, path: 384),
        model=fake_model_dir, load_model=True,
    )
    assert wrong.status is Status.FAIL
    assert "384" in wrong.message and "2048" in wrong.message

    def _boom(spec: Any, path: Path) -> int:
        raise OSError("weights are missing")

    failed = _d9(
        tmp_path, "gpu-nemotron", _probes(encoder_loader=_boom),
        model=fake_model_dir, load_model=True,
    )
    assert failed.status is Status.FAIL
    assert "OSError" in failed.message and "weights are missing" in failed.message
    assert "Traceback" not in failed.message

    with_flag = _checks(
        tmp_path, _probes(), model=fake_model_dir, load_model=True, encoder_profile="cpu-default"
    )
    assert "D8" not in [item.id for item in with_flag]
    without_flag = _checks(tmp_path, _probes(), model=fake_model_dir, load_model=True)
    assert "D8" in [item.id for item in without_flag]


def test_unpinned_spike_profile_warns(tmp_path: Path, fake_model_dir: Path) -> None:
    probes = _probes()
    gpu = _d9(tmp_path, "gpu-nemotron", probes, model=fake_model_dir)
    assert gpu.status is Status.WARN
    assert "not pinned" in gpu.message
    results = _checks(
        tmp_path, probes, model=fake_model_dir, encoder_profile="gpu-nemotron"
    )
    assert json.loads(report_json(results))["ok"] is True
    cpu = _d9(tmp_path, "cpu-default", probes, model=fake_model_dir)
    assert cpu.status is Status.PASS


def test_default_loader_is_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_network: list[object]
) -> None:
    from mindrian_eureka import doctor
    from mindrian_eureka.encoder_spec import profile_spec

    seen: dict[str, Any] = {}

    class FakeModel:
        max_seq_length = 256

        def __init__(self, path: str, **kwargs: Any) -> None:
            seen["path"] = path
            seen["kwargs"] = kwargs

        def get_embedding_dimension(self) -> int:
            return 384

        def encode(self, items: Any, **kwargs: Any) -> np.ndarray:
            return np.zeros((len(items), 384))

    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = FakeModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    width = doctor._default_encoder_loader(profile_spec("cpu-default"), tmp_path)
    assert width == 384
    assert seen["path"] == str(tmp_path)
    assert seen["kwargs"]["local_files_only"] is True
    assert no_network == []


def test_doctor_command_passes_the_profile(tmp_path: Path) -> None:
    out = io.StringIO()
    code = doctor_command(
        json_output=False, load_model=False, model_path=None, out=out, encoder_profile="nope"
    )
    assert code == 1
    assert "[FAIL] D9" in out.getvalue()


def test_cli_flag(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["doctor", "--encoder-profile", "nope"])
    shown = capsys.readouterr().out
    assert code == 1
    assert any(line.startswith("[FAIL] D9") for line in shown.splitlines())
    with pytest.raises(SystemExit) as caught:
        main(["doctor", "--help"])
    assert caught.value.code == 0
    assert "--encoder-profile" in capsys.readouterr().out
