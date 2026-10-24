"""The command layer of `eureka run` and `eureka doctor`.

This module defines the flags, turns them into a `RunRequest`, runs the pipeline and maps
every outcome to an exit code: 0 success, 1 failure, 2 usage error, 130 interrupted.
Progress, warnings and errors go to stderr. Results go to stdout.

Importing this module loads only the standard library and light Eureka modules. The
pipeline, the mapping loader and the doctor load inside functions, so `eureka --help`
never imports numpy or torch.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ..limits import HARD_MAX_ARTIFACTS, MAX_ARTIFACTS, MAX_TOP_K
from .console import Console
from .contracts import (
    EXIT_INTERRUPTED,
    LABEL,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    EurekaError,
    UsageError,
)

if TYPE_CHECKING:
    from .mapping import MappingConfig
    from .pipeline import RunRequest

DEFAULT_OUT = "eureka-run"
_MIN_ARTIFACTS = 2

ENGINES_TEXT = (
    f"Eureka ranks pairs of records with two engines: {UNUSUAL_PAIRS_NAME} "
    f"and {WORDING_AND_MEANING_NAME}. "
    f'Every result is "{LABEL}": a lead for human review, never a finding.'
)

EXIT_CODES_TEXT = (
    "Exit codes:\n"
    "  0    success\n"
    "  1    failure (for example: no local model, bad input file, engine error)\n"
    "  2    usage error (a wrong flag or setting)\n"
    "  130  interrupted (Ctrl+C); nothing is written"
)

_RUN_NOTES = (
    "The run is offline and non-interactive. It never asks a question and makes no network "
    "call. It reads the folder and never writes into it. It writes the output folder in "
    "one step, so an interrupted run leaves no partial result. An earlier Eureka run in "
    "--out is replaced. Any other non-empty folder is refused.\n\n"
    "Files written: unusual-pairs.json, wording-and-meaning-pairs.json, ranked-pairs.md, "
    "corpus/records.jsonl, manifest.json and run-info.json.\n\n"
    "A CSV file needs a column mapping: give a --mapping file or the column flags. "
    "A CSV id column made only of non-ASCII letters sanitizes to underscores and collides; "
    "use a different id column or omit it to get hash ids.\n\n"
)


def _bounded(text: str, low: int, high: int, flag: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{flag} must be a whole number from {low} to {high}. You gave {text!r}."
        ) from None
    if not low <= value <= high:
        raise argparse.ArgumentTypeError(
            f"{flag} must be from {low} to {high}. You gave {value}."
        )
    return value


def _top_k(text: str) -> int:
    return _bounded(text, 1, MAX_TOP_K, "--top-k")


def _max_artifacts(text: str) -> int:
    return _bounded(text, _MIN_ARTIFACTS, HARD_MAX_ARTIFACTS, "--max-artifacts")


def _threads(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--threads must be a whole number of 1 or more. You gave {text!r}."
        ) from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"--threads must be 1 or more. You gave {value}.")
    return value


def register_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the `run` and `doctor` subcommands.

    Args:
        subparsers: The subparser group of the top-level parser.
    """
    raw = argparse.RawDescriptionHelpFormatter
    run = subparsers.add_parser(
        "run",
        help="rank unusual pairs in a folder of Markdown and CSV files",
        description=ENGINES_TEXT + "\n\n" + _RUN_NOTES.rstrip("\n"),
        epilog=EXIT_CODES_TEXT,
        formatter_class=raw,
    )
    run.add_argument("folder", help="folder with .md and .csv files (read only)")
    run.add_argument(
        "--out",
        default=DEFAULT_OUT,
        metavar="DIR",
        help=f"output folder (default: ./{DEFAULT_OUT})",
    )
    run.add_argument("--mapping", metavar="FILE", help="JSON file that maps CSV columns")
    run.add_argument(
        "--id-column",
        metavar="C",
        help=(
            "CSV column for record ids. An id column made only of non-ASCII letters sanitizes "
            "to underscores and collides; use a different id column or omit it to get hash ids"
        ),
    )
    run.add_argument("--title-column", metavar="C", help="CSV column for record titles")
    run.add_argument(
        "--text-column",
        action="append",
        metavar="C",
        help="CSV column that holds record text (repeat the flag for more than one)",
    )
    run.add_argument("--source-column", metavar="C", help="CSV column for the source reference")
    run.add_argument("--delimiter", metavar="D", help="one-character CSV delimiter")
    run.add_argument(
        "--model-path",
        type=Path,
        metavar="P",
        help="folder of the local meaning model (default: search the usual places)",
    )
    run.add_argument(
        "--max-artifacts",
        type=_max_artifacts,
        default=MAX_ARTIFACTS,
        metavar="N",
        help=f"most records to rank, from {_MIN_ARTIFACTS} to {HARD_MAX_ARTIFACTS} "
        f"(default: {MAX_ARTIFACTS})",
    )
    run.add_argument(
        "--top-k",
        type=_top_k,
        default=MAX_TOP_K,
        metavar="N",
        help=f"most pairs for each engine, from 1 to {MAX_TOP_K} (default: {MAX_TOP_K})",
    )
    run.add_argument("--objective", default="", metavar="TEXT", help="free text kept in the result")
    run.add_argument(
        "--threads", type=_threads, metavar="N", help="thread count for the numeric libraries"
    )
    run.add_argument(
        "--no-cache", action="store_true", help="use a throwaway embedding cache for this run"
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="read and check the input; load no model and write nothing",
    )
    run.add_argument("--json", action="store_true", help="print the summary as one JSON object")
    run.add_argument(
        "-q", "--quiet", action="store_true", help="hide progress lines (warnings stay)"
    )
    run.add_argument("--no-color", action="store_true", help="never use color")
    run.add_argument(
        "--debug", action="store_true", help="show the traceback of an unexpected error"
    )

    doctor = subparsers.add_parser(
        "doctor",
        help="check that this machine can run Eureka",
        description=(
            "Check Python, uv, the encoder libraries, the local model, the cache and data "
            "folders and the offline settings. Each failed check prints the exact fix. "
            "Nothing is created, changed or downloaded.\n\n"
            + ENGINES_TEXT
        ),
        epilog=EXIT_CODES_TEXT,
        formatter_class=raw,
    )
    doctor.add_argument("--json", action="store_true", help="print the report as JSON")
    doctor.add_argument(
        "--load-model",
        action="store_true",
        help="also load the model and encode one sentence (about 16 seconds)",
    )
    doctor.add_argument(
        "--model-path", type=Path, metavar="P", help="folder of the local meaning model"
    )
    doctor.add_argument("--no-color", action="store_true", help="accepted; doctor never uses color")


