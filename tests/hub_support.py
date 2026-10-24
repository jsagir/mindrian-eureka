"""Build synthetic run folders for the hub tests. No model is needed.

The folders are written with the Phase 2 writers (`corpus_lines`, `canonical_json`,
`render_ranked_markdown`, `StagedRun`, `build_manifest` and the two projectors), so each
one passes `is_eureka_run_folder` and every output hash in its manifest is correct.
The builder is deterministic: the same arguments give the same bytes.
The Potential eureka helper is a synthetic test fixture, not a finding.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mindrian_eureka.run.contracts import Record, sha256_text
from mindrian_eureka.run.manifest import build_manifest, build_run_info
from mindrian_eureka.run.output import (
    OUTPUT_CORPUS,
    OUTPUT_MANIFEST,
    OUTPUT_MARKDOWN,
    OUTPUT_RUN_INFO,
    OUTPUT_UNUSUAL,
    OUTPUT_WORDING,
    FileDigest,
    StagedRun,
    canonical_json,
    corpus_lines,
    render_ranked_markdown,
)
from mindrian_eureka.run.project import project_unusual_pairs, project_wording_and_meaning

THEMES: tuple[tuple[str, ...], ...] = (
    ("river", "flood", "dam", "channel", "delta", "silt"),
    ("grain", "harvest", "soil", "seed", "field", "yield"),
    ("signal", "antenna", "relay", "band", "noise", "gain"),
    ("tooth", "enamel", "gum", "crown", "root", "plaque"),
)
HOSTILE_SCRIPT = "<script>window.__pwned=1</script>"
HOSTILE_IMAGE = '<img src=x onerror="window.__pwned=1">'
LONG_TEXT_CHARS = 5000


def tree_hash(folder: Path) -> str:
    """Return a sha256 over the relative names and the bytes of every path in `folder`."""
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        digest.update(str(path.relative_to(folder)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


# --- Records ----------------------------------------------------------------


def _group(index: int, n_records: int, clusters: int) -> int:
    return min(clusters - 1, index * clusters // max(1, n_records))


def _base_text(index: int, group: int, seed_text: str) -> str:
    theme = THEMES[group % len(THEMES)]
    words = [theme[(index + step) % len(theme)] for step in range(5)]
    return f"{seed_text} Notes {index} on {' '.join(words)} in group {group}."


def _title(index: int, group: int) -> str:
    theme = THEMES[group % len(THEMES)]
    return f"{theme[index % len(theme)].title()} study {index}"


def _make_records(
    n_records: int,
    clusters: int,
    seed_text: str,
    copies: int,
    empty_text: int,
    hostile: bool,
    long_text: int,
) -> list[Record]:
    groups = [_group(i, n_records, clusters) for i in range(n_records)]
    ids = [f"doc{i:03d}" for i in range(n_records)]
    titles = [_title(i, groups[i]) for i in range(n_records)]
    texts = [_base_text(i, groups[i], seed_text) for i in range(n_records)]
    files = [f"{ids[i]}.md" for i in range(n_records)]
    for j in range(min(long_text, n_records)):
        index = (n_records // 2 + j) % n_records
        grown = texts[index] + " " + "long words repeat. " * 300
        texts[index] = grown[:LONG_TEXT_CHARS].strip()
    for j in range(min(copies, n_records - 1)):
        texts[1 + j] = texts[0]
    for j in range(min(empty_text, n_records)):
        texts[n_records - 1 - j] = ""
    if hostile:
        _make_hostile(ids, titles, texts, files)
    return [
        Record(
            id=ids[i],
            title=titles[i],
            text=texts[i],
            source_ref=f"{files[i]}#{i}",
            source_file=files[i],
            text_sha256=sha256_text(texts[i]),
        )
        for i in range(n_records)
    ]


def _make_hostile(ids: list[str], titles: list[str], texts: list[str], files: list[str]) -> None:
    """Put hostile text and ids into the first records. The lists change in place."""
    count = len(ids)
    if count > 0:
        ids[0] = "bank"
        files[0] = "bank.md"
    if count > 1:
        ids[1] = "hub-results"
        files[1] = "hub-results.md"
    if count > 2:
        ids[2] = "__proto__"
        files[2] = "proto.md"
    if count > 3:
        titles[3] = f'{HOSTILE_SCRIPT} "quoted" & <b>bold</b>'
        texts[3] = f'{HOSTILE_IMAGE} {HOSTILE_SCRIPT} it\'s "quoted" </script> {{}} & \\ end'
    if count > 4:
        texts[4] = "before </script><script>window.__pwned=1</script> after" + chr(0x2028) + "x"
    if count > 5:
        files[5] = "javascript:window.__pwned=1.md"
    if count > 6:
        titles[6] = "pipe | and back\\slash"


# --- Pairs ------------------------------------------------------------------


def _unit(salt: str, a: int, b: int, part: str) -> float:
    digest = hashlib.sha256(f"{salt}:{a}:{b}:{part}".encode()).digest()
    return int.from_bytes(digest[:6], "big") / float(1 << 48)


def _pick_pairs(groups: Sequence[int], count: int, salt: str) -> list[tuple[int, int]]:
    """Choose `count` distinct index pairs, mostly inside a group, a few across groups.

    The first quarter of the list comes from one shared stream, so the two engines
    overlap. The rest comes from a stream of the engine.
    """
    n = len(groups)
    target = min(count, n * (n - 1) // 2)
    shared = random.Random("shared")
    own = random.Random(salt)
    has_cross = len(set(groups)) > 1
    chosen: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for position in range(target):
        rng = shared if position < target // 4 else own
        want_cross = has_cross and position % 8 == 2
        pair: tuple[int, int] | None = None
        for attempt in range(80):
            a, b = sorted((rng.randrange(n), rng.randrange(n)))
            if a == b or (a, b) in seen:
                continue
            if attempt < 60 and (groups[a] != groups[b]) != want_cross:
                continue
            pair = (a, b)
            break
        if pair is None:
            pair = next((a, b) for a in range(n) for b in range(a + 1, n) if (a, b) not in seen)
        seen.add(pair)
        chosen.append(pair)
    return chosen


def _scores(salt: str, a: int, b: int, rank: int, count: int) -> tuple[float, float, float]:
    """Return wording, meaning and rank score. The rank score falls with the rank."""
    wording = 0.05 + 0.6 * _unit(salt, a, b, "w")
    meaning = min(0.98, max(0.02, wording + (_unit(salt, a, b, "m") - 0.5) * 0.7))
    gap = 0.8 / (count + 1)
    rank_score = 0.9 - (rank - 1) * gap + _unit(salt, a, b, "r") * gap * 0.25
    return wording, meaning, rank_score


def _unusual_result(
    pairs: list[tuple[int, int]], records: Sequence[Record], count: int
) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    for rank, (a, b) in enumerate(pairs, start=1):
        wording, meaning, rank_score = _scores("unusual", a, b, rank, count)
        outputs.append(
            {
                "rank": rank,
                "payload": {
                    "left": {"artifact_id": records[a].id},
                    "right": {"artifact_id": records[b].id},
                    "structural_similarity": wording,
                    "semantic_similarity": meaning,
                    "signed_difference": meaning - wording,
                    "disagreement": rank_score,
                    "method_signals": {"signal_a": _unit("unusual", a, b, "s")},
                },
            }
        )
    return {"outputs": outputs, "warnings": []}


def _wording_pairs(
    pairs: list[tuple[int, int]],
    records: Sequence[Record],
    count: int,
    floor: float,
    below: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, (a, b) in enumerate(pairs, start=1):
        wording, meaning, rank_score = _scores("wording", a, b, rank, count)
        percentile = floor + (1.0 - floor) * (1.0 - (rank - 1) / (count + 1))
        if rank > len(pairs) - below:
            percentile = floor * 0.5
        rows.append(
            {
                "rank": rank,
                "left_id": records[a].id,
                "right_id": records[b].id,
                "lsa_sim": wording,
                "semantic_sim": meaning,
                "hsi_score": rank_score,
                "hsi_percentile": percentile,
            }
        )
    return rows


# --- Run folder -------------------------------------------------------------


def make_run_folder(
    base: Path,
    *,
    name: str = "run",
    n_records: int = 30,
    pairs_per_engine: int | tuple[int, int] = 40,
    seed_text: str = "Synthetic record for the hub tests.",
    unusual_floor: float = 0.9,
    wording_floor: float = 0.0,
    clusters: int = 3,
    copies: int = 0,
    empty_text: int = 0,
    hostile: bool = False,
    zero_pairs: bool = False,
    percentile_below_floor: int = 0,
    notes: Sequence[str] | None = None,
    long_text: int = 0,
    with_run_info: bool = True,
    dropped: Sequence[dict[str, Any]] | None = None,
    caps_hit: Sequence[dict[str, Any]] | None = None,
) -> Path:
    """Write a valid Eureka run folder with synthetic data and return its path.

    Args:
        base: The folder that will hold the run folder.
        name: The name of the run folder.
        n_records: The number of records.
        pairs_per_engine: The number of pairs for both engines, or one number for each
            engine as (unusual pairs, wording pairs). Fewer pairs are written when the
            records cannot form that many.
        seed_text: A sentence at the start of every record text.
        unusual_floor: The `min_percentile` setting of the unusual-pairs engine.
        wording_floor: The `min_percentile` setting of the wording engine. It must be
            above 0 when `percentile_below_floor` is above 0.
        clusters: The number of record groups. Most pairs join two records of one group.
        copies: The number of records that copy the text of the first record.
        empty_text: The number of records at the end with an empty text.
        hostile: Put HTML, script text, quotes and odd ids and file names into some records.
        zero_pairs: Write empty pair lists for both engines.
        percentile_below_floor: The number of wording pairs at the end of the list that get
            a percentile below the wording floor.
        notes: The notes of both pair files. The default is one plain sentence.
        long_text: The number of records with a text of about 5,000 characters.
        with_run_info: Write `run-info.json`.
        dropped: The dropped records for the corpus section of the manifest.
        caps_hit: The limits that were reached, for the corpus section of the manifest.

    Returns:
        The path of the run folder.

    Raises:
        ValueError: `percentile_below_floor` is above 0 and `wording_floor` is 0 or less.
    """
    if percentile_below_floor > 0 and wording_floor <= 0:
        raise ValueError("set wording_floor above 0 to get pairs below the floor")
    if isinstance(pairs_per_engine, int):
        unusual_count = wording_count = pairs_per_engine
    else:
        unusual_count, wording_count = pairs_per_engine
    if zero_pairs:
        unusual_count = wording_count = 0
    plain_notes = list(notes) if notes is not None else ["A plain engine note."]
    records = _make_records(
        n_records, max(1, clusters), seed_text, copies, empty_text, hostile, long_text
    )
    groups = [_group(i, n_records, max(1, clusters)) for i in range(n_records)]

    unusual_pairs = _pick_pairs(groups, unusual_count, "unusual")
    wording_pairs = _pick_pairs(groups, wording_count, "wording")
    top_k_unusual = max(50, len(unusual_pairs))
    top_k_wording = max(50, len(wording_pairs))
    unusual_settings = {"min_percentile": unusual_floor, "scoring": "synthetic"}
    wording_settings = {"min_percentile": wording_floor, "seed": 7}

    unusual_doc = project_unusual_pairs(
        _unusual_result(unusual_pairs, records, len(unusual_pairs)),
        records,
        settings=unusual_settings,
        top_k=top_k_unusual,
        notes=plain_notes,
    )
    wording_doc = project_wording_and_meaning(
        _wording_pairs(
            wording_pairs, records, len(wording_pairs), wording_floor, percentile_below_floor
        ),
        records,
        settings=wording_settings,
        top_k=top_k_wording,
        notes=plain_notes,
    )

    out_dir = base / name
    with StagedRun(out_dir) as staged:
        corpus_digest = staged.write(OUTPUT_CORPUS, corpus_lines(records))
        unusual_digest = staged.write(OUTPUT_UNUSUAL, canonical_json(unusual_doc))
        wording_digest = staged.write(OUTPUT_WORDING, canonical_json(wording_doc))
        markdown = render_ranked_markdown(unusual_doc, wording_doc)
        markdown_digest = staged.write(OUTPUT_MARKDOWN, markdown.encode("utf-8"))
        outputs = [
            corpus_digest.as_dict(),
            _manifest_output(unusual_digest, unusual_doc),
            _manifest_output(wording_digest, wording_doc),
            markdown_digest.as_dict(),
        ]
        manifest = build_manifest(
            engines={
                "unusual_pairs": {"capability_id": "synthetic", "tie_break": "id"},
                "wording_and_meaning": {
                    "capability_id": "synthetic",
                    "reference": "hsi_reference.py",
                },
            },
            inputs={"files": []},
            corpus={
                "records_read": n_records + len(dropped or []),
                "records_used": n_records,
                "dropped": [dict(item) for item in dropped or []],
                "corpus_digest": sha256_text("synthetic"),
                "caps_hit": [dict(item) for item in caps_hit or []],
            },
            settings={
                "unusual_pairs": unusual_settings,
                "wording_and_meaning": wording_settings,
                "run": {"top_k": top_k_unusual, "max_artifacts": 5000, "objective": "synthetic"},
            },
            seeds={"unusual_pairs_svd_random_state": 7, "wording_and_meaning_lsa_seed": 7},
            model={"name": "synthetic", "snapshot": None, "files": {}},
            environment={"python": "synthetic"},
            outputs=outputs,
            engine_notes=sorted(set(plain_notes)),
        )
        manifest_digest = staged.write(OUTPUT_MANIFEST, canonical_json(manifest))
        if with_run_info:
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


def _manifest_output(digest: FileDigest, doc: dict[str, Any]) -> dict[str, Any]:
    item = digest.as_dict()
    item["pairs"] = doc["counts"]["pairs"]
    item["top_k_reached"] = doc["counts"]["top_k_reached"]
    return item


def build_run_folder_with_potential_eureka(
    base: Path, *, name: str = "synthetic-potential-eureka"
) -> Path:
    """Write a synthetic test fixture, not a finding, with visible bridge records.

    Two controlled dense groups and a connecting record exercise the unchanged
    Plan 05 rule. Scores come from the existing hashing encoder stub and a fixed
    synthetic gap, not a real research finding. No model or network is used.
    All serialized paths are relative, and no clock or random state is read.

    Args:
        base: Temporary test directory receiving the synthetic run folder.
        name: Run folder name; it never enters serialized data.

    Returns:
        A valid run folder for model and browser tests. It is never package data
        or part of the public example.
    """
    from itertools import combinations

    from hashing_stub import HashingEncoder

    marker = "synthetic test fixture, not a finding"
    topics = {"a": "alpha-synthetic-reservoir", "b": "beta-synthetic-antenna"}
    records: list[Record] = []
    groups: dict[str, list[int]] = {"a": [], "b": []}
    for group in ("a", "b"):
        for index in range(10):
            record_id = f"synthetic-{group}-{index:03d}"
            text = f"{marker}. " + (topics[group] + " ") * 64 + record_id
            groups[group].append(len(records))
            records.append(
                Record(
                    id=record_id,
                    title=f"Synthetic test fixture {group.upper()} {index:03d}, not a finding",
                    text=text,
                    source_ref=record_id + ".md",
                    source_file=record_id + ".md",
                    text_sha256=sha256_text(text),
                )
            )
    connector_id = "synthetic-z-connector"
    connector_text = f"{marker}. " + ((topics["a"] + " " + topics["b"] + " ") * 64) + connector_id
    connector = len(records)
    records.append(
        Record(
            id=connector_id,
            title="Synthetic test fixture connector, not a finding",
            text=connector_text,
            source_ref=connector_id + ".md",
            source_file=connector_id + ".md",
            text_sha256=sha256_text(connector_text),
        )
    )
    vectors = HashingEncoder(marker, allow_download=False).encode(
        [record.model_text for record in records]
    )
    edges = [edge for group in ("a", "b") for edge in combinations(groups[group], 2)]
    edges.extend((anchor[0], connector) for anchor in (groups["a"], groups["b"]))
    scored = []
    for left, right in edges:
        meaning = max(0.0, min(1.0, float(vectors[left] @ vectors[right])))
        wording = meaning * 0.5
        scored.append((meaning - wording, left, right, wording, meaning))
    scored.sort(key=lambda row: (-row[0], records[row[1]].id, records[row[2]].id))
    unusual_rows: list[dict[str, Any]] = []
    wording_rows: list[dict[str, Any]] = []
    for rank, (score, left, right, wording, meaning) in enumerate(scored, start=1):
        unusual_rows.append(
            {
                "rank": rank,
                "payload": {
                    "left": {"artifact_id": records[left].id},
                    "right": {"artifact_id": records[right].id},
                    "structural_similarity": wording,
                    "semantic_similarity": meaning,
                    "signed_difference": score,
                    "disagreement": score,
                    "method_signals": {},
                },
            }
        )
        wording_rows.append(
            {
                "rank": rank,
                "left_id": records[left].id,
                "right_id": records[right].id,
                "lsa_sim": wording,
                "semantic_sim": meaning,
                "hsi_score": score,
                "hsi_percentile": (len(scored) - rank + 1) / (len(scored) + 1),
            }
        )
    unusual_settings = {"min_percentile": 0.9, "scoring": "synthetic-controlled-gap"}
    wording_settings = {"min_percentile": 0.0, "seed": 7}
    top_k = len(scored)
    unusual = project_unusual_pairs(
        {"outputs": unusual_rows, "warnings": []},
        records,
        settings=unusual_settings,
        top_k=top_k,
        notes=[marker],
    )
    wording_doc = project_wording_and_meaning(
        wording_rows,
        records,
        settings=wording_settings,
        top_k=top_k,
        notes=[marker],
    )
    out = base / name
    with StagedRun(out) as staged:
        corpus_digest = staged.write(OUTPUT_CORPUS, corpus_lines(records))
        unusual_digest = staged.write(OUTPUT_UNUSUAL, canonical_json(unusual))
        wording_digest = staged.write(OUTPUT_WORDING, canonical_json(wording_doc))
        markdown_digest = staged.write(
            OUTPUT_MARKDOWN,
            render_ranked_markdown(unusual, wording_doc).encode(),
        )
        manifest = build_manifest(
            engines={
                "unusual_pairs": {"capability_id": "synthetic", "tie_break": "id"},
                "wording_and_meaning": {"capability_id": "synthetic"},
            },
            inputs={"files": []},
            corpus={
                "records_read": len(records),
                "records_used": len(records),
                "dropped": [],
                "caps_hit": [],
                "corpus_digest": sha256_text(
                    "\n".join(r.id + ":" + r.text_sha256 for r in records)
                ),
            },
            settings={
                "unusual_pairs": unusual_settings,
                "wording_and_meaning": wording_settings,
                "run": {"top_k": top_k, "max_artifacts": 5000, "objective": marker},
            },
            seeds={"unusual_pairs_svd_random_state": 7, "wording_and_meaning_lsa_seed": 7},
            model={"name": marker + " (HashingEncoder)", "snapshot": None, "files": {}},
            environment={"python": "synthetic"},
            outputs=[
                corpus_digest.as_dict(),
                _manifest_output(unusual_digest, unusual),
                _manifest_output(wording_digest, wording_doc),
                markdown_digest.as_dict(),
            ],
            engine_notes=[marker],
        )
        staged.write(OUTPUT_MANIFEST, canonical_json(manifest))
        staged.publish()
    return out
