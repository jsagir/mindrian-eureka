"""Translate engine outcomes into explicit MindrianOS host next steps.

This is guidance for the host workflow, not an invocation of MindrianOS
commands and not authorization to modify room or portfolio state.
"""

from __future__ import annotations


def host_handoff(status: str, outputs: list[dict] | None = None) -> dict:
    outputs = outputs or []
    if status == "completed" and outputs:
        return {
            "state": "awaiting_mindrianos_review",
            "owner": "mindrianos",
            "next_action": "resolve_sources_and_select_candidates",
            "recommended_command": "/mos:find-connections",
            "candidate_ids": [item.get("id") for item in outputs if item.get("id")],
            "sequence": [
                {"action": "resolve_source_refs", "owner": "mindrianos", "required": True},
                {
                    "action": "select_a_bounded_shortlist_and_trace_room_relationships",
                    "owner": "mindrianos",
                    "command": "/mos:find-connections",
                    "required": True,
                },
                {
                    "action": "gather_and_review_supporting_and_counterevidence_if_needed",
                    "owner": "mindrianos",
                    "approval_required_for_external_research": True,
                },
                {
                    "action": "ask_human_to_qualify_candidate_after_evidence_review",
                    "owner": "mindrianos",
                    "command": "/mos:qualify-opportunity",
                    "required": True,
                },
                {
                    "action": "file_only_after_human_decision_using_host_graph_writer",
                    "owner": "mindrianos",
                    "automatic": False,
                },
            ],
            "warning": "Engine candidates and ranking signals are discovery leads, not qualified opportunities.",
        }
    if status == "completed_empty":
        return {
            "state": "review_scope",
            "owner": "mindrianos",
            "next_action": "inspect_coverage_and_decide_whether_to_refine_scope",
            "recommended_command": "/mos:status",
            "automatic_retry": False,
            "warning": "An empty result is not evidence that the room contains no opportunities.",
        }
    if status in {"queued", "running"}:
        return {
            "state": "awaiting_engine_completion",
            "owner": "mindrianos",
            "next_action": "poll_job_or_offer_cancellation",
            "recommended_tool": "scout_status",
        }
    return {
        "state": status,
        "owner": "mindrianos",
        "next_action": "inspect_failure_or_partial_result_before_retrying",
        "recommended_command": "/mos:status",
        "automatic_retry": False,
    }
