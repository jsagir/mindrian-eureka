"""Build, check and write a room seed (Phase 2.3).

`build_pair_seed` turns one pair of a verified run into the seed document and its evidence
files. `validate_seed` checks the document against the closed schema before anything is
written. `write_seed` publishes one folder with `seed.json` and the evidence files. The
run folder is read only and Eureka writes nothing outside the output folder. The folder is
not a room: it holds no ROOM.md, STATE.md, registry entry or room.db.

Import rule: the standard library, `jsonschema`, `..run.*`, `..hub.contracts` and the
other seed modules. No numpy, no network, no process.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ..hub.contracts import ENGINE_KEYS, RunPair
from ..run.contracts import LABEL, SUMMARY_LINE, Record, RunError, UsageError, sha256_bytes
from ..run.manifest import tool_version
from ..run.output import FileDigest, StagedRun, canonical_json, ensure_out_dir_allowed
from .contracts import (
    DEFAULT_SEED_OUT_PREFIX,
    EVIDENCE_DIR,
    MODEL_BOUNDARY,
    OUTPUT_SEED,
    REVIEW_STATUS_PROPOSED,
    ROLE_NEIGHBOUR,
    ROLE_PAIR_MEMBER,
    ROLE_SPINE,
    SCORE_NOTE,
    SEED_KIND_CLUSTER,
    SEED_KIND_PAIR,
    SEED_SCHEMA,
    SEED_SUMMARY_SCHEMA,
)
from .evidence import evidence_slug, render_evidence
from .graph import PairGraph
from .sections import merge_lists, order_sections, section_lists
from .source import SeedSource, combine_maps, find_pair, room_map_for
from .statement import build_statement

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemas" / "room-seed.v1.json"
_KIND = "Eureka seed"
_NOT_A_ROOM = (
    "This folder is not a room. MindrianOS opens it through its own birth gate; "
    "see docs/room-seed-contract.md."
)


@dataclass(frozen=True)
class EvidenceFile:
    """One evidence file of a seed.

    Attributes:
        path: The path inside the seed folder, with "/" separators.
        data: The bytes of the file.
        sha256: The sha256 of the bytes.
    """

    path: str
    data: bytes
    sha256: str


@dataclass(frozen=True)
class Seed:
    """A seed that is built and checked, but not yet written.

    Attributes:
        kind: `pair` or `cluster`.
        document: The `seed.json` document.
        evidence: The evidence files, sorted by path.
        default_out_name: The default name of the output folder.
    """

    kind: str
    document: dict[str, Any]
    evidence: tuple[EvidenceFile, ...]
    default_out_name: str


# --- Schema check -----------------------------------------------------------


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_seed(document: Mapping[str, Any]) -> None:
    """Check a seed document against the closed schema.

    Raises:
        RunError: The document breaks the schema, or a label is not the standard label.
            The message names the place and the rule, never a value.
    """
    problems = sorted(_validator().iter_errors(document), key=lambda item: item.json_path)
    if problems:
        first = problems[0]
        raise RunError(
            f"The seed failed its own schema check ({len(problems)} problem(s)): "
            f"{first.json_path} breaks the rule {first.validator}",
            fix="Report this to the Eureka maintainer; nothing was written.",
        )
    labels = [document.get("label")]
    labels += [entry["statement"]["label"] for entry in document.get("bank_entries", [])]
    if any(label != LABEL for label in labels):
        raise RunError(
            "The seed failed its own schema check (1 problem(s)): a label is not the standard "
            "label",
            fix="Report this to the Eureka maintainer; nothing was written.",
        )


def is_seed_folder(path: Path) -> bool:
    """Return True when `path/seed.json` is a Eureka seed document."""
    try:
        data = json.loads((path / OUTPUT_SEED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("schema_version") == SEED_SCHEMA


# --- Pieces of the document -------------------------------------------------


def _one_class(entries: Sequence[RunPair]) -> str | None:
    classes = {entry.pair_class for entry in entries}
    if len(classes) > 1:
        raise RunError(
            "The two engines of the run give different classes to one pair",
            fix="Run eureka run again to rebuild the run folder.",
        )
    return classes.pop() if classes else None


def _record_entry(record: Record, role: str, evidence: EvidenceFile) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "record_id": record.id,
        "title": record.title,
        "role": role,
        "evidence_file": evidence.path,
        "evidence_sha256": evidence.sha256,
    }
    if record.outcome_class is not None:
        entry["outcome_class"] = record.outcome_class
    carried = {key: value for key, value in record.extras.items() if value}
    if carried:
        entry["carried"] = carried
    if record.text_source is not None:
        entry["text_source"] = record.text_source
    return entry


def _evidence_file(record: Record, role: str) -> EvidenceFile:
    data = render_evidence(record, role)
    return EvidenceFile(
        path=f"{EVIDENCE_DIR}/{evidence_slug(record.id)}.md", data=data, sha256=sha256_bytes(data)
    )


def _pair_entry(entries: Sequence[RunPair]) -> dict[str, Any]:
    first = entries[0]
    left, right = sorted((first.left_id, first.right_id))
    engines: list[dict[str, Any]] = []
    for key in ENGINE_KEYS:
        for entry in entries:
            if entry.engine != key:
                continue
            item: dict[str, Any] = {
                "engine": entry.engine,
                "rank": entry.rank,
                "wording_similarity": entry.wording,
                "meaning_similarity": entry.meaning,
                "rank_score": entry.rank_score,
                "reading": entry.reading,
            }
            if entry.percentile is not None:
                item["percentile"] = entry.percentile
            engines.append(item)
    pair: dict[str, Any] = {
        "pair_id": first.pair_id,
        "left_id": left,
        "right_id": right,
        "engines": engines,
    }
    pair_class = _one_class(entries)
    if pair_class is not None:
        pair["pair_class"] = pair_class
    return pair


def _bank_entry(
    source: SeedSource, entries: Sequence[RunPair], neighbour_id: str | None = None
) -> dict[str, Any]:
    pair = _pair_entry(entries)
    left = source.records_by_id[pair["left_id"]]
    right = source.records_by_id[pair["right_id"]]
    readings: list[str] = []
    for key in ENGINE_KEYS:
        for entry in entries:
            if entry.engine == key and entry.reading not in readings:
                readings.append(entry.reading)
    # In a cluster seed the spine comes first in the statement; a pair seed keeps id order.
    first, second = (right, left) if neighbour_id == left.id else (left, right)
    bank: dict[str, Any] = {
        "entry_id": pair["pair_id"],
        "pair_id": pair["pair_id"],
        "left_id": pair["left_id"],
        "right_id": pair["right_id"],
        "review_status": REVIEW_STATUS_PROPOSED,
        "statement": build_statement(
            (first.id, first.title), (second.id, second.title), pair.get("pair_class"), readings
        ),
    }
    if neighbour_id is not None:
        bank["neighbour_id"] = neighbour_id
    if "pair_class" in pair:
        bank["pair_class"] = pair["pair_class"]
    return bank


def assemble_seed(
    source: SeedSource,
    *,
    kind: str,
    selection: dict[str, Any],
    members: Sequence[tuple[Record, str]],
    pair_groups: Sequence[Sequence[RunPair]],
    bank_entries: Sequence[dict[str, Any]],
    default_out_name: str,
    list_records: Sequence[Record] | None = None,
) -> Seed:
    """Build the seed document and its evidence files, and check the document.

    Args:
        source: The verified run.
        kind: `pair` or `cluster`.
        selection: The `selection` object.
        members: The records of the seed with their roles, in output order.
        pair_groups: The run entries of each pair of the seed.
        bank_entries: The bank entries, sorted by pair id.
        default_out_name: The default name of the output folder.
        list_records: The records that fill `known` and `feed_next`. The default is every
            member. A cluster seed gives the spine record only.

    Returns:
        The checked seed.

    Raises:
        RunError: A cell state is missing, or the document breaks the schema.
    """
    files = {record.id: _evidence_file(record, role) for record, role in members}
    listed = [record for record, _ in members] if list_records is None else list(list_records)
    maps = [room_map_for(source, record) for record in listed]
    per_record = [
        section_lists(record, room_map) for record, room_map in zip(listed, maps, strict=True)
    ]
    combined = combine_maps(maps)
    known, feed_next = merge_lists(per_record, combined.section_names)
    document: dict[str, Any] = {
        "schema_version": SEED_SCHEMA,
        "label": LABEL,
        "seed_kind": kind,
        "scope_id": "eureka-run-" + source.run.manifest_sha256[:16],
        "snapshot_id": source.run.corpus_sha256,
        "manifest_sha256": source.run.manifest_sha256,
        "engine_versions": dict(source.run.tool),
        "seed_writer": {"name": "mindrian-eureka", "version": tool_version()},
        "selection": selection,
        "records": [_record_entry(record, role, files[record.id]) for record, role in members],
        "source_refs": [
            {
                "record_id": record.id,
                "source_ref": record.source_ref,
                "source_file": record.source_file,
                "text_sha256": record.text_sha256,
            }
            for record, _ in members
        ],
        "pairs": sorted((_pair_entry(group) for group in pair_groups), key=_pair_key),
        "bank_entries": list(bank_entries),
        "known": known,
        "feed_next": feed_next,
        "suggested_sections": order_sections(known, feed_next, combined),
        "score_note": SCORE_NOTE,
        "model_boundary": MODEL_BOUNDARY,
    }
    validate_seed(document)
    return Seed(
        kind=kind,
        document=document,
        evidence=tuple(sorted(files.values(), key=lambda item: item.path)),
        default_out_name=default_out_name,
    )


def _pair_key(pair: Mapping[str, Any]) -> str:
    return str(pair["pair_id"])


def build_pair_seed(source: SeedSource, pair_id: str) -> Seed:
    """Build the seed of one pair.

    Args:
        source: The verified run.
        pair_id: The id of a pair of the run.

    Returns:
        The checked seed. The same run and the same pair give the same bytes.

    Raises:
        UsageError: The run has no pair with that id.
        RunError: A cell state is missing, or the document breaks the schema.
    """
    entries = find_pair(source, pair_id)
    first = entries[0]
    ids = sorted((first.left_id, first.right_id))
    members = [(source.records_by_id[record_id], ROLE_PAIR_MEMBER) for record_id in ids]
    return assemble_seed(
        source,
        kind=SEED_KIND_PAIR,
        selection={"pair_ids": [pair_id]},
        members=members,
        pair_groups=[entries],
        bank_entries=[_bank_entry(source, entries)],
        default_out_name=f"{DEFAULT_SEED_OUT_PREFIX}-{pair_id}",
    )


def build_cluster_seed(
    source: SeedSource, graph: PairGraph, record_id: str, *, min_degree: int
) -> Seed:
    """Build the seed of the cluster around one record.

    The spine record fills `known` and `feed_next`. Each paired neighbour becomes one bank
    entry with its own statement draft. Every record gets an evidence file.

    Args:
        source: The verified run.
        graph: The pair graph of the run.
        record_id: The id of the spine record.
        min_degree: The least number of pairs the spine record must sit in.

    Returns:
        The checked seed. The same run and the same record give the same bytes.

    Raises:
        UsageError: The run has no such record, or the record sits in too few pairs.
        RunError: A cell state is missing, or the document breaks the schema.
    """
    spine = source.records_by_id.get(record_id)
    if spine is None:
        raise UsageError(
            "This run has no record with that id",
            fix="Check the record id in corpus/records.jsonl.",
        )
    degree = graph.degree(record_id)
    if degree < min_degree:
        raise UsageError(
            f"The record is in {degree} pair(s). A cluster seed needs at least {min_degree}.",
            fix="Lower the minimum with --min-degree, or start from one pair with --pair.",
        )
    neighbours = graph.neighbours(record_id)
    members: list[tuple[Record, str]] = [(spine, ROLE_SPINE)]
    seen = {record_id}
    for neighbour_id, _ in neighbours:
        if neighbour_id not in seen:
            seen.add(neighbour_id)
            members.append((source.records_by_id[neighbour_id], ROLE_NEIGHBOUR))
    groups = [graph.nodes[pair_id].runs for _, pair_id in neighbours]
    bank = [
        _bank_entry(source, graph.nodes[pair_id].runs, neighbour_id)
        for neighbour_id, pair_id in neighbours
    ]
    bank.sort(key=lambda entry: str(entry["pair_id"]))
    digest = hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:12]
    return assemble_seed(
        source,
        kind=SEED_KIND_CLUSTER,
        selection={
            "spine_record_id": record_id,
            "degree": degree,
            "min_degree": min_degree,
            "pair_ids": sorted(pair_id for _, pair_id in neighbours),
        },
        members=members,
        pair_groups=groups,
        bank_entries=bank,
        default_out_name=f"{DEFAULT_SEED_OUT_PREFIX}-cluster-{digest}",
        list_records=[spine],
    )


# --- Writing ----------------------------------------------------------------


@dataclass(frozen=True)
class SeedSummary:
    """The result of a seed write. The output folder shows only in terminal text.

    Attributes:
        out_dir: The output folder.
        kind: `pair` or `cluster`.
        seed_sha256: The sha256 of `seed.json`.
        files: The digests of every written file, sorted by path.
        records: The number of records.
        evidence_files: The number of evidence files.
        bank_entries: The number of bank entries.
        known_count: The number of `known` entries.
        feed_next_count: The number of `feed_next` entries.
        sections: The suggested sections, in order.
    """

    out_dir: Path
    kind: str
    seed_sha256: str
    files: tuple[FileDigest, ...]
    records: int
    evidence_files: int
    bank_entries: int
    known_count: int
    feed_next_count: int
    sections: tuple[str, ...]

    def lines(self) -> str:
        """Return the human summary. The shared status is the last line."""
        return "\n".join(
            (
                "Eureka seed written.",
                f"Seed folder: {self.out_dir}",
                f"Seed file: {OUTPUT_SEED} (sha256 {self.seed_sha256})",
                f"Kind: {self.kind}. Records: {self.records}. "
                f"Evidence files: {self.evidence_files}. Bank entries: {self.bank_entries}.",
                f"Known: {self.known_count} entries. Feed next: {self.feed_next_count} entries. "
                f"Sections: {', '.join(self.sections)}.",
                _NOT_A_ROOM,
                SUMMARY_LINE,
            )
        )

    def to_json_dict(self) -> dict[str, Any]:
        """Return the summary facts with the label and without a machine path."""
        return {
            "schema_version": SEED_SUMMARY_SCHEMA,
            "label": LABEL,
            "seed_kind": self.kind,
            "seed_sha256": self.seed_sha256,
            "files": [item.as_dict() for item in self.files],
            "counts": {
                "records": self.records,
                "evidence_files": self.evidence_files,
                "bank_entries": self.bank_entries,
                "known": self.known_count,
                "feed_next": self.feed_next_count,
            },
            "sections": list(self.sections),
            "summary_line": SUMMARY_LINE,
        }


def write_seed(seed: Seed, run_dir: Path, out_dir: Path) -> SeedSummary:
    """Write the seed folder in one step.

    Args:
        seed: The checked seed.
        run_dir: The run folder. It is only used to refuse an overlapping output folder.
        out_dir: The output folder. An earlier Eureka seed there is replaced.

    Returns:
        The summary of the write.

    Raises:
        UsageError: The output folder overlaps the run folder, or is a foreign folder.
    """
    ensure_out_dir_allowed(run_dir, out_dir, replaceable=is_seed_folder, kind=_KIND)
    document = seed.document
    with StagedRun(out_dir, replaceable=is_seed_folder, kind=_KIND) as staged:
        digests = [staged.write(item.path, item.data) for item in seed.evidence]
        seed_digest = staged.write(OUTPUT_SEED, canonical_json(document))
        staged.publish()
    files = tuple(sorted([*digests, seed_digest], key=lambda item: item.path))
    return SeedSummary(
        out_dir=out_dir,
        kind=seed.kind,
        seed_sha256=seed_digest.sha256,
        files=files,
        records=len(document["records"]),
        evidence_files=len(digests),
        bank_entries=len(document["bank_entries"]),
        known_count=sum(len(items) for items in document["known"].values()),
        feed_next_count=sum(len(items) for items in document["feed_next"].values()),
        sections=tuple(document["suggested_sections"]),
    )
