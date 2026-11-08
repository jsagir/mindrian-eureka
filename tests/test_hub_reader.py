"""Tests for the run-folder reader of the hub."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hub_support import make_run_folder, tree_hash
from mindrian_eureka.hub.contracts import ENGINE_UNUSUAL, ENGINE_WORDING, RunData
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.run.contracts import (
    CORPUS_SCHEMA,
    PAIRS_SCHEMA,
    SCORE_MEANING,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    Record,
    RunError,
    UsageError,
    sha256_bytes,
)
from mindrian_eureka.run.manifest import sha256_file
from mindrian_eureka.run.output import (
    OUTPUT_CORPUS,
    OUTPUT_MANIFEST,
    OUTPUT_MARKDOWN,
    OUTPUT_RUN_INFO,
    OUTPUT_UNUSUAL,
    OUTPUT_WORDING,
    canonical_json,
    is_eureka_run_folder,
)
from mindrian_eureka.run.project import READING_AGREE

FIXED_FILES = [OUTPUT_CORPUS, OUTPUT_UNUSUAL, OUTPUT_WORDING, OUTPUT_MARKDOWN]


# --- helpers ----------------------------------------------------------------


def read_manifest(folder: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((folder / OUTPUT_MANIFEST).read_text(encoding="utf-8"))
    return data


def write_manifest(folder: Path, manifest: dict[str, Any]) -> None:
    (folder / OUTPUT_MANIFEST).write_bytes(canonical_json(manifest))


def rewrite(folder: Path, name: str, data: bytes) -> None:
    """Replace a file and fix its hash in the manifest, so the hash check still passes."""
    (folder / name).write_bytes(data)
    manifest = read_manifest(folder)
    for item in manifest["outputs"]:
        if item["path"] == name:
            item["sha256"] = sha256_bytes(data)
            item["bytes"] = len(data)
    write_manifest(folder, manifest)


def edit_json(folder: Path, name: str, change: Callable[[dict[str, Any]], None]) -> None:
    doc = json.loads((folder / name).read_text(encoding="utf-8"))
    change(doc)
    rewrite(folder, name, canonical_json(doc))


@pytest.fixture
def run(tmp_path: Path) -> Path:
    return make_run_folder(tmp_path)


# --- helper folder ----------------------------------------------------------


def test_helper_folder_is_a_valid_run_folder(run: Path) -> None:
    assert is_eureka_run_folder(run)
    manifest = read_manifest(run)
    assert {item["path"] for item in manifest["outputs"]} == set(FIXED_FILES)
    for item in manifest["outputs"]:
        assert sha256_file(run / item["path"]) == item["sha256"]
        assert (run / item["path"]).stat().st_size == item["bytes"]
    assert (run / OUTPUT_RUN_INFO).is_file()


def test_helper_is_deterministic(tmp_path: Path) -> None:
    first = make_run_folder(tmp_path, name="a")
    second = make_run_folder(tmp_path, name="b")
    assert tree_hash(first) == tree_hash(second)


def test_helper_options(tmp_path: Path) -> None:
    one = load_run(make_run_folder(tmp_path, name="a", pairs_per_engine=(7, 0), n_records=12))
    assert len(one.engines[ENGINE_UNUSUAL].pairs) == 7
    assert len(one.engines[ENGINE_WORDING].pairs) == 0
    zero = load_run(make_run_folder(tmp_path, name="b", zero_pairs=True))
    assert all(not engine.pairs for engine in zero.engines.values())
    copies = load_run(make_run_folder(tmp_path, name="c", copies=3))
    assert len({r.text_sha256 for r in copies.records[:4]}) == 1
    empty = load_run(make_run_folder(tmp_path, name="d", empty_text=2))
    assert [r.text for r in empty.records[-2:]] == ["", ""]
    longer = load_run(make_run_folder(tmp_path, name="e", long_text=2))
    assert sum(1 for r in longer.records if len(r.text) > 4000) == 2
    below = load_run(
        make_run_folder(tmp_path, name="f", wording_floor=0.5, percentile_below_floor=4)
    )
    low = [p for p in below.engines[ENGINE_WORDING].pairs if (p.percentile or 0) < 0.5]
    assert len(low) == 4
    with pytest.raises(ValueError):
        make_run_folder(tmp_path, name="g", percentile_below_floor=1)


def test_helper_hostile_records(tmp_path: Path) -> None:
    data = load_run(make_run_folder(tmp_path, hostile=True))
    ids = [r.id for r in data.records]
    assert ids[:3] == ["bank", "hub-results", "__proto__"]
    assert "window.__pwned" in data.records[3].text
    assert chr(0x2028) in data.records[4].text
    assert data.records[5].source_file.startswith("javascript:")
    assert "|" in data.records[6].title and "\\" in data.records[6].title


# --- good run ---------------------------------------------------------------


def test_load_run_counts_and_types(run: Path) -> None:
    data = load_run(run)
    assert isinstance(data, RunData)
    assert len(data.records) == 30
    assert all(isinstance(r, Record) for r in data.records)
    assert [r.id for r in data.records] == [f"doc{i:03d}" for i in range(30)]
    assert set(data.engines) == {ENGINE_UNUSUAL, ENGINE_WORDING}
    assert data.engines[ENGINE_UNUSUAL].name == UNUSUAL_PAIRS_NAME
    assert data.engines[ENGINE_WORDING].name == WORDING_AND_MEANING_NAME
    for key, engine in data.engines.items():
        assert len(engine.pairs) == 40
        assert [p.rank for p in engine.pairs] == list(range(1, 41))
        assert all(p.engine == key for p in engine.pairs)
        assert engine.top_k == 50
        assert engine.top_k_reached is False
    assert data.records_read == 30
    assert data.dropped == ()
    assert data.caps_hit == ()
    assert data.dropped_note_count == 0


def test_load_run_values_pass_through(run: Path) -> None:
    data = load_run(run)
    doc = json.loads((run / OUTPUT_WORDING).read_text(encoding="utf-8"))
    first = doc["pairs"][0]
    pair = data.engines[ENGINE_WORDING].pairs[0]
    assert pair.pair_id == first["pair_id"]
    assert pair.left_id == first["left"]["id"]
    assert pair.rank_score == first["scores"]["rank_score"]
    assert pair.percentile == first["scores"]["percentile"]
    assert pair.reading == first["reading"]
    unusual = data.engines[ENGINE_UNUSUAL].pairs[0]
    assert unusual.percentile is None


def test_manifest_values(run: Path) -> None:
    data = load_run(run)
    assert data.manifest_sha256 == sha256_file(run / OUTPUT_MANIFEST)
    manifest = read_manifest(run)
    assert data.tool_version == manifest["tool"]["version"]
    assert data.engines[ENGINE_UNUSUAL].score_meaning == SCORE_MEANING["unusual_pairs"]
    assert data.engines[ENGINE_WORDING].score_meaning == SCORE_MEANING["wording_and_meaning"]
    assert data.engines[ENGINE_UNUSUAL].min_percentile == 0.9
    assert data.engines[ENGINE_WORDING].min_percentile == 0.0


def test_score_meaning_comes_from_the_manifest_verbatim(run: Path) -> None:
    manifest = read_manifest(run)
    manifest["score_meaning"]["unusual_pairs"] = "Changed text. Keep it exact."
    write_manifest(run, manifest)
    assert load_run(run).engines[ENGINE_UNUSUAL].score_meaning == "Changed text. Keep it exact."


def test_min_percentile_missing_key_is_zero(run: Path) -> None:
    manifest = read_manifest(run)
    del manifest["settings"]["unusual_pairs"]["min_percentile"]
    del manifest["settings"]["wording_and_meaning"]
    write_manifest(run, manifest)
    data = load_run(run)
    assert data.engines[ENGINE_UNUSUAL].min_percentile == 0.0
    assert data.engines[ENGINE_WORDING].min_percentile == 0.0


def test_min_percentile_not_a_number_is_an_error(run: Path) -> None:
    manifest = read_manifest(run)
    manifest["settings"]["unusual_pairs"]["min_percentile"] = "high"
    write_manifest(run, manifest)
    with pytest.raises(RunError):
        load_run(run)


def test_dropped_and_caps_are_passed_through(tmp_path: Path) -> None:
    dropped = [{"id": "x1", "reason": "empty text", "source_file": "x1.md"}]
    caps = [{"name": "max_artifacts", "limit": 30, "records_in": 31, "dropped_count": 1}]
    data = load_run(make_run_folder(tmp_path, dropped=dropped, caps_hit=caps))
    assert data.dropped == tuple(dropped)
    assert data.caps_hit == tuple(caps)
    assert data.records_read == 31


def test_determinism(run: Path) -> None:
    assert load_run(run) == load_run(run)


def test_load_does_not_write(run: Path) -> None:
    before = tree_hash(run)
    load_run(run)
    assert tree_hash(run) == before


def test_zero_pairs_load(tmp_path: Path) -> None:
    data = load_run(make_run_folder(tmp_path, zero_pairs=True))
    for engine in data.engines.values():
        assert engine.pairs == ()
        assert "No candidate pairs were returned for this collection." in engine.notes


def test_hostile_folder_loads_and_keeps_text(tmp_path: Path) -> None:
    folder = make_run_folder(tmp_path, hostile=True, n_records=12)
    data = load_run(folder)
    assert len(data.records) == 12
    # A line-separator character inside a text does not split a corpus line.
    assert data.records[4].text.endswith(chr(0x2028) + "x")
    assert data.records[3].title.startswith("<script>")


# --- not a run --------------------------------------------------------------


@pytest.mark.parametrize("kind", ["missing", "empty", "file", "wrong_schema", "broken"])
def test_not_a_run_folder(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "x"
    if kind == "empty":
        target.mkdir()
    elif kind == "file":
        target.write_text("hello")
    elif kind == "wrong_schema":
        target.mkdir()
        (target / OUTPUT_MANIFEST).write_text(json.dumps({"schema_version": "other.v1"}))
    elif kind == "broken":
        target.mkdir()
        (target / OUTPUT_MANIFEST).write_text("{broken")
    with pytest.raises(UsageError) as caught:
        load_run(target)
    assert "not a finished Eureka run" in caught.value.message
    assert caught.value.fix is not None
    assert "eureka run" in caught.value.fix


# --- hash checks ------------------------------------------------------------


@pytest.mark.parametrize("name", FIXED_FILES)
def test_changed_file_is_refused_and_named(run: Path, name: str) -> None:
    path = run / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert name in caught.value.message
    assert caught.value.fix is not None


@pytest.mark.parametrize("name", FIXED_FILES)
def test_missing_file_is_refused_and_named(run: Path, name: str) -> None:
    (run / name).unlink()
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert name in caught.value.message


@pytest.mark.parametrize("name", FIXED_FILES)
def test_file_missing_from_manifest_outputs_is_refused(run: Path, name: str) -> None:
    manifest = read_manifest(run)
    manifest["outputs"] = [item for item in manifest["outputs"] if item["path"] != name]
    write_manifest(run, manifest)
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert name in caught.value.message


def test_outputs_list_missing_is_refused(run: Path) -> None:
    manifest = read_manifest(run)
    del manifest["outputs"]
    write_manifest(run, manifest)
    with pytest.raises(RunError):
        load_run(run)


def test_conflicting_duplicate_entries_are_refused(run: Path) -> None:
    manifest = read_manifest(run)
    manifest["outputs"].append({"path": OUTPUT_UNUSUAL, "sha256": "0" * 64, "bytes": 1})
    write_manifest(run, manifest)
    with pytest.raises(RunError):
        load_run(run)


@pytest.mark.parametrize(
    "crafted",
    ["../unusual-pairs.json", "/etc/passwd", "corpus/../manifest.json", "C:\\x.json", "..\\x"],
)
def test_crafted_manifest_paths_are_ignored(run: Path, crafted: str) -> None:
    manifest = read_manifest(run)
    manifest["outputs"].append({"path": crafted, "sha256": "0" * 64, "bytes": 1})
    manifest["outputs"].append({"path": 7, "sha256": 5})
    manifest["outputs"].append("not a mapping")
    write_manifest(run, manifest)
    assert load_run(run) == load_run(run)
    assert len(load_run(run).records) == 30


def test_crafted_path_cannot_stand_in_for_a_fixed_name(run: Path) -> None:
    manifest = read_manifest(run)
    for item in manifest["outputs"]:
        if item["path"] == OUTPUT_UNUSUAL:
            item["path"] = "../" + OUTPUT_UNUSUAL
    write_manifest(run, manifest)
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert OUTPUT_UNUSUAL in caught.value.message


# --- schemas and shapes -----------------------------------------------------


def test_corpus_schema_must_match(run: Path) -> None:
    text = (run / OUTPUT_CORPUS).read_text(encoding="utf-8")
    rewrite(run, OUTPUT_CORPUS, text.replace(CORPUS_SCHEMA, "eureka.other.v1").encode())
    with pytest.raises(RunError):
        load_run(run)


@pytest.mark.parametrize("name", [OUTPUT_UNUSUAL, OUTPUT_WORDING])
def test_pair_schema_must_match(run: Path, name: str) -> None:
    edit_json(run, name, lambda doc: doc.update(schema_version="eureka.other.v1"))
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert name in caught.value.message
    assert PAIRS_SCHEMA not in caught.value.message


def test_pair_file_under_the_wrong_engine_is_refused(run: Path) -> None:
    edit_json(run, OUTPUT_UNUSUAL, lambda doc: doc["engine"].update(name="Some other engine"))
    with pytest.raises(RunError):
        load_run(run)


def test_pair_count_must_match_counts(run: Path) -> None:
    edit_json(run, OUTPUT_UNUSUAL, lambda doc: doc["counts"].update(pairs=3))
    with pytest.raises(RunError):
        load_run(run)


def test_pair_with_an_unknown_record_is_refused(run: Path) -> None:
    edit_json(run, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0]["left"].update(id="ghost"))
    with pytest.raises(RunError):
        load_run(run)


def test_corpus_record_count_must_match_header(run: Path) -> None:
    lines = (run / OUTPUT_CORPUS).read_bytes().split(b"\n")
    del lines[-2]
    rewrite(run, OUTPUT_CORPUS, b"\n".join(lines))
    with pytest.raises(RunError):
        load_run(run)


def test_duplicate_record_id_is_refused(run: Path) -> None:
    lines = (run / OUTPUT_CORPUS).read_bytes().split(b"\n")
    lines[2] = lines[1]
    rewrite(run, OUTPUT_CORPUS, b"\n".join(lines))
    with pytest.raises(RunError):
        load_run(run)


def test_nan_in_a_pair_file_is_refused(run: Path) -> None:
    text = (run / OUTPUT_UNUSUAL).read_text(encoding="utf-8")
    first = json.loads(text)["pairs"][0]["scores"]["rank_score"]
    rewrite(run, OUTPUT_UNUSUAL, text.replace(repr(first), "NaN", 1).encode())
    with pytest.raises(RunError):
        load_run(run)


# --- readings ---------------------------------------------------------------


def test_unknown_reading_is_refused_even_when_the_hash_is_right(run: Path) -> None:
    edit_json(run, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(reading="A new claim."))
    manifest = read_manifest(run)
    listed = {item["path"]: item["sha256"] for item in manifest["outputs"]}
    assert sha256_file(run / OUTPUT_UNUSUAL) == listed[OUTPUT_UNUSUAL]
    with pytest.raises(RunError) as caught:
        load_run(run)
    assert "reading" in caught.value.message
    assert "A new claim." not in caught.value.message


def test_known_readings_are_accepted(run: Path) -> None:
    edit_json(run, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(reading=READING_AGREE))
    assert load_run(run).engines[ENGINE_UNUSUAL].pairs[0].reading == READING_AGREE


# --- notes ------------------------------------------------------------------


def test_notes_with_an_internal_name_are_dropped_and_counted(run: Path) -> None:
    bad = ["Built from rs" + "_corpus_exclude_terms", "See hsi" + "_reference.py for details"]
    good = ["First plain note.", "Second plain note."]

    def change(doc: dict[str, Any]) -> None:
        doc["notes"] = [good[0], bad[0], good[1], bad[1]]

    edit_json(run, OUTPUT_WORDING, change)
    data = load_run(run)
    assert data.engines[ENGINE_WORDING].notes == tuple(good)
    assert data.dropped_note_count == 2
    assert data.engines[ENGINE_UNUSUAL].notes == ("A plain engine note.",)


def test_notes_keep_their_order(tmp_path: Path) -> None:
    notes = ["Zeta note.", "Alpha note.", "Mid note."]
    data = load_run(make_run_folder(tmp_path, notes=notes))
    assert data.engines[ENGINE_UNUSUAL].notes == tuple(notes)
    assert data.dropped_note_count == 0


# --- run-info.json is never read -------------------------------------------


@pytest.mark.parametrize("state", ["present", "deleted", "corrupted", "never_written"])
def test_run_info_does_not_matter(tmp_path: Path, state: str) -> None:
    folder = make_run_folder(tmp_path, with_run_info=state != "never_written")
    expected = load_run(folder)
    info = folder / OUTPUT_RUN_INFO
    if state == "deleted":
        info.unlink()
    elif state == "corrupted":
        info.write_bytes(b"\xff\xfe not json at all {")
    assert load_run(folder) == expected


def test_run_info_is_never_opened(run: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    original_open = Path.open
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes

    def spy_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        seen.append(str(self))
        return original_open(self, *args, **kwargs)

    def spy_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        seen.append(str(self))
        return original_read_text(self, *args, **kwargs)

    def spy_read_bytes(self: Path) -> bytes:
        seen.append(str(self))
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "open", spy_open)
    monkeypatch.setattr(Path, "read_text", spy_read_text)
    monkeypatch.setattr(Path, "read_bytes", spy_read_bytes)
    load_run(run)
    monkeypatch.undo()
    names = sorted({Path(path).name for path in seen})
    assert names, "the spy saw no file"
    assert not any(path.endswith(OUTPUT_RUN_INFO) for path in seen)
    assert set(names) == {
        "manifest.json",
        "records.jsonl",
        Path(OUTPUT_UNUSUAL).name,
        Path(OUTPUT_WORDING).name,
        Path(OUTPUT_MARKDOWN).name,
    }


# --- the second signal flag (Phase 2.3.1 plan 04) ---------------------------


def _first_wording_pair(run: Path):  # type: ignore[no-untyped-def]
    return load_run(run).engines[ENGINE_WORDING].pairs[0]


def test_confirmed_is_none_without_a_second_signal(run: Path) -> None:
    data = load_run(run)
    assert all(pair.confirmed is None for pair in data.engines[ENGINE_WORDING].pairs)
    assert all(pair.confirmed is None for pair in data.engines[ENGINE_UNUSUAL].pairs)


@pytest.mark.parametrize(
    "signal,expected",
    [
        ({"method": "synthetic", "confirmed": True}, True),
        ({"method": "synthetic", "confirmed": False}, False),
        ({"method": "synthetic", "confirmed": "yes"}, None),
        ({"method": "synthetic", "confirmed": 1}, None),
        ({"method": "synthetic"}, None),
        ("not a mapping", None),
    ],
)
def test_confirmed_follows_the_second_signal(run: Path, signal: Any, expected: bool | None) -> None:
    def change(doc: dict[str, Any]) -> None:
        doc["pairs"][0]["scores"]["second_signal"] = signal

    edit_json(run, OUTPUT_WORDING, change)
    assert _first_wording_pair(run).confirmed is expected


def test_unusual_pairs_engine_gives_no_confirmed_flag(run: Path) -> None:
    edit_json(
        run,
        OUTPUT_UNUSUAL,
        lambda doc: doc["pairs"][0]["scores"].update(second_signal={"confirmed": True}),
    )
    assert load_run(run).engines[ENGINE_UNUSUAL].pairs[0].confirmed is None


def test_load_run_imports_stay_light() -> None:
    import subprocess
    import sys

    code = (
        "import sys; import mindrian_eureka.hub.reader; "
        "assert not {'numpy', 'torch', 'sklearn', 'cryptography'} & set(sys.modules)"
    )
    src = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={"PYTHONPATH": src, "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
