"""Regression tests for three wrong-number defects. Real engines, no mocks."""

from __future__ import annotations

import unittest

from mindrian_eureka.discovery_workflows import portfolio_coverage


def _coverage(artifact_categories: list[list[str]], taxonomy_ids: list[str]) -> dict:
    return portfolio_coverage({
        "artifacts": [{"id": f"a{i}", "category_ids": ids} for i, ids in enumerate(artifact_categories)],
        "taxonomy": [{"id": cid, "label": cid.upper()} for cid in taxonomy_ids],
    })["coverage"]


class PortfolioCoverageCounts(unittest.TestCase):
    """W1: unrepresented_categories must count categories with no artifact."""

    def test_one_of_three_represented(self):
        cov = _coverage([["x"], ["x"]], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 1)
        self.assertEqual(cov["unrepresented_categories"], 2)
        self.assertAlmostEqual(cov["represented_fraction"], 1 / 3)

    def test_all_covered(self):
        cov = _coverage([["x"], ["y"], ["z", "x"]], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 3)
        self.assertEqual(cov["unrepresented_categories"], 0)
        self.assertEqual(cov["represented_fraction"], 1.0)

    def test_none_covered(self):
        cov = _coverage([[], []], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 0)
        self.assertEqual(cov["unrepresented_categories"], 3)
        self.assertEqual(cov["represented_fraction"], 0.0)

    def test_counts_always_sum_to_taxonomy_size(self):
        cov = _coverage([["a"], ["b"], ["b"]], ["a", "b", "c", "d", "e"])
        self.assertEqual(cov["represented_categories"], 2)
        self.assertEqual(cov["unrepresented_categories"], 3)
        self.assertEqual(cov["represented_categories"] + cov["unrepresented_categories"], 5)


if __name__ == "__main__":
    unittest.main()
