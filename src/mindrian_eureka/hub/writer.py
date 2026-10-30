"""Build a local hub using the standard library and light Eureka modules only.

Files are assembled before publication and written through the canonical staged
writer. The run and source folders are read only. No model or network is used.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..run.console import Console
from ..run.contracts import LABEL, MANIFEST_SCHEMA, SUMMARY_LINE, RunError, UsageError
from ..run.manifest import tool_version
from ..run.output import FileDigest, StagedRun, canonical_json, ensure_out_dir_allowed
from . import assets
from .contracts import (
    ENGINE_KEYS,
    HUB_MANIFEST_SCHEMA,
    HUB_SUMMARY_SCHEMA,
    OUTPUT_HUB_COPY,
    OUTPUT_HUB_DATA,
    OUTPUT_HUB_HTML,
    OUTPUT_HUB_MANIFEST,
    is_hub_folder,
    js_assignment,
)
from .deck import deck_js_bytes
from .links import file_links
from .model import build_payload
from .page import render_page
from .reader import load_run
from .verify import verify_payload


@dataclass(frozen=True)
class HubRequest:
    """Paths for a hub build; source_dir optionally enables local file links."""

    run_dir: Path
    out_dir: Path
    source_dir: Path | None = None
    password: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class HubSummary:
    """Deterministic build facts; out_dir is shown only in terminal output."""

    out_dir: Path
    run_fingerprint: str
    manifest_sha256: str
    files: tuple[FileDigest, ...]
    records: int
    pairs: dict[str, int]
    source_links: Literal["files", "catalogue"]
    warnings: tuple[str, ...]
    gated: bool = False

    def to_json_dict(self) -> dict[str, Any]:
        """Return summary facts with labels and without machine paths."""
        data: dict[str, Any] = {
            "schema_version": HUB_SUMMARY_SCHEMA,
            "label": LABEL,
            "run_fingerprint": self.run_fingerprint,
            "manifest_sha256": self.manifest_sha256,
            "counts": {"records": self.records, "pairs": self.pairs},
            "source_links": self.source_links,
            "files": [item.as_dict() for item in self.files],
            "warnings": list(self.warnings),
            "summary_line": SUMMARY_LINE,
        }
        if self.gated:
            data["gated"] = True
        return data

    def lines(self) -> str:
        """Return the human CLI summary with the shared status as its last line."""
        source = (
            "to files in the source folder" if self.source_links == "files"
            else "to the catalogue rows"
        )
        return "\n".join((
            "Eureka hub written.",
            f"Hub folder: {self.out_dir}",
            "Open the page: hub.html",
            f"Records: {self.records}. Pairs: {self.pairs['unusual_pairs']} "
            f"(unusual-pairs engine), {self.pairs['wording_and_meaning']} (wording engine).",
            f"Hub manifest: hub-manifest.json (sha256 {self.manifest_sha256})",
            f"Source links: {source}",
            *(["Gate: on. The data is stored encrypted. Keep the passphrase safe."]
              if self.gated else []),
            SUMMARY_LINE,
        ))


def build_hub(request: HubRequest, console: Console) -> HubSummary:
    """Validate and atomically publish a deterministic hub folder.

    Args:
        request: Finished run, output folder, and optional original source folder.
        console: Destination for progress and warnings; never global print.

    Returns:
        File hashes, counts, status, and warnings for the finished build.

    Raises:
        UsageError: Output overlaps input or a foreign folder, or sources are absent.
        RunError: Run hashes, payload provenance, or canonical asset hashes fail.
    """
    ensure_out_dir_allowed(
        request.run_dir, request.out_dir, replaceable=is_hub_folder, kind="Eureka hub"
    )
    if request.source_dir is not None:
        if not request.source_dir.is_dir():
            raise UsageError(
                "source folder does not exist or is not a folder",
                fix="Give --source-dir a folder containing the original source files.",
            )
        ensure_out_dir_allowed(
            request.source_dir, request.out_dir, replaceable=is_hub_folder, kind="Eureka hub"
        )
    console.stage("Read the finished run")
    run = load_run(request.run_dir)
    warnings: list[str] = []
    if run.dropped_note_count:
        warnings.append(f"Omitted {run.dropped_note_count} engine notes with internal names.")
    links: dict[str, str] = {}
    if request.source_dir is not None:
        links, missing = file_links(
            run.records, out_dir=request.out_dir, source_dir=request.source_dir
        )
        if missing:
            warnings.append(
                f"Source files unavailable for {len(missing)} records; catalogue links used."
            )
    if request.password is not None and len(request.password) < 12:
        warnings.append("The passphrase is short. A longer one protects the file better.")
    for warning in warnings:
        console.warn(warning)
    payload = build_payload(run, file_links=links)
    problems = verify_payload(payload)
    if problems:
        raise RunError(
            f"Hub data check failed ({len(problems)} problems): {problems[0]}",
            fix="Report this to the Eureka maintainer; the hub was not written.",
        )
    content: dict[str, bytes] = {}
    for asset in assets.all_assets():
        data = asset.package_path.read_bytes()
        expected = assets.EXPECTED_STATIC.get(asset.output_path)
        if expected is not None and hashlib.sha256(data).hexdigest() != expected:
            raise RunError(
                f"A packaged hub file changed: {asset.output_path}",
                fix="Reinstall Eureka from the approved package; the hub was not written.",
            )
        content[asset.output_path] = data
    content[OUTPUT_HUB_COPY] = deck_js_bytes()
    gated = request.password is not None
    if gated:
        from .gate import encrypt_payload

        assert request.password is not None
        envelope = encrypt_payload(canonical_json(payload), request.password, run.manifest_sha256)
        content[OUTPUT_HUB_DATA] = js_assignment("HUB_ENVELOPE", envelope)
        content[OUTPUT_HUB_HTML] = render_page(
            None, gated=True, files=set(content) | {OUTPUT_HUB_HTML}
        )
    else:
        content[OUTPUT_HUB_DATA] = js_assignment("HUB", payload)
        content[OUTPUT_HUB_HTML] = render_page(payload, files=set(content) | {OUTPUT_HUB_HTML})
    source_kind: Literal["files", "catalogue"] = (
        "files" if request.source_dir is not None else "catalogue"
    )
    pair_counts = {key: len(run.engines[key].pairs) for key in ENGINE_KEYS}
    console.stage("Write the hub folder")
    with StagedRun(request.out_dir, replaceable=is_hub_folder, kind="Eureka hub") as staged:
        digests = [staged.write(name, data) for name, data in sorted(content.items())]
        manifest: dict[str, Any] = {
            "schema_version": HUB_MANIFEST_SCHEMA,
            "label": LABEL,
            "tool": {"name": "mindrian-eureka", "version": tool_version()},
            "run": {"manifest_sha256": run.manifest_sha256, "schema_version": MANIFEST_SCHEMA},
            "source_links": source_kind,
            "files": [item.as_dict() for item in digests],
        }
        if gated:
            manifest["gated"] = True
        else:
            manifest["counts"] = {"records": len(run.records), "pairs": pair_counts}
        manifest_digest = staged.write(OUTPUT_HUB_MANIFEST, canonical_json(manifest))
        staged.publish()
    return HubSummary(
        out_dir=request.out_dir, run_fingerprint=run.manifest_sha256,
        manifest_sha256=manifest_digest.sha256,
        files=tuple(sorted([*digests, manifest_digest], key=lambda item: item.path)),
        records=len(run.records), pairs=pair_counts, source_links=source_kind,
        warnings=tuple(warnings), gated=gated,
    )
