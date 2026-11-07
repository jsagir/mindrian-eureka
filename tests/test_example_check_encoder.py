"""Tests of `eureka check-example` for runs that are not CPU-exact (Phase 5, plan 04).

A run whose manifest names the determinism class `gpu-approx` is compared with the shipped
reference run by ranking overlap, not by bytes. While no threshold is measured, such a run is
never a match. The tests copy the public fixture run to a temporary folder before every change
and load no model.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.cli import main
from mindrian_eureka.example.build import build_expected
from mindrian_eureka.example.check import CheckReport, check_run
from mindrian_eureka.run.contracts import LABEL
from mindrian_eureka.run.manifest import sha256_file
from mindrian_eureka.run.output import canonical_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RUN = ROOT / "tests/fixtures/hub_public/run"
CHECK_IDS = ["X1", "X2", "X3", "X4", "X5", "X6", "X7"]
JSON_KEYS = ["checks", "info", "label", "note", "result", "schema"]
UNUSUAL = "unusual-pairs.json"
WORDING = "wording-and-meaning-pairs.json"


def make_expected(run: Path) -> dict[str, Any]:
    return build_expected(run, repo_root=ROOT, records=36)


def copy_run(tmp_path: Path, name: str = "run") -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURE_RUN, target)
    return target


def load_manifest(run: Path) -> dict[str, Any]:
    return json.loads((run / "manifest.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def edit_manifest(run: Path, change: Callable[[dict[str, Any]], None]) -> None:
    manifest = load_manifest(run)
    change(manifest)
    (run / "manifest.json").write_bytes(canonical_json(manifest, digits=None))


def set_encoder(run: Path, determinism_class: str) -> None:
    from mindrian_eureka.encoder_spec import encoder_block, profile_spec

    block = encoder_block(profile_spec("cpu-default"), profile_spec("cpu-default"))
    block["determinism_class"] = determinism_class
    edit_manifest(run, lambda manifest: manifest.__setitem__("encoder", block))


def refresh_manifest_hash(run: Path, name: str) -> None:
    def change(manifest: dict[str, Any]) -> None:
        for entry in manifest["outputs"]:
            if entry["path"] == name:
                entry["sha256"] = sha256_file(run / name)
                entry["bytes"] = (run / name).stat().st_size

    edit_manifest(run, change)


def rewrite_pairs(
    run: Path,
    name: str,
    keep: Callable[[int], bool] = lambda index: True,
    *,
    nudge: bool = False,
) -> None:
    document = json.loads((run / name).read_text(encoding="utf-8"))
    pairs = [pair for index, pair in enumerate(document["pairs"]) if keep(index)]
    if nudge:
        for pair in pairs:
            pair["scores"]["rank_score"] = round(pair["scores"]["rank_score"] + 0.000123, 6)
    document["pairs"] = pairs
    (run / name).write_bytes(canonical_json(document, digits=None))
    refresh_manifest_hash(run, name)


def approx_run(tmp_path: Path, name: str = "approx") -> Path:
    """Return a copy with the class gpu-approx and changed bytes in both pair files."""
    run = copy_run(tmp_path, name)
    set_encoder(run, "gpu-approx")
    rewrite_pairs(run, UNUSUAL, nudge=True)
    rewrite_pairs(run, WORDING, nudge=True)
    return run


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


def test_exact_class_and_missing_block_are_unchanged(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    plain = check_run(FIXTURE_RUN, expected)
    exact = copy_run(tmp_path, "exact")
    set_encoder(exact, "cpu-exact")
    exact_report = check_run(exact, expected)
    removed = copy_run(tmp_path, "removed")
    edit_manifest(removed, lambda manifest: manifest.pop("encoder", None))
    removed_report = check_run(removed, expected)
    for report in (plain, exact_report, removed_report):
        assert report.result == "match"
        assert [item.id for item in report.checks] == CHECK_IDS
        assert sorted(report.to_json_dict()) == JSON_KEYS
    assert plain.to_text() == removed_report.to_text() == exact_report.to_text()
    assert plain.to_json_dict() == removed_report.to_json_dict() == exact_report.to_json_dict()
    with_reference = check_run(exact, expected, reference_run=FIXTURE_RUN)
    assert with_reference.to_text() == plain.to_text()
    assert with_reference.to_json_dict() == plain.to_json_dict()
    assert check_run(FIXTURE_RUN, expected, reference_run=FIXTURE_RUN).to_text() == plain.to_text()


def test_ranking_overlap_unit() -> None:
    from mindrian_eureka.example.check import ranking_overlap

    assert ranking_overlap(["a", "b", "c"], ["a", "b", "d"]) == pytest.approx(2 / 3)
    assert ranking_overlap(["a", "b"], ["a", "b"]) == 1.0
    assert ranking_overlap(["b", "a"], ["a", "b"]) == 1.0
    assert ranking_overlap(["a", "a", "a"], ["a", "b"]) == pytest.approx(0.5)
    assert ranking_overlap([], []) == 1.0
    assert ranking_overlap(["a"], []) == 0.0


def test_approx_run_with_equal_ranking_and_no_threshold_is_not_a_match(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    from mindrian_eureka.example import contracts

    assert contracts.GPU_APPROX_MIN_OVERLAP is None
    run = approx_run(tmp_path)
    report = check_run(run, expected, reference_run=FIXTURE_RUN)
    assert report.result == "no_match"
    result = statuses(report)
    for check_id in ("X1", "X2", "X3", "X4", "X5", "X7"):
        assert result[check_id] == "PASS"
    assert result["X6"] == "FAIL"
    detail = by_id(report, "X6").detail
    assert UNUSUAL in detail
    assert WORDING in detail
    assert detail.count("1.0000") == 2
    assert "63" in detail
    assert "200" in detail
    assert "no overlap threshold has been measured yet" in detail
    assert report.note == contracts.GPU_APPROX_NOTE
    assert "expected sha256" not in report.to_text()


def test_approx_run_passes_with_a_measured_threshold(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = approx_run(tmp_path)
    report = check_run(run, expected, reference_run=FIXTURE_RUN)
    assert report.result == "match"
    assert statuses(report)["X6"] == "PASS"
    assert "0.9" in by_id(report, "X6").detail
    document = report.to_json_dict()
    assert document["determinism_class"] == "gpu-approx"
    overlap = document["ranking_overlap"]
    assert isinstance(overlap, dict)
    assert UNUSUAL in overlap
    assert WORDING in overlap


def test_approx_run_below_the_threshold_fails(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = copy_run(tmp_path, "approx")
    set_encoder(run, "gpu-approx")
    rewrite_pairs(run, UNUSUAL, lambda index: index >= 20)
    rewrite_pairs(run, WORDING, nudge=True)
    report = check_run(run, expected, reference_run=FIXTURE_RUN)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "0.6825" in by_id(report, "X6").detail


def test_approx_run_still_compares_the_corpus_by_bytes(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = approx_run(tmp_path)
    flip_last_byte(run / "corpus/records.jsonl")
    refresh_manifest_hash(run, "corpus/records.jsonl")
    report = check_run(run, expected, reference_run=FIXTURE_RUN)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "corpus/records.jsonl" in by_id(report, "X6").detail


def test_approx_run_still_finds_a_change_after_the_run(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = approx_run(tmp_path)
    document = json.loads((run / UNUSUAL).read_text(encoding="utf-8"))
    document["pairs"][0]["scores"]["rank_score"] = 9.5
    (run / UNUSUAL).write_bytes(canonical_json(document, digits=None))
    report = check_run(run, expected, reference_run=FIXTURE_RUN)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "changed after the run" in by_id(report, "X6").detail


@pytest.mark.parametrize("reference", [None, "missing"])
def test_missing_reference_fails_closed(
    tmp_path: Path,
    expected: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    reference: str | None,
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = approx_run(tmp_path)
    given = None if reference is None else tmp_path / reference
    report = check_run(run, expected, reference_run=given)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "reference run" in by_id(report, "X6").detail


def test_tampered_reference_fails_closed(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    run = approx_run(tmp_path)
    reference = copy_run(tmp_path, "reference")
    flip_last_byte(reference / UNUSUAL)
    report = check_run(run, expected, reference_run=reference)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    assert "reference run does not match" in by_id(report, "X6").detail


def test_unknown_and_unreadable_class_fail_closed(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    unknown = copy_run(tmp_path, "unknown")
    set_encoder(unknown, "gpu-fast")
    report = check_run(unknown, expected, reference_run=FIXTURE_RUN)
    assert report.result == "no_match"
    assert statuses(report)["X6"] == "FAIL"
    detail = by_id(report, "X6").detail
    assert "unknown determinism class" in detail
    assert "gpu-fast" in detail

    as_list = copy_run(tmp_path, "as_list")
    edit_manifest(as_list, lambda manifest: manifest.__setitem__("encoder", ["gpu-approx"]))
    no_class = copy_run(tmp_path, "no_class")
    edit_manifest(no_class, lambda manifest: manifest.__setitem__("encoder", {"profile": "x"}))
    for run in (as_list, no_class):
        report = check_run(run, expected, reference_run=FIXTURE_RUN)
        assert report.result == "no_match"
        assert statuses(report)["X6"] == "FAIL"
        assert "encoder block" in by_id(report, "X6").detail


def test_claim_does_not_hide_other_faults(
    tmp_path: Path, expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    assert check_run(approx_run(tmp_path, "base"), expected, reference_run=FIXTURE_RUN).result == (
        "match"
    )

    model = approx_run(tmp_path, "model")
    edit_manifest(model, lambda m: m["model"].__setitem__("name", "another-model"))
    inputs = approx_run(tmp_path, "inputs")
    edit_manifest(inputs, lambda m: m["inputs"]["files"][0].__setitem__("sha256", "0" * 64))
    settings = approx_run(tmp_path, "settings")
    edit_manifest(settings, lambda m: m["settings"]["run"].__setitem__("top_k", 150))
    label = approx_run(tmp_path, "label")
    text = (label / UNUSUAL).read_text(encoding="utf-8").replace(LABEL, "unmarked")
    (label / UNUSUAL).write_text(text, encoding="utf-8")
    refresh_manifest_hash(label, UNUSUAL)

    for run, check_id in ((model, "X4"), (inputs, "X2"), (settings, "X3"), (label, "X7")):
        report = check_run(run, expected, reference_run=FIXTURE_RUN)
        assert report.result == "no_match", check_id
        assert statuses(report)[check_id] == "FAIL", check_id


def write_layout(tmp_path: Path, expected: dict[str, Any], *, with_reference: bool) -> Path:
    base = tmp_path / ("with_reference" if with_reference else "without_reference")
    folder = base / "examples" / "public-example"
    folder.mkdir(parents=True)
    expected_file = folder / "expected-hashes.json"
    expected_file.write_bytes(canonical_json(copy.deepcopy(expected), digits=None))
    if with_reference:
        shutil.copytree(FIXTURE_RUN, folder / "reference-run")
    return expected_file


def test_command_uses_the_reference_folder_next_to_the_expected_file(
    tmp_path: Path,
    expected: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from mindrian_eureka.example import contracts as contracts_module

    approx = approx_run(tmp_path)
    plain = copy_run(tmp_path, "plain")
    with_reference = write_layout(tmp_path, expected, with_reference=True)
    without_reference = write_layout(tmp_path, expected, with_reference=False)

    code = main(["check-example", str(approx), "--expected", str(with_reference)])
    assert code == 1
    assert "no overlap threshold has been measured yet" in capsys.readouterr().out

    monkeypatch.setattr(contracts_module, "GPU_APPROX_MIN_OVERLAP", 0.9)
    assert main(["check-example", str(approx), "--expected", str(with_reference)]) == 0
    capsys.readouterr()

    code = main(["check-example", str(approx), "--expected", str(without_reference)])
    assert code == 1
    assert "reference run" in capsys.readouterr().out

    for layout in (with_reference, without_reference):
        assert main(["check-example", str(plain), "--expected", str(layout)]) == 0
        capsys.readouterr()


def test_constants_agree_with_the_spec_module() -> None:
    from mindrian_eureka import encoder_spec
    from mindrian_eureka.example import contracts

    assert contracts.DETERMINISM_CPU_EXACT == encoder_spec.DETERMINISM_CPU_EXACT
    assert contracts.DETERMINISM_GPU_APPROX == encoder_spec.DETERMINISM_GPU_APPROX
    assert contracts.ENCODER_KEY == "encoder"
    value = contracts.GPU_APPROX_MIN_OVERLAP
    assert value is None or (isinstance(value, float) and 0.0 < value <= 1.0)


def test_threshold_is_not_invented() -> None:
    from mindrian_eureka.example import contracts

    if contracts.GPU_APPROX_MIN_OVERLAP is not None:
        pytest.skip("the threshold is set from the recorded spike result")
    package = ROOT / "src/mindrian_eureka/example"
    assignment = re.compile(r"^\s*\w*MIN_OVERLAP\w*\s*(:[^=]+)?=[^=]", re.MULTILINE)
    holders = [
        path.name
        for path in sorted(package.glob("*.py"))
        if assignment.search(path.read_text(encoding="utf-8"))
    ]
    assert holders == ["contracts.py"]


def test_import_weight_stays_light() -> None:
    code = (
        "import sys\n"
        "import mindrian_eureka.example.check\n"
        "import mindrian_eureka.example.command\n"
        "bad = [m for m in ('numpy', 'sklearn', 'scipy', 'torch', 'sentence_transformers',\n"
        "                   'transformers', 'mindrian_eureka.encoder_spec') if m in sys.modules]\n"
        "print(','.join(bad))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert done.stdout.strip() == ""
