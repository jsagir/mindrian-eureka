"""Lightweight hub CLI flags and exit-code mapping.

Only the standard library and light Eureka modules load at import time. The writer
loads inside hub_command so CLI help never imports a model or numeric library.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from ..run.command import ENGINES_TEXT, EXIT_CODES_TEXT
from ..run.console import Console
from ..run.contracts import EXIT_INTERRUPTED, EurekaError, UsageError
from .contracts import DEFAULT_HUB_OUT

_NOTES = (
    "The hub reads a finished run folder, never writes into it or into the source folder, "
    "and makes no network call. The page runs from local files and sends nothing over "
    "the internet. An earlier Eureka hub in --out is replaced. Any other non-empty "
    "folder is refused.\n\nFiles written: hub.html, hub-data.js, hub-copy.js, "
    "hub-manifest.json, the style and script files, and the assets folder.\n\n"
    "The optional password gate protects the file at rest. It does not protect a computer "
    "that already has the passphrase, or the data after unlock."
)


def register_hub(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add hub with the shared engine descriptions, flags and exit-code help."""
    parser = subparsers.add_parser(
        "hub", help="write a local hub page from a finished Eureka run", allow_abbrev=False,
        description=ENGINES_TEXT + "\n\n" + _NOTES,
        epilog=EXIT_CODES_TEXT, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("run_dir", help="a finished Eureka run folder, read only")
    parser.add_argument(
        "--out", metavar="DIR", default=DEFAULT_HUB_OUT,
        help=f"output folder (default: ./{DEFAULT_HUB_OUT})",
    )
    parser.add_argument(
        "--source-dir", metavar="DIR",
        help="folder with the original source files; the page then links each record to its file",
    )
    parser.add_argument(
        "--password-env", metavar="NAME",
        help="name of an environment variable that holds a passphrase; "
             "the page data is then stored encrypted",
    )
    parser.add_argument("--json", action="store_true", help="print the summary as one JSON object")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="hide progress lines (warnings stay)"
    )
    parser.add_argument("--no-color", action="store_true", help="never use color")
    parser.add_argument(
        "--debug", action="store_true", help="show the traceback of an unexpected error"
    )


def hub_command(args: argparse.Namespace) -> int:
    """Build the hub and return 0, failure 1, usage 2, or interrupted 130."""
    console = Console(quiet=args.quiet, no_color=args.no_color)
    try:
        from ..run.output import canonical_json
        from .writer import HubRequest, build_hub

        password = None
        if args.password_env is not None:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.password_env):
                raise UsageError(
                    "The password environment variable name is invalid.",
                    fix="Use a variable name made of letters, digits and underscores.",
                )
            password = os.environ.get(args.password_env)
            if not password:
                raise UsageError(
                    f"The environment variable {args.password_env} is missing or empty.",
                    fix="Set the variable in your shell, then run the command again.",
                )
        request = HubRequest(
            run_dir=Path(args.run_dir).expanduser().resolve(),
            out_dir=Path(args.out).expanduser().resolve(),
            source_dir=Path(args.source_dir).expanduser().resolve() if args.source_dir else None,
            password=password,
        )
        summary = build_hub(request, console)
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
