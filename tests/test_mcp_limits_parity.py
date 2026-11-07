"""Parity tests: the MCP pair tools and their published schemas follow `limits.py`.

Decision D-08 of phase 3. The three pair-engine routes take their artifact cap
and their pair cap from `limits.py`. Other families keep their own caps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mindrian_eureka
import pytest
from mindrian_eureka import opportunity_discovery
from mindrian_eureka.contracts import capability_record
from mindrian_eureka.limits import MAX_ARTIFACTS, MAX_TOP_K
from mindrian_eureka.opportunity_pairs.mcp_server import OpportunityScoutInput, ScoutRunInput
from pydantic import ValidationError

SCHEMA_DIR = Path(mindrian_eureka.__file__).parent / "data" / "schemas"
MODELS = [ScoutRunInput, OpportunityScoutInput]


def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _artifacts(count: int) -> list[dict[str, str]]:
    return [{"id": f"a{index}", "source_ref": "s://n", "text": "t" * 60} for index in range(count)]


def _payload(count: int, **extra: Any) -> dict[str, Any]:
    base = {"objective": "find pairs", "scope_id": "scope-1", "artifacts": _artifacts(count)}
    return {**base, **extra}


@pytest.mark.parametrize("model", MODELS)
def test_mcp_models_take_their_caps_from_limits(model: type) -> None:
    properties = model.model_json_schema()["properties"]
    assert properties["artifacts"]["maxItems"] == MAX_ARTIFACTS
    assert properties["top_k"]["maximum"] == MAX_TOP_K


@pytest.mark.parametrize("model", MODELS)
def test_mcp_models_refuse_one_over_the_cap_and_accept_the_cap(model: type) -> None:
    with pytest.raises(ValidationError):
        model(**_payload(MAX_ARTIFACTS + 1))
    with pytest.raises(ValidationError):
        model(**_payload(2, top_k=MAX_TOP_K + 1))
    accepted = model(**_payload(2, top_k=MAX_TOP_K))
    assert accepted.top_k == MAX_TOP_K


def test_published_input_schemas_carry_the_same_caps() -> None:
    for name in ("cross-domain-pairs-input.v1.json", "discovery-signals-input.v1.json"):
        properties = _schema(name)["properties"]
        assert properties["artifacts"]["maxItems"] == MAX_ARTIFACTS, name
        assert properties["top_k"]["maximum"] == MAX_TOP_K, name
    signals = _schema("discovery-signals-input.v1.json")
    projection = signals["properties"]["projection"]["properties"]
    assert projection["artifact_count"]["maximum"] == MAX_ARTIFACTS
    assert projection["max_artifacts"]["maximum"] == MAX_ARTIFACTS
    hsi = _schema("hsi-pairs-input.v1.json")["properties"]
    assert hsi["artifacts"]["maxItems"] == MAX_ARTIFACTS
    assert hsi["top_k"]["maximum"] == MAX_TOP_K


def test_signal_scout_cap_follows_limits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Sentinel(Exception):
        pass

    def stop(*_args: Any, **_kwargs: Any) -> None:
        raise Sentinel

    request = {"encoder": "stub", "model_path": "none", "top_k": 5}
    over = {**request, "artifacts": _artifacts(MAX_ARTIFACTS + 1)}
    with pytest.raises(ValueError, match=str(MAX_ARTIFACTS)):
        opportunity_discovery.run_signal_synthesis(over, data_dir=tmp_path, job_id="job")

    monkeypatch.setattr(opportunity_discovery, "run_document", stop)
    between = {**request, "artifacts": _artifacts(2501)}
    with pytest.raises(Sentinel):
        opportunity_discovery.run_signal_synthesis(between, data_dir=tmp_path, job_id="job")


def test_catalog_sentence_follows_limits() -> None:
    record = capability_record("opportunity.synthesize_discovery_signals")
    assert record is not None
    requires = record["requires"]
    assert any("2..3000" in item for item in requires)
    assert not any("2..2500" in item for item in requires)


def test_other_families_keep_their_caps() -> None:
    record = capability_record("graph.prepare_artifact_bundle")
    assert record is not None
    assert record["resource_limits"]["max_artifacts"] == 2500
