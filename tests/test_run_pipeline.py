"""Tests for the pipeline of `eureka run` (pipeline.py)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from collections.abc import Callable, Iterator
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from conftest import InputSet
from mindrian_eureka.run import corpus, engines, pipeline
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import (
    LABEL,
    SUMMARY_LINE,
    RunError,
    UsageError,
)
from mindrian_eureka.run.mapping import MappingConfig, load_mapping_file, mapping_from_flags
from mindrian_eureka.run.pipeline import RunRequest, run_pipeline

RANKED_FILES = ("unusual-pairs.json", "wording-and-meaning-pairs.json", "ranked-pairs.md")
HASHED_FILES = (*RANKED_FILES, "corpus/records.jsonl")
ALL_FILES = (*HASHED_FILES, "manifest.json", "run-info.json")
MANIFEST_KEYS = {
    "schema_version",
    "label",
    "score_meaning",
    "tool",
    "inputs",
    "corpus",
    "settings",
    "seeds",
    "model",
    "environment",
    "outputs",
    "engine_notes",
}


def make_console(quiet: bool = False) -> tuple[Console, StringIO, StringIO]:
    out, err = StringIO(), StringIO()
    return Console(quiet=quiet, no_color=True, stdout=out, stderr=err), out, err


def csv_mapping(flags: list[str]) -> MappingConfig | None:
    return mapping_from_flags(
        id_column=flags[flags.index("--id-column") + 1] if "--id-column" in flags else None,
        title_column=flags[flags.index("--title-column") + 1]
        if "--title-column" in flags
        else None,
        text_columns=[flags[i + 1] for i, item in enumerate(flags) if item == "--text-column"],
        source_column=None,
        delimiter=None,
    )


def tree_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        digest.update(str(path.relative_to(folder)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def run(
    inputs: InputSet,
    out: Path,
    model: Path,
    *,
    console: Console | None = None,
    **extra: Any,
) -> pipeline.RunSummary:
    mapping = extra.pop("mapping", csv_mapping(inputs.mapping_flags))
    request = RunRequest(
        input_dir=inputs.folder, out_dir=out, mapping=mapping, model_path=model, **extra
    )
    return run_pipeline(request, console or make_console()[0])


def read(out: Path, name: str) -> bytes:
    return (out / name).read_bytes()


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


# --- Happy paths ------------------------------------------------------------


@pytest.mark.parametrize("kind", ["markdown", "csv"])
def test_happy_path_writes_every_file(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path, kind: str
) -> None:
    inputs = tmp_inputs(kind)
    out = tmp_path / "out"
    summary = run(inputs, out, fake_model_dir, top_k=15)
    for name in ALL_FILES:
        assert (out / name).is_file(), name
    assert summary.unusual_pairs > 0
    assert summary.wording_and_meaning_pairs > 0
    assert summary.records_used == 32
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        document = json.loads(read(out, name))
        ranks = [pair["rank"] for pair in document["pairs"]]
        assert ranks == list(range(1, len(ranks) + 1))
        assert 0 < len(ranks) <= 15
    manifest = json.loads(read(out, "manifest.json"))
    assert set(manifest) == MANIFEST_KEYS
    listed = {item["path"]: item for item in manifest["outputs"]}
    assert set(listed) == set(HASHED_FILES)
    for relative, item in listed.items():
        data = read(out, relative)
        assert item["sha256"] == hashlib.sha256(data).hexdigest()
        assert item["bytes"] == len(data)
    assert listed["unusual-pairs.json"]["pairs"] == summary.unusual_pairs
    assert listed["wording-and-meaning-pairs.json"]["top_k_reached"] is True
    assert summary.manifest_sha256 == hashlib.sha256(read(out, "manifest.json")).hexdigest()
    info = json.loads(read(out, "run-info.json"))
    assert info["manifest_sha256"] == summary.manifest_sha256


def test_manifest_holds_no_absolute_path(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    run(inputs, out, fake_model_dir)
    manifest = json.loads(read(out, "manifest.json"))

    def strings(value: object) -> Iterator[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)

    for text in strings(manifest):
        assert not text.startswith("/"), text
        assert str(tmp_path) not in text
        assert str(env) not in text


def test_mapping_file_and_flags_give_equal_ranked_files(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("csv")
    plain = tmp_path / "plain-mapping.json"
    plain.write_text(
        json.dumps(
            {
                "schema_version": "eureka.run-mapping.v1",
                "files": {
                    "*": {
                        "id_column": "case_id",
                        "title_column": "title",
                        "text_columns": ["description"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    from_flags = tmp_path / "by-flags"
    from_file = tmp_path / "by-file"
    run(inputs, from_flags, fake_model_dir)
    run(inputs, from_file, fake_model_dir, mapping=load_mapping_file(plain))
    for name in (*RANKED_FILES, "corpus/records.jsonl"):
        assert read(from_flags, name) == read(from_file, name), name


def test_both_engines_get_same_records_in_same_order(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, tuple[Any, ...]] = {}
    real_unusual = engines.run_unusual_pairs
    real_wording = engines.run_wording_and_meaning

    def unusual(records: Any, **kwargs: Any) -> Any:
        seen["unusual"] = tuple(records)
        return real_unusual(records, **kwargs)

    def wording(records: Any, **kwargs: Any) -> Any:
        seen["wording"] = tuple(records)
        return real_wording(records, **kwargs)

    monkeypatch.setattr(engines, "run_unusual_pairs", unusual)
    monkeypatch.setattr(engines, "run_wording_and_meaning", wording)
    inputs = tmp_inputs("markdown")
    run(inputs, tmp_path / "out", fake_model_dir)
    assert seen["unusual"] == seen["wording"]
    ids = [record.id for record in seen["unusual"]]
    assert ids == sorted(ids)
    assert ids == inputs.ids


def test_source_folder_is_not_changed(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    for kind in ("markdown", "csv"):
        inputs = tmp_inputs(kind, name=f"inputs-{kind}")
        before = tree_hash(inputs.folder)
        run(inputs, tmp_path / f"out-{kind}", fake_model_dir)
        assert tree_hash(inputs.folder) == before


def test_network_stays_silent(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    no_network: list[object],
) -> None:
    run(tmp_inputs("markdown"), tmp_path / "out", fake_model_dir)
    assert no_network == []


# --- Output folder rules ----------------------------------------------------


def test_out_inside_input_is_usage_error(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet]
) -> None:
    inputs = tmp_inputs("markdown")
    with pytest.raises(UsageError):
        run(inputs, inputs.folder / "result", fake_model_dir)
    assert not (inputs.folder / "result").exists()


def test_foreign_out_folder_is_refused_and_untouched(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "mine"
    out.mkdir()
    (out / "notes.txt").write_text("keep me", encoding="utf-8")
    before = tree_hash(out)
    with pytest.raises(UsageError):
        run(tmp_inputs("markdown"), out, fake_model_dir)
    assert tree_hash(out) == before


def test_second_run_replaces_first_run_folder(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    run(inputs, out, fake_model_dir)
    (out / "leftover.txt").write_text("old", encoding="utf-8")
    run(inputs, out, fake_model_dir)
    assert not (out / "leftover.txt").exists()
    assert (out / "manifest.json").is_file()
    assert not [item for item in tmp_path.iterdir() if ".staging-" in item.name]


def test_engine_error_leaves_no_staging_and_keeps_previous_run(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    run(inputs, out, fake_model_dir)
    before = tree_hash(out)

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RunError("engine stopped")

    monkeypatch.setattr(engines, "run_wording_and_meaning", boom)
    with pytest.raises(RunError):
        run(inputs, out, fake_model_dir)
    assert tree_hash(out) == before
    assert not [item for item in tmp_path.iterdir() if ".staging-" in item.name]


def test_keyboard_interrupt_propagates_and_cleans_up(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def stop(*args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(engines, "run_unusual_pairs", stop)
    out = tmp_path / "out"
    with pytest.raises(KeyboardInterrupt):
        run(tmp_inputs("markdown"), out, fake_model_dir)
    assert not out.exists()
    assert not [item for item in tmp_path.iterdir() if ".staging-" in item.name]


# --- Caps, drops, empty result ----------------------------------------------


def test_cap_is_reported_everywhere(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    console, _out, err = make_console()
    out = tmp_path / "out"
    summary = run(tmp_inputs("markdown"), out, fake_model_dir, console=console, max_artifacts=10)
    manifest = json.loads(read(out, "manifest.json"))
    (hit,) = manifest["corpus"]["caps_hit"]
    assert hit["limit"] == 10
    assert hit["records_in"] == 32
    assert hit["records_used"] == 10
    assert hit["dropped_count"] == 22
    assert summary.caps_hit[0]["limit"] == 10
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        notes = " ".join(json.loads(read(out, name))["notes"])
        assert "limit of 10 records" in notes
    assert "limit of 10 records" in err.getvalue()
    assert "Caps hit: The limit of 10 records" in summary.lines()


def test_short_records_are_dropped_and_listed(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown", count=12)
    for index in range(3):
        (inputs.folder / f"short{index}.md").write_text(
            f"# Short {index}\n\nToo short.\n", encoding="utf-8"
        )
    out = tmp_path / "out"
    summary = run(inputs, out, fake_model_dir)
    manifest = json.loads(read(out, "manifest.json"))
    dropped = manifest["corpus"]["dropped"]
    assert len(dropped) == 3
    assert {item["reason"] for item in dropped} == {"body_under_50_chars"}
    assert summary.dropped_count == 3
    assert summary.records_used == 12


def test_empty_result_is_not_an_error(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    console, _out, err = make_console()
    out = tmp_path / "out"
    summary = run(tmp_inputs("markdown", count=4), out, fake_model_dir, console=console)
    assert summary.unusual_pairs == 0
    document = json.loads(read(out, "unusual-pairs.json"))
    assert document["pairs"] == []
    assert "No candidate pairs were returned for this collection." in document["notes"]
    assert "returned no candidate pairs" in err.getvalue()
    assert any("returned no candidate pairs" in item for item in summary.warnings)
    assert LABEL in read(out, "unusual-pairs.json").decode("utf-8")


# --- Model, dry run, cache, threads, umask, modes ---------------------------


def test_missing_model_stops_before_the_corpus(
    env: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the corpus must not be read")

    monkeypatch.setattr(corpus, "build_corpus", forbidden)
    out = tmp_path / "out"
    inputs = tmp_inputs("markdown")
    request = RunRequest(input_dir=inputs.folder, out_dir=out)
    with pytest.raises(RunError) as caught:
        run_pipeline(request, make_console()[0])
    assert caught.value.message.startswith("No local model found.")
    assert "Fix:" in caught.value.message
    assert not out.exists()


def test_unusable_explicit_model_is_reported(
    env: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    with pytest.raises(RunError) as caught:
        run(inputs, tmp_path / "out", tmp_path / "no-such-model")
    assert "--model-path" in caught.value.message
    assert not (tmp_path / "out").exists()


def test_dry_run_loads_no_model_and_writes_nothing(
    env: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    request = RunRequest(input_dir=inputs.folder, out_dir=out, dry_run=True)
    summary = run_pipeline(request, make_console()[0])
    assert not out.exists()
    assert summary.dry_run is True
    assert summary.files == ()
    assert summary.manifest_sha256 is None
    text = summary.lines()
    assert text.startswith("Eureka dry run finished. No model was loaded and nothing was written.")
    assert "Manifest:" not in text
    assert "Report:" not in text
    assert text.splitlines()[-1] == SUMMARY_LINE


def test_summary_lines_and_json(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    summary = run(tmp_inputs("markdown"), out, fake_model_dir)
    lines = summary.lines().splitlines()
    assert lines[0] == "Eureka run finished."
    assert lines[1] == f"Output folder: {out}"
    assert lines[2] == "Records: 32 used, 32 read, 0 dropped"
    assert lines[3].startswith("Find Unusual Pairs Across a Research Collection: ")
    assert lines[3].endswith("(unusual-pairs.json)")
    assert lines[4].startswith("Rank Unusual Pairs by Wording and Meaning: ")
    assert lines[5] == "Report: ranked-pairs.md"
    assert lines[6] == f"Manifest: manifest.json (sha256 {summary.manifest_sha256})"
    assert lines[7] == "Caps hit: none"
    assert lines[-1] == SUMMARY_LINE
    document = summary.to_json_dict()
    assert document["schema"] == "eureka.run-summary.v1"
    assert document["label"] == LABEL
    assert document["summary_line"] == SUMMARY_LINE
    assert document["out_dir"] == str(out)
    json.dumps(document)


@pytest.mark.parametrize("use_cache", [True, False])
def test_cache_use(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    use_cache: bool,
) -> None:
    cache_dir = env / "cache"
    assert not cache_dir.exists()
    run(tmp_inputs("markdown"), tmp_path / "out", fake_model_dir, use_cache=use_cache)
    assert cache_dir.exists() is use_cache


def test_threads_sets_variables(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
    for name in names:
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)
    torch_module = sys.modules.get("torch")
    previous = torch_module.get_num_threads() if torch_module is not None else None
    try:
        run(tmp_inputs("markdown"), tmp_path / "out", fake_model_dir, threads=2)
        for name in names:
            assert os.environ[name] == "2"
        manifest = json.loads(read(tmp_path / "out", "manifest.json"))
        assert manifest["environment"]["threads_requested"] == 2
    finally:
        if torch_module is not None and previous is not None:
            torch_module.set_num_threads(previous)


def test_umask_is_restored(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    old = os.umask(0o022)
    try:
        run(tmp_inputs("markdown"), tmp_path / "out", fake_model_dir)
        assert os.umask(0o022) == 0o022
    finally:
        os.umask(old)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_output_modes_are_owner_only(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run(tmp_inputs("markdown"), out, fake_model_dir)
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    assert stat.S_IMODE((out / "corpus").stat().st_mode) == 0o700
    for name in ALL_FILES:
        assert stat.S_IMODE((out / name).stat().st_mode) == 0o600, name


@pytest.mark.parametrize(
    ("top_k", "max_artifacts"), [(0, 100), (201, 100), (10, 1), (10, 5001)]
)
def test_settings_out_of_range_are_usage_errors(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    top_k: int,
    max_artifacts: int,
) -> None:
    with pytest.raises(UsageError):
        run(
            tmp_inputs("markdown"),
            tmp_path / "out",
            fake_model_dir,
            top_k=top_k,
            max_artifacts=max_artifacts,
        )
