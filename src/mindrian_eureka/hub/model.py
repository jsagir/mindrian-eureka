"""Build deterministic graph model values from hub run data.

Import rule: the standard library, `.contracts`, `..run.output` for the
4-decimal score text helper, and `..seed.contracts` for the seed constants only. Do not
import numpy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..run.contracts import LABEL
from ..run.output import _score
from ..seed.contracts import PAIR_ID_PATTERN, pair_command
from .contracts import (
    ENGINE_KEYS,
    ENGINE_UNUSUAL,
    ENGINE_WORDING,
    HUB_CONFIG,
    HUB_DATA_SCHEMA,
    NEIGHBORHOOD_TINTS,
    WIDTH_CROSSING,
    WIDTH_MAX,
    WIDTH_MIN,
    Payload,
    PayloadBridge,
    PayloadEngine,
    PayloadHood,
    PayloadPair,
    PayloadRecord,
    RunData,
    RunPair,
    deep_link,
)


def pair_key(pair: RunPair) -> str:
    """Return the stable payload key of a pair."""
    return f"{pair.engine}:{pair.pair_id}"


def score_text(value: float) -> str:
    """Format a score with the same four decimals used in ranked-pairs.md."""
    return _score({"score": value}, "score")


def engine_weights(pairs: Sequence[RunPair]) -> dict[str, float]:
    """Normalize nonnegative rank scores within each engine.

    Args:
        pairs: Visible pairs to normalize.

    Returns:
        A mapping from engine-and-pair key to a weight between zero and one.
    """
    maxima: dict[str, float] = {}
    for pair in pairs:
        score = max(pair.rank_score, 0.0)
        maxima[pair.engine] = max(maxima.get(pair.engine, 0.0), score)

    weights: dict[str, float] = {}
    for pair in sorted(pairs, key=pair_key):
        maximum = maxima[pair.engine]
        score = max(pair.rank_score, 0.0)
        weights[pair_key(pair)] = score / maximum if maximum > 0.0 else 0.0
    return weights


def label_propagation(
    edges: Mapping[tuple[str, str], float], nodes: Sequence[str]
) -> dict[str, str]:
    """Group connected visible records with sorted, weighted label propagation.

    Args:
        edges: Pairwise weights keyed by a pair of record IDs.
        nodes: Candidate record IDs. IDs with no incident edge are omitted.

    Returns:
        A mapping from each connected record ID to its stable final label.
    """
    adjacency: dict[str, dict[str, float]] = {}
    for (first, second), weight in sorted(edges.items()):
        first_neighbors = adjacency.setdefault(first, {})
        first_neighbors[second] = first_neighbors.get(second, 0.0) + weight
        second_neighbors = adjacency.setdefault(second, {})
        second_neighbors[first] = second_neighbors.get(first, 0.0) + weight

    ordered_nodes = [node for node in sorted(set(nodes)) if adjacency.get(node)]
    labels = {node: node for node in ordered_nodes}
    for _ in range(100):
        changed = False
        for node in ordered_nodes:
            totals: dict[str, float] = {}
            for neighbor in sorted(adjacency[node]):
                label = labels[neighbor]
                totals[label] = totals.get(label, 0.0) + adjacency[node][neighbor]
            if not totals:
                continue
            largest = max(totals.values())
            current = labels[node]
            if totals.get(current) == largest:
                next_label = current
            else:
                next_label = min(label for label, total in totals.items() if total == largest)
            if next_label != current:
                labels[node] = next_label
                changed = True
        if not changed:
            break
    return labels


def number_hoods(labels: Mapping[str, str]) -> list[PayloadHood]:
    """Number label groups by size and lowest record ID, then assign book tints.

    Args:
        labels: The final record-to-label mapping.

    Returns:
        Neighborhoods ordered by descending size, then by their lowest record ID.
    """
    groups: dict[str, list[str]] = {}
    for record_id in sorted(labels):
        groups.setdefault(labels[record_id], []).append(record_id)
    ordered = sorted(groups.values(), key=lambda record_ids: (-len(record_ids), record_ids[0]))
    return [
        {
            "number": number,
            "size": len(record_ids),
            "tint": NEIGHBORHOOD_TINTS[(number - 1) % len(NEIGHBORHOOD_TINTS)],
            "record_ids": record_ids,
        }
        for number, record_ids in enumerate(ordered, start=1)
    ]


def pair_widths(pairs: Sequence[RunPair], labels: Mapping[str, str]) -> dict[str, float]:
    """Scale visible pair widths and mark cross-neighborhood pairs.

    Args:
        pairs: Pairs that pass their engine's visibility floor.
        labels: The final neighborhood label for each visible record.

    Returns:
        A mapping from engine-and-pair key to its drawing width.
    """
    ranges: dict[str, tuple[float, float]] = {}
    for engine in sorted({pair.engine for pair in pairs}):
        scores = [pair.rank_score for pair in pairs if pair.engine == engine]
        ranges[engine] = (min(scores), max(scores))

    widths: dict[str, float] = {}
    for pair in sorted(pairs, key=pair_key):
        if labels.get(pair.left_id) != labels.get(pair.right_id):
            widths[pair_key(pair)] = WIDTH_CROSSING
            continue
        low, high = ranges[pair.engine]
        if high == low:
            widths[pair_key(pair)] = WIDTH_MAX
        else:
            ratio = (pair.rank_score - low) / (high - low)
            widths[pair_key(pair)] = WIDTH_MIN + (WIDTH_MAX - WIDTH_MIN) * ratio
    return widths


def _is_weak(pair: RunPair, floor: float | None) -> bool:
    return floor is not None and pair.percentile is not None and pair.percentile < floor


def _bridge_candidates(
    pairs: Sequence[RunPair],
    weights: Mapping[str, float],
    hood_by_record: Mapping[str, int],
) -> dict[str, tuple[float, str, list[int]]]:
    """Return each qualified record's best one-engine bridge reading."""
    candidates: dict[str, tuple[float, str, list[int]]] = {}
    for engine in ENGINE_KEYS:
        by_record: dict[str, dict[int, float]] = {}
        for pair in pairs:
            if pair.engine != engine:
                continue
            first_hood = hood_by_record.get(pair.left_id)
            second_hood = hood_by_record.get(pair.right_id)
            if first_hood is None or second_hood is None:
                continue
            weight = weights[pair_key(pair)]
            first_partners = by_record.setdefault(pair.left_id, {})
            second_partners = by_record.setdefault(pair.right_id, {})
            first_partners[second_hood] = max(first_partners.get(second_hood, 0.0), weight)
            second_partners[first_hood] = max(second_partners.get(first_hood, 0.0), weight)
        for record_id in sorted(by_record):
            partners = by_record[record_id]
            if len(partners) < 2:
                continue
            top_weights = sorted(partners.values(), reverse=True)[:2]
            score = sum(top_weights)
            hoods = sorted(partners)
            existing = candidates.get(record_id)
            if existing is None or score > existing[0] or (
                score == existing[0] and engine == ENGINE_UNUSUAL and existing[1] != ENGINE_UNUSUAL
            ):
                candidates[record_id] = (score, engine, hoods)
    return candidates


