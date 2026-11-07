"""Tests for the staging of a host bundle as the CSV input of the pipeline."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from host_run_support import make_request
from mindrian_eureka.run.contracts import normalize_text
from mindrian_eureka.run.corpus import build_corpus

POSIX = sys.platform != "win32"
BODY = "Synthetic body about {tag}. It has enough words to pass the short body rule."


def _artifact(artifact_id: str, text: str, ref: str | None = None) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "source_ref": ref or f"host://{artifact_id}",
        "title": f"Title of {artifact_id}",
        "text": text,
    }


def _stage(tmp_path: Path, request: dict[str, Any], name: str = "run") -> Any:
    from mindrian_eureka.host_run.bundle import stage_bundle
    from mindrian_eureka.host_run.contracts import normalize_request

    return stage_bundle(normalize_request(request), tmp_path / name)


def test_stage_writes_the_expected_files(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.bundle import StagedBundle

    staged = _stage(tmp_path, make_request())
    run_dir = tmp_path / "run"
    assert isinstance(staged, StagedBundle)
    assert (run_dir / "in" / "artifacts.csv").is_file()
    assert (run_dir / "mapping.json").is_file()
    assert [path.name for path in (run_dir / "in").iterdir()] == ["artifacts.csv"]
    assert staged.input_dir == run_dir / "in"
    assert staged.mapping_path == run_dir / "mapping.json"
    if POSIX:
        assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE((run_dir / "in").stat().st_mode) == 0o700
        assert stat.S_IMODE((run_dir / "in" / "artifacts.csv").stat().st_mode) == 0o600
        assert stat.S_IMODE((run_dir / "mapping.json").stat().st_mode) == 0o600


def test_a_reused_job_folder_is_an_error(tmp_path: Path) -> None:
    _stage(tmp_path, make_request())
    with pytest.raises(FileExistsError):
        _stage(tmp_path, make_request())


def test_staging_is_byte_stable(tmp_path: Path) -> None:
    request = make_request()
    _stage(tmp_path, request, "one")
    _stage(tmp_path, request, "two")
    reordered = make_request()
    reordered["artifacts"] = list(reversed(reordered["artifacts"]))
    _stage(tmp_path, reordered, "three")
    for name in ("two", "three"):
        for rel in ("in/artifacts.csv", "mapping.json"):
            assert (tmp_path / "one" / rel).read_bytes() == (tmp_path / name / rel).read_bytes()


def test_csv_round_trip_keeps_hard_text(tmp_path: Path) -> None:
    hard = [
        'Plain, with commas, and "double quotes" inside the sentence of this record.',
        "Line one of the record body is here.\nLine two follows after a newline mark.",
        "Carriage return follows here.\r\nSecond line after the CRLF pair, long enough.",
        "Tab\tseparated\tcells inside one body of text that is long enough to keep.",
        "Naive café 中文 ไทย text that holds non-ASCII letters, kept.",
        "=SUM(A1:A9) starts with an equals sign and then goes on long enough to keep.",
    ]
    request = make_request(
        artifacts=[_artifact(f"hard-{index}", text) for index, text in enumerate(hard)]
    )
    staged = _stage(tmp_path, request)
    corpus = build_corpus(staged.input_dir, mapping=staged.mapping)
    by_id = {record.id: record for record in corpus.records}
    assert len(by_id) == len(hard)
    for index, text in enumerate(hard):
        assert by_id[f"artifacts/hard-{index}"].text == normalize_text(text)


def test_record_ids_match_the_corpus_builder(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.bundle import record_id_for

    ids = ["claim:abc/1", "claim:abc/2", "note 7", "ünï-9", "plain-id"]
    request = make_request(artifacts=[_artifact(item, BODY.format(tag=item)) for item in ids])
    staged = _stage(tmp_path, request)
    corpus = build_corpus(staged.input_dir, mapping=staged.mapping)
    built = sorted(record.id for record in corpus.records)
    assert built == sorted(staged.id_map)
    assert sorted(record_id_for(item) for item in ids) == built


def test_id_map_keeps_host_ids_and_source_refs(tmp_path: Path) -> None:
    ids = ["claim:abc/1", "note 7", "plain-id"]
    request = make_request(
        artifacts=[
            _artifact(item, BODY.format(tag=item), ref=f"host://source/{index}")
            for index, item in enumerate(ids)
        ]
    )
    staged = _stage(tmp_path, request)
    corpus = build_corpus(staged.input_dir, mapping=staged.mapping)
    host_refs = {item: f"host://source/{index}" for index, item in enumerate(ids)}
    for entry in staged.id_map.values():
        assert entry.source_ref == host_refs[entry.artifact_id]
    for record in corpus.records:
        assert record.source_ref == staged.id_map[record.id].source_ref
        assert not record.source_ref.startswith("artifacts.csv#")


def test_short_text_is_dropped_not_refused(tmp_path: Path) -> None:
    request = make_request(
        artifacts=[
            _artifact("tiny", "too short"),
            _artifact("long-a", BODY.format(tag="a")),
            _artifact("long-b", BODY.format(tag="b")),
        ]
    )
    staged = _stage(tmp_path, request)
    corpus = build_corpus(staged.input_dir, mapping=staged.mapping)
    assert [item.id for item in corpus.dropped] == ["artifacts/tiny"]
    assert len(corpus.records) == 2


def test_html_like_text_is_not_rewritten(tmp_path: Path) -> None:
    text = "<b>bold</b> & more words, so the record body is long enough to pass the rule."
    request = make_request(
        artifacts=[_artifact("html-a", text), _artifact("html-b", BODY.format(tag="b"))]
    )
    staged = _stage(tmp_path, request)
    corpus = build_corpus(staged.input_dir, mapping=staged.mapping)
    by_id = {record.id: record for record in corpus.records}
    assert by_id["artifacts/html-a"].text == text


def test_mapping_hash_is_stable(tmp_path: Path) -> None:
    first = _stage(tmp_path, make_request(), "one")
    second = _stage(tmp_path, make_request(), "two")
    assert first.mapping.sha256 == second.mapping.sha256
    data = json.loads((tmp_path / "one" / "mapping.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "eureka.run-mapping.v1"
    assert set(data["files"]) == {"artifacts.csv"}
    assert data["files"]["artifacts.csv"]["html"] == "never"


def test_staging_makes_no_network_call_and_reads_no_request_path(
    tmp_path: Path, no_network: list[object]
) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "other.txt").write_text("keep", encoding="utf-8")
    before = sorted(os.listdir(tmp_path))
    from mindrian_eureka.host_run.bundle import stage_bundle
    from mindrian_eureka.host_run.contracts import normalize_request

    run_dir = tmp_path / "run"
    stage_bundle(normalize_request(make_request()), run_dir)
    after = sorted(os.listdir(tmp_path))
    assert no_network == []
    assert sorted(set(after) - set(before)) == ["run"]
    assert sorted(set(before) - set(after)) == []
    assert (sandbox / "other.txt").read_text(encoding="utf-8") == "keep"
