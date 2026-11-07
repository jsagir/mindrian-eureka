"""Run the pair screen as a durable job and clean up everything but the result.

`run_pair_screen_job` stages the host bundle in a private folder below the data
directory, runs the Phase 2 pipeline on it with no embedding cache, builds the result
envelope and deletes the folder in a `finally` block. It deletes the folder on success,
on failure and on cancel. The job writes nothing to standard output, which is the host
protocol channel, and it gets no room path.

The pipeline and the engines load inside the function, so importing this module stays light.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from mindrian_eureka.host_run.bundle import stage_bundle
from mindrian_eureka.host_run.contracts import (
    CAPABILITY_ID,
    HostRunError,
    NormalizedRequest,
    normalize_request,
)
from mindrian_eureka.host_run.envelope import build_result
from mindrian_eureka.limits import MAX_ARTIFACTS
from mindrian_eureka.opportunity_pairs.algorithm import RunCancelled
from mindrian_eureka.run.console import Console

__all__ = ["JobConsole", "build_job_request", "run_pair_screen_job"]

_JOB_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_-]{1,64}")
_RUNS_DIR_NAME: Final[str] = "host-runs"
_OUT_DIR_NAME: Final[str] = "out"
_DIR_MODE: Final[int] = 0o700
_ARGV: Final[tuple[str, ...]] = ("mcp", "pair-screen")


def _approval_missing() -> HostRunError:
    return HostRunError(
        "approval_missing",
        "A pair screen job needs an approval block.",
        "Send the plan digest and an approval reference with the start request.",
    )


def build_job_request(norm: NormalizedRequest) -> dict[str, Any]:
    """Return the dictionary that the job store keeps for a checked request.

    Args:
        norm: A request that passed `normalize_request`.

    Returns:
        The stored job request. Every artifact has the corpus `room`, which the job
        store requires for the mode `local`.

    Raises:
        HostRunError: The request has no approval block (`approval_missing`).
    """
    if norm.approval is None:
        raise _approval_missing()
    return {
        "capability_id": CAPABILITY_ID,
        "mode": "local",
        "objective": norm.objective,
        "scope_id": norm.scope_id,
        "snapshot_id": norm.snapshot_id,
        "artifacts": [
            {
                "id": artifact.id,
                "source_ref": artifact.source_ref,
                "title": artifact.title,
                "text": artifact.text,
                "corpus": "room",
            }
            for artifact in norm.artifacts
        ],
        "top_k": norm.top_k,
        "approval": {
            "plan_digest": norm.approval.plan_digest,
            "approval_ref": norm.approval.approval_ref,
        },
    }


class JobConsole(Console):
    """A console that prints nothing and takes cancel and progress between stages.

    The pipeline calls `stage` at each step. This console checks the cancel flag first,
    then passes the stage name to the callback. A warning is kept by the pipeline in its
    own summary, so it needs no output here.
    """

    def __init__(
        self,
        stage_callback: Callable[[str], object] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(quiet=True, no_color=True)
        self._stage_callback = stage_callback
        self._cancel_check = cancel_check

    def _check_cancel(self) -> None:
        if self._cancel_check is not None and self._cancel_check():
            raise RunCancelled("Run cancelled")

    def info(self, message: str) -> None:
        """Check the cancel flag. Write nothing."""
        self._check_cancel()

    def stage(self, name: str) -> None:
        """Check the cancel flag, then pass the stage name to the callback."""
        self._check_cancel()
        if self._stage_callback is not None:
            self._stage_callback(name)

    def warn(self, message: str) -> None:
        """Write nothing."""

    def error(self, message: str, fix: str | None = None) -> None:
        """Write nothing."""

    def out(self, text: str) -> None:
        """Write nothing."""


def run_pair_screen_job(
    request: dict[str, Any],
    *,
    data_dir: Path,
    job_id: str,
    cancel_check: Callable[[], bool] | None = None,
    stage_callback: Callable[[str], object] | None = None,
) -> dict[str, Any]:
    """Run one stored pair screen request and return the result envelope.

    Args:
        request: The stored job request from `build_job_request`.
        data_dir: The data directory of the job store.
        job_id: The job id. It names the private folder, so it must be a safe name.
        cancel_check: Returns True when the job must stop. Checked between stages.
        stage_callback: Called with the name of each pipeline stage.

    Returns:
        A dictionary that validates against `pair-screen-output.v1.json`.

    Raises:
        ValueError: The capability id or the job id is wrong.
        HostRunError: The request breaks a rule or has no approval.
        RunCancelled: The cancel check returned True.
        RunError: No local model, or the pipeline failed.
    """
    body = dict(request)
    if body.pop("capability_id", None) != CAPABILITY_ID:
        raise ValueError("This job request is not a pair screen request.")
    body.pop("mode", None)
    norm = normalize_request(body)
    approval = norm.approval
    if approval is None:
        raise _approval_missing()
    if not _JOB_ID_PATTERN.fullmatch(job_id):
        raise ValueError("The job id is not a safe folder name.")

    root = Path(data_dir)
    root.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    runs_dir = root / _RUNS_DIR_NAME
    runs_dir.mkdir(mode=_DIR_MODE, exist_ok=True)
    run_dir = runs_dir / job_id
    if run_dir.exists():
        raise FileExistsError("The private folder of this job exists already.")
    console = JobConsole(stage_callback, cancel_check)
    try:
        if cancel_check is not None and cancel_check():
            raise RunCancelled("Run cancelled")
        staged = stage_bundle(norm, run_dir)
        from mindrian_eureka.run.pipeline import RunRequest, run_pipeline

        run_pipeline(
            RunRequest(
                input_dir=staged.input_dir,
                out_dir=run_dir / _OUT_DIR_NAME,
                mapping=staged.mapping,
                text_sidecar=None,
                model_path=None,
                max_artifacts=MAX_ARTIFACTS,
                top_k=norm.top_k,
                objective=norm.objective,
                threads=None,
                use_cache=False,
                dry_run=False,
                argv=_ARGV,
            ),
            console,
        )
        if cancel_check is not None and cancel_check():
            raise RunCancelled("Run cancelled")
        return build_result(
            run_dir / _OUT_DIR_NAME,
            id_map=staged.id_map,
            scope_id=norm.scope_id,
            snapshot_id=norm.snapshot_id,
            approval=approval,
            job_id=job_id,
        )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
