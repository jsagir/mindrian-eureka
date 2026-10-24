"""RUN-04 proof: two runs on the same input give byte-identical ranked output."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import site
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import InputSet
from mindrian_eureka.cli import main
from mindrian_eureka.run.output import canonical_json

REPO = Path(__file__).resolve().parents[1]
RANKED = ("unusual-pairs.json", "wording-and-meaning-pairs.json", "ranked-pairs.md")
RANKED_AND_CORPUS = (*RANKED, "corpus/records.jsonl")
STABLE = (*RANKED_AND_CORPUS, "manifest.json")
ALL_FILES = (*STABLE, "run-info.json")
JSON_FILES = ("unusual-pairs.json", "wording-and-meaning-pairs.json", "manifest.json")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:")


def cli_run(folder: Path, out: Path, model: Path, *extra: str) -> Path:
    code = main(["run", str(folder), "--out", str(out), "--model-path", str(model), *extra])
    assert code == 0
    return out


def same(first: Path, second: Path, names: tuple[str, ...]) -> None:
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


# --- (a) repeat runs ----------------------------------------------------------


def test_two_runs_give_byte_equal_files(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    first = cli_run(inputs.folder, tmp_path / "one", fake_model_dir)
    second = cli_run(inputs.folder, tmp_path / "two", fake_model_dir)
    same(first, second, STABLE)
    assert (first / "run-info.json").read_bytes() != (second / "run-info.json").read_bytes()
    for folder in (first, second):
        info = json.loads((folder / "run-info.json").read_text(encoding="utf-8"))
        manifest_hash = hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest()
        assert info["manifest_sha256"] == manifest_hash


def test_csv_runs_are_byte_equal(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("csv")
    flags = list(inputs.mapping_flags)
    first = cli_run(inputs.folder, tmp_path / "one", fake_model_dir, *flags)
    second = cli_run(inputs.folder, tmp_path / "two", fake_model_dir, *flags)
    same(first, second, STABLE)


# --- (b) cache states ---------------------------------------------------------


def test_cold_warm_and_no_cache_runs_are_equal(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    cache_dir = env / "cache"
    assert not cache_dir.exists()
    cold = cli_run(inputs.folder, tmp_path / "cold", fake_model_dir)
    assert (cache_dir / "embeddings.sqlite3").is_file()
    warm = cli_run(inputs.folder, tmp_path / "warm", fake_model_dir)
    none = cli_run(inputs.folder, tmp_path / "none", fake_model_dir, "--no-cache")
    same(cold, warm, STABLE)
    same(cold, none, STABLE)


# --- (c) moved input ----------------------------------------------------------


def test_moved_input_folder_gives_equal_files(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    moved = tmp_path / "elsewhere" / "a-different-name"
    shutil.copytree(inputs.folder, moved)
    first = cli_run(inputs.folder, tmp_path / "one", fake_model_dir)
    second = cli_run(moved, tmp_path / "two", fake_model_dir)
    same(first, second, STABLE)


# --- (d) CRLF -----------------------------------------------------------------


def test_crlf_input_gives_equal_ranked_files(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    crlf = tmp_path / "crlf"
    shutil.copytree(inputs.folder, crlf)
    for path in crlf.rglob("*.md"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    first = cli_run(inputs.folder, tmp_path / "one", fake_model_dir)
    second = cli_run(crlf, tmp_path / "two", fake_model_dir)
    same(first, second, RANKED_AND_CORPUS)
    assert (first / "manifest.json").read_bytes() != (second / "manifest.json").read_bytes()


# --- (e) shuffled CSV rows ----------------------------------------------------


def test_shuffled_csv_rows_give_equal_ranked_files(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("csv")
    flags = list(inputs.mapping_flags)
    shuffled = tmp_path / "shuffled"
    shuffled.mkdir()
    with (inputs.folder / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    with (shuffled / "records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(rows[0])
        writer.writerows(reversed(rows[1:]))
    assert (shuffled / "records.csv").read_bytes() != (inputs.folder / "records.csv").read_bytes()
    first = cli_run(inputs.folder, tmp_path / "one", fake_model_dir, *flags)
    second = cli_run(shuffled, tmp_path / "two", fake_model_dir, *flags)
    same(first, second, RANKED_AND_CORPUS)


# --- (f) threads --------------------------------------------------------------


def test_one_thread_and_default_give_equal_ranked_files(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)
    inputs = tmp_inputs("markdown")
    default = cli_run(inputs.folder, tmp_path / "default", fake_model_dir)
    single = cli_run(inputs.folder, tmp_path / "single", fake_model_dir, "--threads", "1")
    same(default, single, RANKED_AND_CORPUS)


# --- (g) no times, no paths ---------------------------------------------------


def _real_home() -> str | None:
    try:
        import pwd
    except ImportError:
        return None
    return pwd.getpwuid(os.getuid()).pw_dir


def test_stable_files_hold_no_time_and_no_local_path(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    out = cli_run(inputs.folder, tmp_path / "out", fake_model_dir)
    forbidden = [str(tmp_path), str(env), str(fake_model_dir), str(inputs.folder)]
    real_home = _real_home()
    if real_home and real_home != "/":
        forbidden.append(real_home)
    for name in STABLE:
        text = (out / name).read_text(encoding="utf-8")
        assert TIMESTAMP.search(text) is None, name
        for value in forbidden:
            assert value not in text, (name, value)
    info = (out / "run-info.json").read_text(encoding="utf-8")
    assert TIMESTAMP.search(info) is not None


# --- (h) canonical writer only ------------------------------------------------


@pytest.mark.parametrize("name", [*JSON_FILES, "run-info.json"])
def test_json_files_are_canonical(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    name: str,
) -> None:
    out = cli_run(tmp_inputs("markdown").folder, tmp_path / "out", fake_model_dir)
    data = (out / name).read_bytes()
    assert canonical_json(json.loads(data)) == data


def test_records_file_lines_are_compact_json(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = cli_run(tmp_inputs("markdown").folder, tmp_path / "out", fake_model_dir)
    lines = (out / "corpus" / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 33
    assert json.loads(lines[0])["record_type"] == "header"
    ids = [json.loads(line)["id"] for line in lines[1:]]
    assert ids == sorted(ids)


# --- (i) real model, gated ----------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("EUREKA_TEST_MODEL_PATH"),
    reason="needs EUREKA_TEST_MODEL_PATH with a local model folder",
)
def test_real_model_runs_are_equal_across_hash_seeds(
    isolated_env: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    model = os.environ["EUREKA_TEST_MODEL_PATH"]
    inputs = tmp_inputs("markdown")
    outs: list[Path] = []
    for seed in ("0", "1"):
        out = tmp_path / f"real-{seed}"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPO / "src")
        environment["PYTHONHASHSEED"] = seed
        # isolated_env moves HOME; keep the user site (installed libraries) visible.
        environment["PYTHONUSERBASE"] = site.getuserbase()
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "mindrian_eureka.cli",
                "run",
                str(inputs.folder),
                "--out",
                str(out),
                "--model-path",
                model,
            ],
            capture_output=True,
            text=True,
            env=environment,
            timeout=600,
        )
        assert done.returncode == 0, done.stderr
        outs.append(out)
    same(outs[0], outs[1], STABLE)
