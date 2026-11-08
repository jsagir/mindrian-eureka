"""The pipeline of `eureka run`: a folder in, a complete hashed output folder out.

`run_pipeline` is a plain function with a request and a summary object, so the MCP server
of a later phase can call it. It prints nothing: all text goes through the `Console`
argument. It catches no error. A failure leaves no staging folder and does not touch an
earlier run in the output folder.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import models
from ..encoder_spec import DEFAULT_PROFILE, PROFILES, encoder_block, profile_spec
from ..limits import HARD_MAX_ARTIFACTS, MAX_ARTIFACTS, MAX_TOP_K
from . import corpus, engines
from .console import Console
from .contracts import (
    LABEL,
    SUMMARY_LINE,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    Record,
    RunError,
    UsageError,
)
from .manifest import build_manifest, build_run_info, collect_environment
from .manifest import model_fingerprint as describe_model
from .output import (
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
    ensure_out_dir_allowed,
    render_ranked_markdown,
)
from .project import (
    attach_pair_classes,
    describe_caps,
    describe_drops,
    filter_engine_warnings,
    project_unusual_pairs,
    project_wording_and_meaning,
)

if TYPE_CHECKING:
    from .mapping import MappingConfig

RUN_SUMMARY_SCHEMA = "eureka.run-summary.v1"
MODEL_NOTE = "Model files are identified by sha256 in the manifest."
_MIN_ARTIFACTS = 2
_OLD_GATE_PREFIX = re.compile(r"\bLATEST RS hybrid\b")
_SHORT_CODE = re.compile(r"\b(?:RS|HSI)\b\s*")


@dataclass(frozen=True)
class RunRequest:
    """The input of one run.

    Attributes:
        input_dir: The folder with Markdown and CSV files. It is only read.
        out_dir: The output folder. An earlier Eureka run in it is replaced.
        mapping: The CSV mapping, or None when the input holds no CSV file.
        text_sidecar: The side-car file keyed by the raw record id, or None. Its text is
            added to records whose own text is thin.
        model_path: The folder given with --model-path, or None.
        max_artifacts: The most records to rank.
        top_k: The most pairs for each engine.
        objective: Free text that the unusual-pairs engine records. It is not a signal.
        threads: The thread count for the numeric libraries, or None.
        use_cache: False uses a throwaway embedding cache.
        dry_run: True reads the input and reports, but loads no model and writes nothing.
        argv: The command line words, kept in run-info.json.
        encoder_profile: The name of the encoder profile. The default is the CPU profile that
            the shipped example uses. Another profile needs `model_path`.
    """

    input_dir: Path
    out_dir: Path
    mapping: MappingConfig | None = None
    text_sidecar: Path | None = None
    model_path: Path | None = None
    max_artifacts: int = MAX_ARTIFACTS
    top_k: int = MAX_TOP_K
    objective: str = ""
    threads: int | None = None
    use_cache: bool = True
    dry_run: bool = False
    argv: tuple[str, ...] = ()
    encoder_profile: str = DEFAULT_PROFILE


@dataclass(frozen=True)
class RunSummary:
    """The result of one run.

    Attributes:
        out_dir: The output folder.
        dry_run: True when nothing was written.
        records_read: The records found before drops and caps.
        records_used: The records that were ranked.
        dropped_count: The records dropped for a short body.
        caps_hit: The caps that cut the collection, as manifest dictionaries.
        unusual_pairs: The pair count of the unusual-pairs engine.
        wording_and_meaning_pairs: The pair count of the wording-and-meaning engine.
        files: The digest of every file written.
        manifest_sha256: The sha256 of manifest.json, or None for a dry run.
        warnings: The warnings shown during the run.
        pair_classes: The pair class counts of each engine, keyed `unusual_pairs` and
            `wording_and_meaning`, or None when the mapping has no outcome rule.
        text_coverage: The 4 text coverage counts (`records_total`, `own_text_ok`,
            `filled_from_sidecar`, `still_thin`), or None without a text side-car.
    """

    out_dir: Path
    dry_run: bool
    records_read: int
    records_used: int
    dropped_count: int
    caps_hit: tuple[dict[str, Any], ...] = ()
    unusual_pairs: int = 0
    wording_and_meaning_pairs: int = 0
    files: tuple[FileDigest, ...] = ()
    manifest_sha256: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    pair_classes: Mapping[str, Mapping[str, int]] | None = None
    text_coverage: Mapping[str, int] | None = None

    def to_json_dict(self) -> dict[str, Any]:
        """Return the summary as a JSON-ready dictionary."""
        counts: dict[str, Any] = {
            "records_read": self.records_read,
            "records_used": self.records_used,
            "dropped": self.dropped_count,
            "unusual_pairs": self.unusual_pairs,
            "wording_and_meaning_pairs": self.wording_and_meaning_pairs,
        }
        if self.pair_classes is not None:
            counts["pair_classes"] = {
                key: dict(value) for key, value in self.pair_classes.items()
            }
        if self.text_coverage is not None:
            counts["text_coverage"] = dict(self.text_coverage)
        return {
            "schema": RUN_SUMMARY_SCHEMA,
            "label": LABEL,
            "dry_run": self.dry_run,
            "out_dir": str(self.out_dir),
            "counts": counts,
            "caps_hit": [dict(item) for item in self.caps_hit],
            "files": [item.as_dict() for item in self.files],
            "manifest_sha256": self.manifest_sha256,
            "summary_line": SUMMARY_LINE,
        }

    def _class_line(self, name: str, key: str) -> str:
        assert self.pair_classes is not None
        counts = self.pair_classes[key]
        return (
            f"{name} classes: cross {counts.get('cross', 0)}, "
            f"open_open {counts.get('open_open', 0)}, "
            f"licensed_licensed {counts.get('licensed_licensed', 0)}"
        )

    def lines(self) -> str:
        """Return the text for standard output. The last line is the label sentence."""
        if self.dry_run:
            head = "Eureka dry run finished. No model was loaded and nothing was written."
        else:
            head = "Eureka run finished."
        out = [head, f"Output folder: {self.out_dir}"]
        out.append(
            f"Records: {self.records_used} used, {self.records_read} read, "
            f"{self.dropped_count} dropped"
        )
        if self.text_coverage is not None:
            coverage = self.text_coverage
            out.append(
                f"Text coverage: {coverage['records_total']} records, "
                f"{coverage['own_text_ok']} with own text, "
                f"{coverage['filled_from_sidecar']} filled from the side-car, "
                f"{coverage['still_thin']} still thin and dropped"
            )
        if not self.dry_run:
            out.append(
                f"{UNUSUAL_PAIRS_NAME}: {self.unusual_pairs} pairs ({OUTPUT_UNUSUAL})"
            )
            if self.pair_classes is not None:
                out.append(self._class_line(UNUSUAL_PAIRS_NAME, "unusual_pairs"))
            out.append(
                f"{WORDING_AND_MEANING_NAME}: {self.wording_and_meaning_pairs} pairs "
                f"({OUTPUT_WORDING})"
            )
            if self.pair_classes is not None:
                out.append(self._class_line(WORDING_AND_MEANING_NAME, "wording_and_meaning"))
            out.append(f"Report: {OUTPUT_MARKDOWN}")
            out.append(f"Manifest: {OUTPUT_MANIFEST} (sha256 {self.manifest_sha256})")
        if self.caps_hit:
            out.append("Caps hit: " + " ".join(describe_caps(self.caps_hit)))
        else:
            out.append("Caps hit: none")
        out.append(SUMMARY_LINE)
        return "\n".join(out)


# --- Steps ------------------------------------------------------------------


def _validate(request: RunRequest) -> None:
    if not 1 <= request.top_k <= MAX_TOP_K:
        raise UsageError(
            f"The pair count must be from 1 to {MAX_TOP_K}. You gave {request.top_k}.",
            fix=f"Use --top-k with a number from 1 to {MAX_TOP_K}.",
        )
    if not _MIN_ARTIFACTS <= request.max_artifacts <= HARD_MAX_ARTIFACTS:
        raise UsageError(
            f"The record limit must be from {_MIN_ARTIFACTS} to {HARD_MAX_ARTIFACTS}. "
            f"You gave {request.max_artifacts}.",
            fix=f"Use --max-artifacts with a number from {_MIN_ARTIFACTS} to "
            f"{HARD_MAX_ARTIFACTS}.",
        )
    if request.text_sidecar is not None and not request.text_sidecar.is_file():
        raise UsageError(
            f"The side-car file {request.text_sidecar.name} does not exist",
            fix="Check the side-car path",
        )
    names = ", ".join(sorted(PROFILES))
    if request.encoder_profile not in PROFILES:
        raise UsageError(
            f"The encoder profile {request.encoder_profile!r} is not known. The names are: "
            f"{names}.",
            fix=f"Use --encoder-profile with one of: {names}",
        )
    if (
        request.encoder_profile != DEFAULT_PROFILE
        and request.model_path is None
        and not request.dry_run
    ):
        wanted = PROFILES[request.encoder_profile].model_id
        raise UsageError(
            f"The encoder profile {request.encoder_profile} needs the folder of its own model "
            f"({wanted}). Eureka does not use another model for a named profile.",
            fix=f"Give --model-path with the folder of {wanted}",
        )


def _profile_fix_text(profile: str) -> str:
    """Return the fix block for a model folder of a named profile (not the default)."""
    wanted = PROFILES[profile].model_id
    return (
        f"1. The profile {profile} needs the folder of its own model: {wanted}. "
        "Eureka does not use another model for it.\n"
        "2. The weights of this profile are fetched by the owner-run spike steps in "
        "docs/encoder-spike-results.md, not by the fix lines of the default model.\n"
        f"3. Pass --model-path with the folder of {wanted}."
    )


def _find_model(request: RunRequest) -> Path:
    resolution = models.discover_model(request.model_path)
    if not resolution.ok or resolution.path is None:
        fix_text = (
            None
            if request.encoder_profile == DEFAULT_PROFILE
            else _profile_fix_text(request.encoder_profile)
        )
        raise RunError(
            models.missing_model_message(
                resolution, explicit_given=request.model_path is not None, fix_text=fix_text
            )
        )
    return resolution.path


def _plain_engine_text(text: str) -> str:
    """Rewrite one engine warning so it holds no short engine code."""
    cleaned = _OLD_GATE_PREFIX.sub("The hybrid", text)
    return _SHORT_CODE.sub("", cleaned)


def _unique(items: Sequence[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def _corpus_notes(built: corpus.Corpus, manifest_corpus: dict[str, Any]) -> list[str]:
    notes = list(built.warnings)
    notes.extend(describe_caps(manifest_corpus["caps_hit"]))
    notes.extend(describe_drops(manifest_corpus["dropped"]))
    return _unique(notes)


@contextlib.contextmanager
def _restored_umask() -> Iterator[None]:
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


@contextlib.contextmanager
def _cache_path(use_cache: bool, profile: str = DEFAULT_PROFILE) -> Iterator[Path]:
    if use_cache:
        from mindrian_eureka.opportunity_pairs.cache import default_cache_path

        yield default_cache_path(profile)
        return
    with tempfile.TemporaryDirectory(prefix="eureka-cache-") as folder:
        yield Path(folder) / "embeddings.sqlite3"


def _model_digest(files: Mapping[str, str]) -> str | None:
    """Return one sha256 over the file hashes of the model folder, or None when none is known."""
    if not files:
        return None
    text = json.dumps(dict(files), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _gpu_details() -> dict[str, str]:
    """Return the name of the CUDA device and the CUDA version, or an empty dict on any error."""
    try:
        import torch

        return {
            "name": str(torch.cuda.get_device_name(0)),
            "cuda": str(torch.version.cuda),
        }
    except Exception:
        return {}


NON_EXACT_WARNING = (
    "This run used a non-exact encoder profile (gpu-approx), so two runs on different "
    "computers can differ in bytes; compare them by ranking overlap and not by bytes."
)
WEIGHTS_NOTE = (
    "The model weights are not pinned: no model file could be hashed, so this identity does "
    "not tell two model folders apart."
)


def _manifest_output(digest: FileDigest, projected: dict[str, Any]) -> dict[str, Any]:
    counts = projected["counts"]
    item = digest.as_dict()
    item["pairs"] = counts["pairs"]
    item["top_k_reached"] = counts["top_k_reached"]
    return item


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _empty_warning(warn: Callable[[str], None], name: str, count: int) -> None:
    if count == 0:
        warn(f"{name} returned no candidate pairs for this collection.")


def _write_outputs(
    request: RunRequest,
    console: Console,
    built: corpus.Corpus,
    model_dir: Path,
    staged: StagedRun,
    started_at: str,
    started_clock: float,
    warn: Callable[[str], None],
    warned: list[str],
) -> RunSummary:
    records: tuple[Record, ...] = built.records
    manifest_corpus = built.manifest_corpus()
    files: list[FileDigest] = []

    profile = request.encoder_profile
    named = profile != DEFAULT_PROFILE
    model_info = describe_model(model_dir)
    unusual_spec = profile_spec(
        profile,
        revision=model_info["snapshot"],
        model_digest=_model_digest(model_info["files"]),
    )
    wording_spec = unusual_spec.for_caller_chunks()
    if named:
        warn(NON_EXACT_WARNING)

    console.stage("Writing the clean corpus")
    corpus_digest = staged.write(OUTPUT_CORPUS, corpus_lines(records))
    files.append(corpus_digest)

    with _cache_path(request.use_cache, profile) as cache_file:
        console.stage(f"Ranking with {UNUSUAL_PAIRS_NAME}")
        unusual = engines.run_unusual_pairs(
            records,
            model_dir=model_dir,
            top_k=request.top_k,
            max_artifacts=request.max_artifacts,
            cache_path=cache_file,
            objective=request.objective,
            progress=console.stage,
            encoder_spec=unusual_spec,
        )
        console.stage("Loading the local model")
        if named:
            encode = engines.load_local_encode(model_dir, wording_spec)
        else:
            encode = engines.load_local_encode(model_dir)
        console.stage(f"Ranking with {WORDING_AND_MEANING_NAME}")
        wording = engines.run_wording_and_meaning(
            records,
            encode=encode,
            top_k=request.top_k,
            progress=console.info,
            model_name=wording_spec.model_id if named else None,
        )

    console.stage("Writing files")
    sections = engines.manifest_engine_sections(unusual, wording)
    common = _corpus_notes(built, manifest_corpus)
    common.append(MODEL_NOTE)
    engine_warnings = [
        _plain_engine_text(text)
        for text in filter_engine_warnings(list(unusual.result.get("warnings", [])))
    ]
    unusual_notes = _unique([*common, *engine_warnings])
    wording_notes = _unique([*common, *wording.engine_notes])

    unusual_doc = project_unusual_pairs(
        unusual.result,
        records,
        settings=sections["settings"]["unusual_pairs"],
        top_k=request.top_k,
        notes=unusual_notes,
        encoder_fingerprint=unusual_spec.fingerprint() if named else None,
    )
    wording_doc = project_wording_and_meaning(
        wording.pairs,
        records,
        settings=sections["settings"]["wording_and_meaning"],
        top_k=request.top_k,
        notes=wording_notes,
        encoder_fingerprint=wording_spec.fingerprint() if named else None,
    )
    unusual_doc = attach_pair_classes(unusual_doc, records)
    wording_doc = attach_pair_classes(wording_doc, records)
    pair_classes: dict[str, Any] | None = None
    if "pair_classes" in unusual_doc["counts"]:
        pair_classes = {
            "unusual_pairs": unusual_doc["counts"]["pair_classes"],
            "wording_and_meaning": wording_doc["counts"]["pair_classes"],
        }
    _empty_warning(warn, UNUSUAL_PAIRS_NAME, unusual_doc["counts"]["pairs"])
    _empty_warning(warn, WORDING_AND_MEANING_NAME, wording_doc["counts"]["pairs"])

    unusual_digest = staged.write(OUTPUT_UNUSUAL, canonical_json(unusual_doc))
    wording_digest = staged.write(OUTPUT_WORDING, canonical_json(wording_doc))
    markdown = render_ranked_markdown(unusual_doc, wording_doc)
    markdown_digest = staged.write(OUTPUT_MARKDOWN, markdown.encode("utf-8"))
    files.extend([unusual_digest, wording_digest, markdown_digest])

    settings = dict(sections["settings"])
    settings["run"] = {
        "max_artifacts": request.max_artifacts,
        "top_k": request.top_k,
        "objective": request.objective,
    }
    if request.mapping is not None:
        rules = {
            key: entry.outcome_rule.as_data()
            for key, entry in request.mapping.files.items()
            if entry.outcome_rule is not None
        }
        carried = {
            key: list(entry.carry_columns)
            for key, entry in request.mapping.files.items()
            if entry.carry_columns
        }
        room_maps = {
            key: entry.room_sections.as_data()
            for key, entry in request.mapping.files.items()
            if entry.room_sections is not None
        }
        if rules:
            settings["run"]["outcome_rules"] = rules
        if carried:
            settings["run"]["carry_columns"] = carried
        if room_maps:
            settings["run"]["room_sections"] = room_maps
    outputs = [
        corpus_digest.as_dict(),
        _manifest_output(unusual_digest, unusual_doc),
        _manifest_output(wording_digest, wording_doc),
        markdown_digest.as_dict(),
    ]
    block = encoder_block(unusual_spec, wording_spec)
    if unusual_spec.device.startswith("cuda"):
        block["gpu"] = _gpu_details()
    if unusual_spec.model_digest is None:
        block["weights_note"] = WEIGHTS_NOTE
    manifest = build_manifest(
        engines=sections["engines"],
        inputs=built.manifest_inputs(),
        corpus=manifest_corpus,
        settings=settings,
        seeds=sections["seeds"],
        model=model_info,
        environment=collect_environment(request.threads),
        outputs=outputs,
        engine_notes=sections["engine_notes"],
        encoder=block,
    )
    manifest_digest = staged.write(OUTPUT_MANIFEST, canonical_json(manifest))
    files.append(manifest_digest)
    run_info = build_run_info(
        started_at=started_at,
        finished_at=_now(),
        duration_ms=int((time.monotonic() - started_clock) * 1000),
        argv=request.argv,
        manifest_sha256=manifest_digest.sha256,
    )
    files.append(staged.write(OUTPUT_RUN_INFO, canonical_json(run_info)))
    staged.publish()

    return RunSummary(
        out_dir=request.out_dir,
        dry_run=False,
        records_read=built.records_read,
        records_used=len(records),
        dropped_count=len(built.dropped),
        caps_hit=tuple(manifest_corpus["caps_hit"]),
        unusual_pairs=unusual_doc["counts"]["pairs"],
        wording_and_meaning_pairs=wording_doc["counts"]["pairs"],
        files=tuple(files),
        manifest_sha256=manifest_digest.sha256,
        warnings=tuple(warned),
        pair_classes=pair_classes,
        text_coverage=built.text_coverage,
    )


# --- Entry point ------------------------------------------------------------


def run_pipeline(request: RunRequest, console: Console) -> RunSummary:
    """Turn a folder of sources into a complete output folder.

    The steps are: validate, check the output folder, find the model, build the clean
    corpus, rank with both engines, project, write the files and the manifest, publish.

    Args:
        request: What to run.
        console: Where progress and warnings go.

    Returns:
        The summary of the run.

    Raises:
        UsageError: A setting is out of range or the output folder is not allowed.
        RunError: No local model, bad input or an engine failure.
    """
    started_at = _now()
    started_clock = time.monotonic()
    _validate(request)
    ensure_out_dir_allowed(request.input_dir, request.out_dir)
    warned: list[str] = []

    def warn(message: str) -> None:
        warned.append(message)
        console.warn(message)

    with contextlib.ExitStack() as stack:
        model_dir: Path | None = None
        if not request.dry_run:
            engines.prepare_offline_environment()
            engines.apply_thread_limits(request.threads)
            stack.enter_context(_restored_umask())
            model_dir = _find_model(request)

        console.stage("Reading sources")
        built = corpus.build_corpus(
            request.input_dir,
            mapping=request.mapping,
            max_artifacts=request.max_artifacts,
            text_sidecar=request.text_sidecar,
        )
        manifest_corpus = built.manifest_corpus()
        for message in built.warnings:
            warn(message)
        for message in describe_caps(manifest_corpus["caps_hit"]):
            warn(message)
        for message in describe_drops(manifest_corpus["dropped"]):
            warn(message)

        if request.dry_run or model_dir is None:
            return RunSummary(
                out_dir=request.out_dir,
                dry_run=True,
                records_read=built.records_read,
                records_used=len(built.records),
                dropped_count=len(built.dropped),
                caps_hit=tuple(manifest_corpus["caps_hit"]),
                warnings=tuple(warned),
                text_coverage=built.text_coverage,
            )

        with StagedRun(request.out_dir) as staged:
            summary = _write_outputs(
                request,
                console,
                built,
                model_dir,
                staged,
                started_at,
                started_clock,
                warn,
                warned,
            )
    return summary
