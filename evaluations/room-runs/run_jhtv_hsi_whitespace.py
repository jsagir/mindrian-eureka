"""Run the HSI-seeded room-whitespace workflow on Oliver's six banked pairs.

This evaluation uses a TF-IDF lexical proxy and JHTV taxonomy paths as
reference frameworks because the room has no MindrianOS whitespace vectors or
Brain baseline bundle. It writes its report under this repository and never
modifies the room.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


REPO = Path(__file__).resolve().parents[2]
ROOM = Path("/home/jsagi/MindrianRooms/jhtv-oliver-kuntz")
CSV_DIR = ROOM / "research/2026-07-06-jhu-tech-csv-source"
SOURCE_DIR = ROOM / "solution-design/full-catalog-sme-2026-10-18"
RUN_DIR = ROOM / "solution-design/full-catalog-run-2026-10-18"
OUT_DIR = REPO / "evaluations/room-runs"


def main() -> None:
    with (CSV_DIR / "technologies.csv").open(encoding="utf-8-sig", newline="") as stream:
        technologies = list(csv.DictReader(stream))
    with (CSV_DIR / "categories.csv").open(encoding="utf-8-sig", newline="") as stream:
        category_rows = list(csv.DictReader(stream))
    bank = json.loads((SOURCE_DIR / "candidate-opportunity-bank.json").read_text())
    selected = [row for row in bank["records"] if row.get("status") == "banked_candidate"]
    if len(selected) != 6:
        raise ValueError(f"Expected six banked candidates, found {len(selected)}")

    hsi = json.loads((RUN_DIR / "hsi-full-catalog.json").read_text())
    hsi_pairs = {
        frozenset((row["left_id"].split("/")[-1], row["right_id"].split("/")[-1])): row
        for row in hsi["hsi_pairs"]
    }
    texts = [" ".join(row.get(key, "") for key in (
        "title", "keywords", "unmet_need", "value_prop", "tech_description", "description_full"
    )) for row in technologies]
    category_paths = sorted({row["category_path"] for row in category_rows if row.get("category_path")})
    vectorizer = TfidfVectorizer(max_features=512, ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
    vectors = vectorizer.fit_transform(texts + category_paths)

    artifacts = []
    for i, row in enumerate(technologies):
        artifacts.append({
            "id": row["case_id"], "title": row.get("title") or row["case_id"],
            "source_ref": row.get("url") or f"technologies.csv#{row['case_id']}",
            "text": texts[i][:10_000], "vector": vectors[i].toarray().ravel().tolist(),
        })
    frameworks = []
    for i, label in enumerate(category_paths, start=len(technologies)):
        vector = vectors[i].toarray().ravel()
        if np.linalg.norm(vector) == 0:
            continue
        frameworks.append({
            "id": f"jhtv-category-{len(frameworks)+1:03d}", "label": label,
            "source_ref": "categories.csv", "vector": vector.tolist(),
        })
    seeds = []
    for row in selected:
        pair = hsi_pairs.get(frozenset((row["case_a"], row["case_b"])))
        if pair is None:
            raise ValueError(f"No matching HSI result for {row['case_a']} / {row['case_b']}")
        seeds.append({
            "left_id": row["case_a"], "right_id": row["case_b"],
            "hsi_score": pair["hsi_score"], "hsi_percentile": pair.get("hsi_percentile"),
            "candidate_id": row.get("banked_opportunity_id"),
        })

    request = {
        "scope_id": "jhtv-oliver-kuntz", "snapshot_id": "jhu-catalog-2026-07-06",
        "embedding_model": "TF-IDF word/bigram, max_features=512 (lexical proxy; not a semantic sentence encoder)",
        "artifacts": artifacts, "baseline_frameworks": frameworks, "hsi_pairs": seeds,
    }
    with tempfile.TemporaryDirectory(prefix="jhtv-hsi-whitespace-") as directory:
        input_path = Path(directory) / "request.json"
        output_path = Path(directory) / "result.json"
        input_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        process = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "portfolio.discover_hsi_whitespace",
             str(input_path), "--output", str(output_path)],
            cwd=REPO, env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONPATH": str(REPO / "src")},
            capture_output=True, text=True,
        )
        if process.returncode:
            raise RuntimeError(f"Workflow CLI failed: {process.stderr}\n{process.stdout}")
        result = json.loads(output_path.read_text())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "jhtv-hsi-whitespace-six-opportunities-2026-10-18.json"
    md_path = OUT_DIR / "jhtv-hsi-whitespace-six-opportunities-2026-10-18.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    by_case = {row["case_id"]: row for row in technologies}
    lines = [
        "# HSI whitespace run: six banked JHTV opportunity pairs", "",
        f"**Run status:** {result['status']}",
        "**Scope:** 2,117 JHU technology records from the July 6, 2026 snapshot; six selected banked pairs OPP-019–OPP-024.",
        f"**Method:** local TF-IDF word/bigram vectors (512-feature cap) as a lexical proxy; {len(frameworks)} non-empty unique JHTV category paths as reference frameworks; HSI values from the October 18 full-catalog run.",
        "**Interpretation limit:** workflow/mechanics exercise, not a semantic embedding result. Category paths are not MindrianOS Brain baselines. Signals indicate only sparse regions within this supplied catalog relative to those paths; no outside research, market, novelty, or opportunity validation was performed.", "",
        f"Input counts: {result['input_counts']['artifacts']} artifacts, {result['input_counts']['baseline_frameworks']} category frameworks, {result['input_counts']['hsi_pairs']} HSI seed pairs; {result['input_counts']['zones']} zones produced.", "",
        "| Candidate | Seed assets | Signal | Nearest category framework | Room density / reference density |",
        "|---|---|---|---|---|",
    ]
    for zone in result["zones"]:
        left_id, right_id = zone["seed_pair"]["left_id"], zone["seed_pair"]["right_id"]
        left, right = by_case[left_id].get("title", left_id), by_case[right_id].get("title", right_id)
        candidate = next((row["candidate_id"] for row in seeds
                          if {row["left_id"], row["right_id"]} == {left_id, right_id}), "")
        nearest = zone["nearest_baseline_frameworks"][0]["label"] if zone["nearest_baseline_frameworks"] else "—"
        lines.append(
            f"| {candidate} | {left} ↔ {right} | {zone['gap_signal']} | {nearest} | "
            f"{zone['room_density_excluding_seeds']:.3f} / {zone['baseline_density']:.3f} |"
        )
    lines += [
        "", "## Reading the result", "",
        "All six seed pairs completed and returned source-linked pair/framework leads. Output depends strongly on the lexical proxy and category labels. Treat nearest frameworks as questions for Theo to investigate, not discovered missing mechanisms.", "",
        "## Next validation step", "",
        "Repeat with one declared local dense embedding model and a genuine, versioned MindrianOS reference-framework bundle. Compare rankings and nearest frameworks. Send persistent leads to approved outside research and human review.", "",
        f"Full machine-readable output: `{json_path.name}`", "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "input_counts": result["input_counts"],
                      "framework_count": len(frameworks), "report": str(md_path), "result": str(json_path)}, indent=2))


if __name__ == "__main__":
    main()
