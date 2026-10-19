"""CLI for source-bounded local discovery workflow stages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import discovery_workflows as workflows
from .pitch_analysis import analyze_corpus
from .hsi_engine import run_hsi
from .analogy_fitness import assess_analogy_fitness


HANDLERS = {
    "analysis.compare_text_differences": lambda payload: analyze_corpus(
        payload, legacy=bool(payload.get("legacy", False)),
        input_bytes=json.dumps(payload, ensure_ascii=False).encode("utf-8")),
    "portfolio.find_hybrid_similarity_pairs": run_hsi,
    "analogy.assess_structural_fitness": assess_analogy_fitness,
    "portfolio.inventory_taxonomy_coverage": workflows.portfolio_coverage,
    "portfolio.discover_hsi_whitespace": workflows.discover_hsi_whitespace,
    "analogy.retrieve_mechanism_candidates": workflows.retrieve_mechanisms,
    "research.prepare_multidomain_plan": workflows.plan_multidomain_research,
    "research.group_multidomain_findings": workflows.synthesize_research_findings,
    "analysis.audit_claim_traceability": workflows.critique_proposal,
    "deliberation.prepare_six_hat_review": workflows.structure_debate,
    "graph.package_relationship_proposals": workflows.propose_graph_relationships,
    "discovery.plan_opportunity_scout": workflows.plan_opportunity_discovery,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-workflow", description="Run a local MindrianOS Eureka workflow stage from a JSON bundle.")
    parser.add_argument("capability_id", choices=sorted(HANDLERS))
    parser.add_argument("input", help="JSON request bundle")
    parser.add_argument("--output", default="-", help="Output JSON path, or - for stdout")
    args = parser.parse_args()
    try:
        source = Path(args.input)
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Input bundle exceeds 20 MiB")
        document = json.loads(source.read_text(encoding="utf-8-sig"))
        if not isinstance(document, dict):
            raise ValueError("Input bundle must contain a JSON object")
        result = HANDLERS[args.capability_id](document)
        if args.capability_id == "analysis.compare_text_differences" and result.get("errors"):
            result["status"] = "invalid_input"
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"eureka-workflow: {exc}\n")


if __name__ == "__main__":
    main()
