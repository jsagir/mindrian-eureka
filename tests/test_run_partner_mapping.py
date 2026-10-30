"""Tests for the shipped partner export mapping (Phase 2.2, plan 01).

The mapping file is data. These tests load it, pin the dictionary columns, keep the
people, money and outcome columns out of the text, and check that the schema refuses
a wrong `outcome_rule` or `carry_columns` shape. Synthetic data only.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.run.contracts import MAPPING_SCHEMA, UsageError
from mindrian_eureka.run.corpus import build_corpus
from mindrian_eureka.run.mapping import load_mapping_file

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "examples" / "mappings" / "technology-audit-export.json"

TEXT_COLUMNS = (
    "abstract",
    "problem_solved",
    "end_user",
    "size_of_unmet_need",
    "marginal_or_groundbreaking",
    "target_companies",
    "stage_work_required",
    "topics",
)
RULE_COLUMNS = (
    "licensed_to_jh_startup",
    "licensed_externally",
    "licenses",
    "options",
    "had_corporate_research",
    "status",
)
CARRY_COLUMNS = (
    "licensed_to_jh_startup",
    "licensed_externally",
    "had_corporate_research",
    "had_translational_funding",
    "had_any_funding",
    "had_follow_on",
    "licenses",
    "options",
    "ndas",
    "mtas",
    "licensing_deals_lost",
    "funding_awards",
    "translational_awards",
    "follow_on_awards",
    "sponsored_research_agreements",
    "corporate_partnerships_won",
    "first_license_or_option_date",
    "first_translational_date",
    "disclosure_date",
    "status",
)
FORBIDDEN = {
    "inventors",
    "lead_inventor",
    "ip_manager",
    "licensing_associate",
    "jh_startup_licensees",
    "external_licensees",
    "corporate_partners",
    "funding_invested",
    "translational_funds",
    "follow_on_summary",
    "marketing_status",
}
MONEY = {
    "funding_total",
    "translational_total",
    "follow_on_total",
    "startup_funding_after_deal",
    "corporate_partnership_amount",
}
PADDING = " A synthetic abstract with enough words to pass the short body rule of the run."


def _write(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _doc(entry: dict[str, Any], key: str = "*") -> dict[str, Any]:
    return {"schema_version": MAPPING_SCHEMA, "files": {key: entry}}


def _write_csv(folder: Path, name: str, rows: list[list[str]]) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    path.write_bytes(buffer.getvalue().encode("utf-8"))
    return path


def test_shipped_mapping_loads_with_the_dictionary_columns() -> None:
    config = load_mapping_file(SHIPPED)
    entry = config.files["*"]
    assert entry.id_column == "case_number"
    assert entry.title_column == "title"
    assert entry.text_columns == TEXT_COLUMNS
    assert entry.html == "always"
    for column in TEXT_COLUMNS[1:]:
        assert entry.labels[column], column
    assert "abstract" not in entry.labels
    assert entry.outcome_rule is not None
    conditions = entry.outcome_rule.conditions
    assert len(conditions) == 6
    assert tuple(condition.column for condition in conditions) == RULE_COLUMNS
    assert entry.outcome_rule.columns == RULE_COLUMNS
    assert [c.equals for c in conditions] == ["Y", "Y", None, None, "Y", "Inactive- Licensed"]
    assert [c.greater_than for c in conditions] == [None, None, 0, 0, None, None]
    assert entry.outcome_rule.as_data() == {
        "licensed_when_any": [
            {"column": "licensed_to_jh_startup", "equals": "Y"},
            {"column": "licensed_externally", "equals": "Y"},
            {"column": "licenses", "greater_than": 0},
            {"column": "options", "greater_than": 0},
            {"column": "had_corporate_research", "equals": "Y"},
            {"column": "status", "equals": "Inactive- Licensed"},
        ]
    }
    assert entry.carry_columns == CARRY_COLUMNS
    assert len(entry.carry_columns) == 20


def test_shipped_mapping_keeps_people_money_and_outcome_columns_out_of_text() -> None:
    entry = load_mapping_file(SHIPPED).files["*"]
    assert entry.outcome_rule is not None
    text = set(entry.text_columns)
    assert FORBIDDEN.isdisjoint(text)
    assert FORBIDDEN.isdisjoint(entry.extra_fields)
    assert FORBIDDEN.isdisjoint(entry.carry_columns)
    assert FORBIDDEN.isdisjoint(entry.outcome_rule.columns)
    assert MONEY.isdisjoint(text)
    assert MONEY.isdisjoint(entry.carry_columns)
    assert set(entry.carry_columns).isdisjoint(text)
    assert set(entry.outcome_rule.columns).isdisjoint(text)
    assert entry.id_column not in text
    assert entry.title_column not in text


@pytest.mark.parametrize(
    "entry",
    [
        {"text_columns": ["a"], "outcome_rule": {"licensed_when_any": []}},
        {"text_columns": ["a"], "outcome_rule": {"licensed_when_any": [{"equals": "Y"}]}},
        {
            "text_columns": ["a"],
            "outcome_rule": {
                "licensed_when_any": [{"column": "c", "equals": "Y", "greater_than": 0}]
            },
        },
        {"text_columns": ["a"], "outcome_rule": {"licensed_when_any": [{"column": "c"}]}},
        {
            "text_columns": ["a"],
            "outcome_rule": {"licensed_when_any": [{"column": "c", "greater_than": "0"}]},
        },
        {"text_columns": ["a"], "carry_columns": ["x", "x"]},
        {"text_columns": ["a"], "carry_columns": "x"},
        {
            "text_columns": ["a"],
            "outcome_rule": {
                "licensed_when_any": [{"column": "c", "equals": "Y"}],
                "classes": ["licensed", "open"],
            },
        },
    ],
)
def test_rule_and_carry_schema_refusals(tmp_path: Path, entry: dict[str, Any]) -> None:
    path = _write(tmp_path / "bad-map.json", _doc(entry))
    with pytest.raises(UsageError) as info:
        load_mapping_file(path)
    assert "bad-map.json" in info.value.message
    assert info.value.exit_code == 2
    assert info.value.fix


def test_entity_only_abstract_is_decoded_under_html_always(tmp_path: Path) -> None:
    config = load_mapping_file(SHIPPED)
    entry = config.files["*"]
    assert entry.id_column is not None
    assert entry.title_column is not None
    assert entry.outcome_rule is not None
    headers = list(
        dict.fromkeys(
            [
                *entry.text_columns,
                entry.id_column,
                entry.title_column,
                *entry.carry_columns,
                *entry.outcome_rule.columns,
            ]
        )
    )
    rows = [headers]
    for case in ("C00001", "C00002"):
        row = {name: "" for name in headers}
        row["case_number"] = case
        row["title"] = f"Synthetic title {case}"
        row["abstract"] = "It&rsquo;s a &amp; test" + PADDING
        row["problem_solved"] = "A made-up problem about sorting pebbles by weight."
        row["licenses"] = "0"
        row["options"] = "0"
        row["status"] = "Active"
        rows.append([row[name] for name in headers])
    folder = tmp_path / "in"
    _write_csv(folder, "export.csv", rows)
    corpus = build_corpus(folder, mapping=config)
    assert len(corpus.records) == 2
    text = corpus.records[0].text
    assert "s a & test" in text
    assert "&rsquo;" not in text
    assert "&amp;" not in text
    assert "Problem solved:" in text
    assert corpus.records[0].id.split("/", 1)[1] == "C00001"
