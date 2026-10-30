import unittest
import json
import asyncio
import importlib.util
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import tomllib
from unittest.mock import patch

from mindrian_eureka.graph_relations.common import assert_read_only
from mindrian_eureka.graph_relations.runner import GraphInputError, explore, prepare_artifact_bundle
from mindrian_eureka.graph_relations.sme_bridge import analyze as analyze_sme_bridge
from mindrian_eureka.workflow_handlers import HANDLERS
from mindrian_eureka.discovery_workflows import plan_opportunity_discovery
from mindrian_eureka.opportunity_pairs.runner import validate_document as validate_scout_document
from mindrian_eureka.cli import main as eureka_main
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.graph_relations.cli import main as graph_cli_main
from mindrian_eureka.contracts import ContractError, schema_for, validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.opportunity_pairs.mcp_server import scout_capability_contract


def fixture():
    names = dict(zip("abcdef", ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]))
    nodes = [{"id": key, "labels": ["Framework"], "name": names[key], "attrs": {"problem_type": "x"}, "text": names[key]}
             for key in "abcdef"]
    # Induced four-cycle; diagonals a-d and b-c are absent.
    edges = [{"s": a, "t": b, "type": "RELATES_TO"} for a, b in [("a", "b"), ("a", "c"), ("d", "b"), ("d", "c")]]
    return {"nodes": nodes, "edges": edges, "meta": {"snapshot_id": "fixture-1"}}


