"""Lightweight seed CLI flags and exit-code mapping.

Only the standard library and light Eureka modules load at import time. The builder loads
inside `seed_command`, so CLI help never imports it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..run.command import ENGINES_TEXT, EXIT_CODES_TEXT, _bounded
from ..run.console import Console
from ..run.contracts import EXIT_INTERRUPTED, LABEL, EurekaError, UsageError
from .contracts import DEFAULT_SEED_OUT_PREFIX, MIN_DEGREE_DEFAULT, PAIR_ID_PATTERN

_MAX_MIN_DEGREE = 1000
_MAX_LIMIT = 10000
LIMIT_DEFAULT = 25

_NOTES = (
    "The command reads a finished run folder and never writes into it. It makes no network "
    "call and calls no model: the seed is written offline, and the same run and the same "
    "pair give the same bytes.\n\n"
    "Files written: seed.json and an evidence folder with one Markdown file for each "
    "record. The folder is not a room. MindrianOS opens it through its own birth gate. "
    "Eureka writes no room, no registry entry and no database.\n\n"
    "An earlier Eureka seed in --out is replaced. Any other non-empty folder is refused. "
    f'Every result in the seed is "{LABEL}". The seed needs a run that was '
    "made with a mapping file that holds room_sections.\n\n"
    "--pair writes the seed of one pair. --cluster writes the seed of one record and every "
    "record that is paired with it. --list prints the pairs and the records to start from, "
    "as counts and classes, and writes nothing. The list does not rank rooms by value."
)


def _min_degree(text: str) -> int:
    return _bounded(text, 1, _MAX_MIN_DEGREE, "--min-degree")


def _limit(text: str) -> int:
    return _bounded(text, 0, _MAX_LIMIT, "--limit")


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
    selector.add_argument(
        "--cluster",
        metavar="RECORD_ID",
        help="write the seed of one record and the records paired with it (one room, one "
        "bank entry for each neighbour)",
    )
    selector.add_argument(
        "--list",
        action="store_true",
        help="print the pairs and records to start from, as counts and classes; nothing is written",
    )
    parser.add_argument(
        "--min-degree",
        metavar="N",
        type=_min_degree,
        default=None,
        help=f"with --cluster or --list: the least number of pairs a record must sit in "
        f"(1 to {_MAX_MIN_DEGREE}, default {MIN_DEGREE_DEFAULT})",
    )
    parser.add_argument(
        "--limit",
        metavar="N",
        type=_limit,
        default=LIMIT_DEFAULT,
        help=f"with --list: the most rows to show in each group (0 to {_MAX_LIMIT}, "
        f"default {LIMIT_DEFAULT}, 0 shows all)",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        default=None,
        help=f"output folder (default: ./{DEFAULT_SEED_OUT_PREFIX}-<pair id>, or "
        f"./{DEFAULT_SEED_OUT_PREFIX}-cluster-<12 hex> for --cluster)",
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
        from .candidates import build_candidates, render_text, to_json_dict
        from .graph import build_pair_graph
        from .source import load_source

        run_dir = Path(args.run_dir).expanduser().resolve()
        if args.list and args.out is not None:
            raise UsageError(
                "--out is not used with --list",
                fix="Remove --out. The list is printed and nothing is written.",
            )
        if args.pair is not None and args.min_degree is not None:
            raise UsageError(
                "--min-degree is used with --cluster and --list only",
                fix="Remove --min-degree.",
            )
        min_degree = MIN_DEGREE_DEFAULT if args.min_degree is None else args.min_degree
        if args.pair is not None and not PAIR_ID_PATTERN.fullmatch(args.pair):
            raise UsageError(
                "The pair id has the wrong form",
                fix="Check the pair id. It looks like pair- and 20 hex characters.",
            )
        console.stage("Read the finished run")
        source = load_source(run_dir)
        if args.list:
            candidates = build_candidates(build_pair_graph(source.run), min_degree)
            if args.json:
                document = to_json_dict(candidates, args.limit)
                console.out(canonical_json(document).decode("utf-8").rstrip("\n"))
            else:
                console.out(render_text(candidates, args.limit))
            return 0
        from . import builder

        if args.cluster is not None:
            graph = build_pair_graph(source.run)
            seed = builder.build_cluster_seed(source, graph, args.cluster, min_degree=min_degree)
        else:
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
