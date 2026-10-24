"""Shared fixtures for the one-command run tests.

No fixture here runs by default, so older tests are not affected.
"""

from __future__ import annotations

import csv
import json
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from hashing_stub import HashingEncoder

CORPUS_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rs_parity" / "corpus.json"
REGION_NAMES = {
    "1": "Northern Fictia",
    "2": "Southern Fictia",
    "3": "Eastern Fictia",
    "4": "Western Fictia",
}


@dataclass(frozen=True)
class InputSet:
    """A synthetic input folder and the settings that describe it.

    Attributes:
        folder: The input folder.
        kind: "csv" or "markdown".
        ids: The record ids that a correct run produces, in sorted order.
        mapping_flags: Command line flags that map the CSV columns. Empty for Markdown.
        mapping_file: A mapping file that describes the same columns, or None.
    """

    folder: Path
    kind: str
    ids: list[str]
    mapping_flags: list[str]
    mapping_file: Path | None


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point home, cache, data and model variables at a temporary home folder.

    The cache and data folders are not created, so doctor tests can see them absent.

    Returns:
        The temporary home folder.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("MINDRIAN_EUREKA_CACHE_DIR", str(home / "cache"))
    monkeypatch.setenv("MINDRIAN_EUREKA_DATA_DIR", str(home / "data"))
    monkeypatch.setenv("HF_HOME", str(home / "hf"))
    for name in (
        "HF_HUB_CACHE",
        "MINDRIAN_EUREKA_RS_MODEL_PATH",
        "MINDRIAN_EUREKA_HSI_MODEL_PATH",
        "NO_COLOR",
        "HF_HUB_OFFLINE",
    ):
        monkeypatch.delenv(name, raising=False)
    return home


@pytest.fixture
def fake_model_dir(tmp_path: Path) -> Path:
    """Create the smallest folder that counts as a valid model folder.

    It holds config.json, modules.json, one weight file and one tokenizer file.
    """
    folder = tmp_path / "all-MiniLM-L6-v2"
    folder.mkdir()
    (folder / "config.json").write_text("{}", encoding="utf-8")
    (folder / "modules.json").write_text("[]", encoding="utf-8")
    (folder / "model.safetensors").write_bytes(b"stub-weights")
    (folder / "tokenizer.json").write_text("{}", encoding="utf-8")
    return folder


@pytest.fixture
def hashing_encoder(monkeypatch: pytest.MonkeyPatch) -> type[HashingEncoder]:
    """Replace the sentence encoder of the unusual-pairs runner with HashingEncoder."""
    import mindrian_eureka.opportunity_pairs.runner as runner

    monkeypatch.setattr(runner, "SentenceTransformerEncoder", HashingEncoder)
    return HashingEncoder


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Block socket connects and name lookups. Returns the list of blocked addresses."""
    blocked: list[object] = []

    def _block(*args: Any, **kwargs: Any) -> Any:
        has_self = bool(args) and isinstance(args[0], socket.socket)
        rest = args[1:] if has_self else args
        blocked.append(rest[0] if rest else None)
        raise RuntimeError("network call blocked")

    monkeypatch.setattr(socket.socket, "connect", _block)
    monkeypatch.setattr(socket.socket, "connect_ex", _block)
    monkeypatch.setattr(socket, "create_connection", _block)
    monkeypatch.setattr(socket, "getaddrinfo", _block)
    return blocked


def _synthetic_records() -> list[dict[str, str]]:
    data = json.loads(CORPUS_FIXTURE.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = data["artifacts"]
    return records


@pytest.fixture
def tmp_inputs(tmp_path: Path) -> Callable[..., InputSet]:
    """Return a factory that writes a synthetic input folder (CSV or Markdown)."""

    def make(kind: str, count: int = 32, name: str = "inputs") -> InputSet:
        if kind not in ("csv", "markdown"):
            raise ValueError("kind must be csv or markdown")
        records = _synthetic_records()[: min(count, 32)]
        folder = tmp_path / name
        folder.mkdir()
        if kind == "markdown":
            sub = folder / "synthetic"
            sub.mkdir()
            for record in records:
                body = f"# {record['title']}\n\n{record['text']}\n"
                (sub / f"{record['id']}.md").write_text(body, encoding="utf-8")
            ids = sorted(f"synthetic/{record['id']}" for record in records)
            return InputSet(folder, kind, ids, [], None)
        with (folder / "records.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["case_id", "title", "description", "state_code"])
            for index, record in enumerate(records):
                writer.writerow(
                    [record["id"], record["title"], record["text"], str(index % 4 + 1)]
                )
        mapping_file = tmp_path / f"{name}-mapping.json"
        mapping = {
            "schema_version": "eureka.run-mapping.v1",
            "files": {
                "*": {
                    "id_column": "case_id",
                    "title_column": "title",
                    "text_columns": ["description"],
                    "value_maps": {"state_code": REGION_NAMES},
                    "extra_fields": ["state_code"],
                }
            },
        }
        mapping_file.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
        ids = sorted(f"records/{record['id']}" for record in records)
        flags = [
            "--id-column", "case_id",
            "--title-column", "title",
            "--text-column", "description",
        ]
        return InputSet(folder, kind, ids, flags, mapping_file)

    return make
