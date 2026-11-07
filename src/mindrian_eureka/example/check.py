"""Compare a finished run folder with the shipped expected hashes.

The check reads files and hashes bytes. It never imports, runs or evaluates folder content.
It makes no network call and loads no model.

Import rule: the standard library and `..run.contracts`, `..run.manifest`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..run.contracts import LABEL, MANIFEST_SCHEMA, SUMMARY_LINE, UsageError
from ..run.manifest import sha256_file
from . import contracts as example_contracts
from .contracts import (
    CHECK_ENGINE,
    CHECK_INPUTS,
    CHECK_LABEL,
    CHECK_MODEL,
    CHECK_OUTPUTS,
    CHECK_RUN_FOLDER,
    CHECK_SETTINGS,
    DETERMINISM_CPU_EXACT,
    DETERMINISM_GPU_APPROX,
    ENCODER_KEY,
    EXPECTED_SCHEMA,
    GPU_APPROX_NOTE,
    MANIFEST_NAME,
    MAX_JSON_BYTES,
    NO_THRESHOLD_TEXT,
    NOT_REPRODUCED_TEXT,
    OUTPUT_FILES,
    OVERLAP_FILES,
    PAIR_FILES,
    REPORT_SCHEMA,
    RESULT_MATCH,
    RESULT_MATCH_ID,
    RESULT_NO_MATCH,
    RESULT_NO_MATCH_ID,
    STATUS_FAIL,
    STATUS_PASS,
)

_HEX64 = re.compile(r"[0-9a-f]{64}")
_BLOCK_SIZE = 1024 * 1024
_REQUIRED_KEYS = (
    "schema_version",
    "label",
    "example",
    "command",
    "inputs",
    "corpus",
    "model",
    "settings",
    "seeds",
    "engine",
    "engine_sources",
    "outputs",
    "reference_environment",
)


@dataclass(frozen=True)
class Check:
    """The result of one check.

    Attributes:
        id: The check id, for example `X6`.
        name: The check name, for example `outputs`.
        status: `PASS` or `FAIL`.
        detail: One line that says what was compared.
        fix: The action that fixes a failure, or None.
    """

    id: str
    name: str
    status: str
    detail: str
    fix: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        """Return the JSON form of the check."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class CheckReport:
    """The full result of `check_run`.

    Attributes:
        result: `match` or `no_match`.
        checks: The 7 checks, in order.
        info: Environment lines. They never change the result.
        note: An extra sentence for the reader, or None.
        determinism_class: The class that the manifest names for a non-exact run, or None.
        ranking_overlap: The overlap numbers of a non-exact run, or None.
    """

    result: str
    checks: tuple[Check, ...]
    info: tuple[str, ...] = field(default_factory=tuple)
    note: str | None = None
    determinism_class: str | None = None
    ranking_overlap: dict[str, Any] | None = None

    def to_text(self) -> str:
        """Return the text report, ending with the summary line."""
        lines: list[str] = []
        for item in self.checks:
            lines.append(f"{item.status} {item.id} {item.name}: {item.detail}")
            if item.status == STATUS_FAIL and item.fix:
                lines.append(f"  Fix: {item.fix}")
        lines.extend(self.info)
        if self.note:
            lines.append(self.note)
        lines.append(RESULT_MATCH if self.result == RESULT_MATCH_ID else RESULT_NO_MATCH)
        lines.append(SUMMARY_LINE)
        return "\n".join(lines)

    def to_json_dict(self) -> dict[str, Any]:
        """Return the JSON form of the report."""
        document: dict[str, Any] = {
            "schema": REPORT_SCHEMA,
            "result": self.result,
            "checks": [item.to_json_dict() for item in self.checks],
            "info": list(self.info),
            "note": self.note,
            "label": LABEL,
        }
        if self.determinism_class is not None:
            document["determinism_class"] = self.determinism_class
        if self.ranking_overlap is not None:
            document["ranking_overlap"] = self.ranking_overlap
        return document


# --- Expected file ----------------------------------------------------------


def _bad_expected(message: str) -> UsageError:
    return UsageError(
        f"The expected-hash file is not valid: {message}",
        fix="Use the expected-hash file that ships with Eureka, or rebuild it with "
        "scripts/make-example-hashes.",
    )