class GraphRelationshipTests(unittest.TestCase):
    def test_capability_schemas_are_retrievable_from_cli_and_mcp(self):
        tools = asyncio.run(mcp_server.server.list_tools())
        self.assertIn("scout_capability_contract", {tool.name for tool in tools})
        contract = scout_capability_contract("graph.explore_local_relationships")
        self.assertEqual(contract["capability"]["id"], "graph.explore_local_relationships")
        self.assertEqual(contract["schemas"]["input"]["$id"], "eureka.graph-explore-input.v1")
        self.assertEqual(contract["schemas"]["output"]["$id"], "eureka.graph-relationship-result.v1")
        genesis_contract = scout_capability_contract("research.run_genesis_local_plan")
        self.assertEqual(genesis_contract["schemas"]["input"]["$id"], "eureka.genesis-local-plan-input.v1")
        self.assertEqual(genesis_contract["schemas"]["output"]["$id"], "eureka.genesis-local-plan-output.v1")
        tail_contract = scout_capability_contract("portfolio.classify_weak_signal_tail")
        self.assertEqual(tail_contract["schemas"]["input"]["$id"], "eureka.weak-signal-tail-input.v1")
        self.assertEqual(tail_contract["schemas"]["output"]["$id"], "eureka.weak-signal-tail-output.v1")
        critic_contract = scout_capability_contract("portfolio.inspect_candidate_grounding")
        self.assertEqual(critic_contract["schemas"]["input"]["$id"], "eureka.critic-evaluate-input.v1")
        self.assertEqual(critic_contract["schemas"]["output"]["$id"], "eureka.critic-evaluate-output.v1")
        critic_rubric_contract = scout_capability_contract("portfolio.evaluate_critic_rubric")
        self.assertEqual(critic_rubric_contract["schemas"]["input"]["$id"], "eureka.critic-rubric-evaluate-input.v1")
        self.assertEqual(critic_rubric_contract["schemas"]["output"]["$id"], "eureka.critic-rubric-evaluate-output.v1")
        absent = scout_capability_contract("analysis.compare_text_differences")
        self.assertEqual(absent["schemas"]["input"]["$id"], "eureka.text-differences-input.v1")
        self.assertEqual(scout_capability_contract("unknown.id")["status"], "not_found")

        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(
            sys, "argv", ["eureka", "schema", "graph.explore_local_relationships", "--direction", "input"]
        ):
            eureka_main()
        self.assertEqual(json.loads(output.getvalue())["input_schema"]["$id"], "eureka.graph-explore-input.v1")

        catalog = json.loads((Path(__file__).parents[1] / "src/mindrian_eureka/data/capability-catalog.v1.json").read_text())
        runnable = [row for row in catalog["capabilities"] if row.get("status") in {"experimental", "host_brokered"}]
        self.assertEqual(len(runnable), 59)
        for capability in runnable:
            capability_id = capability["id"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch.object(sys, "argv", ["eureka", "capability", capability_id]):
                eureka_main()
            cli_capability = json.loads(output.getvalue())
            self.assertEqual(cli_capability["id"], capability_id)
            self.assertIn("cli", cli_capability["routes"])
            self.assertIn("mcp", cli_capability["routes"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch.object(sys, "argv", ["eureka", "schema", capability_id]):
                eureka_main()
            cli_schemas = json.loads(output.getvalue())
            contract = scout_capability_contract(capability_id)
            self.assertEqual(contract["capability"]["id"], capability_id)
            for direction in ("input", "output"):
                self.assertIn("$schema", cli_schemas[f"{direction}_schema"], (capability_id, direction))
                self.assertEqual(cli_schemas[f"{direction}_schema"], contract["schemas"][direction], (capability_id, direction))

    def test_published_schema_is_enforced_before_cli_and_mcp_workflow_dispatch(self):
        request = {"snapshot": fixture(), "null_rounds": 1}
        validate_request("graph.explore_local_relationships", request)
        with self.assertRaises(ContractError):
            validate_request("graph.explore_local_relationships", {**request, "unexpected": True})
        response = mcp_server.scout_run_workflow("graph.explore_local_relationships", {**request, "unexpected": True})
        self.assertEqual(response["status"], "invalid_input")
        self.assertIn("unexpected", response["error"])
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "invalid.json"
            input_path.write_text(json.dumps({**request, "unexpected": True}), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), patch.object(
                sys, "argv", ["eureka-workflow", "graph.explore_local_relationships", str(input_path)]
            ), self.assertRaises(SystemExit) as error:
                workflow_cli_main()
            self.assertEqual(error.exception.code, 2)
            self.assertIn("unexpected", stderr.getvalue())

    def test_remaining_graph_tasks_share_cli_mcp_handlers_and_contracts(self):
        backtest_snapshot = fixture()
        for index, edge in enumerate(backtest_snapshot["edges"]):
            edge["created_at"] = f"2025-01-0{index + 1}T00:00:00Z"
        requests = {
            "graph.backtest_relationship_methods": {"snapshot": backtest_snapshot, "cutoff": "2025-01-03T00:00:00Z",
                                                     "seed": 7},
            "graph.score_bayesian_surprise": {"scope_id": "room:test", "snapshot_id": "s1", "claims": [
                {"id": "claim-1", "claim": "A test claim", "prior": [0.2, 0.3], "posterior": [0.7, 0.8]}]},
            "graph.compare_bidirectional_topics": {"scope_id": "room:test", "snapshot_id": "s1",
                "texts_a": ["cell signal pathway", "cell receptor signal"],
                "texts_b": ["engine gear torque", "gear torque drive"], "k": 1, "seeds": [3]},
            "graph.rank_evidence_paths": {"scope_id": "room:test", "snapshot_id": "s1", "paths": [
                {"hops": 1, "nodes": [{"name": "A"}, {"name": "B"}],
                 "edges": [{"from": "A", "to": "B", "type": "SUPPORTS", "evidence": "source excerpt"}]}]},
        }
        for capability_id, request in requests.items():
            with self.subTest(capability_id=capability_id):
                validate_request(capability_id, request)
                direct = HANDLERS[capability_id](request)
                validate_result(capability_id, direct)
                self.assertEqual(mcp_server.scout_run_workflow(capability_id, request), direct)
                with tempfile.TemporaryDirectory() as temp_dir:
                    input_path = Path(temp_dir) / "task.json"
                    input_path.write_text(json.dumps(request), encoding="utf-8")
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout), patch.object(
                        sys, "argv", ["eureka-workflow", capability_id, str(input_path)]
                    ):
                        workflow_cli_main()
                    self.assertEqual(json.loads(stdout.getvalue()), direct)
                    if capability_id == "graph.backtest_relationship_methods":
                        graph_snapshot = Path(temp_dir) / "snapshot.json"
                        graph_snapshot.write_text(json.dumps(request["snapshot"]), encoding="utf-8")
                        argv = ["eureka-graph", "--task", "backtest", "--snapshot", str(graph_snapshot),
                                "--cutoff", request["cutoff"], "--seed", str(request["seed"])]
                    else:
                        if capability_id == "graph.score_bayesian_surprise":
                            task_name = "surprise"
                        elif capability_id == "graph.compare_bidirectional_topics":
                            task_name = "btm"
                        else:
                            task_name = "traversal"
                        input_path.write_text(json.dumps(request), encoding="utf-8")
                        argv = ["eureka-graph", "--task", task_name, "--input", str(input_path)]
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout), patch.object(sys, "argv", argv):
                        graph_cli_main()
                    self.assertEqual(json.loads(stdout.getvalue()), direct)

    def test_standalone_graph_algorithms_are_separate_cli_and_mcp_services(self):
        snapshot = fixture()
        requests = {
            "graph.find_structural_gaps": {"snapshot": snapshot, "min_common": 2, "top": 10},
            "graph.find_network_holes": {"snapshot": snapshot, "rounds": 1, "cycle_limit": 100, "top": 10},
            "graph.find_bridge_pairs": {"snapshot": snapshot, "top": 10, "per_node": 5},
            "graph.assess_edge_atypicality": {"snapshot": snapshot, "shuffles": 2},
            "graph.find_semantic_gaps": {"snapshot": snapshot, "min_similarity": 0.0, "top": 10},
        }
        for capability_id, request in requests.items():
            with self.subTest(capability_id=capability_id):
                validate_request(capability_id, request)
                result = HANDLERS[capability_id](request)
                validate_result(capability_id, result)
                self.assertEqual(mcp_server.scout_run_workflow(capability_id, request), result)
                with tempfile.TemporaryDirectory() as temp_dir:
                    input_path = Path(temp_dir) / "request.json"
                    input_path.write_text(json.dumps(request), encoding="utf-8")
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout), patch.object(
                        sys, "argv", ["eureka-workflow", capability_id, str(input_path)]
                    ):
                        workflow_cli_main()
                    self.assertEqual(json.loads(stdout.getvalue()), result)

    def test_cross_domain_research_is_exposed_as_host_brokered_stages(self):
        request = {"stage": "prepare_research_plan", "request": {
            "run_id": "run-1", "stage": "mechanism_discovery", "scope_id": "room:test",
            "queries": [{"query_id": "q-1", "provider": "openalex",
                         "query": "passive cooling mechanism", "why": "Find an analogous mechanism",
                         "intent": "find_mechanism"}],
        }}
        cli_result = HANDLERS["analogy.cross_domain_research"](request)
        validate_result("analogy.cross_domain_research", cli_result)
        mcp_result = mcp_server.scout_run_workflow("analogy.cross_domain_research", request)
        self.assertEqual(cli_result, mcp_result)
        self.assertEqual(cli_result["egress"], "none; host approval and provider execution are still required")
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "stage.json"
            input_path.write_text(json.dumps(request), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "analogy.cross_domain_research", str(input_path)]
            ):
                workflow_cli_main()
            self.assertEqual(json.loads(stdout.getvalue()), cli_result)
        invalid = mcp_server.scout_run_workflow("analogy.cross_domain_research", {
            "stage": "prepare_research_plan", "request": {"queries": []}})
        self.assertEqual(invalid["status"], "invalid_input")

    def test_genesis_local_planner_runs_over_host_graph_projection_on_cli_and_mcp(self):
        text = ("Neural network training uses a model and dataset for classification and regression. "
                "Deep learning systems compare supervised and unsupervised learning methods.")
        request = {"scope_id": "room:test", "snapshot_id": "snapshot-genesis-1",
                   "objective": "Explore alternative futures for machine learning in evidence discovery.",
                   "research_year": 2026,
                   "artifacts": [{"id": "graph-node-1", "source_ref": "mindrian-graph://node/graph-node-1",
                                  "title": "Research system", "text": text}]}
        validate_request("research.run_genesis_local_plan", request)
        cli_result = HANDLERS["research.run_genesis_local_plan"](request)
        validate_result("research.run_genesis_local_plan", cli_result)
        mcp_result = mcp_server.scout_run_workflow("research.run_genesis_local_plan", request)
        self.assertEqual(cli_result["status"], "plan_ready_for_host_review")
        self.assertEqual(cli_result["capability_version"], "0.1.0")
        self.assertEqual(len(cli_result["input_fingerprint"]), 64)
        self.assertGreaterEqual(int(cli_result["run_config"]["runtime"].lstrip("v").split(".", 1)[0]), 22)
        self.assertEqual(cli_result["source_manifest"]["snapshot_id"], "snapshot-genesis-1")
        self.assertEqual(cli_result["source_manifest"]["included_artifacts"][0]["id"], "graph-node-1")
        self.assertTrue(cli_result["personas"])
        self.assertTrue(cli_result["research_plan"]["executionPhases"])
        self.assertNotIn(text, json.dumps(cli_result))
        self.assertIn("performs no search", " ".join(cli_result["limitations"]))
        def stable_projection(result):
            result = json.loads(json.dumps(result))
            result["research_plan"].pop("planId", None)
            result["research_plan"].get("provenance", {}).pop("generatedAt", None)
            result["handoff"].pop("executionId", None)
            result["handoff"].pop("timestamp", None)
            return result
        self.assertEqual(stable_projection(cli_result), stable_projection(mcp_result))
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "genesis.json"
            input_path.write_text(json.dumps(request), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "research.run_genesis_local_plan", str(input_path)]
            ):
                workflow_cli_main()
            self.assertEqual(stable_projection(json.loads(stdout.getvalue())), stable_projection(cli_result))

    def test_genesis_returns_insufficient_domain_signal_instead_of_fake_plan(self):
        request = {"scope_id": "room:test", "objective": "Investigate this system and its future.",
                   "artifacts": [{"id": "n1", "source_ref": "mindrian-graph://node/n1",
                                  "text": "A short description of a general system and its use.", "title": "System"}]}
        result = HANDLERS["research.run_genesis_local_plan"](request)
        validate_result("research.run_genesis_local_plan", result)
        self.assertEqual(result["status"], "insufficient_domain_signal")
        self.assertEqual(result["personas"], [])
        self.assertEqual(result["research_plan"]["status"], "not_generated")

    def test_genesis_rejects_a_false_graph_content_hash(self):
        request = {"scope_id": "room:test", "objective": "Explore the research context.",
                   "artifacts": [{"id": "n1", "source_ref": "mindrian-graph://node/n1", "text": "Graph text",
                                  "sha256": "0" * 64}]}
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            HANDLERS["research.run_genesis_local_plan"](request)

    def test_genesis_mcp_reports_missing_node_runtime_as_blocked(self):
        request = {"scope_id": "room:test", "objective": "Explore the research context.",
                   "artifacts": [{"id": "n1", "source_ref": "mindrian-graph://node/n1",
                                  "text": "A general description of a research system.", "title": "System"}]}
        with patch("mindrian_eureka.workflow_handlers.shutil.which", return_value=None):
            result = mcp_server.scout_run_workflow("research.run_genesis_local_plan", request)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "runtime_unavailable")

    def test_genesis_discloses_truncated_and_omitted_graph_artifacts(self):
        request = {"scope_id": "room:test", "objective": "Explore this supplied graph context for future research opportunities.",
                   "artifacts": [
                       {"id": "large", "source_ref": "mindrian-graph://node/large", "title": "Large", "text": "x " * 100000},
                       {"id": "omitted", "source_ref": "mindrian-graph://node/omitted", "title": "Omitted", "text": "This record will be outside the analysis limit."},
                   ]}
        result = HANDLERS["research.run_genesis_local_plan"](request)
        self.assertTrue(result["source_manifest"]["included_artifacts"][0]["truncated"])
        self.assertEqual(result["source_manifest"]["included_artifacts"][0]["source_chars"], 200000)
        self.assertIn("large", result["source_manifest"]["omitted_artifact_ids"])
        self.assertIn("omitted", result["source_manifest"]["omitted_artifact_ids"])

    def test_weak_signal_tail_matches_latest_eureka_classifier_on_shared_fixture(self):
        items = [{"id": f"T{i}", "attention": i / 40, "growth": ((i * 7) % 41) / 40}
                 for i in range(41)]
        request = {"scope_id": "room:test", "snapshot_id": "tail-snapshot-1",
                   "attention_proxy": "portfolio-relative pairing frequency",
                   "growth_proxy": "case-number-recency", "items": items}
        validate_request("portfolio.classify_weak_signal_tail", request)
        result = HANDLERS["portfolio.classify_weak_signal_tail"](request)
        validate_result("portfolio.classify_weak_signal_tail", result)
        self.assertEqual(result["status"], "completed_analysis")
        self.assertEqual(result["classification"]["cohort_size"], 41)
        self.assertTrue(result["classification"]["tail"])
        self.assertEqual(result["classification"]["growth_proxy"], "case-number-recency")
        mcp_result = mcp_server.scout_run_workflow("portfolio.classify_weak_signal_tail", request)
        self.assertEqual(mcp_result["classification"], result["classification"])
        self.assertEqual(mcp_result["input_fingerprint"], result["input_fingerprint"])
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "tail.json"
            input_path.write_text(json.dumps(request), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "portfolio.classify_weak_signal_tail", str(input_path)]
            ):
                workflow_cli_main()
            self.assertEqual(json.loads(stdout.getvalue()), result)

    def test_weak_signal_tail_marks_sparse_flat_and_noisy_cohorts(self):
        sparse = {"scope_id": "room:test", "attention_proxy": "a", "growth_proxy": "g",
                  "items": [{"id": str(i), "attention": i / 9, "growth": (9 - i) / 9} for i in range(10)]}
        result = HANDLERS["portfolio.classify_weak_signal_tail"](sparse)
        self.assertEqual(result["status"], "insufficient_structure")
        flat = {**sparse, "items": [{**item, "growth": 0.5} for item in sparse["items"]], "min_cohort": 1}
        self.assertEqual(HANDLERS["portfolio.classify_weak_signal_tail"](flat)["status"], "insufficient_structure")
        noisy = {"scope_id": "room:test", "attention_proxy": "a", "growth_proxy": "g",
                 "max_tail_fraction": 0.01,
                 "items": [{"id": f"x{i:02}", "attention": i / 39, "growth": (i * 7 % 40) / 39}
                           for i in range(40)]}
        self.assertEqual(HANDLERS["portfolio.classify_weak_signal_tail"](noisy)["status"], "suspect_noise")

    def test_weak_signal_tail_rejects_nonfinite_axes_and_duplicate_graph_ids(self):
        request = {"scope_id": "room:test", "attention_proxy": "a", "growth_proxy": "g",
                   "items": [{"id": "same", "attention": float("nan"), "growth": 0.5}]}
        with self.assertRaisesRegex(ValueError, "attention must be finite"):
            HANDLERS["portfolio.classify_weak_signal_tail"](request)
        request["items"] = [{"id": "same", "attention": 0.5, "growth": 0.5},
                            {"id": "same", "attention": 0.6, "growth": 0.7}]
        with self.assertRaisesRegex(ValueError, "duplicate item IDs"):
            HANDLERS["portfolio.classify_weak_signal_tail"](request)

    def test_critic_stage_a_prepare_and_inspect_match_cli_mcp_routes(self):
        mechanism = "The COX enzyme inhibits Prostaglandin receptors in tissue"
        prep_request = {"candidate": {"mechanismText": mechanism}}
        validate_request("portfolio.prepare_candidate_critic", prep_request)
        prepared = HANDLERS["portfolio.prepare_candidate_critic"](prep_request)
        validate_result("portfolio.prepare_candidate_critic", prepared)
        self.assertEqual(prepared, mcp_server.scout_run_workflow("portfolio.prepare_candidate_critic", prep_request))
        evaluate_request = {
            "candidate_id": "candidate-01", "source_node_id": "node-7", "scope_id": "room:test",
            "snapshot_id": "snapshot-critic-1",
            "candidate": {"text": mechanism, "mechanismText": mechanism,
                          "mappingStatement": "The mechanism may transfer across these distinct systems.",
                          "sourceDomainTag": "medicine", "targetDomainTag": "biology"},
            "embedding": {"model": "mindrian-local-test-v1",
                          "vectors": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                          "text_sha256": prepared["mechanism_variant_sha256"]},
            "nearest_neighbors": [{"node_id": "node-8", "similarity": 0.2}],
            "source_refs": ["mindrian-graph://node/node-7"],
        }
        validate_request("portfolio.inspect_candidate_grounding", evaluate_request)
        result = HANDLERS["portfolio.inspect_candidate_grounding"](evaluate_request)
        validate_result("portfolio.inspect_candidate_grounding", result)
        self.assertEqual(result, mcp_server.scout_run_workflow("portfolio.inspect_candidate_grounding", evaluate_request))
        self.assertEqual(result["status"], "passed_deterministic_gates")
        self.assertEqual(result["host_context"]["snapshot_id"], "snapshot-critic-1")
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "critic.json"
            input_path.write_text(json.dumps(evaluate_request), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "portfolio.inspect_candidate_grounding", str(input_path)]
            ):
                workflow_cli_main()
            self.assertEqual(json.loads(stdout.getvalue()), result)
        rubric_request = {"candidate_id": "candidate-01", "source_node_id": "node-7", "scope_id": "room:test",
            "snapshot_id": "snapshot-critic-1", "candidate": evaluate_request["candidate"],
            "stage_a_result": result}
        rubric = HANDLERS["portfolio.prepare_critic_rubric"](rubric_request)
        validate_result("portfolio.prepare_critic_rubric", rubric)
        self.assertEqual(rubric, mcp_server.scout_run_workflow("portfolio.prepare_critic_rubric", rubric_request))
        rubric_eval = {**rubric_request, "source_node_id": "node-7",
            "prompt_sha256": rubric["prompt_sha256"], "judge_model": "mindrian-local-test-judge",
            "judge_responses": {"neutral": {key: True for key in "abcdef"},
                                "adversarial": {key: True for key in "abcdef"}}}
        rubric_result = HANDLERS["portfolio.evaluate_critic_rubric"](rubric_eval)
        validate_result("portfolio.evaluate_critic_rubric", rubric_result)
        self.assertEqual(rubric_result, mcp_server.scout_run_workflow("portfolio.evaluate_critic_rubric", rubric_eval))
        self.assertEqual(rubric_result["verdict"], "transferable")
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "critic-rubric.json"
            input_path.write_text(json.dumps(rubric_eval), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "portfolio.evaluate_critic_rubric", str(input_path)]
            ):
                workflow_cli_main()
            self.assertEqual(json.loads(stdout.getvalue()), rubric_result)
        invalid = json.loads(json.dumps(evaluate_request))
        invalid["embedding"]["text_sha256"][0] = "0" * 64
        response = mcp_server.scout_run_workflow("portfolio.inspect_candidate_grounding", invalid)
        self.assertEqual(response["status"], "invalid_input")

    def test_discovery_planner_can_select_genesis_and_tail_with_host_dependencies(self):
        result = plan_opportunity_discovery({"objective": "Explore an uncertain future from local graph knowledge",
            "capability_ids": ["graph.prepare_artifact_bundle", "research.run_genesis_local_plan",
                               "portfolio.classify_weak_signal_tail"]})
        by_id = {row["capability_id"]: row for row in result["steps"]}
        self.assertIn("graph.prepare_artifact_bundle", by_id["research.run_genesis_local_plan"]["depends_on"])
        self.assertIn("Theo review before approved research execution",
                      by_id["research.run_genesis_local_plan"]["depends_on"])
        self.assertIn("precomputed, labeled attention and growth signals",
                      by_id["portfolio.classify_weak_signal_tail"]["depends_on"][0])

    def test_readonly_query_guard(self):
        assert_read_only("MATCH (n) RETURN n")
        with self.assertRaises(ValueError):
            assert_read_only("MATCH (n) SET n.x=1 RETURN n")

    def test_proposals_are_pending_and_exclude_existing_edges(self):
        result = explore(fixture(), top=20, seed=3, null_rounds=2)
        self.assertEqual(result["status"], "completed_analysis")
        self.assertEqual(result["snapshot_id"], "fixture-1")
        self.assertEqual(result["capability_version"], "0.1.0")
        self.assertEqual(result["input_fingerprint"], explore(fixture(), top=20, seed=3, null_rounds=2)["input_fingerprint"])
        self.assertEqual(result["run_config"]["seed"], 3)
        self.assertTrue(all(row["status"] == "proposed" and not row["evidence"] for row in result["proposals"]))
        self.assertTrue(all({row["s"], row["t"]} != {"a", "b"} for row in result["proposals"]))
        self.assertTrue(any({row["s"], row["t"]} == {"a", "d"} for row in result["proposals"]))

    def test_bad_bounds_rejected(self):
        with self.assertRaises(ValueError):
            explore(fixture(), top=0)
        malformed = fixture()
        malformed["edges"].append({"s": "a", "t": "unknown", "type": "RELATES_TO"})
        with self.assertRaises(GraphInputError):
            explore(malformed)

    def test_focus_projection_discloses_boundary_and_omissions(self):
        result = explore(fixture(), focus_node_id="a", focus_hops=1, null_rounds=1)
        self.assertEqual(result["focus_projection"]["included_node_ids"], ["a", "b", "c"])
        self.assertEqual(result["focus_projection"]["omitted_node_count"], 3)
        self.assertEqual(result["summary"]["nodes"], 3)
        with self.assertRaises(ValueError):
            explore(fixture(), focus_node_id="missing")

    def test_graph_results_preserve_host_scope_and_reject_scope_mismatch(self):
        snapshot = fixture()
        snapshot["meta"].update({"scope_id": "room:active", "projection_version": "mindrianos.graph.v1"})
        result = explore(snapshot, null_rounds=1)
        validate_result("graph.explore_local_relationships", result)
        self.assertEqual(result["scope_id"], "room:active")
        bundle = prepare_artifact_bundle(snapshot, "Explore this graph", "room:active")
        self.assertEqual(bundle["scope_id"], "room:active")
        with self.assertRaisesRegex(GraphInputError, "does not match"):
            prepare_artifact_bundle(snapshot, "Explore this graph", "room:other")

    def test_mindrianos_local_graph_projection_runs_through_eureka_mcp(self):
        # This is the wire shape emitted by MindrianOS eureka_graph_project:
        # local graph identity and authorization stay with the host, while the
        # engine receives only the bounded snapshot and returns proposals.
        snapshot = {
            "nodes": [
                {"id": key, "labels": ["Research"], "name": name,
                 "text": f"{name} studies biological systems, sensing, and adaptive control.",
                 "attrs": {"review_status": "accepted"},
                 "source_ref": f"mindrian-graph://node/{key}",
                 "text_sha256": "a" * 64, "text_truncated": False}
                for key, name in zip("abcdef", ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"])
            ],
            "edges": [{"s": a, "t": b, "type": "RELATES_TO"}
                      for a, b in [("a", "b"), ("a", "c"), ("d", "b"), ("d", "c")]],
            "meta": {
                "scope_id": "room:mindrian-test", "snapshot_id": "mindrian-snapshot-42",
                "projection_version": "mindrian.engine-graph-projection.v1",
                "selection_policy": "explicit_node_ids_only", "edge_policy": "induced_edges_only",
                "complete": True,
                "omissions": {"requested_nodes": 6, "missing_nodes": 0, "excluded_system_nodes": 0,
                              "empty_text_nodes": 0, "text_truncated_nodes": 0, "edges_truncated": False},
                "source_text_is_untrusted": True,
            },
        }
        request = {"snapshot": snapshot, "top": 20, "null_rounds": 1}
        response = mcp_server.scout_run_workflow("graph.explore_local_relationships", request)
        validate_result("graph.explore_local_relationships", response)
        self.assertEqual(response["status"], "completed_analysis")
        self.assertEqual(response["graph_access"], "read_only_snapshot")
        self.assertEqual(response["scope_id"], "room:mindrian-test")
        self.assertEqual(response["snapshot_id"], "mindrian-snapshot-42")
        self.assertTrue(all(row["status"] == "proposed" for row in response["proposals"]))
        self.assertTrue(all(not row["evidence"] for row in response["proposals"]))
        self.assertIn("Human review and source-backed validation", " ".join(response["limitations"]))

    def test_graph_projection_is_accepted_by_existing_scout_contract(self):
        snapshot = fixture()
        snapshot["nodes"][0]["attrs"]["path"] = "C:/private/research/source.pdf"
        bundle = prepare_artifact_bundle(snapshot, "Find links worth investigating", "room:test")
        validate_result("graph.prepare_artifact_bundle", bundle)
        validate_scout_document(bundle)
        self.assertEqual(bundle["capability_id"], "graph.prepare_artifact_bundle")
        self.assertEqual(bundle["handoff"]["next_capability"], "opportunity.synthesize_discovery_signals")
        self.assertTrue(all(row["source_ref"].startswith("mindrian-graph://node/") for row in bundle["artifacts"]))
        self.assertNotIn("C:/private", json.dumps(bundle))

    def test_discovery_signal_handoff_schema_rejects_malformed_projection_and_vectors(self):
        from mindrian_eureka.contracts import ContractError, validate_request

        bundle = prepare_artifact_bundle(fixture(), "Find links worth investigating", "room:test")
        validate_request("opportunity.synthesize_discovery_signals", bundle)

        malformed_projection = {**bundle, "projection": {**bundle["projection"], "artifact_count": "many"}}
        with self.assertRaises(ContractError):
            validate_request("opportunity.synthesize_discovery_signals", malformed_projection)

        malformed_vectors = {**bundle, "dense_vectors": {bundle["artifacts"][0]["id"]: []}}
        with self.assertRaises(ContractError):
            validate_request("opportunity.synthesize_discovery_signals", malformed_vectors)

    def test_mindrian_graph_artifact_projection_feeds_genesis_without_room_access(self):
        snapshot = {"nodes": [
            {"id": f"n{i}", "labels": ["Research"], "name": f"Node {i}", "text":
             "Neural network training model dataset classification regression deep learning supervised learning."}
            for i in range(2)
        ], "edges": [], "meta": {"snapshot_id": "mos-room-snapshot-7"}}
        projection = prepare_artifact_bundle(snapshot, "Explore future machine learning opportunities", "room:authorized")
        request = {**projection, "research_year": 2026}
        validate_request("research.run_genesis_local_plan", request)
        result = HANDLERS["research.run_genesis_local_plan"](request)
        validate_result("research.run_genesis_local_plan", result)
        self.assertEqual(result["source_manifest"]["snapshot_id"], "mos-room-snapshot-7")
        self.assertEqual(result["input_fingerprint"], HANDLERS["research.run_genesis_local_plan"](request)["input_fingerprint"])
        self.assertEqual({row["id"] for row in result["source_manifest"]["included_artifacts"]}, {"n0", "n1"})
        self.assertNotIn("room.db", json.dumps(result))

    def test_graph_sme_bridge_uses_bundled_engine_and_keeps_proposals_unaccepted(self):
        snapshot = {
            "meta": {"snapshot_id": "sme-fixture"},
            "nodes": [{"id": key, "name": key, "attrs": {"problem_type": "process"}} for key in "abcdef"],
            "edges": [{"s": "a", "t": "b", "type": "ENABLES"}, {"s": "b", "t": "c", "type": "INFORMS"},
                      {"s": "d", "t": "e", "type": "ENABLES"}, {"s": "e", "t": "f", "type": "INFORMS"}],
        }
        result = analyze_sme_bridge(snapshot, "a", "d", hops=2)
        self.assertEqual(result["capability_id"], "graph.map_neighbourhoods")
        self.assertEqual(result["snapshot_id"], "sme-fixture")
        snapshot["meta"]["scope_id"] = "room:sme"
        result = analyze_sme_bridge(snapshot, "a", "d", hops=2)
        self.assertEqual(result["scope_id"], "room:sme")
        self.assertGreater(result["mapping"]["match_count"], 0)
        self.assertTrue(all(proposal["status"] == "proposed" and proposal["evidence"] == []
                            for match in result["mapping"]["matches"] for proposal in match["proposals"]))
        validate_result("graph.map_neighbourhoods", result)

    def test_analogy_whitespace_runs_as_source_scoped_cli_mcp_method(self):
        request = {
            "snapshot_id": "analogy-fixture-v1", "mode": "percentile", "min_corpus": 5,
            "artifacts": [
                {"id": "source", "title": "Source mechanism", "section": "biology", "vector": [1, 0]},
                {"id": "target", "title": "Target problem", "section": "engineering", "vector": [0, 1]},
                {"id": "other", "title": "Unrelated room record", "section": "other", "vector": [-1, -1]},
            ],
            "baselines": [{"id": "framework-1", "name": "Feedback control", "vector": [1, 1]}],
            "analogy_edges": [{"source_id": "source", "target_id": "target", "analogy_distance": "far", "structural_fitness": 0.72}],
        }
        cli_result = HANDLERS["analogy.discover_transfer_whitespace"](request)
        validate_result("analogy.discover_transfer_whitespace", cli_result)
        mcp_result = mcp_server.scout_run_workflow("analogy.discover_transfer_whitespace", request)
        cli_result["metadata"].pop("timestamp", None)
        mcp_result["metadata"].pop("timestamp", None)
        self.assertEqual(cli_result, mcp_result)
        self.assertEqual(cli_result["metadata"]["source"], "host-analogy-edges")
        self.assertEqual(cli_result["snapshot_id"], "analogy-fixture-v1")
        self.assertTrue(cli_result["input_fingerprint"].startswith("sha256:"))
        self.assertEqual(cli_result["zones"][0]["nearest_other_artifact"]["artifact"], "other")
        self.assertEqual(cli_result["zones"][0]["verification"]["novelty_check"], "not_checked")
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "whitespace.json"
            input_path.write_text(json.dumps(request), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch.object(
                sys, "argv", ["eureka-workflow", "analogy.discover_transfer_whitespace", str(input_path)]
            ):
                workflow_cli_main()
            cli_json = json.loads(stdout.getvalue())
            self.assertEqual(cli_json["capability_id"], "analogy.discover_transfer_whitespace")
            self.assertEqual(cli_json["zones"][0]["source_artifact"], "source")

    def test_shared_workflow_handlers_are_registered_for_cli_and_mcp(self):
        tool_names = {tool.name for tool in asyncio.run(mcp_server.server.list_tools())}
        catalog = json.loads((Path(__file__).parents[1] / "src/mindrian_eureka/data/capability-catalog.v1.json").read_text())
        by_id = {capability["id"]: capability for capability in catalog["capabilities"]}
        scripts = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]["scripts"]
        self.assertIn("eureka-workflow", scripts)
        for capability_id in HANDLERS:
            self.assertIn(capability_id, by_id)
            self.assertIn("CLI", by_id[capability_id]["surface"])
            self.assertIn("MCP", by_id[capability_id]["surface"])
        for capability in catalog["capabilities"]:
            for direction in ("input", "output"):
                if capability.get(f"{direction}_schema"):
                    schema = schema_for(capability["id"], direction)
                    self.assertIsInstance(schema, dict, (capability["id"], direction))
        runnable = [item for item in catalog["capabilities"]
                    if item.get("status") in {"experimental", "host_brokered"}
                    and any(surface in item.get("surface", []) for surface in ("CLI", "MCP"))]
        for capability in runnable:
            self.assertTrue(capability.get("input_schema"), capability["id"])
            self.assertTrue(capability.get("output_schema"), capability["id"])
        data_root = Path(__file__).parents[1] / "src/mindrian_eureka/data"
        graph_caps = [item for item in catalog["capabilities"] if item["id"].startswith("graph.") and item["id"] not in {
            "graph.package_relationship_proposals"}]
        for capability in graph_caps:
            self.assertIn("version", capability)
            for schema_key in ("input_schema", "output_schema"):
                schema_path = data_root / capability[schema_key]
                self.assertTrue(schema_path.is_file(), schema_path)
                json.loads(schema_path.read_text())

        scripts = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]["scripts"]
        for legacy, descriptive in (("eureka-rs", "eureka-pair-scout"),
                                    ("eureka-sme", "eureka-structure-mapping"),
                                    ("eureka-omm", "eureka-decision-sequences"),
                                    ("eureka-scout", "eureka-signal-scout"),
                                    ("eureka-omm-web", "eureka-decision-sequences-web")):
            self.assertIn(legacy, scripts)
            self.assertEqual(scripts[legacy], scripts[descriptive], (legacy, descriptive))
        direct_cli = {
            "opportunity.find_cross_domain_pairs": {"eureka-pair-scout"},
            "opportunity.synthesize_discovery_signals": {"eureka-signal-scout"},
            "analogy.map_structure": {"eureka-structure-mapping"},
            "analogy.cross_domain_research": {"eureka-structure-mapping"},
            "decision.compare_sequence_patterns": {"eureka-decision-sequences"},
            "decision.fit_sequence_patterns": {"eureka-decision-sequences"},
            "graph.explore_local_relationships": {"eureka-graph", "eureka-workflow"},
            "graph.backtest_relationship_methods": {"eureka-graph"},
            "graph.score_bayesian_surprise": {"eureka-graph"},
            "graph.compare_bidirectional_topics": {"eureka-graph"},
            "graph.rank_evidence_paths": {"eureka-graph"},
            "graph.map_neighbourhoods": {"eureka-graph"},
        }
        for capability in catalog["capabilities"]:
            if "CLI" not in capability.get("surface", []):
                continue
            capability_id = capability["id"]
            route = {"eureka-workflow"} if capability_id in HANDLERS else direct_cli.get(capability_id, set())
            self.assertTrue(route & scripts.keys(), capability_id)
        runnable = [item for item in catalog["capabilities"]
                    if item.get("status") in {"experimental", "host_brokered"}]
        for capability in runnable:
            capability_id = capability["id"]
            routes = capability.get("routes", {})
            self.assertIn("cli", routes, capability_id)
            self.assertIn("mcp", routes, capability_id)
            self.assertIn(routes["cli"].get("executable"), scripts, capability_id)
            self.assertIsInstance(routes["cli"].get("arguments"), list, capability_id)
            self.assertIsInstance(routes["mcp"].get("arguments"), dict, capability_id)
            mcp_route = routes["mcp"].get("tool")
            if capability_id in HANDLERS:
                self.assertEqual(mcp_route, "scout_run_workflow", capability_id)
            else:
                self.assertIn(mcp_route, tool_names, capability_id)

        # Readiness labels are enforcement boundaries, not catalog decoration:
        # blocked/planned jobs must not acquire a callable route by accident.
        non_runnable = [item for item in catalog["capabilities"]
                        if item.get("status") in {"blocked", "planned"}]
        self.assertTrue(non_runnable)
        for capability in non_runnable:
            capability_id = capability["id"]
            self.assertNotIn(capability_id, HANDLERS, capability_id)
            self.assertNotIn("routes", capability, capability_id)
            self.assertIsNone(capability.get("input_schema"), capability_id)
            self.assertIsNone(capability.get("output_schema"), capability_id)
            response = mcp_server.scout_run_workflow(capability_id, {})
            self.assertEqual(response["status"], "blocked_or_not_implemented", capability_id)

        result = HANDLERS["analogy.find_mechanisms"]({
            "problem": "transfer heat using a passive fluid cycle",
            "mechanisms": [{"id": "m1", "domain": "thermal", "mechanism": "passive fluid cycle transfers heat", "source_ref": "fixture:m1"}],
        })
        self.assertEqual(result["capability_id"], "analogy.find_mechanisms")
        self.assertEqual(result["provenance"]["external_research"], "not_performed")
        plan = plan_opportunity_discovery({"objective": "explore future care opportunities", "capability_ids": [
            "analogy.find_mechanisms", "graph.propose_relationships", "graph.map_neighbourhoods", "graph.backtest_relationship_methods"]})
        self.assertEqual([step["capability_id"] for step in plan["steps"]], [
            "analogy.find_mechanisms", "graph.propose_relationships", "graph.map_neighbourhoods", "graph.backtest_relationship_methods"])

    def test_portfolio_coverage_gap_capability_composes_only_supplied_signals(self):
        request = {
            "artifacts": [
                {"id": "a", "category_ids": ["represented"], "title": "A", "vector": [1, 0]},
                {"id": "b", "category_ids": ["represented"], "title": "B", "vector": [0, 1]},
                {"id": "c", "category_ids": [], "title": "C", "vector": [-1, 0]},
            ],
            "taxonomy": [{"id": "represented", "label": "Represented"}, {"id": "thin", "label": "Thin"}],
            "taxonomy_source": "fixture",
        }
        inventory = HANDLERS["portfolio.find_coverage_gaps"](request)
        validate_result("portfolio.find_coverage_gaps", inventory)
        self.assertEqual(inventory["status"], "completed_taxonomy_coverage_scan")
        self.assertIsNone(inventory["room_relative_whitespace"])
        request.update({
            "baseline_frameworks": [{"id": "baseline", "label": "Baseline", "vector": [0.5, 0.5]}],
            "hsi_pairs": [{"left_id": "a", "right_id": "b", "hsi_score": 0.9}],
        })
        combined = HANDLERS["portfolio.find_coverage_gaps"](request)
        validate_result("portfolio.find_coverage_gaps", combined)
        self.assertEqual(combined["status"], "completed_coverage_and_whitespace_scan")
        self.assertEqual(combined["room_relative_whitespace"]["capability_id"], "portfolio.discover_hsi_whitespace")
        self.assertIn("do not prove", combined["interpretation"])

    def test_pitch_diagnostics_combine_local_text_and_evidence_checks(self):
        result = HANDLERS["analysis.critique_pitch"]({
            "pitch": "A system tracks heat and moves it with a passive cycle.",
            "comparisons": [{"id": "compare-1", "a": "A system tracks heat.", "b": "A system monitors heat."}],
            "proposal": "Build a passive thermal transfer product.",
            "claims": [{"id": "claim-1", "text": "The cycle transfers heat", "evidence_ids": ["source-1"],
                        "counterevidence_ids": [], "falsifier": "It fails to transfer heat in a controlled test."}],
            "evidence": [{"id": "source-1", "source_ref": "fixture:thermal-study", "evidence_quote": "Heat moved through the cycle."}],
        })
        self.assertEqual(result["capability_id"], "analysis.critique_pitch")
        self.assertEqual(result["status"], "completed_local_diagnostics")
        self.assertEqual(result["decision"], "not_assessed")
        self.assertTrue(result["pitch_diagnostics"]["pairs"])
        self.assertEqual(result["claim_traceability"]["claims"][0]["support_refs"][0]["id"], "source-1")
        validate_result("analysis.critique_pitch", result)

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "optional MCP server extra is not installed")
    def test_catalog_mcp_surfaces_have_a_registered_route(self):
        from mindrian_eureka.opportunity_pairs import mcp_server

        tool_names = {tool.name for tool in asyncio.run(mcp_server.server.list_tools())}
        direct_routes = {
            "opportunity.find_cross_domain_pairs": {"scout_start", "scout_find_hybrid_similarity_pairs"},
            "opportunity.synthesize_discovery_signals": {"scout_start_opportunity_signal_scout"},
            "analogy.map_structure": {"scout_sme_map"},
            "analogy.cross_domain_research": {"scout_sme_prepare_research", "scout_sme_validate_research_bundle", "scout_sme_map", "scout_sme_finalize"},
            "decision.compare_sequence_patterns": {"decision_compare_sequence_patterns"},
            "decision.fit_sequence_patterns": {"decision_fit_sequence_patterns"},
            "analysis.compare_text_differences": {"scout_compare_text_differences"},
            "portfolio.find_hybrid_similarity_pairs": {"scout_find_hybrid_similarity_pairs"},
            "analogy.assess_structural_fitness": {"scout_assess_analogy_fitness"},
        }
        catalog = json.loads((Path(__file__).parents[1] / "src/mindrian_eureka/data/capability-catalog.v1.json").read_text())
        catalog_by_id = {item["id"]: item for item in catalog["capabilities"]}
        for capability in catalog["capabilities"]:
            if "MCP" not in capability.get("surface", []):
                continue
            capability_id = capability["id"]
            route = capability.get("routes", {}).get("mcp", {}).get("tool")
            self.assertTrue(route, capability_id)
            follow_up_tools = capability.get("routes", {}).get("mcp", {}).get("follow_up_tools", [])
            for follow_up_tool in follow_up_tools:
                self.assertIn(follow_up_tool, tool_names, capability_id)
            if capability_id in HANDLERS:
                self.assertEqual(route, "scout_run_workflow", capability_id)
                self.assertIn(route, tool_names, capability_id)
            else:
                self.assertIn(route, direct_routes.get(capability_id, set()), capability_id)
                self.assertIn(route, tool_names, capability_id)
        for capability_id in ("opportunity.find_cross_domain_pairs", "opportunity.synthesize_discovery_signals"):
            self.assertEqual(catalog_by_id[capability_id]["routes"]["mcp"]["follow_up_tools"],
                             ["scout_status", "scout_result"])
        self.assertIn("--model-path <local-model-path>",
                      catalog_by_id["opportunity.find_cross_domain_pairs"]["routes"]["cli"]["required_options"])
        response = mcp_server.scout_run_workflow("graph.explore_local_relationships", {"snapshot": fixture(), "focus_node_id": "a", "focus_hops": 1, "null_rounds": 1})
        self.assertEqual(response["status"], "completed_analysis")
        invalid = mcp_server.scout_run_workflow("graph.explore_local_relationships", {"snapshot": {"nodes": [], "edges": []}})
        self.assertEqual(invalid["status"], "invalid_input")
        alias = mcp_server.scout_run_workflow("graph.propose_relationships", {"snapshot": fixture(), "null_rounds": 1})
        self.assertEqual(alias["capability_id"], "graph.propose_relationships")
        bundle = mcp_server.scout_run_workflow("graph.prepare_artifact_bundle", {
            "snapshot": fixture(), "objective": "Find relationships worth testing", "scope_id": "room:test"})
        validate_scout_document(bundle)
        self.assertEqual(bundle["handoff"]["next_capability"], "opportunity.synthesize_discovery_signals")

    def test_host_workflow_keeps_room_graph_projection_owned_by_mindrianos(self):
        from mindrian_eureka.opportunity_pairs.mcp_server import scout_host_workflow

        workflow = scout_host_workflow()
        self.assertEqual(workflow["status"], "host_integration_contract")
        self.assertTrue(any("canonical room-local graph" in item for item in workflow["ownership"]["mindrianos"]))
        self.assertTrue(any("ICM run record, graph writes" in item for item in workflow["ownership"]["mindrianos"]))
        self.assertIn("Never let Eureka read room paths", " ".join(workflow["rules"]))

        stages = {stage["id"]: stage for stage in workflow["stages"]}
        projection = stages["prepare_snapshot"]
        self.assertIn("authorized", projection["action"])
        self.assertIn("navigation", projection["action"])
        self.assertIn("visualization-only graph export", projection["action"])

        pair_scan = stages["hsi_pair_whitespace_analysis"]
        self.assertEqual(pair_scan["owner"], "mindrianos")
        self.assertEqual(pair_scan["optional_capability"], "portfolio.discover_hsi_whitespace")
        routing = stages["problem_type_method_routing"]
        self.assertEqual(routing["owner"], "mindrianos")
        self.assertEqual(routing["optional_capability"], "portfolio.interpret_whitespace")
        self.assertIn("same snapshot", routing["action"])
        downstream = stages["downstream_whitespace_analysis"]
        self.assertEqual(downstream["owner"], "mindrianos")
        self.assertEqual(downstream["optional_capability"], "portfolio.discover_rs_whitespace")
        self.assertIn("same snapshot", downstream["action"])


if __name__ == "__main__":
    unittest.main()
