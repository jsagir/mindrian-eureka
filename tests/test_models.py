"""Tests for the shared model discovery (models.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from mindrian_eureka import models
from mindrian_eureka.models import (
    ENV_HSI_MODEL_PATH,
    ENV_RS_MODEL_PATH,
    HF_MODEL_DIR_NAME,
    discover_model,
    missing_files,
    missing_model_message,
    os_variants,
)

SRC = Path(__file__).resolve().parents[1] / "src"


def _make_valid(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text("{}", encoding="utf-8")
    (folder / "modules.json").write_text("[]", encoding="utf-8")
    (folder / "model.safetensors").write_bytes(b"w")
    (folder / "tokenizer.json").write_text("{}", encoding="utf-8")
    return folder


def _snapshot(root: Path, name: str, *, valid: bool = True) -> Path:
    folder = root / HF_MODEL_DIR_NAME / "snapshots" / name
    if valid:
        return _make_valid(folder)
    folder.mkdir(parents=True)
    (folder / "config.json").write_text("{}", encoding="utf-8")
    return folder


def _ref(root: Path, name: str) -> None:
    refs = root / HF_MODEL_DIR_NAME / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    (refs / "main").write_text(name + "\n", encoding="utf-8")


def _default_root(home: Path) -> Path:
    return home / ".cache" / "huggingface" / "hub"


# --- missing_files ------------------------------------------------------------


def test_fake_model_dir_is_valid(fake_model_dir: Path) -> None:
    assert missing_files(fake_model_dir) == []


@pytest.mark.parametrize(
    ("remove", "expected"),
    [
        ("config.json", ["config.json"]),
        ("modules.json", ["modules.json"]),
        ("model.safetensors", ["model.safetensors or pytorch_model.bin"]),
        ("tokenizer.json", ["tokenizer.json or vocab.txt"]),
    ],
)
def test_missing_files_names_the_gap(
    fake_model_dir: Path, remove: str, expected: list[str]
) -> None:
    (fake_model_dir / remove).unlink()
    assert missing_files(fake_model_dir) == expected


def test_alternative_weight_and_tokenizer_files_count(fake_model_dir: Path) -> None:
    (fake_model_dir / "model.safetensors").unlink()
    (fake_model_dir / "tokenizer.json").unlink()
    (fake_model_dir / "pytorch_model.bin").write_bytes(b"w")
    (fake_model_dir / "vocab.txt").write_text("a", encoding="utf-8")
    assert missing_files(fake_model_dir) == []


def test_missing_files_on_absent_folder_lists_all(tmp_path: Path) -> None:
    assert len(missing_files(tmp_path / "nope")) == 4


# --- source order ---------------------------------------------------------------


def test_explicit_path_wins(fake_model_dir: Path, tmp_path: Path) -> None:
    other = _make_valid(tmp_path / "other")
    result = discover_model(
        fake_model_dir, env={ENV_RS_MODEL_PATH: str(other)}, home=tmp_path / "h"
    )
    assert result.ok
    assert result.path == fake_model_dir
    assert result.origin == "--model-path"


def test_rs_variable_before_hsi_variable(tmp_path: Path) -> None:
    first = _make_valid(tmp_path / "first")
    second = _make_valid(tmp_path / "second")
    env = {ENV_RS_MODEL_PATH: str(first), ENV_HSI_MODEL_PATH: str(second)}
    result = discover_model(env=env, home=tmp_path / "h")
    assert result.path == first
    assert result.origin == ENV_RS_MODEL_PATH


def test_hsi_variable_used_when_rs_variable_absent(tmp_path: Path) -> None:
    folder = _make_valid(tmp_path / "m")
    result = discover_model(env={ENV_HSI_MODEL_PATH: str(folder)}, home=tmp_path / "h")
    assert result.ok
    assert result.origin == ENV_HSI_MODEL_PATH


def test_variable_before_cache(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _snapshot(_default_root(home), "a" * 40)
    folder = _make_valid(tmp_path / "m")
    result = discover_model(env={ENV_RS_MODEL_PATH: str(folder)}, home=home)
    assert result.path == folder


def test_empty_variable_counts_as_not_set(tmp_path: Path) -> None:
    result = discover_model(env={ENV_RS_MODEL_PATH: "  "}, home=tmp_path / "h")
    assert not result.ok
    assert not result.problems


# --- no fall-through ------------------------------------------------------------


def test_invalid_explicit_does_not_fall_through(fake_model_dir: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    result = discover_model(bad, env={ENV_RS_MODEL_PATH: str(fake_model_dir)}, home=tmp_path)
    assert not result.ok
    assert result.path is None
    assert result.origin == "--model-path"
    assert "lacks" in result.problems[0]
    assert "config.json" in result.problems[0]
    assert all(ENV_RS_MODEL_PATH not in line for line in result.searched)


def test_missing_folder_in_variable_does_not_fall_through(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _snapshot(_default_root(home), "b" * 40)
    env = {ENV_RS_MODEL_PATH: str(tmp_path / "gone")}
    result = discover_model(env=env, home=home)
    assert not result.ok
    assert "does not exist" in result.problems[0]
    assert ENV_RS_MODEL_PATH in result.problems[0]


# --- Hugging Face cache -----------------------------------------------------------


def test_cache_refs_main_snapshot(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _default_root(home)
    wanted = _snapshot(root, "1" * 40)
    _snapshot(root, "2" * 40)
    _ref(root, "1" * 40)
    result = discover_model(env={}, home=home)
    assert result.ok
    assert result.path == wanted
    assert result.origin == "Hugging Face cache"


def test_cache_two_valid_without_ref_is_ambiguous(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _default_root(home)
    _snapshot(root, "1" * 40)
    _snapshot(root, "2" * 40)
    result = discover_model(env={}, home=home)
    assert not result.ok
    assert result.path is None
    assert "1" * 40 in result.problems[0]
    assert "2" * 40 in result.problems[0]
    assert "--model-path" in result.problems[0]


def test_cache_one_valid_without_ref(tmp_path: Path) -> None:
    home = tmp_path / "home"
    wanted = _snapshot(_default_root(home), "3" * 40)
    result = discover_model(env={}, home=home)
    assert result.path == wanted
    assert result.ok


def test_cache_ref_names_invalid_snapshot_other_is_only_valid(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _default_root(home)
    _snapshot(root, "4" * 40, valid=False)
    good = _snapshot(root, "5" * 40)
    _ref(root, "4" * 40)
    result = discover_model(env={}, home=home)
    assert result.ok
    assert result.path == good


def test_cache_ref_names_invalid_snapshot_two_others_valid_is_ambiguous(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _default_root(home)
    _snapshot(root, "4" * 40, valid=False)
    _snapshot(root, "5" * 40)
    _snapshot(root, "6" * 40)
    _ref(root, "4" * 40)
    result = discover_model(env={}, home=home)
    assert not result.ok
    assert result.problems


def test_cache_only_invalid_snapshot_continues_and_fails_softly(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _snapshot(_default_root(home), "7" * 40, valid=False)
    result = discover_model(env={}, home=home)
    assert not result.ok
    assert not result.problems
    assert any("no valid snapshot" in line for line in result.searched)


def test_cache_model_in_second_root(tmp_path: Path) -> None:
    home = tmp_path / "home"
    first = tmp_path / "hub-a"
    first.mkdir()
    second = tmp_path / "hf-home" / "hub"
    wanted = _snapshot(second, "8" * 40)
    env = {"HF_HUB_CACHE": str(first), "HF_HOME": str(tmp_path / "hf-home")}
    result = discover_model(env=env, home=home)
    assert result.path == wanted
    assert any(str(first) in line and "not in this cache" in line for line in result.searched)


def test_cache_roots_are_not_listed_twice(tmp_path: Path) -> None:
    hub = tmp_path / "hf" / "hub"
    env = {"HF_HUB_CACHE": str(hub), "HF_HOME": str(tmp_path / "hf")}
    result = discover_model(env=env, home=tmp_path / "home")
    cache_lines = [line for line in result.searched if line.startswith("Hugging Face cache")]
    assert len(cache_lines) == 2


def test_no_environment_fresh_home_gives_four_searched_lines(tmp_path: Path) -> None:
    result = discover_model(env={}, home=tmp_path / "fresh")
    assert not result.ok
    assert result.path is None
    assert result.problems == ()
    assert len(result.searched) == 4


def test_default_environment_is_read(
    isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_RS_MODEL_PATH, str(fake_model_dir))
    result = discover_model()
    assert result.ok
    assert result.path == fake_model_dir


def test_searched_line_format(tmp_path: Path) -> None:
    result = discover_model(env={}, home=tmp_path / "fresh")
    assert result.searched[0] == "--model-path: not set (not given)"
    assert result.searched[1] == f"{ENV_RS_MODEL_PATH}: not set (variable not set)"
    assert result.searched[2] == f"{ENV_HSI_MODEL_PATH}: not set (variable not set)"
    assert result.searched[3].startswith("Hugging Face cache: ")


# --- messages -----------------------------------------------------------------------


def test_message_for_nothing_found(tmp_path: Path) -> None:
    result = discover_model(env={}, home=tmp_path / "fresh")
    text = missing_model_message(result)
    assert text.splitlines()[0] == "No local model found."
    for line in result.searched:
        assert line in text
    assert "uv run hf download sentence-transformers/all-MiniLM-L6-v2" in text
    assert "--local-dir all-MiniLM-L6-v2" in text
    assert "On Linux or macOS: export MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/" in text
    assert "On Windows (PowerShell): $env:MINDRIAN_EUREKA_RS_MODEL_PATH" in text
    assert "--model-path" in text


def test_message_for_invalid_source(tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    result = discover_model(bad, env={}, home=tmp_path)
    text = missing_model_message(result, explicit_given=True)
    assert text.splitlines()[0] == "The local model is not usable."
    for line in result.searched:
        assert line in text
    assert result.problems[0] in text
    assert "given with --model-path" in text


# --- os_variants ----------------------------------------------------------------------


def test_os_variants_names_both_systems() -> None:
    text = os_variants("ls", "dir")
    assert text == "On Linux or macOS: ls\nOn Windows (PowerShell): dir"


def test_os_variants_equal_texts_return_text_alone() -> None:
    assert os_variants("uv --version", "uv --version") == "uv --version"


# --- import safety -----------------------------------------------------------------------


def test_module_stays_light_and_clean() -> None:
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import mindrian_eureka.models; "
        "bad = {'numpy', 'huggingface_hub', 'torch', 'socket', 'urllib.request'}; "
        "found = bad & set(sys.modules); "
        "sys.exit(0 if not ({'numpy', 'huggingface_hub', 'torch'} & found) else 1)"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-c", code, str(SRC)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr


def test_constants_have_literal_names() -> None:
    assert models.ENV_RS_MODEL_PATH == "MINDRIAN_EUREKA_RS_MODEL_PATH"
    assert models.ENV_HSI_MODEL_PATH == "MINDRIAN_EUREKA_HSI_MODEL_PATH"
    assert models.MODEL_REPO == "sentence-transformers/all-MiniLM-L6-v2"
