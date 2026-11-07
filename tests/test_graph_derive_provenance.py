"""Tests for the replay provenance record, the gap list and the emit script (Phase 3, HOST-02).

The replay behind five JHTV candidates cannot be rebuilt from this repo. The record states that
as a provenance gap. The script emits the list of candidates to mark. These tests read repo files
and run the script offline. They read no room and call no model.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evaluations" / "graph-derive-replay" / "record.v1.json"
GOLDEN = ROOT / "evaluations" / "graph-derive-replay" / "gap-list.v1.json"
DOC = ROOT / "docs" / "jhtv-replay-record.md"
SCHEMAS = ROOT / "src" / "mindrian_eureka" / "data" / "schemas"
RECORD_SCHEMA = SCHEMAS / "provenance-gap-record.v1.json"
LIST_SCHEMA = SCHEMAS / "provenance-gap-list.v1.json"
MODULE_FILE = ROOT / "src" / "mindrian_eureka" / "provenance" / "gap_list.py"
WRAPPER = ROOT / "scripts" / "emit-provenance-gap-list"
CLI_FILE = ROOT / "src" / "mindrian_eureka" / "cli.py"

ITEM_IDS = ["OPP-027", "OPP-028", "OPP-029", "OPP-030", "OPP-031"]
LABEL = "candidate, not verified"
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)

DOC_HEADINGS = [
    "# JHTV replay record: OPP-027 to OPP-031",
    "## What this page is for",
    "## What the room says",
    "## What this repo holds",
    "## What exists outside this repo",
    "## The pair count check",
    "## Verdict",
    "## Why no replay script is built here",
    "## What would close the gap",
    "## The room mark is a hand-off item",
    "## How to emit the list",
    "## Front matter keys",
]


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    src = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src + (os.pathsep + existing if existing else "")
    return env


def _run(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "mindrian_eureka.provenance.gap_list", *args],
        capture_output=True,
        cwd=ROOT,
        env=_env(),
        check=False,
    )


def _validate(doc: Any, schema_path: Path) -> None:
    import jsonschema

    jsonschema.Draft202012Validator(_json(schema_path)).validate(doc)


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "record must start with a front matter block"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    data: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def test_record_validates_and_names_exactly_five_items():
    record = _json(RECORD)
    _validate(record, RECORD_SCHEMA)
    assert [item["opportunity_id"] for item in record["items"]] == ITEM_IDS
    assert record["verdict"] == "provenance_gap"
    assert record["outcome"] == "provenance_gap"
    assert record["room_mark"] == "pending_approval"
    assert record["label"] == LABEL


def test_checks_carry_allowed_labels_and_the_core_facts():
    record = _json(RECORD)
    checks = record["checks"]
    assert [c["id"] for c in checks] == [f"C{i}" for i in range(1, 10)]
    for check in checks:
        assert set(check) == {"id", "statement", "label", "how"}
        assert check["label"] in {"PROVEN", "INFERRED", "UNVERIFIED"}
        assert check["statement"].strip() and check["how"].strip()
    by_id = {c["id"]: c["label"] for c in checks}
    for cid in ("C1", "C2", "C3", "C4", "C6", "C7"):
        assert by_id[cid] == "PROVEN", cid
    assert by_id["C5"] == "UNVERIFIED"
    assert by_id["C8"] == "INFERRED"


def test_count_proof_block_states_the_addendum_facts():
    proof = _json(RECORD)["count_proof"]
    assert proof["stored_vectors"] == 2130
    assert proof["dimensions"] == 384
    assert proof["all_pairs"] == 2130 * 2129 // 2 == 2267385
    assert proof["pairs_at_floor"] == 2165
    assert proof["floor"] == 0.55
    assert proof["label"] == "PROVEN"
    assert proof["model_on_disk"] is False
    assert proof["model_cited"] == "mdbr-leaf-ir"
    assert proof["store_dated"] == "2026-10-29"
    assert proof["replay_dated"] == "2026-10-21"
    assert proof["same_set_label"] == "INFERRED"
    assert "read-only vector export" in proof["partial_replay_needs"]
    assert "3.1" in proof["partial_replay_needs"]


def test_pair_count_identity_holds_and_a_wrong_record_is_refused():
    from mindrian_eureka.provenance.gap_list import GapListError, verify_arithmetic

    record = _json(RECORD)
    pairs = {(c["n"], c["pairs"]) for c in record["identity_checks"]}
    assert (2130, 2267385) in pairs
    assert (2117, 2239786) in pairs
    for n, total in pairs:
        assert n * (n - 1) // 2 == total
    assert record["replay"]["claims_cited"] == 2130
    assert record["replay"]["pairs_cited"] == 2267385
    verify_arithmetic(record)
    bad = copy.deepcopy(record)
    bad["replay"]["pairs_cited"] += 1
    with pytest.raises(GapListError):
        verify_arithmetic(bad)


def test_list_matches_the_golden_bytes():
    from mindrian_eureka.provenance.gap_list import build_list, load_record, render_json

    record_bytes = RECORD.read_bytes()
    record = load_record(RECORD)
    assert render_json(build_list(record, record_bytes)) == GOLDEN.read_bytes()


def test_list_content():
    golden = _json(GOLDEN)
    _validate(golden, LIST_SCHEMA)
    assert golden["schema_version"] == "eureka.provenance-gap-list.v1"
    assert golden["verdict"] == "provenance_gap"
    assert golden["outcome"] == "provenance_gap"
    assert golden["room_mark"] == "pending_approval"
    assert golden["label"] == LABEL
    assert [i["opportunity_id"] for i in golden["items"]] == ITEM_IDS
    for item in golden["items"]:
        assert set(item) == {"opportunity_id", "mark", "mark_text", "cites", "host_action"}
        assert item["mark"] == "provenance gap"
        assert LABEL in item["mark_text"]
    replay = golden["replay"]
    assert replay["claims_cited"] == 2130
    assert replay["pairs_cited"] == 2267385
    assert replay["artifact_found"] is False
    assert "Eureka writes nothing to a room" in golden["write_boundary"]
    assert isinstance(golden["closes_when"], list) and golden["closes_when"]
    assert golden["record_sha256"] == hashlib.sha256(RECORD.read_bytes()).hexdigest()


def test_text_format():
    from mindrian_eureka.provenance.gap_list import build_list, load_record, render_text

    text = render_text(build_list(load_record(RECORD), RECORD.read_bytes()))
    for item_id in ITEM_IDS:
        assert text.count(item_id) >= 1
    assert text.count("provenance gap") >= 5
    for item_id in ITEM_IDS:
        block = text.split(item_id, 1)[1].split("OPP-0", 1)[0]
        assert "provenance gap" in block
    assert LABEL in text
    assert "The room mark is a host-owned write that needs approval." in text
    assert EN_DASH not in text and EM_DASH not in text
    assert "/home/" not in text


def test_script_runs_twice_with_equal_output():
    first = _run()
    second = _run()
    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout == second.stdout == GOLDEN.read_bytes()
    lines = first.stderr.decode("utf-8").strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("sha256 ")
    assert lines[0] == "sha256 " + hashlib.sha256(first.stdout).hexdigest()
    text_run = _run("--format", "text")
    assert text_run.returncode == 0
    out = text_run.stdout.decode("utf-8")
    for item_id in ITEM_IDS:
        assert item_id in out
    assert not out.lstrip().startswith("{")


def test_check_mode(tmp_path):
    assert _run("--check").returncode == 0
    golden = bytearray(GOLDEN.read_bytes())
    golden[10] = golden[10] ^ 0x01
    bad_golden = tmp_path / "golden.json"
    bad_golden.write_bytes(bytes(golden))
    assert _run("--check", "--golden", str(bad_golden)).returncode == 1
    record = _json(RECORD)
    record["replay"]["pairs_cited"] += 1
    bad_record = tmp_path / "record.json"
    bad_record.write_text(json.dumps(record), encoding="utf-8")
    result = _run("--record", str(bad_record), "--check")
    assert result.returncode == 1
    assert result.stdout == b""
    plain = _run("--record", str(bad_record))
    assert plain.returncode == 1
    assert plain.stdout == b""


def test_bad_input_exits_2(tmp_path):
    missing = tmp_path / "missing.json"
    not_json = tmp_path / "not-json.json"
    not_json.write_text("this is not json", encoding="utf-8")
    bad_schema = tmp_path / "bad-schema.json"
    bad_schema.write_text("{}", encoding="utf-8")
    for path in (missing, not_json, bad_schema):
        result = _run("--record", str(path))
        assert result.returncode == 2, path.name
        assert result.stdout == b""
        err = result.stderr.decode("utf-8")
        assert len(err.strip().splitlines()) == 1
        assert "Traceback" not in err
        assert str(tmp_path) not in err
        assert "/home/" not in err


def test_wrapper_script_exists_and_is_executable():
    assert WRAPPER.is_file()
    assert os.access(WRAPPER, os.X_OK)
    text = WRAPPER.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "mindrian_eureka.provenance.gap_list" in text
    assert "uv run --offline" in text


def test_module_is_offline_light_and_read_only():
    source = MODULE_FILE.read_text(encoding="utf-8")
    for word in (
        "urllib",
        "requests",
        "socket",
        "subprocess",
        "http.client",
        "room.db",
        "sqlite3",
        "write_text",
        "write_bytes",
    ):
        assert word not in source, word
    assert not re.search(r"open\([^)]*[\"'](w|wb|a|ab|w\+)[\"']", source)
    probe = (
        "import sys\n"
        "import mindrian_eureka.provenance.gap_list\n"
        "heavy = {'numpy', 'sklearn', 'torch', 'pydantic', 'mcp'}\n"
        "loaded = sorted(heavy & {m.split('.')[0] for m in sys.modules})\n"
        "print(','.join(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, cwd=ROOT, env=_env(), check=False
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert result.stdout.decode("utf-8").strip() == ""


def test_record_doc_front_matter_contract():
    fm = parse_front_matter(DOC.read_text(encoding="utf-8"))
    record = _json(RECORD)
    assert fm["outcome"] == "provenance_gap"
    assert fm["room_mark"] == "pending_approval"
    assert fm["outcome"] == record["outcome"]
    assert fm["room_mark"] == record["room_mark"]
    assert fm["room_mark"] in {"done", "pending_approval"}
    for key in ("claims", "pairs", "two_run_hashes_equal"):
        assert key not in fm
    assert set(fm) == {"outcome", "room_mark", "label", "checked_on"}
    assert fm["label"] == LABEL
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["checked_on"])


def test_record_doc_headings_and_content():
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    body = lines[end + 1 :]
    headings: list[str] = []
    fenced = False
    for line in body:
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and (line.startswith("# ") or line.startswith("## ")):
            headings.append(line)
    assert headings == DOC_HEADINGS
    for term in (
        "2,130",
        "2,267,385",
        "2,165",
        "384",
        "derive_results.json",
        "provenance gap",
        LABEL,
        "PROVEN",
        "INFERRED",
        "UNVERIFIED",
        "scripts/emit-provenance-gap-list",
        "writes nothing to a room",
        "pending_approval",
    ):
        assert term in text, term


def test_house_style_of_every_new_text_file():
    names = ("Sagir", "Aronhime", "Jonathan", "Lawrence")
    for path in (DOC, RECORD, GOLDEN, WRAPPER, MODULE_FILE):
        text = path.read_text(encoding="utf-8")
        assert EN_DASH not in text and EM_DASH not in text, path.name
        assert "/home/" not in text and "/mnt/" not in text, path.name
        lowered = text.lower()
        assert "university" not in lowered and "institute" not in lowered, path.name
        for name in names:
            assert name not in text, (path.name, name)
    for path in (DOC, GOLDEN):
        assert not re.search(r"\b(RS|HSI)\b", path.read_text(encoding="utf-8")), path.name


def test_cli_py_is_not_part_of_this_plan():
    assert "provenance" not in CLI_FILE.read_text(encoding="utf-8")