def build_run_request(args: argparse.Namespace, argv: Sequence[str] = ()) -> RunRequest:
    """Turn parsed flags into a `RunRequest`.

    Args:
        args: The parsed command line.
        argv: The command line words, kept in run-info.json.

    Returns:
        The request, with absolute input and output paths.

    Raises:
        UsageError: Both --mapping and a column flag were given, or a flag value is wrong.
    """
    from .mapping import load_mapping_file, mapping_from_flags
    from .pipeline import RunRequest

    flags_set = any(
        value
        for value in (
            args.id_column,
            args.title_column,
            args.text_column,
            args.source_column,
            args.delimiter,
        )
    )
    if args.mapping and flags_set:
        raise UsageError(
            "Use either --mapping or the column flags, not both.",
            fix="Remove --mapping, or remove the column flags and --delimiter.",
        )
    mapping: MappingConfig | None
    if args.mapping:
        mapping = load_mapping_file(Path(args.mapping).expanduser())
    else:
        mapping = mapping_from_flags(
            id_column=args.id_column,
            title_column=args.title_column,
            text_columns=args.text_column or [],
            source_column=args.source_column,
            delimiter=args.delimiter,
        )
    return RunRequest(
        input_dir=Path(args.folder).expanduser().resolve(),
        out_dir=Path(args.out).expanduser().resolve(),
        mapping=mapping,
        model_path=args.model_path.expanduser() if args.model_path else None,
        max_artifacts=args.max_artifacts,
        top_k=args.top_k,
        objective=args.objective,
        threads=args.threads,
        use_cache=not args.no_cache,
        dry_run=args.dry_run,
        argv=tuple(argv),
    )


def run_command(args: argparse.Namespace, argv: Sequence[str] | None = None) -> int:
    """Run `eureka run` and return the exit code.

    Args:
        args: The parsed command line.
        argv: The raw command line words. The default is `sys.argv[1:]`.

    Returns:
        0 on success, 1 on failure, 2 on a usage error, 130 when interrupted.
    """
    console = Console(quiet=args.quiet, no_color=args.no_color)
    words = tuple(sys.argv[1:] if argv is None else argv)
    try:
        from .output import canonical_json
        from .pipeline import run_pipeline

        summary = run_pipeline(build_run_request(args, words), console)
        if args.json:
            console.out(canonical_json(summary.to_json_dict()).decode("utf-8").rstrip("\n"))
        else:
            console.out(summary.lines())
        return 0
    except EurekaError as error:
        console.error(error.message, error.fix)
        return error.exit_code
    except KeyboardInterrupt:
        console.error("Interrupted. No output was written.")
        return EXIT_INTERRUPTED
    except Exception as error:
        # CLI boundary: the user gets one plain line, not a traceback. --debug re-raises.
        if args.debug:
            raise
        console.error(f"unexpected error ({type(error).__name__}): {error}")
        return 1


def doctor_cli(args: argparse.Namespace) -> int:
    """Run `eureka doctor` and return the exit code.

    Args:
        args: The parsed command line.

    Returns:
        0 when no check failed, 1 when a check failed, 130 when interrupted.
    """
    from .. import doctor

    try:
        return doctor.doctor_command(
            json_output=args.json,
            load_model=args.load_model,
            model_path=args.model_path,
            out=None,
        )
    except KeyboardInterrupt:
        Console(no_color=True).error("Interrupted.")
        return EXIT_INTERRUPTED
