"""Lightweight seed CLI flags and exit-code mapping.

Only the standard library and light Eureka modules load at import time. The builder loads
inside `seed_command`, so CLI help never imports it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..run.command import ENGINES_TEXT, EXIT_CODES_TEXT
from ..run.console import Console
from ..run.contracts import EXIT_INTERRUPTED, LABEL, EurekaError, UsageError
from .contracts import DEFAULT_SEED_OUT_PREFIX, PAIR_ID_PATTERN

_NOTES = (
    "The command reads a finished run folder and never writes into it. It makes no network "
    "call and calls no model: the seed is written offline, and the same run and the same "
    "pair give the same bytes.\n\n"
    "Files written: seed.json and an evidence folder with one Markdown file for each "
    "record. The folder is not a room. MindrianOS opens it through its own birth gate. "
    "Eureka writes no room, no registry entry and no database.\n\n"
    "An earlier Eureka seed in --out is replaced. Any other non-empty folder is refused. "
    f'Every result in the seed is "{LABEL}". The seed needs a run that was '
    "made with a mapping file that holds room_sections."
)


def register_seed(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add seed with the shared engine descriptions, flags and exit-code help."""
    parser = subparsers.add_parser(
        "seed",
        help="write a room seed folder from a finished Eureka run",
        allow_abbrev=False,
        description=ENGINES_TEXT + "\n\n" + _NOTES,
        epilog=EXIT_CODES_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("run_dir", help="a finished Eureka run folder, read only")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--pair", metavar="PAIR_ID", help="write the seed of one pair (the id shows in the hub)"
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        default=None,
        help=f"output folder (default: ./{DEFAULT_SEED_OUT_PREFIX}-<pair id>)",
    )
    parser.add_argument("--json", action="store_true", help="print the summary as one JSON object")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="hide progress lines (warnings stay)"
    )
    parser.add_argument("--no-color", action="store_true", help="never use color")
    parser.add_argument(
        "--debug", action="store_true", help="show the traceback of an unexpected error"
    )


def seed_command(args: argparse.Namespace) -> int:
    """Write the seed and return 0, failure 1, usage 2, or interrupted 130."""
    console = Console(quiet=args.quiet, no_color=args.no_color)
    try:
        from ..run.output import canonical_json
        from . import builder
        from .source import load_source

        run_dir = Path(args.run_dir).expanduser().resolve()
        if not PAIR_ID_PATTERN.fullmatch(args.pair):
            raise UsageError(
                "The pair id has the wrong form",
                fix="Check the pair id. It looks like pair- and 20 hex characters.",
            )
        console.stage("Read the finished run")
        source = load_source(run_dir)
        seed = builder.build_pair_seed(source, args.pair)
        out_dir = Path(args.out or seed.default_out_name).expanduser().resolve()
        console.stage("Write the seed folder")
        summary = builder.write_seed(seed, run_dir, out_dir)
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
        if args.debug:
            raise
        console.error(f"unexpected error ({type(error).__name__}): {error}")
        return 1
