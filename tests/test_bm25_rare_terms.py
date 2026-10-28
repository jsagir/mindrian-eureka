"""Deterministic synthetic regression corpus for the BM25 vocabulary cap.

Synthetic test data, not a finding. The corpus has more distinct terms than
the cap, so the cut lands inside the rare band. A rare identifier shared by
2 documents must survive the cap whatever its spelling.
"""

import random

from mindrian_eureka.hsi_reference import (
    _term_count_matrix,
    compute_bm25_similarity,
    tokenize,
)
from mindrian_eureka.opportunity_pairs.algorithm import _bm25_cosine, _rs_tokens

N_DOCS = 60
A, B = 3, 55  # the planted pair
C, D = 10, 40  # partners that give A and B private df == 2 terms
SEED = 2026
CAP = 5000
FILLERS = [i for i in range(N_DOCS) if i not in (A, B, C, D)]

S1 = "error code means the power unit failed"
S2 = "the fault was logged by the supervisor"


def build_corpus(seed=SEED) -> list[str]:
    rng = random.Random(seed)
    docs: list[list[str]] = [[] for _ in range(N_DOCS)]
    for k in range(4200):
        for d in rng.sample(FILLERS, 3):
            docs[d].append(f"c{k:04d}")
    for k in range(1200):
        for d in rng.sample(FILLERS, 2):
            docs[d].append(f"w{k:04d}")
    for k in range(30):
        docs[A].append(f"pab{k:02d}")
        docs[B].append(f"pab{k:02d}")
        docs[A].append(f"pac{k:02d}")
        docs[C].append(f"pac{k:02d}")
        docs[B].append(f"pbd{k:02d}")
        docs[D].append(f"pbd{k:02d}")
    for d in docs:
        rng.shuffle(d)
    return [" ".join(d) for d in docs]


def plant(base: list[str], code: str) -> tuple[list[str], list[str]]:
    # Every word of A and B must have df >= 2. C and D mirror S1 and S2 so no
    # sentence word has df == 1. A df == 1 word in A or B is dropped under the
    # cap, changes that document's norm, and the capped lift would differ from
    # the uncapped lift by about 1e-4.
    ctrl = list(base)
    ctrl[A] += " " + S1
    ctrl[C] += " " + S1
    ctrl[B] += " " + S2
    ctrl[D] += " " + S2
    with_code = list(base)
    with_code[A] += f" error code {code} means the power unit failed"
    with_code[C] += " " + S1
    with_code[B] += f" the {code} fault was logged by the supervisor"
    with_code[D] += " " + S2
    return ctrl, with_code


def lift(fn, ctrl, with_code, **kw) -> float:
    return fn(with_code, **kw)[A, B] - fn(ctrl, **kw)[A, B]


def doc_freq(texts, tokenizer) -> dict[str, int]:
    df: dict[str, int] = {}
    for text in texts:
        for term in set(tokenizer(text)):
            df[term] = df.get(term, 0) + 1
    return df


def test_corpus_is_deterministic_and_exceeds_the_cap():
    assert build_corpus() == build_corpus()
    _, with_code = plant(build_corpus(), "ZZ-ZYXW")
    df = doc_freq(with_code, _rs_tokens)
    assert len(df) > CAP
    assert sum(1 for v in df.values() if v == 1) == 0
    assert sum(1 for v in df.values() if v >= 3) < CAP
    assert sum(1 for v in df.values() if v == 2) < CAP


def test_capped_lift_equals_uncapped_lift_for_late_alphabet_code():
    base = build_corpus()
    for code in ("ZZ-ZYXW", "AA-0001"):
        ctrl, with_code = plant(base, code)
        capped = lift(_bm25_cosine, ctrl, with_code)
        uncapped = lift(_bm25_cosine, ctrl, with_code, max_features=10**9)
        assert uncapped > 0, code
        assert abs(capped - uncapped) <= 1e-9, (code, capped, uncapped)


def test_hsi_bm25_similarity_is_higher_with_the_planted_code():
    ctrl, with_code = plant(build_corpus(), "ZZ-ZYXW")
    assert compute_bm25_similarity(with_code)[A, B] > compute_bm25_similarity(ctrl)[A, B]


def test_hsi_term_count_matrix_rare_first_keeps_planted_tokens():
    _, with_code = plant(build_corpus(), "ZZ-ZYXW")
    df = doc_freq(with_code, tokenize)
    _, vocab = _term_count_matrix(with_code, max_features=CAP, cap_order="rare_first")
    assert "zz" in vocab
    assert "zyxw" in vocab
    assert len(vocab) == CAP
    assert all(df[t] >= 2 for t in vocab)


def test_hsi_term_count_matrix_default_order_is_unchanged():
    import pytest

    _, with_code = plant(build_corpus(), "ZZ-ZYXW")
    total: dict[str, int] = {}
    for text in with_code:
        for term in tokenize(text):
            total[term] = total.get(term, 0) + 1
    expected = sorted(sorted(total, key=lambda t: (-total[t], t))[:CAP])
    _, vocab = _term_count_matrix(with_code, max_features=CAP)
    assert vocab == expected
    with pytest.raises(ValueError):
        _term_count_matrix(with_code, max_features=CAP, cap_order="bogus")
