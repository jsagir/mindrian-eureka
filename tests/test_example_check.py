"""Library tests for the public example check (Phase 4, plan 01).

The tests use the real run folder of the public fixture only as a real example of the folder
shape. They copy it to a temporary folder before every change. They load no model.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.example import check as check_module
from mindrian_eureka.example.build import build_expected
from mindrian_eureka.example.check import CheckReport, check_run, load_expected
from mindrian_eureka.example.contracts import (
    EXPECTED_SCHEMA,
    NOT_REPRODUCED_TEXT,
    OUTPUT_FILES,
    PAIR_FILES,
    REPORT_SCHEMA,
    RESULT_MATCH,
    RESULT_NO_MATCH,
)
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE, EurekaError, RunError, UsageError
from mindrian_eureka.run.output import canonical_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RUN = ROOT / "tests/fixtures/hub_public/run"
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
CHECK_IDS = ["X1", "X2", "X3", "X4", "X5", "X6", "X7"]


def make_expected(run: Path) -> dict[str, Any]:
    return build_expected(run, repo_root=ROOT, records=36)


def copy_run(tmp_path: Path, name: str = "run") -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURE_RUN, target)
    return target


def edit_manifest(run: Path, change: Any) -> None:
    path = run / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    change(manifest)
    path.write_bytes(canonical_json(manifest, digits=None))


def flip_last_byte(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[-1] = ord("Z") if data[-1] != ord("Z") else ord("Y")
    path.write_bytes(bytes(data))


def statuses(report: CheckReport) -> dict[str, str]:
    return {item.id: item.status for item in report.checks}


def by_id(report: CheckReport, check_id: str) -> Any:
    return next(item for item in report.checks if item.id == check_id)


@pytest.fixture(scope="module")
def expected() -> dict[str, Any]:
    return make_expected(FIXTURE_RUN)


def test_build_then_check_matches(expected: dict[str, Any]) -> None:
    report = check_run(FIXTURE_RUN, expected)
    assert report.result == "match"
    assert [item.id for item in report.checks] == CHECK_IDS
    assert all(item.status == "PASS" for item in report.checks)
    assert expected["schema_version"] == EXPECTED_SCHEMA


def test_build_is_deterministic(expected: dict[str, Any]) -> None:
    again = make_expected(FIXTURE_RUN)
    assert canonical_json(expected) == canonical_json(again)


@pytest.mark.parametrize("name", OUTPUT_FILES)
def test_one_byte_change_in_each_output_fails(
    tmp_path: Path, expected: dict[str, Any], name: str
) -> None:
    run = copy_run(tmp_path)
    original = next(item["sha256"] for item in expected["outputs"] if item["path"] == name)
    flip_last_byte(run / name)
    report = check_run(run, expected)
    assert report.result == "no_match"
    result = statuses(report)
    assert result["X6"] == "FAIL"
    for check_id in ("X2", "X3", "X4", "X5"):
        assert result[check_id] == "PASS"
    detail = by_id(report, "X6").detail
    assert name in detail
    assert original in detail
    found = check_module.sha256_file(run / name)
    assert found in detail
    assert NOT_REPRODUCED_TEXT in report.to_text()


def test_input_hash_change_fails_x2(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    edit_manifest(run, lambda m: m["inputs"]["files"][0].__setitem__("sha256", "0" * 64))
    report = check_run(run, expected)
    assert statuses(report)["X2"] == "FAIL"
    assert expected["example"]["input_folder"] in (by_id(report, "X2").fix or "")
    run2 = copy_run(tmp_path, "run2")
    edit_manifest(run2, lambda m: m["corpus"].__setitem__("corpus_digest", "1" * 64))
    assert statuses(check_run(run2, expected))["X2"] == "FAIL"


def test_settings_and_seed_change_fail_x3(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    edit_manifest(run, lambda m: m["settings"]["run"].__setitem__("top_k", 150))
    assert statuses(check_run(run, expected))["X3"] == "FAIL"
    run2 = copy_run(tmp_path, "run2")
    edit_manifest(run2, lambda m: m["seeds"].__setitem__("wording_and_meaning_lsa_seed", 7))
    assert statuses(check_run(run2, expected))["X3"] == "FAIL"


def test_model_change_fails_x4(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    edit_manifest(run, lambda m: m["model"].__setitem__("snapshot", "f" * 40))
    report = check_run(run, expected)
    assert statuses(report)["X4"] == "FAIL"
    assert "another model" in (by_id(report, "X4").fix or "")
    run2 = copy_run(tmp_path, "run2")
    edit_manifest(run2, lambda m: m["model"]["files"].__setitem__("vocab.txt", "2" * 64))
    assert statuses(check_run(run2, expected))["X4"] == "FAIL"


def test_engine_change_fails_x5(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    edit_manifest(
        run,
        lambda m: m["tool"]["engines"]["wording_and_meaning"].__setitem__(
            "reference_sha256", "3" * 64
        ),
    )
    assert statuses(check_run(run, expected))["X5"] == "FAIL"
    run2 = copy_run(tmp_path, "run2")
    edit_manifest(run2, lambda m: m["tool"].__setitem__("version", "9.9.9"))
    assert statuses(check_run(run2, expected))["X5"] == "FAIL"


def test_disk_file_changed_after_the_run_fails_x6(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    name = "unusual-pairs.json"
    flip_last_byte(run / name)
    forged = copy.deepcopy(expected)
    for item in forged["outputs"]:
        if item["path"] == name:
            item["sha256"] = check_module.sha256_file(run / name)
    report = check_run(run, forged)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "changed after the run" in by_id(report, "X6").detail


def test_missing_label_fails_x7(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    path = run / "ranked-pairs.md"
    path.write_text(path.read_text(encoding="utf-8").replace(LABEL, "unmarked"), encoding="utf-8")
    report = check_run(run, expected)
    result = statuses(report)
    assert result["X7"] == "FAIL"
    assert result["X6"] == "FAIL"
    assert report.result == "no_match"


def test_environment_difference_is_info_only(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)

    def change(manifest: dict[str, Any]) -> None:
        manifest["environment"]["python"] = "3.11.1"
        manifest["environment"]["libraries"]["numpy"] = "1.0.0"

    edit_manifest(run, change)
    report = check_run(run, expected)
    assert report.result == "match"
    joined = "\n".join(report.info)
    assert "python is 3.11.1" in joined
    assert "numpy is 1.0.0" in joined
    assert all(line.startswith("INFO") for line in report.info)


def test_not_a_run_folder_is_a_usage_error(tmp_path: Path, expected: dict[str, Any]) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(UsageError) as caught:
        check_run(empty, expected)
    assert caught.value.fix
    with pytest.raises(UsageError):
        check_run(tmp_path / "missing", expected)
    no_output = copy_run(tmp_path, "no-output")
    (no_output / "ranked-pairs.md").unlink()
    with pytest.raises(UsageError) as caught2:
        check_run(no_output, expected)
    assert caught2.value.fix
    other = copy_run(tmp_path, "other")
    edit_manifest(other, lambda m: m.__setitem__("schema_version", "eureka.other.v9"))
    with pytest.raises(UsageError):
        check_run(other, expected)
    assert caught.value.exit_code == 2


def test_symbolic_link_outside_the_folder_is_refused(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    run = copy_run(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_bytes((run / "ranked-pairs.md").read_bytes())
    (run / "ranked-pairs.md").unlink()
    (run / "ranked-pairs.md").symlink_to(outside)
    with pytest.raises(UsageError):
        check_run(run, expected)


def write_expected(tmp_path: Path, document: object) -> Path:
    path = tmp_path / "expected.json"
    path.write_bytes(canonical_json(document, digits=None))
    return path


def test_expected_file_is_validated(tmp_path: Path, expected: dict[str, Any]) -> None:
    good = write_expected(tmp_path, expected)
    assert load_expected(good)["schema_version"] == EXPECTED_SCHEMA

    def mutated(change: Any) -> Path:
        document = copy.deepcopy(expected)
        change(document)
        return write_expected(tmp_path, document)

    bad_cases = [
        lambda d: d.__setitem__("schema_version", "eureka.other.v1"),
        lambda d: d.pop("settings"),
        lambda d: d.pop("outputs"),
        lambda d: d["outputs"][0].__setitem__("path", "../escape.md"),
        lambda d: d["outputs"][0].__setitem__("path", "/etc/passwd"),
        lambda d: d["outputs"][0].__setitem__("path", "corpus\\records.jsonl"),
        lambda d: d["outputs"][0].__setitem__("sha256", "ABC"),
        lambda d: d["outputs"][0].__setitem__("sha256", "A" * 64),
        lambda d: d["inputs"]["files"][0].__setitem__("sha256", "xyz"),
        lambda d: d["inputs"].__setitem__("folder_digest", "g" * 64),
        lambda d: d["outputs"].pop(),
    ]
    for change in bad_cases:
        with pytest.raises(UsageError) as caught:
            load_expected(mutated(change))
        assert caught.value.fix
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(UsageError):
        load_expected(broken)
    with pytest.raises(UsageError):
        load_expected(tmp_path / "missing.json")
    big = write_expected(tmp_path, expected)
    original_limit = check_module.MAX_JSON_BYTES
    check_module.MAX_JSON_BYTES = 100
    try:
        with pytest.raises(UsageError):
            load_expected(big)
    finally:
        check_module.MAX_JSON_BYTES = original_limit


def test_maker_refuses_a_changed_or_unclean_run(tmp_path: Path) -> None:
    changed = copy_run(tmp_path, "changed")
    flip_last_byte(changed / "wording-and-meaning-pairs.json")
    with pytest.raises(EurekaError):
        make_expected(changed)

    dropped = copy_run(tmp_path, "dropped")
    edit_manifest(dropped, lambda m: m["corpus"].__setitem__("dropped", [{"id": "x"}]))
    with pytest.raises(RunError):
        make_expected(dropped)

    capped = copy_run(tmp_path, "capped")
    edit_manifest(capped, lambda m: m["corpus"].__setitem__("caps_hit", ["max_artifacts"]))
    with pytest.raises(RunError):
        make_expected(capped)

    with pytest.raises(RunError):
        build_expected(FIXTURE_RUN, repo_root=ROOT, records=35)


def test_maker_records_engine_sources(expected: dict[str, Any]) -> None:
    sources = expected["engine_sources"]
    assert set(sources) == {
        "src/mindrian_eureka/hsi_reference.py",
        "src/mindrian_eureka/opportunity_pairs/algorithm.py",
    }
    for relative, digest in sources.items():
        assert digest == check_module.sha256_file(ROOT / relative)


def test_texts_are_clean(tmp_path: Path, expected: dict[str, Any]) -> None:
    run = copy_run(tmp_path)
    edit_manifest(run, lambda m: m["environment"].__setitem__("python", "3.11.1"))
    flip_last_byte(run / "ranked-pairs.md")
    bad = check_run(run, expected)
    good = check_run(FIXTURE_RUN, expected)
    texts = [bad.to_text(), good.to_text(), json.dumps(bad.to_json_dict())]
    for text in texts:
        assert "–" not in text
        assert "—" not in text
        assert not SHORT_CODE.search(text)
    assert bad.to_text().rstrip("\n").endswith(SUMMARY_LINE)
    assert good.to_text().rstrip("\n").endswith(SUMMARY_LINE)
    assert RESULT_MATCH in good.to_text()
    assert RESULT_NO_MATCH in bad.to_text()
    assert bad.to_json_dict()["schema"] == REPORT_SCHEMA
    assert bad.to_json_dict()["label"] == LABEL
    assert set(PAIR_FILES) < set(OUTPUT_FILES)
