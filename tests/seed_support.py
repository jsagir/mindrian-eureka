"""Build a synthetic seedable run folder for the seed tests. No model is needed.

The folder is written with the Phase 2 writers, as `hub_support.make_run_folder` does, and
it also holds the Phase 2.3 keys: the cell states of each record and the section map of
the manifest. The builder is deterministic. Every record, title and value is invented.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from hub_support import _manifest_output, _unusual_result, _wording_pairs
from mindrian_eureka.run.contracts import (
    CELL_BLANK,
    CELL_CARRIED,
    CELL_EXPORT_ONLY,
    CELL_TEXT,
    OUTCOME_LICENSED,
    OUTCOME_OPEN,
    Record,
    sha256_text,
)
from mindrian_eureka.run.manifest import build_manifest, build_run_info
from mindrian_eureka.run.output import (
    OUTPUT_CORPUS,
    OUTPUT_MANIFEST,
    OUTPUT_MARKDOWN,
    OUTPUT_RUN_INFO,
    OUTPUT_UNUSUAL,
    OUTPUT_WORDING,
    StagedRun,
    canonical_json,
    corpus_lines,
    render_ranked_markdown,
)
from mindrian_eureka.run.project import (
    _pair_id,
    attach_pair_classes,
    project_unusual_pairs,
    project_wording_and_meaning,
)

# The manifest form of the section map (RoomSections.as_data).
SECTION_MAP: dict[str, Any] = {
    "sections": [
        {"section": "problem-definition", "columns": ["problem_solved", "end_user"]},
        {
            "section": "legal-ip",
            "columns": ["status", "licenses", "first_license_or_option_date"],
        },
        {"section": "financial-model", "columns": ["funding_total"]},
        {"section": "team", "columns": ["lead_inventor"]},
    ],
    "not_in_export": [{"item": "patents", "section": "legal-ip", "source": "SynthDB"}],
}

DEFAULT_UNUSUAL: list[tuple[int, int]] = [(0, 1), (0, 2), (0, 3), (0, 4), (5, 6), (7, 8)]
DEFAULT_WORDING: list[tuple[int, int]] = [(0, 1), (0, 5), (2, 3), (8, 9), (1, 3)]

SOURCE_FILE = "recs.csv"


def record_id(index: int) -> str:
    """Return the id of synthetic record `index` (0 based)."""
    return f"recs/C{index + 1:05d}"


def pair_id_of(i: int, j: int) -> str:
    """Return the pair id of the synthetic records `i` and `j`."""
    return _pair_id(record_id(i), record_id(j))


def _cells(i: int, licensed: bool) -> dict[str, str]:
    return {
        "problem_solved": CELL_BLANK if i % 3 == 0 else CELL_TEXT,
        "end_user": CELL_TEXT if i % 2 == 0 else CELL_BLANK,
        "status": CELL_CARRIED,
        "licenses": CELL_CARRIED,
        "first_license_or_option_date": CELL_CARRIED if licensed else CELL_BLANK,
        "funding_total": CELL_EXPORT_ONLY if i % 4 == 0 else CELL_BLANK,
        "lead_inventor": CELL_BLANK if i % 5 == 0 else CELL_EXPORT_ONLY,
    }


def make_records(n_records: int, with_room_sections: bool, with_classes: bool) -> list[Record]:
    records: list[Record] = []
    for i in range(n_records):
        licensed = i % 2 == 0
        text = (
            f"Invented record {i + 1} about a synthetic device for sorting pebbles by weight "
            f"and by colour, written only to test the seed builder, number {i + 1}."
        )
        extras: dict[str, str] = {}
        if with_room_sections:
            extras = {
                "status": "Inactive- Licensed" if licensed else "Active",
                "licenses": "1" if licensed else "0",
                "first_license_or_option_date": "2019-03-01" if licensed else "",
            }
        records.append(
            Record(
                id=record_id(i),
                title="" if i % 4 == 3 else f"Synthetic title {i + 1}",
                text=text,
                source_ref=f"recs.csv#C{i + 1:05d}",
                source_file=SOURCE_FILE,
                text_sha256=sha256_text(text),
                outcome_class=(
                    (OUTCOME_LICENSED if licensed else OUTCOME_OPEN) if with_classes else None
                ),
                extras=extras,
                room_cells=_cells(i, licensed) if with_room_sections else {},
            )
        )
    return records


def make_seed_run(
    base: Path,
    *,
    name: str = "run",
    n_records: int = 10,
    unusual: Sequence[tuple[int, int]] | None = None,
    wording: Sequence[tuple[int, int]] | None = None,
    with_room_sections: bool = True,
    with_classes: bool = True,
    records: Sequence[Record] | None = None,
) -> Path:
    """Write a valid seedable run folder with synthetic data and return its path.

    Args:
        base: The folder that will hold the run folder.
        name: The name of the run folder.
        n_records: The number of records.
        unusual: The index pairs of the unusual-pairs engine, in rank order.
        wording: The index pairs of the wording engine, in rank order.
        with_room_sections: Write the cell states and the section map.
        with_classes: Give every record an outcome class, and every pair a pair class.
        records: Use these records instead of the generated ones (for example with a long
            text). The pairs and the cell table still follow the indexes.

    Returns:
        The path of the run folder.
    """
    unusual_pairs = list(DEFAULT_UNUSUAL if unusual is None else unusual)
    wording_pairs = list(DEFAULT_WORDING if wording is None else wording)
    run_records = (
        list(records)
        if records is not None
        else make_records(n_records, with_room_sections, with_classes)
    )
    unusual_settings = {"min_percentile": 0.9, "scoring": "synthetic"}
    wording_settings = {"min_percentile": 0.0, "seed": 7}
    notes = ["A plain engine note."]
    top_k_unusual = max(50, len(unusual_pairs))
    top_k_wording = max(50, len(wording_pairs))
    unusual_doc = project_unusual_pairs(
        _unusual_result(unusual_pairs, run_records, len(unusual_pairs)),
        run_records,
        settings=unusual_settings,
        top_k=top_k_unusual,
        notes=notes,
    )
    wording_doc = project_wording_and_meaning(
        _wording_pairs(wording_pairs, run_records, len(wording_pairs), 0.0, 0),
        run_records,
        settings=wording_settings,
        top_k=top_k_wording,
        notes=notes,
    )
    if with_classes:
        unusual_doc = attach_pair_classes(unusual_doc, run_records)
        wording_doc = attach_pair_classes(wording_doc, run_records)
    run_settings: dict[str, Any] = {
        "top_k": top_k_unusual,
        "max_artifacts": 5000,
        "objective": "synthetic",
    }
    if with_room_sections:
        run_settings["room_sections"] = {"*": SECTION_MAP}
    out_dir = base / name
    with StagedRun(out_dir) as staged:
        corpus_digest = staged.write(OUTPUT_CORPUS, corpus_lines(run_records))
        unusual_digest = staged.write(OUTPUT_UNUSUAL, canonical_json(unusual_doc))
        wording_digest = staged.write(OUTPUT_WORDING, canonical_json(wording_doc))
        markdown = render_ranked_markdown(unusual_doc, wording_doc)
        markdown_digest = staged.write(OUTPUT_MARKDOWN, markdown.encode("utf-8"))
        manifest = build_manifest(
            engines={
                "unusual_pairs": {
                    "capability_id": "synthetic.unusual",
                    "capability_version": "1.0.0",
                    "tie_break": "id",
                },
                "wording_and_meaning": {
                    "capability_id": "synthetic.wording",
                    "capability_version": "1.0.0",
                },
            },
            inputs={"files": []},
            corpus={
                "records_read": len(run_records),
                "records_used": len(run_records),
                "dropped": [],
                "corpus_digest": sha256_text("synthetic"),
                "caps_hit": [],
            },
            settings={
                "unusual_pairs": unusual_settings,
                "wording_and_meaning": wording_settings,
                "run": run_settings,
            },
            seeds={"unusual_pairs_svd_random_state": 7, "wording_and_meaning_lsa_seed": 7},
            model={"name": "synthetic", "snapshot": None, "files": {}},
            environment={"python": "synthetic"},
            outputs=[
                corpus_digest.as_dict(),
                _manifest_output(unusual_digest, unusual_doc),
                _manifest_output(wording_digest, wording_doc),
                markdown_digest.as_dict(),
            ],
            engine_notes=sorted(set(notes)),
        )
        manifest_digest = staged.write(OUTPUT_MANIFEST, canonical_json(manifest))
        info = build_run_info(
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:00:01Z",
            duration_ms=1000,
            argv=["eureka", "run", "synthetic"],
            manifest_sha256=manifest_digest.sha256,
        )
        staged.write(OUTPUT_RUN_INFO, canonical_json(info))
        staged.publish()
    return out_dir
