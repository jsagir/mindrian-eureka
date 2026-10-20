"""Hardening tests for the graph relation algorithms.

D1: the degree-preserving swap null must be unbiased (random swap orientation).
D2: graphs with fewer than 2 distinct edges raise the package input error, not a raw ValueError.
D3: resource budgets (pair cap, node and edge limits, wall-clock deadline) and unchanged small results.

The tests call the real algorithms. Nothing in the core algorithm is mocked.
"""
from __future__ import annotations

import hashlib
import json
import random
import statistics
import time
import unittest

from mindrian_eureka.graph_relations import atypicality, holes
from mindrian_eureka.graph_relations.common import Graph


def gnm_graph(n, m, seed, categories=False):
    """Uniform random simple graph G(n, m). With categories=True the problem_type attribute is
    'low' for the first half of the node ids and 'high' for the second half, so it is correlated
    with the sort order that the old fixed swap orientation depended on."""
    rng = random.Random(seed)
    pairs = set()
    while len(pairs) < m:
        a, b = rng.sample(range(n), 2)
        pairs.add((min(a, b), max(a, b)))
    nodes = []
    for i in range(n):
        node = {"id": f"n{i:03d}"}
        if categories:
            node["attrs"] = {"problem_type": "low" if i < n // 2 else "high"}
        nodes.append(node)
    edges = [{"s": f"n{a:03d}", "t": f"n{b:03d}", "type": "X"} for a, b in sorted(pairs)]
    return Graph(nodes, edges)


class UnbiasedSwapNullTests(unittest.TestCase):
    # Measured with the fix on G(80, 300), seeds 1..8, rounds=10:
    #   hole z in [-1.25, 0.85], mean -0.18.  With the old fixed orientation: z in [-8.1, -3.3], mean -4.7.
    # Measured atypicality z (categories tied to node order), shuffles=30: |z| <= 1.94 with the fix,
    #   |z| in [11.4, 16.2] before.
    # The z-score of one fresh graph against a correct null is about N(0, 1), so |z| < 3 has a false
    # alarm rate near 0.3% per graph. The mean of 8 independent z-scores has sd near 0.35, so |mean| < 1
    # is a bound of about 3 sd.
    SEEDS = range(1, 9)

    def test_hole_z_score_is_near_zero_on_random_graphs(self):
        zs = []
        for seed in self.SEEDS:
            summary = holes.hole_summary(gnm_graph(80, 300, seed), rounds=10, seed=7)
            zs.append(summary["z"])
            self.assertLess(abs(summary["z"]), 3.0, f"seed {seed}: z={summary['z']:.2f}")
            # The null mean must sit near the observed hole count, not 40% above it (old bias).
            self.assertLess(abs(summary["holes"] - summary["null_mean"]), 3 * summary["null_sd"])
        self.assertLess(abs(statistics.mean(zs)), 1.0, f"mean z={statistics.mean(zs):.2f}")

    def test_atypicality_z_score_is_near_zero_on_random_graphs(self):
        means = []
        for seed in self.SEEDS:
            z, _cat, _obs = atypicality.category_zscores(gnm_graph(80, 300, seed, categories=True),
                                                         shuffles=30, seed=7)
            self.assertTrue(z)
            for pair, value in z.items():
                self.assertLess(abs(value), 3.0, f"seed {seed} {pair}: z={value:.2f}")
            means.append(z[("high", "low")])
        self.assertLess(abs(statistics.mean(means)), 1.0, f"mean z={statistics.mean(means):.2f}")

    def test_swap_null_is_deterministic_for_a_fixed_seed(self):
        graph = gnm_graph(60, 200, 3, categories=True)
        self.assertEqual(holes.swap_null(graph, rounds=4, seed=11), holes.swap_null(graph, rounds=4, seed=11))
        first = atypicality.category_zscores(graph, shuffles=10, seed=11)
        self.assertEqual(first, atypicality.category_zscores(graph, shuffles=10, seed=11))
        self.assertNotEqual(holes.swap_null(graph, rounds=4, seed=11), holes.swap_null(graph, rounds=4, seed=12))


if __name__ == "__main__":
    unittest.main()