def _read_json(path: Path, what: str) -> Any:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise UsageError(
            f"The {what} cannot be read: {path.name}", fix="Check that the file exists."
        ) from error
    if size > MAX_JSON_BYTES:
        raise UsageError(
            f"The {what} is larger than {MAX_JSON_BYTES} bytes",
            fix="Use the file that Eureka wrote. Do not edit it.",
        )
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UsageError(
            f"The {what} is not valid JSON: {path.name}",
            fix="Use the file that Eureka wrote. Do not edit it.",
        ) from error


def _require_hex(value: object, where: str, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise _bad_expected(f"{where} is not a sha256 of 64 lowercase hex characters")


def _safe_relative(path: object, where: str) -> str:
    if not isinstance(path, str) or not path:
        raise _bad_expected(f"{where} is not a path")
    if "\\" in path or PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute():
        raise _bad_expected(f"{where} is not a relative path with forward slashes")
    if ".." in PurePosixPath(path).parts:
        raise _bad_expected(f"{where} holds a parent folder part")
    return path


def _need_mapping(value: object, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _bad_expected(f"{where} is not an object")
    return value


def load_expected(path: Path) -> dict[str, Any]:
    """Read and validate an expected-hash file.

    Args:
        path: The expected-hash file.

    Returns:
        The document as a plain dictionary.

    Raises:
        UsageError: The file is missing, too large, not JSON, or not a valid expected file.
    """
    document = _read_json(Path(path), "expected-hash file")
    if not isinstance(document, dict):
        raise _bad_expected("the top level is not an object")
    if document.get("schema_version") != EXPECTED_SCHEMA:
        raise _bad_expected(f"schema_version is not {EXPECTED_SCHEMA}")
    for key in _REQUIRED_KEYS:
        if key not in document:
            raise _bad_expected(f"the key {key} is missing")
    inputs = _need_mapping(document["inputs"], "inputs")
    for key in ("files", "folder_digest", "mapping_sha256"):
        if key not in inputs:
            raise _bad_expected(f"inputs.{key} is missing")
    files = inputs["files"]
    if not isinstance(files, list) or not files:
        raise _bad_expected("inputs.files is not a list")
    for index, entry in enumerate(files):
        item = _need_mapping(entry, f"inputs.files[{index}]")
        _safe_relative(item.get("path"), f"inputs.files[{index}].path")
        _require_hex(item.get("sha256"), f"inputs.files[{index}].sha256")
    _require_hex(inputs["folder_digest"], "inputs.folder_digest")
    _require_hex(inputs["mapping_sha256"], "inputs.mapping_sha256", allow_none=True)
    corpus = _need_mapping(document["corpus"], "corpus")
    for key in ("corpus_digest", "records_used"):
        if key not in corpus:
            raise _bad_expected(f"corpus.{key} is missing")
    _require_hex(corpus["corpus_digest"], "corpus.corpus_digest")
    model = _need_mapping(document["model"], "model")
    for key in ("name", "snapshot", "files"):
        if key not in model:
            raise _bad_expected(f"model.{key} is missing")
    for name, digest in _need_mapping(model["files"], "model.files").items():
        _require_hex(digest, f"model.files[{name}]")
    engine = _need_mapping(document["engine"], "engine")
    for key in ("tool_version", "engines"):
        if key not in engine:
            raise _bad_expected(f"engine.{key} is missing")
    for name, digest in _need_mapping(document["engine_sources"], "engine_sources").items():
        _safe_relative(name, "an engine_sources path")
        _require_hex(digest, f"engine_sources[{name}]")
    _need_mapping(document["reference_environment"], "reference_environment")
    _need_mapping(document["example"], "example")
    outputs = document["outputs"]
    if not isinstance(outputs, list):
        raise _bad_expected("outputs is not a list")
    paths: list[str] = []
    for index, entry in enumerate(outputs):
        item = _need_mapping(entry, f"outputs[{index}]")
        paths.append(_safe_relative(item.get("path"), f"outputs[{index}].path"))
        _require_hex(item.get("sha256"), f"outputs[{index}].sha256")
    if sorted(paths) != sorted(OUTPUT_FILES):
        raise _bad_expected(f"outputs must list exactly: {', '.join(OUTPUT_FILES)}")
    return document


# --- Run folder -------------------------------------------------------------


def _not_a_run(message: str) -> UsageError:
    return UsageError(
        message,
        fix="Give the folder that `eureka run` wrote. It holds manifest.json and the output files.",
    )


def read_run_folder(run_folder: Path) -> dict[str, Any]:
    """Check that a folder has the shape of a finished run and return its manifest.

    Args:
        run_folder: The folder to read.

    Returns:
        The parsed `manifest.json`.

    Raises:
        UsageError: The folder is missing, or a file is missing, a link leaves the folder,
            or the manifest has another schema.
    """
    folder = Path(run_folder)
    if not folder.is_dir():
        raise _not_a_run(f"The run folder was not found: {folder.name}")
    root = folder.resolve()
    for relative in (MANIFEST_NAME, *OUTPUT_FILES):
        candidate = folder / relative
        if not candidate.exists():
            raise _not_a_run(f"The run folder has no {relative}")
        resolved = candidate.resolve()
        if not resolved.is_file():
            raise _not_a_run(f"{relative} in the run folder is not a regular file")
        if not resolved.is_relative_to(root):
            raise _not_a_run(f"{relative} in the run folder is a link that leaves the folder")
    manifest = _read_json(folder / MANIFEST_NAME, "manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise _not_a_run(f"The manifest does not have the schema {MANIFEST_SCHEMA}")
    return manifest


def _section(manifest: Mapping[str, Any], *path: str) -> Any:
    value: Any = manifest
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _file_pairs(manifest: Mapping[str, Any]) -> list[tuple[Any, Any]] | None:
    files = _section(manifest, "inputs", "files")
    if not isinstance(files, list):
        return None
    pairs: list[tuple[Any, Any]] = []
    for entry in files:
        if not isinstance(entry, Mapping):
            return None
        pairs.append((entry.get("path"), entry.get("sha256")))
    return pairs


def _check_inputs(manifest: Mapping[str, Any], expected: Mapping[str, Any]) -> Check:
    cid, name = CHECK_INPUTS
    exp_inputs = expected["inputs"]
    exp_files = [(item["path"], item["sha256"]) for item in exp_inputs["files"]]
    problems: list[str] = []
    if _file_pairs(manifest) != exp_files:
        problems.append("the input files or their hashes differ")
    if _section(manifest, "inputs", "folder_digest") != exp_inputs["folder_digest"]:
        problems.append("the input folder digest differs")
    if _section(manifest, "inputs", "mapping_sha256") != exp_inputs["mapping_sha256"]:
        problems.append("the mapping hash differs")
    if _section(manifest, "corpus", "corpus_digest") != expected["corpus"]["corpus_digest"]:
        problems.append("the corpus digest differs")
    if _section(manifest, "corpus", "records_used") != expected["corpus"]["records_used"]:
        problems.append("the number of records used differs")
    if problems:
        folder = expected["example"].get("input_folder", "the example input folder")
        return Check(
            cid,
            name,
            STATUS_FAIL,
            "; ".join(problems),
            f"Run Eureka on the unchanged example input folder {folder}.",
        )
    count = len(exp_files)
    return Check(
        cid,
        name,
        STATUS_PASS,
        f"{count} input files, the folder digest and the corpus digest agree",
    )


def _check_settings(manifest: Mapping[str, Any], expected: Mapping[str, Any]) -> Check:
    cid, name = CHECK_SETTINGS
    problems = []
    if _section(manifest, "settings") != expected["settings"]:
        problems.append("the settings differ")
    if _section(manifest, "seeds") != expected["seeds"]:
        problems.append("the seeds differ")
    if problems:
        return Check(
            cid,
            name,
            STATUS_FAIL,
            "; ".join(problems),
            f"Run with the default settings and the command: {expected['command']}",
        )
    return Check(cid, name, STATUS_PASS, "the settings and the seeds agree")


def _check_model(manifest: Mapping[str, Any], expected: Mapping[str, Any]) -> Check:
    cid, name = CHECK_MODEL
    exp = expected["model"]
    problems = []
    if _section(manifest, "model", "name") != exp["name"]:
        problems.append("the model name differs")
    if _section(manifest, "model", "snapshot") != exp["snapshot"]:
        problems.append("the model snapshot differs")
    if _section(manifest, "model", "files") != exp["files"]:
        problems.append("the model file hashes differ")
    if problems:
        return Check(
            cid,
            name,
            STATUS_FAIL,
            "; ".join(problems),
            f"The output cannot match with another model. Use {exp['name']} at snapshot "
            f"{exp['snapshot']}.",
        )
    return Check(cid, name, STATUS_PASS, f"the model {exp['name']} and its file hashes agree")


def _check_engine(manifest: Mapping[str, Any], expected: Mapping[str, Any]) -> Check:
    cid, name = CHECK_ENGINE
    exp = expected["engine"]
    problems = []
    if _section(manifest, "tool", "version") != exp["tool_version"]:
        problems.append("the Eureka version differs")
    if _section(manifest, "tool", "engines") != exp["engines"]:
        problems.append("the engine record differs")
    if problems:
        return Check(
            cid,
            name,
            STATUS_FAIL,
            "; ".join(problems),
            f"Use Eureka version {exp['tool_version']} with the same engine files.",
        )
    return Check(
        cid, name, STATUS_PASS, f"Eureka version {exp['tool_version']} and the engine record agree"
    )


def _manifest_output_hashes(manifest: Mapping[str, Any]) -> dict[str, Any]:
    entries = _section(manifest, "outputs")
    found: dict[str, Any] = {}
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, Mapping):
                found[str(entry.get("path"))] = entry.get("sha256")
    return found


def _check_outputs(
    run_folder: Path, manifest: Mapping[str, Any], expected: Mapping[str, Any]
) -> Check:
    cid, name = CHECK_OUTPUTS
    listed = _manifest_output_hashes(manifest)
    failures: list[str] = []
    for item in sorted(expected["outputs"], key=lambda entry: entry["path"]):
        path = item["path"]
        found = sha256_file(run_folder / path)
        if found != item["sha256"]:
            line = f"{path}: expected {item['sha256']}, found {found}"
            if listed.get(path) != found:
                line += (
                    " (the file also differs from the hash in manifest.json: changed after the run)"
                )
            failures.append(line)
        elif listed.get(path) != found:
            failures.append(
                f"{path}: found {found}, but manifest.json lists {listed.get(path)}: "
                "changed after the run"
            )
    if failures:
        return Check(
            cid,
            name,
            STATUS_FAIL,
            " | ".join(failures),
            "Make a fresh run with the command and the unchanged input. "
            "Do not edit the output files.",
        )
    return Check(
        cid, name, STATUS_PASS, f"all {len(OUTPUT_FILES)} output files have the expected sha256"
    )


# --- Runs that are not CPU-exact ----------------------------------------------


def ranking_overlap(run_ids: Sequence[str], reference_ids: Sequence[str]) -> float:
    """Return the share of reference pair ids that the run also lists.

    Order and repeated ids do not count. An empty reference gives 1.0 for an empty run and
    0.0 for a run that lists pairs.

    Args:
        run_ids: The pair ids of the run, in file order.
        reference_ids: The pair ids of the reference run.

    Returns:
        A number from 0.0 to 1.0.
    """
    reference = set(reference_ids)
    if not reference:
        return 1.0 if not set(run_ids) else 0.0
    return len(reference & set(run_ids)) / len(reference)


def _determinism_class(manifest: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Return `(class, None)`, or `(None, problem)` when the class cannot be trusted."""
    if ENCODER_KEY not in manifest:
        return DETERMINISM_CPU_EXACT, None
    block = manifest[ENCODER_KEY]
    name = block.get("determinism_class") if isinstance(block, Mapping) else None
    if not isinstance(name, str) or not name:
        return None, (
            "the encoder block of manifest.json cannot be read "
            "(it must be an object with a determinism_class)"
        )
    if name not in (DETERMINISM_CPU_EXACT, DETERMINISM_GPU_APPROX):
        return None, f"unknown determinism class {name!r} in the encoder block of manifest.json"
    return name, None


def _pair_ids(path: Path) -> list[str]:
    document = _read_json(path, "pair file")
    pairs = document.get("pairs") if isinstance(document, Mapping) else None
    if not isinstance(pairs, list):
        raise UsageError(
            f"The pair file has no list of pairs: {path.name}",
            fix="Use the file that Eureka wrote. Do not edit it.",
        )
    ids: list[str] = []
    for entry in pairs:
        pair_id = entry.get("pair_id") if isinstance(entry, Mapping) else None
        if not isinstance(pair_id, str):
            raise UsageError(
                f"A pair in {path.name} has no pair_id",
                fix="Use the file that Eureka wrote. Do not edit it.",
            )
        ids.append(pair_id)
    return ids


def _reference_problem(reference_run: Path | None, expected: Mapping[str, Any]) -> str | None:
    if reference_run is None or not Path(reference_run).is_dir():
        return (
            "the reference run folder was not found, so the ranking cannot be compared "
            "(the reference run ships next to the expected-hash file)"
        )
    root = Path(reference_run).resolve()
    for item in sorted(expected["outputs"], key=lambda entry: entry["path"]):
        candidate = Path(reference_run) / item["path"]
        resolved = candidate.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(root):
            return (
                f"the reference run does not match the expected hashes: {item['path']} is missing"
            )
        if sha256_file(candidate) != item["sha256"]:
            return f"the reference run does not match the expected hashes: {item['path']} differs"
    return None


def _check_outputs_approx(
    run_folder: Path,
    manifest: Mapping[str, Any],
    expected: Mapping[str, Any],
    reference_run: Path | None,
) -> tuple[Check, dict[str, Any] | None]:
    """Check X6 for a run of the class gpu-approx: bytes of the corpus, overlap of the ranking."""
    cid, name = CHECK_OUTPUTS
    fix = "Make a fresh run with the command and the unchanged input. Do not edit the output files."
    listed = _manifest_output_hashes(manifest)
    failures = [
        f"{path}: found {sha256_file(run_folder / path)}, but manifest.json lists "
        f"{listed.get(path)}: changed after the run"
        for path in OUTPUT_FILES
        if listed.get(path) != sha256_file(run_folder / path)
    ]
    if failures:
        return Check(cid, name, STATUS_FAIL, " | ".join(failures), fix), None
    problem = _reference_problem(reference_run, expected)
    if problem is not None:
        return (
            Check(
                cid,
                name,
                STATUS_FAIL,
                problem,
                "Use the folder reference-run that ships next to the expected-hash file, "
                "unchanged.",
            ),
            None,
        )
    corpus = next(item for item in expected["outputs"] if item["path"] == OUTPUT_FILES[0])
    found = sha256_file(run_folder / corpus["path"])
    if found != corpus["sha256"]:
        line = f"{corpus['path']}: expected {corpus['sha256']}, found {found}"
        return Check(cid, name, STATUS_FAIL, line, fix), None
    assert reference_run is not None
    numbers: dict[str, Any] = {}
    parts: list[str] = []
    for file_name in OVERLAP_FILES:
        run_ids = _pair_ids(run_folder / file_name)
        reference_ids = _pair_ids(Path(reference_run) / file_name)
        share = ranking_overlap(run_ids, reference_ids)
        numbers[file_name] = {
            "overlap": share,
            "reference_pairs": len(set(reference_ids)),
            "run_pairs": len(set(run_ids)),
        }
        parts.append(
            f"{file_name} overlap {share:.4f} of {len(set(reference_ids))} reference pairs"
        )
    threshold = example_contracts.GPU_APPROX_MIN_OVERLAP
    summary = "; ".join(parts)
    if threshold is None:
        detail = f"{summary}; {NO_THRESHOLD_TEXT}, so a gpu-approx run is not a match"
        return (
            Check(
                cid,
                name,
                STATUS_FAIL,
                detail,
                "Compare the ranking by hand with the reference run. "
                "A threshold is set after the GPU spike has measured the drift.",
            ),
            numbers,
        )
    low = [file_name for file_name in OVERLAP_FILES if numbers[file_name]["overlap"] < threshold]
    if low:
        detail = f"{summary}; below the threshold {threshold:.4f}: {', '.join(low)}"
        return Check(cid, name, STATUS_FAIL, detail, fix), numbers
    detail = (
        f"corpus/records.jsonl has the expected sha256; {summary}; "
        f"threshold {threshold:.4f} reached"
    )
    return Check(cid, name, STATUS_PASS, detail), numbers


def _encoder_info(manifest: Mapping[str, Any]) -> list[str]:
    block = manifest.get(ENCODER_KEY)
    if not isinstance(block, Mapping):
        return []

    def fingerprint(key: str) -> Any:
        part = block.get(key)
        return part.get("fingerprint") if isinstance(part, Mapping) else None

    return [
        f"INFO encoder: profile {block.get('profile')}, "
        f"unusual-pairs fingerprint {fingerprint('unusual_pairs')}, "
        f"wording-and-meaning fingerprint {fingerprint('wording_and_meaning')}"
    ]


def _holds_label(path: Path) -> bool:
    needle = LABEL.encode("utf-8")
    keep = len(needle) - 1
    tail = b""
    with path.open("rb") as handle:
        while True:
            block = handle.read(_BLOCK_SIZE)
            if not block:
                return False
            window = tail + block
            if needle in window:
                return True
            tail = window[-keep:]


def _check_label(run_folder: Path) -> Check:
    cid, name = CHECK_LABEL
    missing = [path for path in PAIR_FILES if not _holds_label(run_folder / path)]
    if missing:
        return Check(
            cid,
            name,
            STATUS_FAIL,
            f'{", ".join(missing)} lacks the label "{LABEL}"',
            "Make a fresh run. A result file without the label is not a Eureka result.",
        )
    return Check(cid, name, STATUS_PASS, f'the 3 result files hold the label "{LABEL}"')


# --- Environment (INFO only) ------------------------------------------------


def _environment_info(manifest: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    reference = expected["reference_environment"]
    current = _section(manifest, "environment")
    current = current if isinstance(current, Mapping) else {}
    libraries = reference.get("libraries") or {}
    lines = [
        "INFO reference environment: "
        f"{reference.get('platform')}, {reference.get('implementation')} "
        f"{reference.get('python')}, threads requested {reference.get('threads_requested')}, "
        + ", ".join(f"{key} {libraries[key]}" for key in sorted(libraries))
    ]
    for key in ("platform", "implementation", "python"):
        if current.get(key) != reference.get(key):
            lines.append(
                f"INFO environment: {key} is {current.get(key)}, "
                f"the expected file was made with {reference.get(key)}"
            )
    now = current.get("libraries")
    now = now if isinstance(now, Mapping) else {}
    for key in sorted(set(now) | set(libraries)):
        if now.get(key) != libraries.get(key):
            lines.append(
                f"INFO environment: {key} is {now.get(key)}, "
                f"the expected file was made with {libraries.get(key)}"
            )
    return lines


# --- Entry point ------------------------------------------------------------


def check_run(
    run_folder: Path, expected: Mapping[str, Any], *, reference_run: Path | None = None
) -> CheckReport:
    """Compare a finished run folder with the expected hashes.

    A run whose manifest has no `encoder` block, or the class `cpu-exact`, is compared by
    bytes. A run of the class `gpu-approx` is compared with `reference_run` by ranking overlap
    and never matches while `GPU_APPROX_MIN_OVERLAP` is None.

    Args:
        run_folder: The folder that `eureka run` wrote.
        expected: A document from `load_expected`.
        reference_run: The shipped reference run folder, or None.

    Returns:
        A report. The result is `match` only when checks X2 to X7 all pass.

    Raises:
        UsageError: The folder does not have the shape of a finished run.
    """
    folder = Path(run_folder)
    manifest = read_run_folder(folder)
    run_check = Check(
        *CHECK_RUN_FOLDER,
        STATUS_PASS,
        f"manifest.json and {len(OUTPUT_FILES)} output files were found",
    )
    determinism, problem = _determinism_class(manifest)
    overlap: dict[str, Any] | None = None
    if problem is not None:
        outputs = Check(
            *CHECK_OUTPUTS,
            STATUS_FAIL,
            problem,
            "Make a fresh run with a Eureka version that writes a valid encoder block.",
        )
    elif determinism == DETERMINISM_GPU_APPROX:
        outputs, overlap = _check_outputs_approx(folder, manifest, expected, reference_run)
    else:
        outputs = _check_outputs(folder, manifest, expected)
    checks = (
        run_check,
        _check_inputs(manifest, expected),
        _check_settings(manifest, expected),
        _check_model(manifest, expected),
        _check_engine(manifest, expected),
        outputs,
        _check_label(folder),
    )
    failed = {item.id for item in checks if item.status == STATUS_FAIL}
    result = RESULT_NO_MATCH_ID if failed else RESULT_MATCH_ID
    info = _environment_info(manifest, expected)
    if problem is not None:
        note = None
    elif determinism == DETERMINISM_GPU_APPROX:
        note = GPU_APPROX_NOTE
        info.extend(_encoder_info(manifest))
    else:
        note = NOT_REPRODUCED_TEXT if failed == {CHECK_OUTPUTS[0]} else None
    return CheckReport(
        result=result,
        checks=checks,
        info=tuple(info),
        note=note,
        determinism_class=DETERMINISM_GPU_APPROX if determinism == DETERMINISM_GPU_APPROX else None,
        ranking_overlap=overlap,
    )
