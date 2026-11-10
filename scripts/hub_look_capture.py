"""Build the Phase 2.3.1 hub from the public fixture and capture its look in both themes.

Plan 02.3.1-09, decisions D-05 and D-06, owner ruling R-01. The script:

1. records the tree hash of the Phase 2.1 evidence folder and of the public fixture;
2. builds the four review hubs (open, locked, 12-record diagram, 1-record empty) through
   `hub_review_capture.build_review_hubs` into `build/hub-look`;
3. runs the book CLI once, read only, with the single argument `doctor`, and writes
   `evidence/data/review-status.json` with the honest sentence about the book review;
4. captures 44 JPEG screenshots (five widths, light and dark, the three views, the page top,
   a pair page, a record page, the locked page, the panel, the empty state and the small
   diagram) into a folder outside the repository;
5. copies them into the Phase 2.3.1 evidence folder with an inventory (bytes and sha256);
6. asserts that the Phase 2.1 evidence and the public fixture did not change.

It never calls the old `screens()` or `review()` of `hub_review_capture`, so the Phase 2.1
evidence pin stays whole. No network, no model, public fixture data only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import hub_review_capture as base  # noqa: E402
from hub_browser_support import file_url, require_browser, run_scenario  # noqa: E402
from hub_support import tree_hash  # noqa: E402

PHASE = (ROOT / ".planning/phases"
         / "02.3.1-hub-look-matches-the-live-jhtv-site-cobalt-red-and-yellow-ac")
EVIDENCE = PHASE / "evidence"
OLD_EVIDENCE = base.EVIDENCE
PUBLIC = base.PUBLIC
CLI = base.CLI
CHECK = ROOT / "tests/hub_browser/checks/capture-state.js"
WIDTHS = (320, 390, 768, 1280, 1600)
HEIGHT = 900
# The Phase 2.1 budget is 6,000,000 bytes for 37 screens; scaled to 44 screens and rounded
# up to the next million.
BUDGET = 8_000_000
REVIEW_SENTENCE = "book review: not run, lock not reconciled, by owner ruling R-01; advisory"

# The new work and evidence folders are set before any call into the base module.
base.WORK = ROOT / "build/hub-look"
base.EVIDENCE = EVIDENCE


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def book_doctor() -> dict[str, object]:
    """Call the book CLI read only. The one argument this helper passes is `doctor`."""
    try:
        completed = subprocess.run(["node", str(CLI), "doctor"], cwd=ROOT,
                                   capture_output=True, text=True, check=False, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        return {"doctor_status": "NOT RUN", "problems": 0, "doctor_note": str(error)}
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        data = {}
    problems = data.get("problems", [])
    status = data.get("status") or ("NOT RUN" if not completed.stdout.strip() else "UNPARSED")
    return {"doctor_status": status,
            "problems": len(problems) if isinstance(problems, list) else 0,
            "doctor_version": data.get("version"),
            "doctor_exit_code": completed.returncode}


def write_review_status() -> Path:
    status = book_doctor()
    status["review"] = REVIEW_SENTENCE
    status["checked"] = datetime.now(UTC).strftime("%Y-%m-%d")
    status["note"] = ("Read-only doctor output, recorded as it is. No book write command "
                      "runs in this phase. The book review is not a gate.")
    target = EVIDENCE / "data/review-status.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_payload(hub: Path) -> dict:
    """Read the payload that the built hub carries in hub-data.js."""
    text = (hub / "hub-data.js").read_text(encoding="utf-8")
    start = text.index("{")
    end = text.rindex("}")
    return json.loads(text[start:end + 1])


def page_hashes(hub: Path) -> tuple[str, str]:
    payload = read_payload(hub)
    engine = next(iter(payload["engines"]))
    pair = next(p for p in payload["pairs"] if p["engine"] == engine and p["rank"] == 3)
    record = next(r for r in payload["records"] if r["pair_count"] > 0)
    return f"/pair/{pair['engine']}/{pair['rank']}", f"/record/{quote(record['id'], safe='')}"


def step(name: str, **args: object) -> dict[str, object]:
    return {"kind": "eval", "file": str(CHECK), "as": name, "args": args}


def capture(hub: Path, steps: list[dict[str, object]], **options: object) -> dict:
    """Run one scenario as `hub_review_capture.capture` does, with longer time limits.

    The host that ran the first capture had a load average near 28 on 12 cores; a screenshot
    then took up to 30 seconds. Each step gets 120 seconds and the whole scenario 900.
    """
    result = run_scenario({"browser": "chromium", "url": file_url(hub / "hub.html"),
                           "steps": steps, "timeoutMs": 120000, **options}, timeout=900)
    assert result["ok"], result["stepErrors"]
    assert not result["pageErrors"], result["pageErrors"]
    assert not result["blockedRequests"], result["blockedRequests"]
    assert not result["cspViolations"], result["cspViolations"]
    errors = [item for item in result["console"] if item["type"] == "error"]
    assert not errors, errors
    return result


def shots(hubs: dict[str, Path], folder: Path, quality: int) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("*.jpg"):
        stale.unlink()
    pair_hash, record_hash = page_hashes(hubs["open"])

    def shot(name: str) -> dict[str, object]:
        return {"kind": "screenshot", "path": str(folder / f"{name}.jpg"), "quality": quality}

    def view_step(prefix: str, view: str, width: int) -> list[dict[str, object]]:
        return [step(f"{prefix}{view}", view=view, clear=True, scroll="results"),
                shot(f"{prefix}{view}-{width}")]

    # The graph view is captured last in every scenario. Measured on 2026-11-10 in Chromium:
    # once the 3D graph has started, a later screenshot of a pair or record page takes about
    # 20 seconds (a capture-tool effect; the page itself is not slow for a person, UNVERIFIED).
    for width in WIDTHS:
        steps = [step("top", scroll="top"), shot(f"top-{width}"),
                 step("pair", hash=pair_hash, scroll="top"), shot(f"pair-{width}"),
                 step("record", hash=record_hash, scroll="top"), shot(f"record-{width}")]
        for view in ("bank", "catalogue", "graph"):
            steps += view_step("", view, width)
        capture(hubs["open"], steps, viewport={"width": width, "height": HEIGHT})
    for width in (390, 1280):
        capture(hubs["locked"], [step("locked"), shot(f"locked-{width}")],
                     viewport={"width": width, "height": HEIGHT})
    capture(hubs["open"], [step("panel-pair", view="bank", panel="pair", scroll="results"),
                                shot("panel-pair-1280")],
                 viewport={"width": 1280, "height": HEIGHT})
    capture(hubs["open"], [step("panel-record", view="bank", panel="record",
                                     scroll="results"), shot("panel-record-390")],
                 viewport={"width": 390, "height": HEIGHT})
    capture(hubs["empty"], [step("empty", view="bank", scroll="results"),
                                 shot("empty-1280")],
                 viewport={"width": 1280, "height": HEIGHT})
    capture(hubs["diagram"], [step("diagram", view="graph", scroll="results"),
                                   shot("diagram-1280")],
                 viewport={"width": 1280, "height": HEIGHT})
    dark = [step("dark-top", theme="dark", scroll="top"), shot("dark-top-1280"),
            step("dark-pair", hash=pair_hash, scroll="top"), shot("dark-pair-1280")]
    dark += view_step("dark-", "bank", 1280)
    dark += [step("dark-panel-pair", view="bank", panel="pair", scroll="results"),
             shot("dark-panel-pair-1280")]
    dark += view_step("dark-", "catalogue", 1280)
    dark += view_step("dark-", "graph", 1280)
    capture(hubs["open"], dark, viewport={"width": 1280, "height": HEIGHT},
                 colorScheme="dark")
    capture(hubs["open"], [step("dark-bank", theme="dark", view="bank", clear=True,
                                     scroll="results"), shot("dark-bank-390"),
                                step("dark-record", hash=record_hash, scroll="top"),
                                shot("dark-record-390")],
                 viewport={"width": 390, "height": HEIGHT}, colorScheme="dark")
    images = sorted(folder.glob("*.jpg"))
    assert len(images) == 44, f"expected 44 screens, captured {len(images)}"
    return images


def store(images: list[Path], command: str) -> Path:
    target = EVIDENCE / "screens"
    target.mkdir(parents=True, exist_ok=True)
    for stale in target.glob("*.jpg"):
        stale.unlink()
    for path in images:
        shutil.copyfile(path, target / path.name)
    stored = sorted(target.glob("*.jpg"))
    total = sum(path.stat().st_size for path in stored)
    assert total < BUDGET, f"Screens reach the budget: {total} bytes, limit {BUDGET}"
    files = []
    for path in stored + sorted((EVIDENCE / "data").glob("*.json")):
        if path.name == "files.json":
            continue
        files.append({"path": path.relative_to(ROOT).as_posix(),
                      "bytes": path.stat().st_size, "sha256": sha(path)})
    inventory = {"capture_command": command, "screens_total_bytes": total, "files": files,
                 "screens": len(stored), "budget_bytes": BUDGET}
    out = EVIDENCE / "data/files.json"
    out.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def file_table() -> None:
    for folder in (EVIDENCE / "data", EVIDENCE / "screens"):
        for path in sorted(folder.iterdir()):
            if path.is_file():
                print(f"{path.relative_to(ROOT).as_posix()} | {path.stat().st_size} | {sha(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shots-dir", type=Path,
                        default=Path(tempfile.gettempdir()) / "eureka-hub-look-shots",
                        help="Folder outside the repository for the raw captures")
    args = parser.parse_args()
    shots_dir = args.shots_dir.resolve()
    if shots_dir == ROOT or ROOT in shots_dir.parents:
        print(f"Refused: --shots-dir must be outside the repository ({shots_dir})",
              file=sys.stderr)
        return 2
    command = "PYTHONPATH=src python3 scripts/hub_look_capture.py --shots-dir " + str(shots_dir)
    old_before = tree_hash(OLD_EVIDENCE)
    public_before = tree_hash(PUBLIC)
    require_browser()
    hubs = base.build_review_hubs()
    print("HUB_REVIEW_PASS=" + os.environ["HUB_REVIEW_PASS"])
    status = write_review_status()
    print(f"review status: {status.relative_to(ROOT).as_posix()}")
    images = shots(hubs, shots_dir, 85)
    total = sum(path.stat().st_size for path in images)
    if total >= BUDGET:
        print(f"Total {total} bytes at quality 85 reaches the budget; recapturing at 80")
        images = shots(hubs, shots_dir, 80)
    store(images, command)
    assert tree_hash(OLD_EVIDENCE) == old_before, "The Phase 2.1 evidence folder changed."
    assert tree_hash(PUBLIC) == public_before, "The frozen public fixture changed."
    file_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
