"""Pins of the optional gpu-encoder extra, the core dependencies and the lock file."""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _lock() -> dict[str, Any]:
    return tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))


def _version_tuple(text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in text.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def test_core_dependencies_are_unchanged() -> None:
    assert _pyproject()["project"]["dependencies"] == [
        "jsonschema>=4.20,<5",
        "numpy>=2.0,<3",
        "scikit-learn>=1.6,<2",
    ]


def test_gpu_extra_holds_two_packages() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]
    assert extras["gpu-encoder"] == ["sentence-transformers>=5.4.1,<6", "transformers>=5.2,<6"]
    assert extras["modern-encoder"] == ["sentence-transformers>=5.0,<6"]
    assert extras["reference-encoder"] == ["torch>=2.6,<3", "transformers>=4.50,<6"]
    assert extras["hub-gate"] == ["cryptography>=44,<51"]


def test_torch_stays_on_the_cpu_index() -> None:
    config = _pyproject()
    assert config["tool"]["uv"]["sources"]["torch"] == {"index": "pytorch-cpu"}
    assert [index["name"] for index in config["tool"]["uv"]["index"]] == ["pytorch-cpu"]
    extras = config["project"]["optional-dependencies"]
    assert not any("cu1" in item or "cu2" in item for items in extras.values() for item in items)
    assert not any("torch" in item for item in extras["gpu-encoder"])


def test_extra_name_matches_the_profile_table() -> None:
    from mindrian_eureka import encoder_spec

    extras = _pyproject()["project"]["optional-dependencies"]
    assert encoder_spec.GPU_EXTRA in extras
    assert encoder_spec.PROFILE_EXTRA["gpu-nemotron"] == encoder_spec.GPU_EXTRA


def test_lock_lists_the_extra_and_adds_no_package() -> None:
    packages = _lock()["package"]
    own = next(item for item in packages if item["name"] == "mindrian-eureka")
    assert "gpu-encoder" in own["metadata"]["provides-extras"]
    listed = own["optional-dependencies"]["gpu-encoder"]
    assert sorted(item["name"] for item in listed) == ["sentence-transformers", "transformers"]
    names = [item["name"] for item in packages]
    assert not any(name.startswith("nvidia-") or name.startswith("triton") for name in names)
    versions = {item["name"]: item["version"] for item in packages}
    assert _version_tuple(versions["sentence-transformers"]) >= (5, 4, 1)
    assert _version_tuple(versions["transformers"]) >= (5, 2)


def test_lock_is_in_sync_with_pyproject() -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not on PATH")
    done = subprocess.run(
        [uv, "lock", "--check", "--offline"], cwd=ROOT, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
