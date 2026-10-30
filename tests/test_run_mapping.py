"""Tests for the CSV mapping module of `eureka run`."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import InputSet
from jsonschema import Draft202012Validator
from mindrian_eureka.run.contracts import MAPPING_SCHEMA, UsageError, sha256_bytes, sha256_text
from mindrian_eureka.run.mapping import (
    MAPPING_JSON_SCHEMA,
    CsvMapping,
    MappingConfig,
    load_mapping_file,
    mapping_from_flags,
    skeleton_mapping,
)

SRC = Path(__file__).resolve().parents[1] / "src"


def _write(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _doc(entry: dict[str, Any], key: str = "*") -> dict[str, Any]:
    return {"schema_version": MAPPING_SCHEMA, "files": {key: entry}}


def test_valid_mapping_file_loads_and_hashes_the_file_bytes(tmp_path: Path) -> None:
    doc = _doc(
        {
            "id_column": "case_id",
            "title_column": "title",
            "text_columns": ["description", "notes"],
            "delimiter": ";",
            "labels": {"notes": "Notes"},
            "extra_fields": ["state_code"],
            "value_maps": {"state_code": {"1": "North"}},
            "html": "never",
        }
    )
    path = _write(tmp_path / "m.json", doc)
    config = load_mapping_file(path)
    assert config.sha256 == sha256_bytes(path.read_bytes())
    entry = config.files["*"]
    assert entry.text_columns == ("description", "notes")
    assert entry.id_column == "case_id"
    assert entry.delimiter == ";"
    assert entry.labels == {"notes": "Notes"}
    assert entry.extra_fields == ("state_code",)
    assert entry.value_maps == {"state_code": {"1": "North"}}
    assert entry.html == "never"


def test_defaults_are_applied(tmp_path: Path) -> None:
    config = load_mapping_file(_write(tmp_path / "m.json", _doc({"text_columns": ["a"]})))
    entry = config.files["*"]
    assert entry.id_column is None
    assert entry.delimiter == ","
    assert entry.html == "auto"
    assert entry.labels == {}


def test_bom_in_mapping_file_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(_doc({"text_columns": ["a"]})).encode())
    assert load_mapping_file(path).files["*"].text_columns == ("a",)


@pytest.mark.parametrize(
    "entry",
    [
        {"id_column": "x"},  # missing text_columns
        {"text_columns": ["a"], "surprise": 1},  # unknown key
        {"text_columns": ["a"], "html": "sometimes"},
        {"text_columns": ["a"], "delimiter": ";;"},
        {"text_columns": ["a"], "delimiter": ""},
        {"text_columns": []},
        {"text_columns": ["a", "a"]},
        {"text_columns": [""]},
    ],
)
def test_invalid_entries_raise_usage_error_naming_the_file(
    tmp_path: Path, entry: dict[str, Any]
) -> None:
    path = _write(tmp_path / "bad-map.json", _doc(entry))
    with pytest.raises(UsageError) as info:
        load_mapping_file(path)
    assert "bad-map.json" in info.value.message
    assert info.value.exit_code == 2
    assert info.value.fix


def test_invalid_json_names_file_and_line(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{\n  "files": \n', encoding="utf-8")
    with pytest.raises(UsageError) as info:
        load_mapping_file(path)
    assert "broken.json" in info.value.message
    assert "line" in info.value.message
    assert info.value.fix is not None
    assert "eureka run --help" in info.value.fix


def test_wrong_schema_version_and_unknown_top_key(tmp_path: Path) -> None:
    doc = {"schema_version": "other", "files": {"*": {"text_columns": ["a"]}}, "extra": 1}
    with pytest.raises(UsageError) as info:
        load_mapping_file(_write(tmp_path / "m.json", doc))
    assert "schema_version" in info.value.message


def test_empty_files_object_is_refused(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        load_mapping_file(
            _write(tmp_path / "m.json", {"schema_version": MAPPING_SCHEMA, "files": {}})
        )


def test_error_text_is_stable_and_capped(tmp_path: Path) -> None:
    doc = {
        "schema_version": MAPPING_SCHEMA,
        "files": {f"f{i}.csv": {"surprise": i} for i in range(9)},
    }
    path = _write(tmp_path / "m.json", doc)
    texts = []
    for _ in range(2):
        with pytest.raises(UsageError) as info:
            load_mapping_file(path)
        texts.append(info.value.message)
    assert texts[0] == texts[1]
    assert "more" in texts[0]
    assert texts[0].count(";") <= 4


def test_oversized_mapping_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(UsageError):
        load_mapping_file(path)


def test_missing_mapping_file_raises_usage_error(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        load_mapping_file(tmp_path / "nope.json")


def test_flags_return_none_when_nothing_is_given() -> None:
    assert (
        mapping_from_flags(
            id_column=None, title_column=None, text_columns=[], source_column=None, delimiter=None
        )
        is None
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id_column": "id"},
        {"title_column": "t"},
        {"source_column": "s"},
        {"delimiter": ";"},
    ],
)
def test_flags_without_text_column_raise(kwargs: dict[str, str]) -> None:
    base: dict[str, Any] = {
        "id_column": None,
        "title_column": None,
        "text_columns": [],
        "source_column": None,
        "delimiter": None,
    }
    base.update(kwargs)
    with pytest.raises(UsageError) as info:
        mapping_from_flags(**base)
    assert "--text-column" in info.value.message


def test_flags_build_star_entry_with_canonical_hash() -> None:
    config = mapping_from_flags(
        id_column="case_id",
        title_column="title",
        text_columns=["description"],
        source_column=None,
        delimiter=";",
    )
    assert config is not None
    assert list(config.files) == ["*"]
    entry = {
        "text_columns": ["description"],
        "id_column": "case_id",
        "title_column": "title",
        "delimiter": ";",
    }
    canonical = json.dumps(
        {"schema_version": MAPPING_SCHEMA, "files": {"*": entry}},
        sort_keys=True,
        separators=(",", ":"),
    )
    assert config.sha256 == sha256_text(canonical)
    assert config.files["*"].delimiter == ";"


def test_flags_bad_delimiter_raises() -> None:
    with pytest.raises(UsageError):
        mapping_from_flags(
            id_column=None,
            title_column=None,
            text_columns=["a"],
            source_column=None,
            delimiter="ab",
        )


def test_for_file_prefers_exact_key_then_star() -> None:
    exact = CsvMapping(text_columns=("a",))
    star = CsvMapping(text_columns=("b",))
    config = MappingConfig(files={"sub/a.csv": exact, "*": star}, sha256="x")
    assert config.for_file("sub/a.csv") is exact
    assert config.for_file("other.csv") is star
    assert MappingConfig(files={"sub/a.csv": exact}, sha256="x").for_file("z.csv") is None


def test_skeleton_guesses_columns_and_validates() -> None:
    text = skeleton_mapping("records.csv", ["Case ID", "Title", "Description"])
    assert text.endswith("\n")
    data = json.loads(text)
    assert list(Draft202012Validator(MAPPING_JSON_SCHEMA).iter_errors(data)) == []
    entry = data["files"]["records.csv"]
    assert entry["id_column"] == "Case ID"
    assert entry["title_column"] == "Title"
    assert entry["text_columns"] == ["Description"]


def test_skeleton_falls_back_to_first_other_header() -> None:
    data = json.loads(skeleton_mapping("x.csv", ["uid", "Weird", "Other"]))
    entry = data["files"]["x.csv"]
    assert entry["id_column"] == "uid"
    assert "title_column" not in entry
    assert entry["text_columns"] == ["Weird"]
    assert list(Draft202012Validator(MAPPING_JSON_SCHEMA).iter_errors(data)) == []


def test_skeleton_loads_through_the_file_loader(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(skeleton_mapping("a.csv", ["a", "b"]), encoding="utf-8")
    assert load_mapping_file(path).for_file("a.csv") is not None


def test_fixture_mapping_file_loads(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("csv")
    assert inputs.mapping_file is not None
    config = load_mapping_file(inputs.mapping_file)
    entry = config.files["*"]
    assert entry.id_column == "case_id"
    assert entry.text_columns == ("description",)
    assert "state_code" in entry.value_maps


def test_module_does_not_import_numpy_or_sklearn() -> None:
    code = (
        f"import sys; sys.path.insert(0, {str(SRC)!r}); import mindrian_eureka.run.mapping; "
        "bad = [m for m in ('numpy', 'sklearn', 'torch') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )
    result = subprocess.run([sys.executable, "-I", "-c", code], check=False)
    assert result.returncode == 0
