"""Project engine results into the fixed output shape of `eureka run`.

The engines return dictionaries that hold times, absolute paths, the model path and
source excerpts. This module copies only a fixed list of fields, so none of those
values reach a hashed output file. Every pair carries the label and a plain-English
reading that follows the numbers. The two engines use one direction label with
opposite meanings, so the reading never uses the label.

The functions take plain dictionaries. They load no numpy and call no engine.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    LABEL,
    PAIR_CLASS_CROSS,
    PAIR_CLASSES,
    PAIRS_SCHEMA,
    SCORE_MEANING,
    UNUSUAL_PAIRS_CAPABILITY,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_CAPABILITY,
    WORDING_AND_MEANING_NAME,
    Record,
)

READING_MEANING_HIGHER = "Similar meaning, different wording."
READING_WORDING_HIGHER = "Similar wording, different meaning."
READING_AGREE = "Wording and meaning agree on this pair."
EMPTY_RESULT_NOTE = "No candidate pairs were returned for this collection."

_MODEL_IDENTITY_PREFIX = "Model identity is recorded as the supplied local path"
_MAX_NAMED_IDS = 10


# --- Readings ---------------------------------------------------------------


def direction_for_unusual_pair(signed_difference: float) -> str:
    """Return the plain reading for a pair of the unusual-pairs engine.

    Args:
        signed_difference: The meaning score minus the wording score, on the common scale.

    Returns:
        A sentence that follows the sign of the number.
    """
    if signed_difference > 0:
        return READING_MEANING_HIGHER
    if signed_difference < 0:
        return READING_WORDING_HIGHER
    return READING_AGREE


def direction_for_wording_pair(wording: float, meaning: float) -> str:
    """Return the plain reading for a pair of the wording-and-meaning engine.

    Args:
        wording: The wording score of the pair.
        meaning: The meaning score of the pair.

    Returns:
        A sentence that follows the order of the two numbers.
    """
    if meaning > wording:
        return READING_MEANING_HIGHER
    if wording > meaning:
        return READING_WORDING_HIGHER
    return READING_AGREE


# --- Helpers ----------------------------------------------------------------


def _pair_id(left_id: str, right_id: str) -> str:
    first, second = sorted((left_id, right_id))
    digest = hashlib.sha256(f"{first}\0{second}".encode()).hexdigest()
    return f"pair-{digest[:20]}"


def _record_index(records: Sequence[Record]) -> dict[str, Record]:
    return {record.id: record for record in records}


def _side(index: Mapping[str, Record], record_id: str) -> dict[str, str]:
    record = index.get(record_id)
    if record is None:
        raise ValueError(f"Unknown record id in engine result: {record_id}")
    return {"id": record.id, "title": record.title, "source_ref": record.source_ref}


def _numeric_only(values: object) -> dict[str, float]:
    if not isinstance(values, Mapping):
        return {}
    kept: dict[str, float] = {}
    for key in sorted(values):
        value = values[key]
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            kept[str(key)] = float(value)
    return kept


def _scalar_copy(values: object) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        return {}
    kept: dict[str, Any] = {}
    for key in sorted(values):
        value = values[key]
        if isinstance(value, str | int | float | bool):
            kept[str(key)] = value
    return kept


def _file_shell(
    *,
    name: str,
    capability_id: str,
    meaning_key: str,
    settings: Mapping[str, Any],
    top_k: int,
    notes: Sequence[str],
    records_scored: int,
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    all_notes = list(notes)
    if not pairs:
        all_notes.append(EMPTY_RESULT_NOTE)
    return {
        "schema_version": PAIRS_SCHEMA,
        "label": LABEL,
        "engine": {"name": name, "capability_id": capability_id},
        "score_meaning": SCORE_MEANING[meaning_key],
        "notes": all_notes,
        "settings": dict(settings),
        "counts": {
            "records_scored": records_scored,
            "pairs": len(pairs),
            "top_k": top_k,
            "top_k_reached": top_k > 0 and len(pairs) >= top_k,
        },
        "pairs": pairs,
    }


# --- Projection -------------------------------------------------------------


def project_unusual_pairs(
    result: Mapping[str, Any],
    records: Sequence[Record],
    *,
    settings: Mapping[str, Any],
    top_k: int,
    notes: Sequence[str],
) -> dict[str, Any]:
    """Project the result of the unusual-pairs engine to the fixed output shape.

    Args:
        result: The engine result. Only `outputs[].rank` and `outputs[].payload` are read.
        records: The clean corpus. Titles and source references come from here.
        settings: The recorded settings of this engine.
        top_k: The requested number of pairs.
        notes: Plain-English notes for the top of the file.

    Returns:
        A dictionary with no time, path, model path or source excerpt.

    Raises:
        ValueError: A pair names a record id that is not in `records`.
    """
    index = _record_index(records)
    pairs: list[dict[str, Any]] = []
    for item in result.get("outputs", []):
        payload = item["payload"]
        left_id = str(payload["left"]["artifact_id"])
        right_id = str(payload["right"]["artifact_id"])
        signed = float(payload["signed_difference"])
        pairs.append(
            {
                "rank": int(item["rank"]),
                "pair_id": _pair_id(left_id, right_id),
                "left": _side(index, left_id),
                "right": _side(index, right_id),
                "scores": {
                    "wording_similarity": float(payload["structural_similarity"]),
                    "meaning_similarity": float(payload["semantic_similarity"]),
                    "signed_gap": signed,
                    "rank_score": float(payload["disagreement"]),
                    "method_signals": _numeric_only(payload.get("method_signals")),
                },
                "reading": direction_for_unusual_pair(signed),
                "label": LABEL,
            }
        )
    return _file_shell(
        name=UNUSUAL_PAIRS_NAME,
        capability_id=UNUSUAL_PAIRS_CAPABILITY,
        meaning_key="unusual_pairs",
        settings=settings,
        top_k=top_k,
        notes=notes,
        records_scored=len(records),
        pairs=pairs,
    )


def project_wording_and_meaning(
    pairs: Sequence[Mapping[str, Any]],
    records: Sequence[Record],
    *,
    settings: Mapping[str, Any],
    top_k: int,
    notes: Sequence[str],
) -> dict[str, Any]:
    """Project the pairs of the wording-and-meaning engine to the fixed output shape.

    Args:
        pairs: The engine pairs, in rank order. Source trails and excerpts are ignored.
        records: The clean corpus. Titles and source references come from here.
        settings: The recorded settings of this engine.
        top_k: The requested number of pairs.
        notes: Plain-English notes for the top of the file.

    Returns:
        A dictionary with no time, path, model path or source excerpt.

    Raises:
        ValueError: A pair names a record id that is not in `records`.
    """
    index = _record_index(records)
    projected: list[dict[str, Any]] = []
    for pair in pairs:
        left_id = str(pair["left_id"])
        right_id = str(pair["right_id"])
        wording = float(pair["lsa_sim"])
        meaning = float(pair["semantic_sim"])
        scores: dict[str, Any] = {
            "wording_similarity": wording,
            "meaning_similarity": meaning,
            "rank_score": float(pair["hsi_score"]),
        }
        optional = (
            ("lexical_similarity", "lexical_sim"),
            ("bm25_similarity", "bm25_sim"),
            ("percentile", "hsi_percentile"),
            ("z_score", "hsi_z"),
        )
        for out_key, in_key in optional:
            value = pair.get(in_key)
            if isinstance(value, int | float) and not isinstance(value, bool):
                scores[out_key] = float(value)
        if isinstance(pair.get("second_signal"), Mapping):
            scores["second_signal"] = _scalar_copy(pair["second_signal"])
        projected.append(
            {
                "rank": int(pair["rank"]),
                "pair_id": _pair_id(left_id, right_id),
                "left": _side(index, left_id),
                "right": _side(index, right_id),
                "scores": scores,
                "reading": direction_for_wording_pair(wording, meaning),
                "label": LABEL,
            }
        )
    return _file_shell(
        name=WORDING_AND_MEANING_NAME,
        capability_id=WORDING_AND_MEANING_CAPABILITY,
        meaning_key="wording_and_meaning",
        settings=settings,
        top_k=top_k,
        notes=notes,
        records_scored=len(records),
        pairs=projected,
    )


def attach_pair_classes(doc: dict[str, Any], records: Sequence[Record]) -> dict[str, Any]:
    """Add the outcome class and the carried cells to every pair of a projected file.

    The engines run on every record. This step classifies the pairs afterwards
    (Phase 2.2, D-02 and D-03): `cross` when the two records differ in class, else
    `<class>_<class>`. Every pair also gets `left_extras` and `right_extras`, the
    trimmed cells of the mapping carry columns. `counts.pair_classes` holds the 3
    counts. Nothing changes when no record carries a class, so a run without a
    rule writes the same bytes as before.

    Args:
        doc: A projected pair file from `project_unusual_pairs` or
            `project_wording_and_meaning`. It is changed in place.
        records: The clean corpus. Classes and extras come from here.

    Returns:
        The same dictionary. It is unchanged when no record carries an outcome class.

    Raises:
        ValueError: A pair names a record id that is not in `records`, or some
            records carry a class and others do not.
    """
    classes = {record.id: record.outcome_class for record in records}
    if not any(classes.values()):
        return doc
    missing = sorted(record_id for record_id, value in classes.items() if value is None)
    if missing:
        raise ValueError(f"Record without an outcome class: {missing[0]}")
    extras = {record.id: dict(record.extras) for record in records}
    counts = {name: 0 for name in sorted(PAIR_CLASSES)}
    for pair in doc["pairs"]:
        left_id = str(pair["left"]["id"])
        right_id = str(pair["right"]["id"])
        for record_id in (left_id, right_id):
            if record_id not in classes:
                raise ValueError(f"Unknown record id in engine result: {record_id}")
        left, right = classes[left_id], classes[right_id]
        pair_class = PAIR_CLASS_CROSS if left != right else f"{left}_{left}"
        if pair_class not in PAIR_CLASSES:
            raise ValueError(f"Unknown pair class: {pair_class}")
        pair["pair_class"] = pair_class
        pair["left_extras"] = extras[left_id]
        pair["right_extras"] = extras[right_id]
        counts[pair_class] += 1
    doc["counts"]["pair_classes"] = counts
    return doc


# --- Plain sentences --------------------------------------------------------


def _name_ids(ids: Sequence[str]) -> str:
    named = ", ".join(ids[:_MAX_NAMED_IDS])
    extra = len(ids) - _MAX_NAMED_IDS
    if extra > 0:
        return f"{named}, and {extra} more"
    return named


def describe_caps(caps_hit: Sequence[Mapping[str, Any]]) -> list[str]:
    """Turn the cap hits of the corpus manifest into plain sentences.

    Args:
        caps_hit: The `caps_hit` list of `Corpus.manifest_corpus()`.

    Returns:
        One sentence for each cap hit.
    """
    sentences: list[str] = []
    for hit in caps_hit:
        sentences.append(
            f"The limit of {hit['limit']} records was reached ({hit['name']}). "
            f"{hit['records_in']} records came in, {hit['records_used']} records were used, "
            f"and {hit['dropped_count']} records were left out."
        )
    return sentences


def describe_drops(dropped: Sequence[Mapping[str, Any]]) -> list[str]:
    """Turn the dropped records of the corpus manifest into plain sentences.

    Args:
        dropped: The `dropped` list of `Corpus.manifest_corpus()`.

    Returns:
        One sentence for each reason, with the first 10 record ids named.
    """
    by_reason: dict[str, list[str]] = {}
    for item in dropped:
        by_reason.setdefault(str(item["reason"]), []).append(str(item["id"]))
    sentences: list[str] = []
    for reason in sorted(by_reason):
        ids = by_reason[reason]
        noun = "record was" if len(ids) == 1 else "records were"
        sentences.append(f"{len(ids)} {noun} left out ({reason}): {_name_ids(ids)}.")
    return sentences


def filter_engine_warnings(warnings: Sequence[str]) -> list[str]:
    """Remove the engine warning about the model path, which the manifest replaces.

    Args:
        warnings: The warnings of the engine, in order.

    Returns:
        The other warnings, in the same order.
    """
    return [text for text in warnings if not text.startswith(_MODEL_IDENTITY_PREFIX)]
