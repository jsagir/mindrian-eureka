"""Hardening tests for the graph relation algorithms.

D1: the degree-preserving swap null must be unbiased (random swap orientation).
D2: graphs with fewer than 2 distinct edges raise the package input error, not a raw ValueError.
D3: resource budgets (pair cap, node and edge limits, wall-clock deadline) and unchanged small results.

The tests call the real algorithms. Nothing in the core algorithm is mocked.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mindrian_eureka.contracts import ContractError, validate_request
from mindrian_eureka.graph_relations import atypicality, backtest, bridging, common, gaps, holes
from mindrian_eureka.graph_relations.common import Graph, GraphBudgetError
from mindrian_eureka.graph_relations.runner import GraphInputError, explore
from mindrian_eureka.graph_relations.services import (assess_edge_atypicality, find_bridge_pairs,
                                                      find_network_holes, find_structural_gaps)
from mindrian_eureka.graph_relations.tasks import backtest_relationship_methods
from mindrian_eureka.opportunity_pairs import mcp_server


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


def tiny_snapshot(edge_pairs, node_ids="abcd"):
    nodes = [{"id": n, "labels": ["Framework"], "name": n.upper(), "attrs": {"problem_type": "x"}, "text": n}
             for n in node_ids]
    return {"nodes": nodes, "edges": [{"s": a, "t": b, "type": "RELATES_TO"} for a, b in edge_pairs],
            "meta": {"scope_id": "s", "snapshot_id": "t"}}


class TooSmallGraphTests(unittest.TestCase):
    ONE = tiny_snapshot([("a", "b")], "ab")
    # Two directed edges that are the same undirected pair count as ONE distinct edge.
    ONE_PAIR_TWICE = tiny_snapshot([("a", "b"), ("b", "a")], "ab")
    ZERO = tiny_snapshot([], "ab")
    TWO = tiny_snapshot([("a", "b"), ("c", "d")])

    def assert_small_graph_error(self, call):
        with self.assertRaises(GraphInputError) as caught:
            call()
        self.assertIn("at least 2 distinct edges", str(caught.exception))
        self.assertNotIn("Sample larger than population", str(caught.exception))

    def test_nulls_raise_the_package_input_error_below_two_distinct_edges(self):
        for snapshot in (self.ZERO, self.ONE, self.ONE_PAIR_TWICE):
            graph = Graph(snapshot["nodes"], snapshot["edges"])
            self.assert_small_graph_error(lambda: holes.swap_null(graph))
            self.assert_small_graph_error(lambda: atypicality.category_zscores(graph))

    def test_services_and_explore_raise_the_package_input_error(self):
        for snapshot in (self.ZERO, self.ONE, self.ONE_PAIR_TWICE):
            self.assert_small_graph_error(lambda: find_network_holes({"snapshot": snapshot}))
            self.assert_small_graph_error(lambda: assess_edge_atypicality({"snapshot": snapshot}))
            self.assert_small_graph_error(lambda: explore(snapshot))

    def test_workflow_handler_reports_invalid_input_not_failed(self):
        for capability in ("graph.explore_local_relationships", "graph.find_network_holes",
                           "graph.assess_edge_atypicality", "graph.propose_relationships"):
            for snapshot in (self.ZERO, self.ONE, self.ONE_PAIR_TWICE):
                response = mcp_server.scout_run_workflow(capability, {"snapshot": snapshot})
                self.assertEqual(response["status"], "invalid_input", (capability, response))
                self.assertEqual(response["capability_id"], capability)
                self.assertIn("at least 2 distinct edges", response["error"])

    def test_two_edges_are_enough(self):
        self.assertEqual(explore(self.TWO)["status"], "completed_analysis")
        self.assertEqual(find_network_holes({"snapshot": self.TWO})["status"], "completed_analysis")
        self.assertEqual(assess_edge_atypicality({"snapshot": self.TWO})["status"], "completed_analysis")
        response = mcp_server.scout_run_workflow("graph.explore_local_relationships", {"snapshot": self.TWO})
        self.assertEqual(response["status"], "completed_analysis")


def small_dated_snapshot(n=36):
    """A fixed, dated, deterministic snapshot (no random module) for byte-identical result checks."""
    nodes = [{"id": f"n{i:02d}", "labels": ["Framework" if i % 3 else "Concept"], "name": f"Node {i:02d}",
              "attrs": {"problem_type": ("A", "B", "C")[i % 3]}, "text": f"alpha topic {i % 5} beta {i % 7}"}
             for i in range(n)]
    seen, edges = set(), []
    for i in range(n):
        for step in (1, 5, 11, 13):
            j = (i * step + i // 3 + 1) % n
            key = (min(i, j), max(i, j))
            if i == j or key in seen:
                continue
            seen.add(key)
            edges.append({"s": f"n{key[0]:02d}", "t": f"n{key[1]:02d}", "type": "RELATES_TO",
                          "created_at": f"2024-{1 + (i * step) % 12:02d}-{1 + i % 27:02d}"})
    return {"nodes": nodes, "edges": edges, "meta": {"scope_id": "scope", "snapshot_id": "small-1"}}


def bridged_snapshot():
    """Two dense blocks joined through two bridge nodes, so bridge pairs exist."""
    ids = [f"a{i}" for i in range(8)] + [f"b{i}" for i in range(8)] + ["x", "y"]
    nodes = [{"id": i, "name": i.upper(), "labels": ["Framework"]} for i in ids]
    pairs = []
    for block in ("a", "b"):
        for i in range(8):
            for step in (1, 2, 3):
                pairs.append((f"{block}{i}", f"{block}{(i + step) % 8}"))
    for bridge in ("x", "y"):
        pairs += [(bridge, "a0"), (bridge, "a3"), (bridge, "b0"), (bridge, "b4")]
    return {"nodes": nodes, "edges": [{"s": a, "t": b, "type": "X"} for a, b in pairs], "meta": {}}


def small_outputs():
    """Outputs of the real algorithms on the fixed snapshot, for byte-identical comparison.

    Only outputs that do not depend on set iteration order are listed, so the hashes hold across
    processes. (Label propagation, bridge pairs, and explore vary with PYTHONHASHSEED in the
    existing code; that is not part of this change and is checked in-process instead.)"""
    snapshot = small_dated_snapshot()
    graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot["meta"])
    return {
        "backtest_handler": backtest_relationship_methods({"snapshot": snapshot}),
        "backtest_evaluate": backtest.evaluate(graph),
        "structural_gaps": find_structural_gaps({"snapshot": snapshot, "min_common": 1}),
        "betweenness": {k: round(v, 9) for k, v in sorted(bridging.betweenness(graph).items())},
    }


def star_snapshot(leaves):
    nodes = [{"id": "hub"}] + [{"id": f"l{i}"} for i in range(leaves)]
    return {"nodes": nodes, "edges": [{"s": "hub", "t": f"l{i}", "type": "X"} for i in range(leaves)], "meta": {}}


def biclique_snapshot(hubs, leaves):
    """Every hub joins every leaf: each hub has `leaves` neighbours, each leaf has `hubs` neighbours."""
    nodes = [{"id": f"h{i}"} for i in range(hubs)] + [{"id": f"l{i}"} for i in range(leaves)]
    edges = [{"s": f"h{i}", "t": f"l{j}", "type": "X"} for i in range(hubs) for j in range(leaves)]
    return {"nodes": nodes, "edges": edges, "meta": {}}


def timed(call):
    started = time.monotonic()
    try:
        return call(), time.monotonic() - started
    except Exception as exc:  # the caller inspects the error and the elapsed time
        return exc, time.monotonic() - started


SCHEMAS = Path(__file__).resolve().parents[1] / "src" / "mindrian_eureka" / "data" / "schemas"


class PairCapTests(unittest.TestCase):
    def test_star_over_the_pair_cap_is_rejected_quickly(self):
        # 2,001 leaves give 2,001,000 neighbour pairs at the hub, one above the 2,000,000 cap.
        graph = Graph(star_snapshot(2001)["nodes"], star_snapshot(2001)["edges"])
        outcome, elapsed = timed(lambda: gaps.open_triads(graph, min_common=1, hub_cap=5000))
        self.assertIsInstance(outcome, GraphBudgetError)
        self.assertIn("2,001,000 neighbour pairs", str(outcome))
        self.assertLess(elapsed, 2.0)

    def test_the_cap_is_exact(self):
        graph = Graph(star_snapshot(100)["nodes"], star_snapshot(100)["edges"])  # 4,950 pairs at the hub
        rows, skipped = gaps.open_triads(graph, min_common=1, hub_cap=200, max_pairs=4950)
        self.assertEqual((len(rows), skipped), (4950, []))
        with self.assertRaises(GraphBudgetError):
            gaps.open_triads(graph, min_common=1, hub_cap=200, max_pairs=4949)
        # Hubs above hub_cap are skipped, so they do not count against the cap.
        self.assertEqual(gaps.open_triads(graph, min_common=1, hub_cap=50, max_pairs=1)[1], ["hub"])

    def test_default_cap_is_two_million(self):
        self.assertEqual(common.MAX_TRIAD_PAIRS, 2_000_000)

    def test_many_hubs_over_the_cap_are_rejected_by_the_service_and_workflow_path(self):
        # 17 hubs of degree 500 (the largest allowed hub_cap) plus 500 leaves of degree 17:
        # 17 * 124,750 + 500 * 136 = 2,189,150 pairs.
        snapshot = biclique_snapshot(17, 500)
        outcome, elapsed = timed(lambda: find_structural_gaps({"snapshot": snapshot, "hub_cap": 500}))
        self.assertIsInstance(outcome, GraphBudgetError)
        self.assertLess(elapsed, 20.0)
        response, elapsed = timed(lambda: mcp_server.scout_run_workflow(
            "graph.find_structural_gaps", {"snapshot": snapshot, "hub_cap": 500}))
        self.assertEqual(response["status"], "invalid_input")
        self.assertIn("neighbour pairs", response["error"])
        self.assertLess(elapsed, 20.0)

    def test_hub_cap_maximum_is_500_in_schemas_and_service(self):
        for name, path in (("input", ("graph-structural-gaps-input.v1.json",)), ("output", ("structural_gaps-output.v1.json",))):
            document = json.loads((SCHEMAS / path[0]).read_text(encoding="utf-8"))
            node = document["properties"]["hub_cap"] if name == "input" else \
                document["properties"]["run_config"]["properties"]["hub_cap"]
            self.assertEqual(node["maximum"], 500, name)
        snapshot = star_snapshot(3)
        validate_request("graph.find_structural_gaps", {"snapshot": snapshot, "hub_cap": 500})
        with self.assertRaises(ContractError):
            validate_request("graph.find_structural_gaps", {"snapshot": snapshot, "hub_cap": 501})
        with self.assertRaises(GraphInputError):
            find_structural_gaps({"snapshot": snapshot, "hub_cap": 501})

    def test_800_leaf_star_no_longer_runs_for_seconds(self):
        snapshot = star_snapshot(800)
        # Within the new maximum the 800-neighbour hub is skipped as a hub.
        result, elapsed = timed(lambda: find_structural_gaps({"snapshot": snapshot, "hub_cap": 500, "min_common": 1}))
        self.assertEqual(result["skipped_hub_node_ids"], ["hub"])
        self.assertLess(elapsed, 2.0)
        # Above it the request is refused before any work.
        response, elapsed = timed(lambda: mcp_server.scout_run_workflow(
            "graph.find_structural_gaps", {"snapshot": snapshot, "hub_cap": 800, "min_common": 1}))
        self.assertEqual(response["status"], "invalid_input")
        self.assertLess(elapsed, 2.0)


class DeadlineTests(unittest.TestCase):
    def test_tiny_deadline_stops_every_budgeted_algorithm(self):
        snapshot = small_dated_snapshot()
        graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot["meta"])
        calls = {
            "open_triads": lambda: gaps.open_triads(graph, budget_seconds=0),
            "induced_c4": lambda: holes.induced_c4(graph, budget_seconds=0),
            "swap_null": lambda: holes.swap_null(graph, budget_seconds=0),
            "category_zscores": lambda: atypicality.category_zscores(graph, budget_seconds=0),
            "betweenness": lambda: bridging.betweenness(graph, budget_seconds=0),
            "bridge_report": lambda: bridging.bridge_report(graph, budget_seconds=0),
            "backtest.evaluate": lambda: backtest.evaluate(graph, budget_seconds=0),
            "explore": lambda: explore(snapshot, budget_seconds=0),
            "find_structural_gaps": lambda: find_structural_gaps({"snapshot": snapshot}, budget_seconds=0),
            "find_network_holes": lambda: find_network_holes({"snapshot": snapshot}, budget_seconds=0),
            "find_bridge_pairs": lambda: find_bridge_pairs({"snapshot": snapshot}, budget_seconds=0),
            "assess_edge_atypicality": lambda: assess_edge_atypicality({"snapshot": snapshot}, budget_seconds=0),
            "backtest_relationship_methods": lambda: backtest_relationship_methods({"snapshot": snapshot}, budget_seconds=0),
        }
        for name, call in calls.items():
            with self.subTest(name):
                with self.assertRaises(GraphBudgetError) as caught:
                    call()
                self.assertIn("time budget of 0 seconds exceeded", str(caught.exception))

    def test_deadline_interrupts_real_work_instead_of_hanging(self):
        graph = gnm_graph(500, 4000, 1)
        started = time.monotonic()
        with self.assertRaises(GraphBudgetError):
            bridging.betweenness(graph, budget_seconds=0.05)
        # One source search over 500 nodes costs a few milliseconds, so the stop is prompt.
        self.assertLess(time.monotonic() - started, 2.0)

    def test_a_generous_deadline_changes_nothing(self):
        snapshot = small_dated_snapshot()
        first, second = explore(snapshot), explore(snapshot, budget_seconds=600)
        for result in (first, second):
            result["summary"].pop("runtime_seconds")
        self.assertEqual(first, second)

    def test_deadline_budget_must_be_a_finite_non_negative_number(self):
        for bad in (-1, float("nan"), float("inf"), True, "5"):
            with self.subTest(bad), self.assertRaises(GraphInputError):
                common.Deadline(bad)

    def test_default_budget_is_120_seconds(self):
        self.assertEqual(common.DEFAULT_BUDGET_SECONDS, 120.0)
        self.assertEqual(common.Deadline().seconds, 120.0)

    def test_workflow_path_reports_a_typed_non_success_status_with_a_reason(self):
        snapshot = small_dated_snapshot()
        with patch.object(common, "DEFAULT_BUDGET_SECONDS", 0):
            for capability in ("graph.explore_local_relationships", "graph.find_bridge_pairs",
                               "graph.backtest_relationship_methods", "graph.find_network_holes",
                               "graph.find_structural_gaps", "graph.assess_edge_atypicality"):
                with self.subTest(capability):
                    response = mcp_server.scout_run_workflow(capability, {"snapshot": snapshot})
                    self.assertEqual(response["status"], "invalid_input")
                    self.assertEqual(response["capability_id"], capability)
                    self.assertIn("time budget of 0 seconds exceeded", response["error"])


class SizeLimitTests(unittest.TestCase):
    def oversize_nodes(self):
        return {"nodes": [{"id": f"n{i}"} for i in range(2501)], "edges": [], "meta": {}}

    def oversize_edges(self):
        nodes = [{"id": f"n{i}"} for i in range(400)]
        pairs = [(i, j) for i in range(400) for j in range(i + 1, 400)][:12001]
        return {"nodes": nodes, "edges": [{"s": f"n{i}", "t": f"n{j}", "type": "X"} for i, j in pairs], "meta": {}}

    def test_explore_and_backtest_reject_oversize_input(self):
        for label, snapshot in (("nodes", self.oversize_nodes()), ("edges", self.oversize_edges())):
            graph = Graph(snapshot["nodes"], snapshot["edges"])
            for name, call in (("explore", lambda: explore(snapshot)),
                               ("evaluate", lambda: backtest.evaluate(graph)),
                               ("backtest handler", lambda: backtest_relationship_methods({"snapshot": snapshot}))):
                with self.subTest((label, name)):
                    outcome, elapsed = timed(call)
                    self.assertIsInstance(outcome, GraphBudgetError)
                    self.assertIn("2,500 nodes and 12,000 edges", str(outcome))
                    self.assertLess(elapsed, 5.0)

    def test_workflow_path_reports_invalid_input_for_oversize_input(self):
        for capability in ("graph.explore_local_relationships", "graph.backtest_relationship_methods",
                           "graph.propose_relationships"):
            for snapshot in (self.oversize_nodes(), self.oversize_edges()):
                with self.subTest(capability):
                    response = mcp_server.scout_run_workflow(capability, {"snapshot": snapshot})
                    self.assertEqual(response["status"], "invalid_input")
                    self.assertIn("2,500 nodes and 12,000 edges", response["error"])

    def test_limits_match_the_bridge_service(self):
        self.assertEqual((common.MAX_BRIDGE_NODES, common.MAX_BRIDGE_EDGES), (2500, 12000))
        with self.assertRaises(GraphInputError) as caught:
            find_bridge_pairs({"snapshot": self.oversize_nodes()})
        self.assertIn("2,500 nodes and 12,000 edges", str(caught.exception))

    def test_a_narrow_focus_can_analyse_part_of_a_large_snapshot(self):
        snapshot = self.oversize_nodes()
        cluster = [("n0", "n1"), ("n1", "n2"), ("n2", "n3"), ("n3", "n0"), ("n0", "n2")]
        snapshot["edges"] = [{"s": a, "t": b, "type": "X"} for a, b in cluster]
        with self.assertRaises(GraphBudgetError):
            explore(snapshot)
        result = explore(snapshot, focus_node_id="n0", focus_hops=1)
        self.assertEqual(result["status"], "completed_analysis")
        self.assertEqual(result["summary"]["nodes"], 4)


def reference_pref(train):
    """The original preferential-attachment ranking: every non-adjacent pair, fully sorted."""
    ids = sorted(train.nodes)
    cand = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if not train.has_edge(ids[i], ids[j]):
                cand.append(((train.deg(ids[i]) * train.deg(ids[j])), (ids[i], ids[j])))
    cand.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in cand]


# SHA-256 of the canonical JSON of each output on the fixed small snapshot. The values were produced by
# the code before the budgets were added (and the backtest and gap values also by the code before the
# swap-null fix), and are stable across PYTHONHASHSEED values.
SMALL_GOLDEN = {
    "backtest_handler": "7d96b8f3522973bb03fe6e22b06c1125132cd806002e159dc31663c9f9929332",
    "backtest_evaluate": "1f12a408daf40123dd003f06dd44ad212170cb3caf7ff9e3ade3e319876244ad",
    "structural_gaps": "6787856f55f7ab917c6a432e7ce74138c37dcc3cddc6adddfbf20ed9e56d1cec",
    "betweenness": "6491e18d860041edeaaa85bff1fa444186a78544b3f2d24e38de3aecb3723329",
}


class SmallInputResultsUnchangedTests(unittest.TestCase):
    def test_outputs_are_byte_identical_to_the_pre_budget_code(self):
        for name, value in small_outputs().items():
            digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")).encode("utf-8")).hexdigest()
            self.assertEqual(digest, SMALL_GOLDEN[name], name)

    def test_streamed_preferential_attachment_matches_the_full_sort(self):
        snapshot = small_dated_snapshot()
        graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot["meta"])
        train, _future = backtest.split(graph, backtest.choose_cutoff(graph))
        expected = reference_pref(train)
        self.assertEqual(backtest.methods(train)["pref_attachment"](), expected)
        for limit in (0, 1, 10, 200, len(expected), len(expected) + 5):
            self.assertEqual(backtest.methods(train, pref_limit=limit)["pref_attachment"](), expected[:limit], limit)

    def test_backtest_candidate_count_matches_the_full_list(self):
        snapshot = small_dated_snapshot()
        graph = Graph(snapshot["nodes"], snapshot["edges"], snapshot["meta"])
        train, _future = backtest.split(graph, backtest.choose_cutoff(graph))
        result = backtest.evaluate(graph)
        self.assertEqual(result["pref_attachment"]["proposed"], len(reference_pref(train)))
        self.assertEqual(result["pref_attachment"]["proposed"], result["candidate_pairs"])


if __name__ == "__main__":
    unittest.main()
