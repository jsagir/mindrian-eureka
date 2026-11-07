"""Tests for the `eureka seed` command with --pair (Phase 2.3, plan 02)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from hub_support import tree_hash
from mindrian_eureka.cli import main
from mindrian_eureka.run.contracts import (
    LABEL,
    MAPPING_SCHEMA,
    SUMMARY_LINE,
)
from mindrian_eureka.run.mapping import load_mapping_file
from mindrian_eureka.run.pipeline import RunRequest, run_pipeline
from mindrian_eureka.seed.contracts import OUTPUT_SEED, SEED_SCHEMA, SEED_SUMMARY_SCHEMA
from seed_support import make_seed_run, pair_id_of
from test_run_cli import ANSI, HEAVY, SHORT_CODE, help_text
from test_run_outcome_class import CARRY, DESC, HEADERS, RULE, TOPICS, quiet_console

ROOM_NAMES = {"ROOM.md", "STATE.md", ".mindrian", "room.db", "registry"}


def files_under(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def seed_args(run: Path, out: Path, i: int = 0, j: int = 2, *extra: str) -> list[str]:
    return ["seed", str(run), "--pair", pair_id_of(i, j), "--out", str(out), *extra]


def printed_sha(text: str) -> str:
    line = next(item for item in text.splitlines() if item.startswith("Seed file:"))
    return line.split("sha256 ")[1].rstrip(")")


def test_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = make_seed_run(tmp_path)
    out = tmp_path / "seed"
    assert main(seed_args(run, out)) == 0
    captured = capsys.readouterr()
    files = files_under(out)
    assert OUTPUT_SEED in files
    evidence = {name for name in files if name != OUTPUT_SEED}
    assert len(evidence) == 2
    assert all(name.startswith("evidence/") and name.endswith(".md") for name in evidence)
    names = {p.name for p in out.rglob("*")}
    assert not names & ROOM_NAMES
    assert printed_sha(captured.out) == hashlib.sha256((out / OUTPUT_SEED).read_bytes()).hexdigest()
    lines = captured.out.splitlines()
    assert lines[0] == "Eureka seed written."
    assert lines[-1] == SUMMARY_LINE
    assert any("not a room" in line for line in lines)
    assert "Traceback" not in captured.err
    # Nothing was written into the run folder.
    assert not any(p.name.startswith("seed") for p in run.iterdir())


def test_json_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = make_seed_run(tmp_path)
    out = tmp_path / "seed"
    assert main(seed_args(run, out, 0, 2, "--json")) == 0
    raw = capsys.readouterr().out
    summary = json.loads(raw)
    document = json.loads((out / OUTPUT_SEED).read_text(encoding="utf-8"))
    assert summary["schema_version"] == SEED_SUMMARY_SCHEMA
    assert summary["label"] == LABEL
    assert summary["seed_kind"] == "pair"
    assert summary["seed_sha256"] == hashlib.sha256((out / OUTPUT_SEED).read_bytes()).hexdigest()
    counts = summary["counts"]
    assert counts["records"] == len(document["records"])
    assert counts["evidence_files"] == len(document["records"])
    assert counts["bank_entries"] == len(document["bank_entries"])
    assert counts["known"] == sum(len(v) for v in document["known"].values())
    assert counts["feed_next"] == sum(len(v) for v in document["feed_next"].values())
    assert summary["summary_line"] == SUMMARY_LINE
    assert document["schema_version"] == SEED_SCHEMA
    assert str(tmp_path) not in raw and "/home/" not in raw and str(out) not in raw
    assert {item["path"] for item in summary["files"]} == files_under(out)


def test_determinism_and_replace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = make_seed_run(tmp_path)
    first, second = tmp_path / "one", tmp_path / "two"
    shas = []
    for out in (first, second, first):
        assert main(seed_args(run, out)) == 0
        shas.append(printed_sha(capsys.readouterr().out))
    assert len(set(shas)) == 1
    assert tree_hash(first) == tree_hash(second)
    assert not [p for p in tmp_path.iterdir() if ".staging" in p.name or ".old" in p.name]


def _tamper(run: Path) -> None:
    with (run / "corpus/records.jsonl").open("ab") as stream:
        stream.write(b" ")


@pytest.mark.parametrize(
    "kind,code",
    [("unknown-pair", 2), ("no-sections", 2), ("not-a-run", 2), ("inside-run", 2),
     ("foreign-out", 2), ("tampered", 1)],
)
def test_refusals(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str, code: int) -> None:
    run = make_seed_run(tmp_path, with_room_sections=kind != "no-sections")
    out = tmp_path / "seed"
    pair = pair_id_of(0, 2)
    if kind == "unknown-pair":
        pair = "pair-" + "0" * 20
    elif kind == "not-a-run":
        run = tmp_path / "plain"
        run.mkdir()
    elif kind == "inside-run":
        out = run / "seed"
    elif kind == "foreign-out":
        out.mkdir()
        (out / "keep.txt").write_text("keep")
    elif kind == "tampered":
        _tamper(run)
    assert main(["seed", str(run), "--pair", pair, "--out", str(out)]) == code
    captured = capsys.readouterr()
    assert not captured.out and "Fix:" in captured.err
    assert "Invented record" not in captured.err
    if kind == "foreign-out":
        assert files_under(out) == {"keep.txt"}
    elif kind != "inside-run":
        assert not out.exists()
    else:
        assert not (run / "seed").exists()


def test_default_out_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = make_seed_run(tmp_path, name="run")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    pair = pair_id_of(0, 2)
    assert main(["seed", str(run), "--pair", pair]) == 0
    capsys.readouterr()
    assert (work / f"eureka-seed-{pair}" / OUTPUT_SEED).is_file()


def test_help(capsys: pytest.CaptureFixture[str]) -> None:
    text = " ".join(help_text(capsys, "seed").split())
    for word in (LABEL, "no network", "not a room", "Exit codes", "--pair", "--out", "--json",
                 "--quiet", "--no-color", "--debug", "never writes into it", "no model",
                 "birth gate", "seed.json", "evidence"):
        assert word in text, word
    assert SHORT_CODE.search(text) is None and ANSI.search(text) is None


def test_top_help_lists_seed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "seed" in capsys.readouterr().out


def test_offline(tmp_path: Path, no_network: list[object]) -> None:
    run = make_seed_run(tmp_path)
    assert main(seed_args(run, tmp_path / "seed")) == 0
    assert no_network == []


def test_light_import() -> None:
    script = (
        "import sys, mindrian_eureka.seed.command, mindrian_eureka.seed.builder\n"
        f"bad = [m for m in {HEAVY!r} if m in sys.modules]\n"
        "assert not bad, bad\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_seed_holds_no_absolute_path(tmp_path: Path) -> None:
    run = make_seed_run(tmp_path)
    out = tmp_path / "seed"
    assert main(seed_args(run, out)) == 0
    for path in out.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert str(run).encode() not in data
            assert str(tmp_path).encode() not in data
            assert b"/home/" not in data and b"file://" not in data


def test_exception_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mindrian_eureka.seed import builder

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt

    run = make_seed_run(tmp_path)
    monkeypatch.setattr(builder, "write_seed", fail)
    assert main(seed_args(run, tmp_path / "seed")) == 130

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("x")

    monkeypatch.setattr(builder, "write_seed", broken)
    assert main(seed_args(run, tmp_path / "seed")) == 1


# --- A real run -------------------------------------------------------------


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


REAL_HEADERS = [*HEADERS, "problem_solved", "lead_inventor", "funding_total"]
REAL_SECTIONS: dict[str, Any] = {
    "problem-definition": ["problem_solved"],
    "legal-ip": ["status", "licenses", "first_license_or_option_date"],
    "financial-model": ["funding_total"],
    "team": ["lead_inventor"],
    "not_in_export": [{"item": "patents", "section": "legal-ip", "source": "SynthDB"}],
}


def real_rows() -> list[dict[str, str]]:
    rows = []
    for index in range(1, 13):
        case = f"C{index:05d}"
        row = {
            "case_number": case,
            "title": f"Synthetic title {index}",
            "text_a": f"{DESC} Row {index} is about {TOPICS[(index - 1) % len(TOPICS)]}.",
            "licensed_to_jh_startup": "Y" if index % 2 else "N",
            "licensed_externally": "N",
            "licenses": str(index % 3),
            "options": "0",
            "had_corporate_research": "N",
            "status": "Inactive- Licensed" if index % 2 else "Active",
            "first_license_or_option_date": f"20{10 + index}-01-01" if index % 2 else "",
            "problem_solved": f"Invented problem {index}" if index % 3 else "",
            "lead_inventor": f"invented-person-{index}" if index % 5 else "",
            "funding_total": str(index * 100) if index % 4 else "",
        }
        rows.append(row)
    return rows


def test_real_run_then_seed(
    env: Path, fake_model_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from mindrian_eureka.seed.builder import validate_seed

    folder = tmp_path / "in"
    folder.mkdir()
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REAL_HEADERS, lineterminator="\n")
    writer.writeheader()
    rows = real_rows()
    writer.writerows(rows)
    (folder / "recs.csv").write_bytes(buffer.getvalue().encode("utf-8"))
    entry = {
        "id_column": "case_number",
        "title_column": "title",
        "text_columns": ["text_a", "problem_solved"],
        "outcome_rule": RULE,
        "carry_columns": CARRY,
        "room_sections": REAL_SECTIONS,
    }
    mapping_path = tmp_path / "map.json"
    mapping_path.write_text(
        json.dumps({"schema_version": MAPPING_SCHEMA, "files": {"*": entry}}), encoding="utf-8"
    )
    mapping = load_mapping_file(mapping_path)
    out = tmp_path / "out"
    request = RunRequest(
        input_dir=folder, out_dir=out, mapping=mapping, model_path=fake_model_dir, top_k=30
    )
    run_pipeline(request, quiet_console())
    first = json.loads((out / "unusual-pairs.json").read_text(encoding="utf-8"))["pairs"][0]
    seed_out = tmp_path / "seed"
    assert main(["seed", str(out), "--pair", first["pair_id"], "--out", str(seed_out)]) == 0
    capsys.readouterr()
    document = json.loads((seed_out / OUTPUT_SEED).read_text(encoding="utf-8"))
    validate_seed(document)
    by_title = {row["title"]: row for row in rows}
    chosen = {
        side["id"]: by_title[side["title"]] for side in (first["left"], first["right"])
    }
    carried = [
        item
        for entries in document["known"].values()
        for item in entries
        if item["held_in"] == "carried"
    ]
    assert carried
    for item in carried:
        assert item["value"] == chosen[item["record_id"]][item["column"]]
    expected_blank = {
        (record_id, column)
        for record_id, row in chosen.items()
        for column in (
            "problem_solved", "status", "licenses", "first_license_or_option_date",
            "funding_total", "lead_inventor",
        )
        if not row[column]
    }
    got_blank = {
        (item["record_id"], item["column"])
        for entries in document["feed_next"].values()
        for item in entries
        if "column" in item
    }
    assert got_blank == expected_blank
    items = [
        item for entries in document["feed_next"].values() for item in entries if "item" in item
    ]
    assert len(items) == 2 and all(item["item"] == "patents" for item in items)
    # The people and money values never reach the seed.
    text = "".join(p.read_text(encoding="utf-8") for p in seed_out.rglob("*") if p.is_file())
    assert "invented-person-" not in text
