"""CLI for read-only relationship discovery on a local graph or explicit snapshot."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import explore, prepare_artifact_bundle, validate_snapshot
from .sme_bridge import analyze as analyze_sme_bridge
from .tasks import (backtest_relationship_methods, compare_bidirectional_topics,
                    rank_evidence_paths, score_bayesian_surprise)
from ..contracts import validate_request, validate_result


def main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-graph", description="Analyze a local graph read-only and return unevidenced relationship candidates.")
    parser.add_argument("--task", choices=("explore", "backtest", "prepare-artifact-bundle", "sme-bridge", "surprise", "btm", "traversal"), default="explore",
                        help="Select one graph-relations method; explore is the integrated candidate pipeline")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--snapshot", help="Existing JSON graph snapshot")
    source.add_argument("--neo4j", action="store_true", help="Read local Neo4j using NEO4J_* environment variables")
    parser.add_argument("--input", help="Task-specific JSON input for surprise, BTM, or traversal")
    parser.add_argument("--labels", help="Comma-separated node labels (default: methodology labels)")
    parser.add_argument("--types", help="Comma-separated relationship types (default: semantic types)")
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--attr", default="problem_type", help="Node category attribute for atypicality/SME mapping")
    parser.add_argument("--text-label", help="Limit semantic comparison to this label")
    parser.add_argument("--focus", help="Focal node ID for bounded graph-neighborhood analysis")
    parser.add_argument("--focus-hops", type=int, default=2, help="Semantic-edge radius around --focus (0..5)")
    parser.add_argument("--null-rounds", type=int, default=8)
    parser.add_argument("--cutoff", help="ISO date/time for temporal backtest; default chooses a dated-edge split")
    parser.add_argument("--objective", help="Discovery objective required for --task prepare-artifact-bundle")
    parser.add_argument("--scope-id", help="MindrianOS-authorized scope reference required for bundle projection")
    parser.add_argument("--base-node", help="Base/focal graph node ID required for --task sme-bridge")
    parser.add_argument("--target-node", help="Target/focal graph node ID required for --task sme-bridge")
    parser.add_argument("--hops", type=int, default=2, help="Neighborhood radius for --task sme-bridge (0..4)")
    parser.add_argument("--rules", choices=("AN", "LS", "MA"), default="AN", help="SME mapping rule set")
    parser.add_argument("--output", default="-", help="Result JSON path, or - for stdout")
    args = parser.parse_args()
    try:
        snapshot = None
        if args.neo4j:
            from .neo4j_read import read_snapshot
            snapshot = read_snapshot(labels=args.labels.split(",") if args.labels else None,
                                     types=args.types.split(",") if args.types else None)
        elif args.snapshot:
            path = Path(args.snapshot)
            if path.stat().st_size > 100 * 1024 * 1024:
                raise ValueError("Snapshot exceeds 100 MiB")
            snapshot = json.loads(path.read_text(encoding="utf-8-sig"))
        if args.task in ("explore", "backtest", "prepare-artifact-bundle", "sme-bridge"):
            if snapshot is None:
                raise ValueError(f"--task {args.task} requires --snapshot or --neo4j")
            validate_snapshot(snapshot)
            if args.task == "explore":
                capability_id = "graph.explore_local_relationships"
                request = {"snapshot": snapshot, "top": args.top, "seed": args.seed, "attr": args.attr,
                           "text_label": args.text_label, "null_rounds": args.null_rounds,
                           "focus_node_id": args.focus, "focus_hops": args.focus_hops}
                request = {key: value for key, value in request.items() if value is not None}
                validate_request(capability_id, request)
                result = explore(snapshot, top=args.top, seed=args.seed, text_label=args.text_label,
                                 null_rounds=args.null_rounds, focus_node_id=args.focus, focus_hops=args.focus_hops,
                                 attr=args.attr)
            elif args.task == "prepare-artifact-bundle":
                capability_id = "graph.prepare_artifact_bundle"
                request = {"snapshot": snapshot, "objective": args.objective, "scope_id": args.scope_id}
                validate_request(capability_id, request)
                result = prepare_artifact_bundle(snapshot, args.objective, args.scope_id)
            elif args.task == "sme-bridge":
                if not args.base_node or not args.target_node:
                    raise ValueError("--task sme-bridge requires --base-node and --target-node")
                capability_id = "graph.map_neighbourhoods"
                request = {"snapshot": snapshot, "base_node_id": args.base_node, "target_node_id": args.target_node,
                           "hops": args.hops, "rules": args.rules, "attr": args.attr}
                validate_request(capability_id, request)
                result = analyze_sme_bridge(snapshot, args.base_node, args.target_node,
                                            hops=args.hops, rules=args.rules, attr=args.attr)
            else:
                capability_id = "graph.backtest_relationship_methods"
                request = {"snapshot": snapshot, "seed": args.seed}
                if args.cutoff is not None:
                    request["cutoff"] = args.cutoff
                validate_request(capability_id, request)
                result = backtest_relationship_methods({"snapshot": snapshot, "cutoff": args.cutoff, "seed": args.seed})
        else:
            if not args.input:
                raise ValueError(f"--task {args.task} requires --input JSON")
            task_path = Path(args.input)
            if task_path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("Task input exceeds 20 MiB")
            payload = json.loads(task_path.read_text(encoding="utf-8-sig"))
            if args.task == "surprise":
                capability_id = "graph.score_bayesian_surprise"
                request = {"claims": payload} if isinstance(payload, list) else payload
                validate_request(capability_id, request)
                result = score_bayesian_surprise(request)
            elif args.task == "btm":
                capability_id = "graph.compare_bidirectional_topics"
                request = payload
                validate_request(capability_id, request)
                result = compare_bidirectional_topics(payload)
            else:
                capability_id = "graph.rank_evidence_paths"
                request = {"paths": payload} if isinstance(payload, list) else payload
                validate_request(capability_id, request)
                result = rank_evidence_paths(request)
        validate_result(capability_id, result)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"eureka-graph: {exc}\n")


if __name__ == "__main__":
    main()
