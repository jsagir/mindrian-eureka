"""Build and capture public-only hub review evidence. No model or network is used."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from hub_browser_support import file_url, require_browser, run_scenario  # noqa: E402
from hub_support import tree_hash  # noqa: E402
from mindrian_eureka.hub.reader import load_run  # noqa: E402
from mindrian_eureka.hub.writer import HubRequest, build_hub  # noqa: E402
from mindrian_eureka.run.console import Console  # noqa: E402
from mindrian_eureka.run.output import (  # noqa: E402
    canonical_json,
    corpus_lines,
    render_ranked_markdown,
)

PUBLIC = ROOT / "tests/fixtures/hub_public"
WORK = ROOT / "build/hub-review"
EVIDENCE = ROOT / ".planning/phases/02.1-opportunity-hub-in-the-mos-brand-format/evidence"
CLI = Path.home() / "mos-brand/bin/mos-brand.cjs"
CHECK = ROOT / "tests/hub_browser/checks/review-state.js"
WIDTHS = (320, 390, 768, 1280, 1600)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_subset(count: int) -> Path:
    """Project stored public records/pairs for a review state, without changing scores.

    This is a temporary review projection, not a new model run or a new finding.
    Ranks become positions in the retained list. Cut-offs and every stored score stay fixed.
    """
    source = PUBLIC / "run"
    records = sorted(load_run(source).records, key=lambda record: record.id)[:count]
    ids = {record.id for record in records}
    folder = WORK / f"public-subset-{count}"
    folder.mkdir(parents=True, exist_ok=True)
    marker = "Public subset for state review; stored scores preserved; no model run or finding."
    docs = []
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        data = json.loads((source / name).read_text())
        data["pairs"] = [pair for pair in data["pairs"]
                         if pair["left"]["id"] in ids and pair["right"]["id"] in ids]
        for rank, pair in enumerate(data["pairs"], 1):
            pair["rank"] = rank
        data["counts"].update(pairs=len(data["pairs"]), records_scored=count,
                              top_k_reached=False)
        data["notes"] = [marker]
        (folder / name).write_bytes(canonical_json(data))
        docs.append(data)
    (folder / "corpus").mkdir(exist_ok=True)
    (folder / "corpus/records.jsonl").write_bytes(corpus_lines(records))
    (folder / "ranked-pairs.md").write_text(render_ranked_markdown(*docs))
    manifest = copy.deepcopy(json.loads((source / "manifest.json").read_text()))
    manifest["corpus"].update(records_read=count, records_used=count, dropped=[], caps_hit=[])
    manifest["corpus"]["corpus_digest"] = sha(folder / "corpus/records.jsonl")
    manifest["engine_notes"] = [marker]
    for output in manifest["outputs"]:
        path = folder / output["path"]
        output.update(bytes=path.stat().st_size, sha256=sha(path))
        if "pairs" in output:
            doc = docs[0 if output["path"] == "unusual-pairs.json" else 1]
            output.update(pairs=len(doc["pairs"]), top_k_reached=False)
    (folder / "manifest.json").write_bytes(canonical_json(manifest))
    loaded = load_run(folder)
    assert len(loaded.records) == count
    provenance = {"purpose": marker, "records": [record.id for record in records],
                  "source_manifest_sha256": sha(source / "manifest.json"),
                  "subset_manifest_sha256": sha(folder / "manifest.json"),
                  "scores_recomputed": False, "cutoffs_changed": False}
    target = EVIDENCE / "data" / f"public-subset-{count}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(provenance))
    return folder


def build_review_hubs() -> dict[str, Path]:
    before = tree_hash(PUBLIC)
    WORK.mkdir(parents=True, exist_ok=True)
    password = os.environ.setdefault("HUB_REVIEW_PASS", "synthetic review passphrase only")
    hubs = {"open": WORK / "hub", "locked": WORK / "hub-locked",
            "diagram": WORK / "hub-diagram", "empty": WORK / "hub-empty"}
    console = Console(stderr=io.StringIO())
    build_hub(HubRequest(PUBLIC / "run", hubs["open"]), console)
    build_hub(HubRequest(PUBLIC / "run", hubs["locked"], password=password), console)
    build_hub(HubRequest(public_subset(12), hubs["diagram"]), console)
    build_hub(HubRequest(public_subset(1), hubs["empty"]), console)
    assert tree_hash(PUBLIC) == before, "The frozen public fixture changed."
    return hubs


def step(name: str, **args: object) -> dict[str, object]:
    return {"kind": "eval", "file": str(CHECK), "as": name, "args": args}


def capture(hub: Path, steps: list[dict[str, object]], **options: object) -> dict:
    result = run_scenario({"browser": "chromium", "url": file_url(hub / "hub.html"),
                           "steps": steps, **options})
    assert result["ok"], result["stepErrors"]
    assert not result["pageErrors"], result["pageErrors"]
    assert not result["blockedRequests"], result["blockedRequests"]
    assert not result["cspViolations"], result["cspViolations"]
    assert not [item for item in result["console"] if item["type"] == "error"]
    return result


def snapshots(hubs: dict[str, Path]) -> dict[str, Path]:
    folder = WORK / "snapshots"
    folder.mkdir(exist_ok=True)
    files = {"hub": hubs["open"] / "hub.html"}
    steps = []
    for view in ("bank", "graph", "catalogue"):
        files[view] = folder / f"{view}.html"
        steps += [step(view, view=view), {"kind": "dom", "path": str(files[view])}]
    for kind in ("record", "pair"):
        name = "panel-" + kind
        files[name] = folder / f"{name}.html"
        steps += [step(name, view="bank", panel=kind, full=True),
                  {"kind": "dom", "path": str(files[name])}]
    capture(hubs["open"], steps)
    files["locked"] = folder / "locked.html"
    capture(hubs["locked"], [{"kind": "dom", "path": str(files["locked"])}])
    return files


def review(files: dict[str, Path]) -> list[dict]:
    folder = WORK / "review"
    folder.mkdir(exist_ok=True)
    target = EVIDENCE / "review"
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for name, path in files.items():
        relative = path.relative_to(ROOT).as_posix()
        completed = subprocess.run(["node", str(CLI), "review", "--file", relative],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
        result = json.loads(completed.stdout)
        result["exit_code"] = completed.returncode
        result["review_name"] = name
        data = canonical_json(result)
        (folder / f"{name}.json").write_bytes(data)
        (target / f"{name}.json").write_bytes(data)
        results.append(result)
    return results


def screens(hubs: dict[str, Path]) -> None:
    folder = WORK / "screens"
    folder.mkdir(exist_ok=True)

    def shot(name: str) -> dict[str, object]:
        return {"kind": "screenshot", "path": str(folder / f"{name}.jpg"), "quality": 85}

    for width in WIDTHS:
        steps = []
        for view in ("bank", "graph", "catalogue"):
            steps += [step(view, view=view, clear=True, scroll="results"), shot(f"{view}-{width}")]
            if width in (390, 1280):
                steps += [step(view + "-header", scroll="top"), shot(f"{view}-header-{width}")]
        capture(hubs["open"], steps, viewport={"width": width, "height": 900})
    capture(hubs["open"], [step("stage", view="graph", scroll="stage"),
                           shot("graph-stage-768")], viewport={"width": 768, "height": 900})
    capture(hubs["empty"], [step("empty-header", view="bank", scroll="top"),
                            shot("empty-header-1280")], viewport={"width": 1280, "height": 900})
    for width in (390, 1280):
        capture(hubs["open"], [step("record", view="bank", panel="record", scroll="results"),
                               shot(f"panel-record-{width}")],
                viewport={"width": width, "height": 900})
        capture(hubs["locked"], [shot(f"locked-{width}")],
                viewport={"width": width, "height": 900})
    capture(hubs["open"], [step("pair", view="bank", panel="pair", scroll="results"),
                           shot("panel-pair-1280")], viewport={"width": 1280, "height": 900})
    for state, hub, view, options in (
        ("diagram", hubs["diagram"], "graph", {}),
        ("empty", hubs["empty"], "bank", {}),
        ("fallback", hubs["open"], "graph", {"webgl": False}),
        ("reduced", hubs["open"], "graph", {"reducedMotion": True}),
    ):
        capture(hub, [step(state, view=view, scroll="results"), shot(state + "-1280")],
                viewport={"width": 1280, "height": 900}, **options)
    for view in ("bank", "graph", "catalogue"):
        capture(hubs["open"], [step(view, view=view, scroll="results"),
                               shot(f"forced-{view}-1280")],
                viewport={"width": 1280, "height": 900}, forcedColors="active")
    none = WORK / "none.js"
    none.write_text("HubApp.go('graph',{focus:false});"
                    "document.getElementById('graph-tour-empty').scrollIntoView();return true;")
    capture(hubs["open"], [step("graph", view="graph"),
                           {"kind": "eval", "file": str(none)}, shot("none-390")],
            viewport={"width": 390, "height": 900})
    rest = WORK / "rest.js"
    rest.write_text("document.getElementById('hub-panel').scrollIntoView();return true;")
    capture(hubs["open"], [step("empty-panel", view="bank", clear=True),
                           {"kind": "eval", "file": str(rest)}, shot("panel-empty-1280")],
            viewport={"width": 1280, "height": 900})
    target = EVIDENCE / "screens"
    target.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.jpg"):
        shutil.copyfile(path, target / path.name)
    total = sum(path.stat().st_size for path in target.glob("*.jpg"))
    assert total < 6_000_000, f"Screens exceed 6 MB: {total} bytes"


def file_table() -> None:
    for folder in (EVIDENCE / "review", EVIDENCE / "screens", EVIDENCE / "data"):
        if folder.exists():
            for path in sorted(folder.iterdir()):
                if path.is_file():
                    print(f"{path.relative_to(ROOT)} | {path.stat().st_size} | {sha(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only", action="store_true",
                        help="Review all snapshots before capture")
    args = parser.parse_args()
    require_browser()
    hubs = build_review_hubs()
    results = review(snapshots(hubs))
    bad = [result for result in results if result["status"] != "REVIEW-REQUIRED"
           or result["findings"] or result["exit_code"] != 2]
    if bad:
        print(json.dumps([{"file": item["file"], "findings": item["findings"]} for item in bad]))
        return 1
    if not args.review_only:
        screens(hubs)
    file_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
