"""Build the expected-hash file of the public example from a real run folder.

The maker refuses a folder whose files differ from its manifest, a folder with dropped
records, a folder with a cap hit and a folder with another record count. It makes no network
call, loads no model and imports no numpy.

Import rule: the standard library and `..run.contracts`, `..run.console`, `..run.manifest`,
`..run.output`, `.check`, `.contracts`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..run.console import Console
from ..run.contracts import LABEL, EurekaError, RunError, UsageError, sha256_bytes
from ..run.manifest import sha256_file
from ..run.output import canonical_json
from .check import read_run_folder
from .contracts import (
    ENGINE_SOURCE_FILES,
    EXAMPLE_COMMAND,
    EXAMPLE_ID,
    EXAMPLE_INPUT,
    EXAMPLE_LICENSE,
    EXAMPLE_LICENSE_RECORD,
    EXAMPLE_MODEL_NOTE,
    EXAMPLE_RECORDS,
    EXPECTED_SCHEMA,
    OUTPUT_FILES,
    PAIR_FILES,
)


def _refuse(message: str, fix: str) -> RunError:
    return RunError(message, fix=fix)


def _section(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    value = manifest.get(key)
    if not isinstance(value, dict):
        raise _refuse(f"The manifest has no {key} section", "Use a run folder made by eureka run.")
    return value


def build_expected(run_folder: Path, *, repo_root: Path, records: int) -> dict[str, Any]:
    """Build the expected-hash document from a clean, real run folder.

    Args:
        run_folder: The folder that `eureka run` wrote.
        repo_root: The Eureka source folder, used to hash the engine source files.
        records: The number of records the example input must give.

    Returns:
        The document to write with `canonical_json`.

    Raises:
        UsageError: The folder is not a run folder, or an engine source file is missing.
        RunError: The run is not clean: a file differs from its manifest, records were
            dropped, a cap was hit, or the record count is wrong.
    """
    folder = Path(run_folder)
    manifest = read_run_folder(folder)
    corpus = _section(manifest, "corpus")
    if corpus.get("dropped"):
        raise _refuse(
            "The run dropped records", "Make the run again on an input where no record is dropped."
        )
    if corpus.get("caps_hit"):
        raise _refuse("The run hit a cap", "Make the run again with settings where no cap is hit.")
    if corpus.get("records_used") != records:
        raise _refuse(
            f"The run used {corpus.get('records_used')} records, not {records}",
            "Make the run again on the example input folder.",
        )
    listed: dict[str, dict[str, Any]] = {}
    entries = manifest.get("outputs")
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                listed[str(entry.get("path"))] = entry
    outputs: list[dict[str, Any]] = []
    for path in OUTPUT_FILES:
        entry = listed.get(path)
        digest = sha256_file(folder / path)
        if entry is None or entry.get("sha256") != digest:
            raise _refuse(
                f"{path} differs from the hash in manifest.json",
                "Do not edit a run folder. Make a fresh run.",
            )
        item: dict[str, Any] = {
            "path": path,
            "sha256": digest,
            "bytes": (folder / path).stat().st_size,
        }
        if path in PAIR_FILES and "pairs" in entry:
            item["pairs"] = entry["pairs"]
        outputs.append(item)
    inputs = _section(manifest, "inputs")
    tool = _section(manifest, "tool")
    model = _section(manifest, "model")
    environment = _section(manifest, "environment")
    engine_sources: dict[str, str] = {}
    for relative in ENGINE_SOURCE_FILES:
        source = Path(repo_root) / relative
        if not source.is_file():
            raise UsageError(
                f"The engine source file was not found: {relative}",
                fix="Give --repo-root with the Eureka source folder.",
            )
        engine_sources[relative] = sha256_file(source)
    return {
        "schema_version": EXPECTED_SCHEMA,
        "label": LABEL,
        "example": {
            "id": EXAMPLE_ID,
            "input_folder": EXAMPLE_INPUT,
            "license_record": EXAMPLE_LICENSE_RECORD,
            "license": EXAMPLE_LICENSE,
            "records": records,
            "model_note": EXAMPLE_MODEL_NOTE,
        },
        "command": EXAMPLE_COMMAND,
        "inputs": {
            "files": [
                {"path": entry["path"], "sha256": entry["sha256"]} for entry in inputs["files"]
            ],
            "folder_digest": inputs["folder_digest"],
            "mapping_sha256": inputs.get("mapping_sha256"),
        },
        "corpus": {
            "corpus_digest": corpus["corpus_digest"],
            "records_used": corpus["records_used"],
        },
        "model": {
            "name": model["name"],
            "snapshot": model["snapshot"],
            "files": model["files"],
        },
        "settings": manifest["settings"],
        "seeds": manifest["seeds"],
        "engine": {"tool_version": tool["version"], "engines": tool["engines"]},
        "engine_sources": engine_sources,
        "outputs": outputs,
        "reference_environment": {
            key: environment.get(key)
            for key in ("platform", "python", "implementation", "libraries", "threads_requested")
        },
    }


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    """Write the expected-hash file. Return 0, failure 1 or usage 2."""
    parser = argparse.ArgumentParser(
        prog="make-example-hashes",
        description="Build the expected-hash file of the public example from a finished run "
        "folder. The command makes no network call and loads no model. "
        f'Every result is "{LABEL}".',
    )
    parser.add_argument("run_folder", metavar="RUN_FOLDER", help="a finished eureka run folder")
    parser.add_argument("--out", metavar="FILE", required=True, help="the expected-hash file")
    parser.add_argument(
        "--repo-root",
        metavar="DIR",
        default=None,
        help="the Eureka source folder (default: the folder of this package)",
    )
    parser.add_argument(
        "--records",
        metavar="N",
        type=int,
        default=EXAMPLE_RECORDS,
        help=f"the record count the run must have (default {EXAMPLE_RECORDS})",
    )
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    console = Console()
    try:
        run_folder = Path(args.run_folder).expanduser().resolve()
        out = Path(args.out).expanduser().resolve()
        if out == run_folder or run_folder in out.parents:
            raise UsageError(
                "The output file is inside the run folder",
                fix="Give an --out path outside the run folder.",
            )
        repo_root = (
            Path(args.repo_root).expanduser().resolve() if args.repo_root else _default_repo_root()
        )
        document = build_expected(run_folder, repo_root=repo_root, records=args.records)
        data = canonical_json(document, digits=None)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        console.out(f"{args.out} {sha256_bytes(data)}")
        return 0
    except EurekaError as error:
        console.error(error.message, error.fix)
        return error.exit_code
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
