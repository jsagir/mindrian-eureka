"""Import the reference script without writing its start note to stderr.

The reference script prints a harmless note to stderr at import time when its
shared exclude-list module is absent. The MindrianOS plugin shows the first
stderr line as the cause of a failed start, so a healthy start of the stdio
server must print nothing. This module runs that first import with stderr
captured. It must be imported before any module that reaches the reference
script. The reference script itself is not changed, because its hash is
recorded in run manifests.
"""

from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Callable


def import_quietly(load: Callable[[], object]) -> str:
    """Run an import step and keep what it writes to stderr.

    Args:
        load: A function that performs the import.

    Returns:
        The text that the step wrote to stderr.

    Raises:
        BaseException: The error of the step, raised again. The captured text
            goes back to stderr first, so a real failure keeps all its output.
    """
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(buffer):
            load()
    except BaseException:
        sys.stderr.write(buffer.getvalue())
        raise
    return buffer.getvalue()


def _load_reference_chain() -> None:
    from .. import hsi_engine  # noqa: F401


IMPORT_NOTES: str = import_quietly(_load_reference_chain)
