"""Lightweight `eureka check-example` flags and exit-code mapping.

Only the standard library and light Eureka modules load at import time. The checker loads
inside `example_command`, so CLI help never imports it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..run.command import ENGINES_TEXT
from ..run.console import Console
from ..run.contracts import EXIT_INTERRUPTED, LABEL, EurekaError, UsageError
from .contracts import EXAMPLE_DIR, EXPECTED_NAME, REFERENCE_RUN_NAME

REPO_ROOT = Path(__file__).resolve().parents[3]

_EXIT_TEXT = (
    "Exit codes:\n"
    "  0    match: the run is identical to the shipped expected hashes\n"
    "  1    no match: at least one check failed\n"
    "  2    usage error (a wrong folder or a wrong expected-hash file)\n"
    "  130  interrupted (Ctrl+C); nothing is written"
)

_NOTES = (
    "The command compares a finished run folder with the shipped expected hashes. It prints "
    "one PASS or FAIL line for each of 7 checks and a final MATCH or NO MATCH line. The rule "
    "is exact: one changed byte in an output file fails the check. Differences in platform, "
    "Python or library versions show as INFO lines and never change the result. A run whose "
    "manifest says its encoder setup is not exact (class gpu-approx) is compared with the "
    "shipped reference run by ranking overlap and not by bytes.\n\n"
    "The command reads the folder and never writes into it. It makes no network call and "
    "loads no model. "
    f'Every result is "{LABEL}".'
)


def register_example(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add check-example with the shared engine description and exit-code help."""
    parser = subparsers.add_parser(
        "check-example",
        help="compare a finished run folder with the shipped expected hashes",
        allow_abbrev=False,
        description=ENGINES_TEXT + "\n\n" + _NOTES,
        epilog=_EXIT_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("run_folder", help="a finished Eureka run folder, read only")
    parser.add_argument(
        "--expected",
        metavar="FILE",
        default=None,
        help=f"the expected-hash file (default: {EXAMPLE_DIR}/{EXPECTED_NAME} under the working "
        "folder, then under the Eureka source folder)",
    )
    parser.add_argument("--json", action="store_true", help="print the report as one JSON object")
    parser.add_argument("--no-color", action="store_true", help="never use color")


def _find_expected(given: str | None) -> Path:
    if given is not None:
        return Path(given).expanduser()
    for base in (Path.cwd(), REPO_ROOT):
        candidate = base / EXAMPLE_DIR / EXPECTED_NAME
        if candidate.is_file():
            return candidate
    raise UsageError(
        "No expected-hash file was found.",
        fix="Give --expected FILE, or run the command from the Eureka source folder.",
    )


def example_command(args: argparse.Namespace) -> int:
    """Check the run and return 0 for a match, 1 for no match, 2 for usage, 130 if interrupted."""
    console = Console(no_color=args.no_color)
    try:
        from ..run.output import canonical_json
        from .check import check_run, load_expected

        expected_path = _find_expected(args.expected)
        expected = load_expected(expected_path)
        reference = expected_path.parent / REFERENCE_RUN_NAME
        report = check_run(
            Path(args.run_folder).expanduser(),
            expected,
            reference_run=reference if reference.is_dir() else None,
        )
        if args.json:
            console.out(canonical_json(report.to_json_dict()).decode("utf-8").rstrip("\n"))
        else:
            console.out(report.to_text())
        return 0 if report.result == "match" else 1
    except EurekaError as error:
        console.error(error.message, error.fix)
        return error.exit_code
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
