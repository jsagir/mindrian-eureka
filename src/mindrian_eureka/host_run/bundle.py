"""Stage a host bundle as the private folder input of the pair screen pipeline.

The layout under the run folder is:

    <run_dir>/in/artifacts.csv   one CSV file: id, title, text, source_ref
    <run_dir>/mapping.json       the column mapping of that file

The staging reads no path from the request, makes no network call and reads no clock.
The same request gives the same bytes, so the mapping hash and the folder hash are stable.
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mindrian_eureka.host_run.contracts import NormalizedRequest, sanitized_record_part
from mindrian_eureka.run.mapping import MappingConfig, load_mapping_file

__all__ = [
    "CSV_NAME",
    "MAPPING_NAME",
    "StagedArtifact",
    "StagedBundle",
    "record_id_for",
    "stage_bundle",
]

CSV_NAME: Final[str] = "artifacts.csv"
MAPPING_NAME: Final[str] = "mapping.json"
_INPUT_DIR_NAME: Final[str] = "in"
_MAPPING_SCHEMA: Final[str] = "eureka.run-mapping.v1"
_DIR_MODE: Final[int] = 0o700
_FILE_MODE: Final[int] = 0o600
_HEADER: Final[tuple[str, ...]] = ("id", "title", "text", "source_ref")


@dataclass(frozen=True)
class StagedArtifact:
    """The host identity of one staged record.

    Attributes:
        artifact_id: The host artifact id, as sent.
        source_ref: The host source reference, as sent.
    """

    artifact_id: str
    source_ref: str


@dataclass(frozen=True)
class StagedBundle:
    """A staged bundle.

    Attributes:
        input_dir: The folder that holds `artifacts.csv`. Pass it to the pipeline.
        mapping_path: The mapping file, outside the input folder.
        mapping: The loaded mapping. Its sha256 is the hash of the file bytes.
        id_map: Record id to the host artifact id and source reference, sorted by record id.
    """

    input_dir: Path
    mapping_path: Path
    mapping: MappingConfig
    id_map: dict[str, StagedArtifact]


def record_id_for(artifact_id: str) -> str:
    """Return the record id that the corpus builder gives to a staged artifact.

    Args:
        artifact_id: A host artifact id.

    Returns:
        The CSV file stem, a slash and the sanitized id part.
    """
    return f"{Path(CSV_NAME).stem}/{sanitized_record_part(artifact_id)}"


def _write_private(path: Path, data: bytes) -> None:
    """Create a new file with owner-only access. A file that exists is an error."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    path.chmod(_FILE_MODE)


def _csv_bytes(request: NormalizedRequest) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_HEADER)
    for artifact in request.artifacts:
        writer.writerow((artifact.id, artifact.title, artifact.text, artifact.source_ref))
    return buffer.getvalue().encode("utf-8")


def _mapping_bytes() -> bytes:
    data = {
        "schema_version": _MAPPING_SCHEMA,
        "files": {
            CSV_NAME: {
                "id_column": "id",
                "title_column": "title",
                "text_columns": ["text"],
                "source_column": "source_ref",
                "html": "never",
            }
        },
    }
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def stage_bundle(request: NormalizedRequest, run_dir: Path) -> StagedBundle:
    """Write a checked request as a private CSV input and a mapping file.

    Args:
        request: A request that passed `normalize_request`. Rows are written
            in the sorted order of the raw artifact id.
        run_dir: The job folder. It must not exist.

    Returns:
        The staged bundle with the loaded mapping and the map from record id to host identity.

    Raises:
        FileExistsError: The job folder exists already.
        UsageError: The mapping file is not valid. This is a fault of the code, not of the request.
    """
    run_dir.mkdir(mode=_DIR_MODE, parents=True, exist_ok=False)
    run_dir.chmod(_DIR_MODE)
    input_dir = run_dir / _INPUT_DIR_NAME
    input_dir.mkdir(mode=_DIR_MODE)
    input_dir.chmod(_DIR_MODE)
    _write_private(input_dir / CSV_NAME, _csv_bytes(request))
    mapping_path = run_dir / MAPPING_NAME
    _write_private(mapping_path, _mapping_bytes())
    mapping = load_mapping_file(mapping_path)
    id_map = {
        record_id_for(artifact.id): StagedArtifact(artifact.id, artifact.source_ref)
        for artifact in request.artifacts
    }
    return StagedBundle(
        input_dir=input_dir,
        mapping_path=mapping_path,
        mapping=mapping,
        id_map=dict(sorted(id_map.items())),
    )
