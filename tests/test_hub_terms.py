"""Tests of the distinctive words of a run (`mindrian_eureka.hub.terms`).

The module is imported inside each test, so a missing module is a clean failure.
The words are a screening aid, never evidence. No test here claims otherwise.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from mindrian_eureka.hub.reader import load_run

FIXTURE_RUN = Path(__file__).parent / "fixtures" / "hub_public" / "run"
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "hub_terms"
GOLDEN_RECORDS = GOLDEN_DIR / "records-top5.json"
GOLDEN_PAIRS = GOLDEN_DIR / "pairs-shared.json"
RULES_DOC = Path(__file__).resolve().parents[1] / "docs" / "brand" / "hub-terms-rules.md"
WRITE_FLAG = "EUREKA_WRITE_TERM_GOLDENS"
WORD_SHAPE = re.compile(r"^[a-z][a-z-]*$")

# The stop list of the rule (item 7 of the plan), copied here as the contract of the test.
RULE_STOP_LIST = (
    "a about above after again all also an and any are as at be because been before being "
    "between both but by can could did do does doing down during each few for from further "
    "had has have having he her here hers him his how i if in into is it its just may more "
    "most much must no nor not now of off on once only or other our out over own same she "
    "should so some such than that the their them then there these they this those through "
    "to too under until up use used uses using very was we were what when where which while "
    "who whom why will with would you your paper papers show shows shown present presents "
    "propose proposed approach method methods result results based new however thus one two "
    "three first second via within without cannot study studies work works given general "
    "case cases number set sets problem problems model models"
).split()


@dataclass(frozen=True)
class FakeRecord:
    """The smallest object that `build_terms` accepts: an id, a title and a text."""

    id: str
    title: str
    text: str


def _records(*items: tuple[str, str]) -> list[FakeRecord]:
    return [FakeRecord(id=rid, title="", text=text) for rid, text in items]


def _dump(mapping: dict[str, list[str]]) -> str:
    """Sorted keys, one line for each key, a newline at the end."""
    keys = sorted(mapping)
    lines = ["{"]
    for index, key in enumerate(keys):
        comma = "," if index < len(keys) - 1 else ""
        lines.append(f"  {json.dumps(key)}: {json.dumps(mapping[key])}{comma}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def test_tokens_and_folding() -> None:
    from mindrian_eureka.hub.terms import tokens

    assert tokens("Learning Logic Programs with Cut") == ["learning", "logic", "program"]
    folds = {
        "properties": ["property"],
        "classes": ["class"],
        "matches": ["match"],
        "indexes": ["index"],
        "programs": ["program"],
        "calculus": ["calculus"],
        "analysis": ["analysis"],
        "glass": ["glass"],
        "bias": ["bias"],
        # Recorded limits of the light folding, not goals. The written rule keeps a word
        # of 5 letters whole under the "es" fold, and drops the "s" of "canvas".
        "boxes": ["boxe"],
        "canvas": ["canva"],
        "studies": [],
        "Self-Adjusting-": ["self-adjusting"],
    }
    for text, expected in folds.items():
        assert tokens(text) == expected, text
    hebrew = "".join(chr(point) for point in (1513, 1500, 1493, 1501))
    assert tokens(hebrew) == []
    assert tokens("1234 5678 90") == []
    assert tokens("") == []


def test_stop_list() -> None:
    from mindrian_eureka.hub.terms import STOP_WORDS

    for word in RULE_STOP_LIST:
        if len(word) >= 3:
            assert word in STOP_WORDS, word
    for word in STOP_WORDS:
        assert word == word.lower(), word
        assert "-" not in word, word
    assert len(STOP_WORDS) <= 180


def test_scores_follow_the_formula() -> None:
    from mindrian_eureka.hub.terms import rank_records, tokens

    records = _records(
        ("r1", "river river river delta silt common common"),
        ("r2", "common grain harvest common"),
        ("r3", "common antenna relay signal signal"),
        ("r4", "common enamel crown river"),
    )
    # The expected lists, computed by a second code path: plain counters and inline math.
    toks = {record.id: tokens(record.text) for record in records}
    seen_in: dict[str, int] = {}
    for words in toks.values():
        for word in set(words):
            seen_in[word] = seen_in.get(word, 0) + 1
    count = len(records)
    expected: dict[str, list[str]] = {}
    for rid, words in toks.items():
        counts: dict[str, int] = {}
        for word in words:
            counts[word] = counts.get(word, 0) + 1
        scores = {
            word: counts[word] * math.log((count + 1) / (seen_in[word] + 0.5)) for word in counts
        }
        expected[rid] = sorted(scores, key=lambda word: (-round(scores[word], 9), word))
    ranked = rank_records(records)
    assert ranked == expected
    # The idf of a word with df 1 is above the idf of a word with df 4 (natural log).
    idf_rare = math.log(5 / 1.5)
    idf_common = math.log(5 / 4.5)
    assert idf_rare > idf_common > 0
    # In r2, "common" has tf 2 and df 4; "grain" has tf 1 and df 1. The rare word wins.
    assert 2 * idf_common < 1 * idf_rare
    assert ranked["r2"][:2] == ["grain", "harvest"]
    assert ranked["r2"][-1] == "common"
    # In r1 "river" (tf 3, df 2) comes first; "common" (tf 2, df 4) comes last.
    assert ranked["r1"][0] == "river"
    assert ranked["r1"][-1] == "common"


def test_ties_are_broken_by_the_word() -> None:
    from mindrian_eureka.hub.terms import TOP_N, build_terms, rank_records

    records = _records(("one", "zebra yacht xylem walnut violet umber"), ("two", "other things"))
    ranked = rank_records(records)
    assert ranked["one"] == ["umber", "violet", "walnut", "xylem", "yacht", "zebra"]
    result = build_terms(records, [])
    assert TOP_N == 5
    assert result["records"]["one"] == ["umber", "violet", "walnut", "xylem", "yacht"]


def test_rounding_absorbs_last_bit_differences(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindrian_eureka.hub import terms

    real_log = math.log
    calls: list[float] = []

    def shaky_log(value: float) -> float:
        """Return the true logarithm, plus 1e-12 on every second call with the same value."""
        calls.append(value)
        bump = 1e-12 if calls.count(value) % 2 == 0 else 0.0
        return real_log(value) + bump

    monkeypatch.setattr(terms.math, "log", shaky_log)
    records = _records(("one", "zebra apple"))
    ranked = terms.rank_records(records)
    assert len(calls) >= 2
    assert ranked["one"] == ["apple", "zebra"]
    # The same with the words swapped in the text, so the call order cannot matter.
    calls.clear()
    ranked = terms.rank_records(_records(("one", "apple zebra")))
    assert ranked["one"] == ["apple", "zebra"]


def _filler(prefix: str, count: int) -> list[str]:
    return [f"{prefix}word{index:03d}" for index in range(count)]


def test_shared_words() -> None:
    from mindrian_eureka.hub.terms import SHARED_MAX, shared_words

    rank_a = _filler("aaa", 8)
    rank_b = _filler("bbb", 8)
    rank_a[0], rank_b[4] = "wone", "wone"
    rank_a[2], rank_b[1] = "wtwo", "wtwo"
    rank_a[5], rank_b[5] = "wthree", "wthree"
    assert shared_words(rank_a, rank_b) == ["wtwo", "wone", "wthree"]
    assert shared_words(rank_b, rank_a) == ["wtwo", "wone", "wthree"]

    nine = [f"shared{index}" for index in range(9)]
    assert SHARED_MAX == 6
    # Ranks (i, 8 - i): the larger rank is 4 for shared4, 5 for shared3 and shared5, and so on.
    assert shared_words(nine, list(reversed(nine))) == [
        "shared4",
        "shared3",
        "shared5",
        "shared2",
        "shared6",
        "shared1",
    ]
    assert len(shared_words(nine, nine)) == 6
    assert shared_words(nine, nine) == nine[:6]

    assert shared_words(_filler("ccc", 5), _filler("ddd", 5)) == []
    assert shared_words([], _filler("ddd", 5)) == []


def test_depth_is_30() -> None:
    from mindrian_eureka.hub.terms import DEPTH, shared_words

    assert DEPTH == 30
    rank_a = _filler("aaa", 40)
    rank_b = _filler("bbb", 40)
    rank_a[29], rank_b[29] = "deep", "deep"
    rank_a[30], rank_b[0] = "toodeep", "toodeep"
    assert shared_words(rank_a, rank_b) == ["deep"]


def test_build_terms_shape() -> None:
    from mindrian_eureka.hub.terms import build_terms

    records = [
        FakeRecord(id="r1", title="Title words", text="river flood delta channel silt"),
        FakeRecord(id="r2", title="", text="grain harvest soil field river"),
        FakeRecord(id="r3", title="", text=""),
        FakeRecord(id="r4", title="", text="1234 !!! the and"),
    ]
    pairs = [("p1", "r1", "r2"), ("p2", "r1", "r3"), ("p1", "r1", "r2")]
    result = build_terms(records, pairs)
    assert set(result) == {"records", "pairs"}
    assert set(result["records"]) == {"r1", "r2", "r3", "r4"}
    for words in result["records"].values():
        assert isinstance(words, list)
        assert len(words) <= 5
    assert result["records"]["r3"] == []
    assert result["records"]["r4"] == []
    assert list(result["pairs"]) == ["p1", "p2"]
    assert result["pairs"]["p1"] == ["river"]
    assert result["pairs"]["p2"] == []
    for words in result["pairs"].values():
        assert len(words) <= 6


def test_deterministic_and_order_independent() -> None:
    from mindrian_eureka.hub.terms import build_terms

    themes = ["river flood dam channel delta silt", "grain harvest soil seed field yield"]
    records = [
        FakeRecord(id=f"doc{index:02d}", title=f"Study {index}", text=themes[index % 2])
        for index in range(12)
    ]
    pairs = [
        (f"pair{index}", f"doc{index:02d}", f"doc{(index + 1) % 12:02d}") for index in range(12)
    ]
    first = build_terms(records, pairs)
    second = build_terms(records, pairs)
    assert first == second
    reversed_result = build_terms(list(reversed(records)), list(reversed(pairs)))
    assert reversed_result == first
    shuffled = [records[index] for index in (7, 2, 11, 0, 9, 4, 1, 10, 3, 8, 5, 6)]
    assert build_terms(shuffled, pairs) == first
    assert json.dumps(first, sort_keys=True) == json.dumps(reversed_result, sort_keys=True)


def test_golden_lists_of_the_public_fixture() -> None:
    from mindrian_eureka.hub.terms import DEPTH, STOP_WORDS, build_terms, rank_records

    run = load_run(FIXTURE_RUN)
    records = list(run.records)
    pairs = [
        (pair.pair_id, pair.left_id, pair.right_id)
        for engine in run.engines.values()
        for pair in engine.pairs
    ]
    result = build_terms(records, pairs)
    records_text = _dump(result["records"])
    pairs_text = _dump(result["pairs"])

    if not (GOLDEN_RECORDS.exists() and GOLDEN_PAIRS.exists()):
        if os.environ.get(WRITE_FLAG) == "1":
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            GOLDEN_RECORDS.write_text(records_text, encoding="utf-8")
            GOLDEN_PAIRS.write_text(pairs_text, encoding="utf-8")
            pytest.fail("golden written, review it")
        pytest.fail(f"golden missing: {GOLDEN_RECORDS} or {GOLDEN_PAIRS}")

    assert GOLDEN_RECORDS.read_text(encoding="utf-8") == records_text
    assert GOLDEN_PAIRS.read_text(encoding="utf-8") == pairs_text
    assert json.loads(records_text) == result["records"]
    assert json.loads(pairs_text) == result["pairs"]

    # Plausibility rules.
    ranked = rank_records(records)
    assert set(result["records"]) == {record.id for record in records}
    for words in result["records"].values():
        assert 1 <= len(words) <= 5
        for word in words:
            assert WORD_SHAPE.match(word), word
            assert len(word) >= 4, word
            assert word not in STOP_WORDS, word
    by_pair = {pair.pair_id: pair for engine in run.engines.values() for pair in engine.pairs}
    assert set(result["pairs"]) == set(by_pair)
    for pair_id, words in result["pairs"].items():
        pair = by_pair[pair_id]
        depth_left = ranked[pair.left_id][:DEPTH]
        depth_right = ranked[pair.right_id][:DEPTH]
        assert len(words) <= 6
        for word in words:
            assert word in depth_left and word in depth_right, (pair_id, word)
            assert WORD_SHAPE.match(word), word


def test_hostile_text_cannot_reach_a_word() -> None:
    from mindrian_eureka.hub.terms import build_terms, tokens

    hostile = (
        '<script>window.__pwned=1</script> "quoted" it\'s & &amp; onerror="alert(1)"'
        + chr(8232)
        + " separated"
        + chr(8212)
        + "dashed "
        + chr(0)
        + "nulled javascript:void(0) <img src=x>"
    )
    words = tokens(hostile)
    assert words
    for word in words:
        assert WORD_SHAPE.match(word), word
    result = build_terms([FakeRecord(id="h", title=hostile, text=hostile)], [("p", "h", "h")])
    for word in result["records"]["h"] + result["pairs"]["p"]:
        assert WORD_SHAPE.match(word), word
        assert "<" not in word and ">" not in word and "&" not in word and '"' not in word


def test_performance_is_linear_enough() -> None:
    from mindrian_eureka.hub.terms import build_terms

    vocabulary = [f"term{index:04d}" for index in range(5000)]
    records = []
    for index in range(2000):
        words = [vocabulary[(index * 7 + step * 13) % len(vocabulary)] for step in range(200)]
        records.append(
            FakeRecord(id=f"rec{index:04d}", title=f"Record {index}", text=" ".join(words))
        )
    pairs = [
        (f"pair{index:04d}", f"rec{index:04d}", f"rec{(index + 1) % 2000:04d}")
        for index in range(2000)
    ]
    started = time.perf_counter()
    result = build_terms(records, pairs)
    seconds = time.perf_counter() - started
    print(f"build_terms over 2000 records of 200 words: {seconds:.2f} s")
    assert len(result["records"]) == 2000
    assert len(result["pairs"]) == 2000


def test_rules_document() -> None:
    assert RULES_DOC.exists(), RULES_DOC
    text = RULES_DOC.read_text(encoding="utf-8")
    assert chr(8211) not in text, "en dash in the rules file"
    assert chr(8212) not in text, "em dash in the rules file"
    for needle in (
        "log((N + 1) / (df + 0.5))",
        "screening aid",
        "not evidence",
        "English letters only",
        "book silent, proposed segment",
        "180",
    ):
        assert needle in text, needle
    assert re.search(r"\b5\b", text)
    assert re.search(r"\b30\b", text)
    assert re.search(r"\b6\b", text)
    assert re.search(r"9 decimal", text)