def build_payload(
    run: RunData, *, file_links: Mapping[str, str] | None = None
) -> Payload:
    """Build a stable payload from run files without reading time or path state.

    Args:
        run: Validated run data from `load_run`.
        file_links: Optional relative links to source files, keyed by record ID.

    Returns:
        The complete JSON-compatible hub payload.

    Raises:
        ValueError: A pair uses an unknown engine or record ID.
    """
    records_by_id = {record.id: record for record in run.records}
    if set(run.engines) != set(ENGINE_KEYS):
        raise ValueError("run must contain both known engines")

    floors: dict[str, float | None] = {}
    all_pairs: list[RunPair] = []
    visible_pairs: list[RunPair] = []
    weak_by_engine: dict[str, int] = {}
    for engine_key in ENGINE_KEYS:
        engine = run.engines[engine_key]
        floor = engine.min_percentile if engine.min_percentile > 0.0 else None
        floors[engine_key] = floor
        weak_by_engine[engine_key] = 0
        for pair in engine.pairs:
            if pair.engine != engine_key:
                raise ValueError(f"pair {pair_key(pair)} is under the wrong engine")
            if pair.left_id not in records_by_id:
                raise ValueError(f"pair {pair_key(pair)} references unknown record {pair.left_id}")
            if pair.right_id not in records_by_id:
                raise ValueError(f"pair {pair_key(pair)} references unknown record {pair.right_id}")
            all_pairs.append(pair)
            if _is_weak(pair, floor):
                weak_by_engine[engine_key] += 1
            else:
                visible_pairs.append(pair)

    weights = engine_weights(visible_pairs)
    edges: dict[tuple[str, str], float] = {}
    visible_ids: set[str] = set()
    for pair in visible_pairs:
        first, second = sorted((pair.left_id, pair.right_id))
        visible_ids.update((first, second))
        edge = (first, second)
        edges[edge] = edges.get(edge, 0.0) + weights[pair_key(pair)]
    labels = label_propagation(edges, sorted(visible_ids))
    hoods = number_hoods(labels)
    hood_by_record = {
        record_id: hood["number"]
        for hood in hoods
        for record_id in hood["record_ids"]
    }
    widths = pair_widths(visible_pairs, labels)
    bridge_candidates = _bridge_candidates(visible_pairs, weights, hood_by_record)
    ranked_bridges = sorted(
        bridge_candidates.items(), key=lambda item: (-item[1][0], item[0])
    )[: HUB_CONFIG["tour_max"]]
    bridges: list[PayloadBridge] = []
    bridge_by_record: dict[str, tuple[int, list[int]]] = {}
    for rank, (record_id, (score, chosen_engine, bridge_hoods)) in enumerate(
        ranked_bridges, start=1
    ):
        bridges.append(
            {
                "record_id": record_id,
                "rank": rank,
                "engine": chosen_engine,
                "score": score,
                "score_text": score_text(score),
                "hoods": bridge_hoods,
            }
        )
        bridge_by_record[record_id] = (rank, bridge_hoods)

    by_text_hash: dict[str, list[str]] = {}
    for record in run.records:
        if record.text and record.text_sha256:
            by_text_hash.setdefault(record.text_sha256, []).append(record.id)
    identical_groups = sorted(
        (sorted(ids) for ids in by_text_hash.values() if len(ids) > 1),
        key=lambda ids: ids[0],
    )
    identical_to: dict[str, list[str]] = {}
    for group in identical_groups:
        for record_id in group:
            identical_to[record_id] = [other for other in group if other != record_id]
    no_text_ids = {record.id for record in run.records if not record.text}

    pair_keys_by_record: dict[str, list[str]] = {record_id: [] for record_id in records_by_id}
    visible_count_by_record: dict[str, int] = {record_id: 0 for record_id in records_by_id}
    for pair in all_pairs:
        key = pair_key(pair)
        pair_keys_by_record[pair.left_id].append(key)
        pair_keys_by_record[pair.right_id].append(key)
        if pair in visible_pairs:
            visible_count_by_record[pair.left_id] += 1
            visible_count_by_record[pair.right_id] += 1

    records: list[PayloadRecord] = []
    link_by_record: dict[str, str] = {}
    for record in sorted(run.records, key=lambda item: item.id):
        catalogue_link = deep_link(record.id)
        file_link = file_links.get(record.id) if file_links is not None else None
        source_link = file_link or catalogue_link
        link_by_record[record.id] = source_link
        bridge = bridge_by_record.get(record.id)
        records.append(
            {
                "id": record.id,
                "title": record.title,
                "text": record.text,
                "source_ref": record.source_ref,
                "source_file": record.source_file,
                "text_sha256": record.text_sha256,
                "hood": hood_by_record.get(record.id),
                "pair_keys": sorted(pair_keys_by_record[record.id]),
                "pair_count": len(pair_keys_by_record[record.id]),
                "visible_pair_count": visible_count_by_record[record.id],
                "bridge": bridge is not None,
                "bridge_rank": bridge[0] if bridge is not None else None,
                "bridge_hoods": bridge[1] if bridge is not None else [],
                "identical_to": identical_to.get(record.id, []),
                "no_text": record.id in no_text_ids,
                "source_link": source_link,
                "catalogue_link": catalogue_link,
                "file_link": file_link,
                "label": LABEL,
            }
        )

    pairs: list[PayloadPair] = []
    for pair in sorted(
        all_pairs,
        key=lambda item: (ENGINE_KEYS.index(item.engine), item.rank, item.pair_id),
    ):
        left = records_by_id[pair.left_id]
        right = records_by_id[pair.right_id]
        weak = _is_weak(pair, floors[pair.engine])
        entry: PayloadPair = {
            "key": pair_key(pair),
            "pair_id": pair.pair_id,
            "engine": pair.engine,
            "rank": pair.rank,
            "left": {
                "id": left.id,
                "title": left.title,
                "source_file": left.source_file,
                "source_link": link_by_record[left.id],
            },
            "right": {
                "id": right.id,
                "title": right.title,
                "source_file": right.source_file,
                "source_link": link_by_record[right.id],
            },
            "wording": pair.wording,
            "meaning": pair.meaning,
            "rank_score": pair.rank_score,
            "wording_text": score_text(pair.wording),
            "meaning_text": score_text(pair.meaning),
            "rank_score_text": score_text(pair.rank_score),
            "percentile": pair.percentile,
            "reading": pair.reading,
            "label": LABEL,
            "weak": weak,
            "weight": 0.0 if weak else weights[pair_key(pair)],
            "width": WIDTH_MIN if weak else widths[pair_key(pair)],
            "crosses": (
                not weak
                and hood_by_record.get(pair.left_id) != hood_by_record.get(pair.right_id)
            ),
            "flag_identical": pair.left_id in identical_to or pair.right_id in identical_to,
            "flag_no_text": pair.left_id in no_text_ids or pair.right_id in no_text_ids,
        }
        # Phase 2.2 (D-02, D-03): the class and the carried cells are written only when
        # the run has them, so a plain run keeps the same payload bytes.
        if pair.pair_class is not None:
            entry["pair_class"] = pair.pair_class
        if pair.left_extras:
            entry["left_extras"] = dict(pair.left_extras)
        if pair.right_extras:
            entry["right_extras"] = dict(pair.right_extras)
        # Phase 2.3 (D-04, SEED-05): the exact seed command, as text to copy. Only for a
        # run that holds a section map, a pair id of the known form, and cell states for
        # both records. A hostile id never reaches a command that a person could paste.
        if (
            run.room_sections
            and PAIR_ID_PATTERN.fullmatch(pair.pair_id)
            and left.room_cells
            and right.room_cells
        ):
            entry["seed_command"] = pair_command(pair.pair_id)
        pairs.append(entry)

    removed_counts: dict[str, int] = {}
    for item in run.dropped:
        reason = str(item.get("reason", "unknown reason"))
        removed_counts[reason] = removed_counts.get(reason, 0) + 1
    removed = [
        {"reason": reason, "count": str(removed_counts[reason])}
        for reason in sorted(removed_counts)
    ]
    removed_text = "; ".join(
        f"{reason} ({removed_counts[reason]})" for reason in sorted(removed_counts)
    )
    engines_payload: dict[str, PayloadEngine] = {}
    short_names = {
        ENGINE_UNUSUAL: "Unusual-pairs engine",
        ENGINE_WORDING: "Wording engine",
    }
    for engine_key in ENGINE_KEYS:
        engine = run.engines[engine_key]
        floor = floors[engine_key]
        engines_payload[engine_key] = {
            "key": engine_key,
            "name": engine.name,
            "short_name": short_names[engine_key],
            "score_meaning": engine.score_meaning,
            "notes": list(engine.notes),
            "floor": floor,
            "floor_text": f"{floor:.2f}" if floor is not None else "",
            "pairs": len(engine.pairs),
            "top_k": engine.top_k,
            "top_k_reached": engine.top_k_reached,
            "weak": weak_by_engine[engine_key],
        }

    visible_record_count = len(visible_ids)
    weak_count = sum(weak_by_engine.values())
    payload: Payload = {
        "schema": HUB_DATA_SCHEMA,
        "label": LABEL,
        "tool_version": run.tool_version,
        "run_fingerprint": run.manifest_sha256,
        "config": dict(HUB_CONFIG),
        "counts": {
            "records": len(run.records),
            "pairs": {key: len(run.engines[key].pairs) for key in ENGINE_KEYS},
            "hoods": len(hoods),
            "records_in_visible_pairs": visible_record_count,
            "records_in_no_pair": len(run.records) - visible_record_count,
            "weak_pairs": weak_count,
        },
        "engines": engines_payload,
        "records": records,
        "pairs": pairs,
        "hoods": hoods,
        "bridges": bridges,
        "data_check": {
            "identical_records": sum(len(group) for group in identical_groups),
            "identical_groups": identical_groups,
            "no_text_records": len(no_text_ids),
            "removed_count": len(run.dropped),
            "removed": removed,
            "removed_text": removed_text,
            "boilerplate": "not_checked",
        },
        "graph": {
            "earned": visible_record_count >= HUB_CONFIG["graph_min_records"],
            "visible_records": visible_record_count,
            "min_records": HUB_CONFIG["graph_min_records"],
            "not_drawn": len(run.records) - visible_record_count,
        },
    }
    if any(pair.pair_class is not None for pair in all_pairs):
        payload["has_pair_classes"] = True
    if any("seed_command" in entry for entry in pairs):
        payload["has_seed_commands"] = True
    return payload
