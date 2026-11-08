"""Prove deterministic hub publication, provenance and filesystem boundaries."""

from __future__ import annotations

import getpass
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest
from hub_scan import scan_dashes, scan_for_network, scan_internal_names
from hub_support import make_run_folder
from mindrian_eureka.hub import assets, writer
from mindrian_eureka.hub.contracts import HUB_MANIFEST_SCHEMA, is_hub_folder
from mindrian_eureka.hub.links import file_links
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import LABEL, RunError, UsageError


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def build(run: Path, out: Path, source: Path | None = None):
    return build_hub(HubRequest(run, out, source), Console(stderr=io.StringIO()))


def assignment(path: Path, name: str):
    return json.loads(path.read_text().removeprefix(f"window.{name} = ").rstrip(";\n"))


def test_hashes_determinism_and_replace(tmp_path: Path, no_network: list[object]) -> None:
    run = make_run_folder(tmp_path)
    before = tree(run)
    first, second = tmp_path / "first", tmp_path / "second"
    summary = build(run, first)
    build(run, second)
    assert tree(first) == tree(second)
    build(run, first)
    assert tree(first) == tree(second)
    assert tree(run) == before
    assert not list(tmp_path.glob(".*.old-*"))
    assert not list(tmp_path.glob(".*.staging-*"))
    manifest = json.loads((first / "hub-manifest.json").read_bytes())
    assert manifest["schema_version"] == HUB_MANIFEST_SCHEMA
    assert manifest["label"] == LABEL
    assert manifest["run"]["manifest_sha256"] == hashlib.sha256(before["manifest.json"]).hexdigest()
    names = {a.output_path for a in assets.all_assets()} | {
        "hub.html", "hub-data.js", "hub-copy.js", "hub-manifest.json"
    }
    assert set(tree(first)) == names
    assert {item["path"] for item in manifest["files"]} == names - {"hub-manifest.json"}
    assert [item["path"] for item in manifest["files"]] == sorted(names - {"hub-manifest.json"})
    for item in manifest["files"]:
        raw = (first / item["path"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["bytes"] == len(raw)
    payload = assignment(first / "hub-data.js", "HUB")
    assert manifest["counts"] == {"records": payload["counts"]["records"],
                                  "pairs": payload["counts"]["pairs"]}
    manifest_bytes = (first / "hub-manifest.json").read_bytes()
    assert summary.manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()
    assert is_hub_folder(first)
    assert no_network == []


@pytest.mark.parametrize("where", ["same", "inside", "parent", "foreign", "symlink"])
def test_refuse_output_damage(tmp_path: Path, where: str) -> None:
    run = make_run_folder(tmp_path / "inputs")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    target = {"same": run, "inside": run / "hub", "parent": run.parent,
              "foreign": foreign}.get(where, tmp_path / "alias")
    if where == "symlink":
        target.symlink_to(foreign, target_is_directory=True)
    before = tree(tmp_path)
    with pytest.raises(UsageError):
        build(run, target)
    assert tree(tmp_path) == before


def test_sources_relative_encoded_and_untouched(tmp_path: Path) -> None:
    run = make_run_folder(tmp_path, n_records=8, hostile=True)
    sources = tmp_path / "sources"
    sources.mkdir()
    records = load_run(run).records
    for record in records[:6]:
        (sources / record.source_file).write_text("original")
    before_run, before_sources = tree(run), tree(sources)
    out = tmp_path / "hub"
    summary = build(run, out, sources)
    payload = assignment(out / "hub-data.js", "HUB")
    by_id = {record["id"]: record for record in payload["records"]}
    assert by_id[records[5].id]["source_link"].startswith("../sources/javascript%3A")
    assert by_id[records[6].id]["source_link"].startswith("#")
    assert len(summary.warnings) == 1 and "2 records" in summary.warnings[0]
    assert tree(run) == before_run and tree(sources) == before_sources
    for target in (sources, sources / "hub", sources.parent):
        with pytest.raises(UsageError):
            build(run, target, sources)


def test_links_missing_escape_symlink_and_drive(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace
    run = make_run_folder(tmp_path, n_records=3)
    records = list(load_run(run).records)
    sources = tmp_path / "sources"
    sources.mkdir()
    records[0] = replace(records[0], source_file="a b:c.md")
    (sources / "a b:c.md").write_text("text")
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    (sources / records[1].source_file).symlink_to(outside)
    links, missing = file_links(records, out_dir=tmp_path, source_dir=sources)
    assert links == {records[0].id: "./sources/a%20b%3Ac.md"}
    assert missing == sorted([records[1].id, records[2].id])
    monkeypatch.setattr("mindrian_eureka.hub.links.os.path.relpath",
                        lambda *args: (_ for _ in ()).throw(ValueError("drive")))
    actual = file_links(records, out_dir=tmp_path, source_dir=sources)
    assert actual == ({}, sorted(r.id for r in records))


def test_rollback_and_guards(tmp_path: Path, monkeypatch) -> None:
    run = make_run_folder(tmp_path)
    out = tmp_path / "hub"
    build(run, out)
    before = tree(out)
    def fail(*args, **kwargs):
        raise RuntimeError("render failed")
    with monkeypatch.context() as patch:
        patch.setattr(writer, "render_page", fail)
        with pytest.raises(RuntimeError, match="render failed"):
            build(run, out)
    assert tree(out) == before
    assert not list(tmp_path.glob(".*.staging-*"))
    original = writer.build_payload
    def broken(*args, **kwargs):
        payload = original(*args, **kwargs)
        payload["records"][0]["label"] = ""
        return payload
    with monkeypatch.context() as patch:
        patch.setattr(writer, "build_payload", broken)
        with pytest.raises(RunError, match="Hub data check failed"):
            build(run, tmp_path / "bad")
        assert not (tmp_path / "bad").exists()
    with monkeypatch.context() as patch:
        patch.setitem(assets.EXPECTED_STATIC, next(iter(assets.EXPECTED_STATIC)), "0" * 64)
        with pytest.raises(RunError, match="A packaged hub file changed"):
            build(run, out)
    assert tree(out) == before


def test_privacy_modes_and_hostile_scans(tmp_path: Path) -> None:
    run = make_run_folder(tmp_path, hostile=True)
    out = tmp_path / "hub"
    build(run, out)
    assert scan_for_network(out) == []
    assert scan_dashes(out) == []
    assert scan_internal_names(out) == []
    for name, raw in tree(out).items():
        assert str(tmp_path).encode() not in raw
        assert str(Path.home()).encode() not in raw
        assert getpass.getuser().encode() not in raw
        assert re.search(rb"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", raw) is None
        if os.name == "posix":
            assert (out / name).stat().st_mode & 0o777 == 0o600
    if os.name == "posix":
        assert all(p.stat().st_mode & 0o777 == 0o700 for p in [out, *out.rglob("*")] if p.is_dir())
    for name, variable in (("hub-data.js", "HUB"), ("hub-copy.js", "HUB_COPY")):
        value = assignment(out / name, variable)
        assert isinstance(value, dict)
        # JSON structural braces remain; only string contents are escaped.
        assert not any(char in (out / name).read_text() for char in ("&", chr(0x2028), chr(0x2029)))


def test_writer_import_stays_light() -> None:
    script = "import sys; import mindrian_eureka.hub.writer; assert 'numpy' not in sys.modules"
    subprocess.run([sys.executable, "-c", script], check=True)


def test_scale_3000(tmp_path: Path) -> None:
    run = make_run_folder(tmp_path, n_records=3000, pairs_per_engine=200, long_text=500)
    first, second = tmp_path / "hub-a", tmp_path / "hub-b"
    started = time.perf_counter()
    summary = build(run, first)
    seconds = time.perf_counter() - started
    assert seconds < 120
    # Plan 10, G3: 9946779 bytes on 2026-11-08 with the inline figures; the bound was 80000000.
    hub_data_bytes = (first / "hub-data.js").stat().st_size
    assert hub_data_bytes < 12_000_000
    build(run, second)
    assert tree(first) == tree(second)
    small = make_run_folder(tmp_path, name="small", n_records=3)
    build(small, tmp_path / "small-hub")
    assert set(tree(first)) == set(tree(tmp_path / "small-hub"))
    pair_keys = sum(summary.pairs.values())
    print(json.dumps({"records": summary.records, "pairs": summary.pairs,
                      "build_seconds": round(seconds, 4),
                      "hub_data_bytes": hub_data_bytes,
                      "hub_data_bytes_per_pair_key": round(hub_data_bytes / pair_keys, 1),
                      "hub_html_bytes": (first / "hub.html").stat().st_size,
                      "logical_cpus": os.cpu_count(),
                      "memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")}))
