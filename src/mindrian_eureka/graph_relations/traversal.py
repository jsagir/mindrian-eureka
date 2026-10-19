"""Formatting and scoring for read-only traversal results (GraphAgents-style paths).
Standard library only. Input rows are the output of cypher/traversal/path_*.cypher.
Rule: confidence that is absent stays unknown. Nothing is imputed or converted to a number."""
from __future__ import annotations

import re

TIER_ORDER = {"low": 0, "medium": 1, "high": 2}
_MARKER = re.compile(r"^source-[a-z-]+$")


def real_evidence(edge: dict):
    """Evidence text, or None. Stored markers such as 'source-feeds-into' name an import source, not a quote."""
    ev = edge.get("evidence")
    if not isinstance(ev, str) or not ev.strip() or _MARKER.match(ev.strip()):
        return None
    return ev.strip()


def confidence_of(edge: dict):
    """Return (value, kind). kind is 'float', 'tier' or 'unknown'."""
    c = edge.get("confidence")
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return float(c), "float"
    t = edge.get("pws_confidence")
    if isinstance(t, str) and t.lower() in TIER_ORDER:
        return t.lower(), "tier"
    return None, "unknown"


def summarize_path(row: dict) -> dict:
    edges = row.get("edges", [])
    scored = [confidence_of(e) for e in edges]
    unknown = sum(1 for _, k in scored if k == "unknown")
    floats = [v for v, k in scored if k == "float"]
    tiers = [v for v, k in scored if k == "tier"]
    weakest_float = min(floats) if floats else None
    weakest_tier = min(tiers, key=TIER_ORDER.get) if tiers else None
    if not edges:
        status = "empty"
    elif unknown == 0:
        status = "fully_scored"
    elif unknown == len(edges):
        status = "unscored"
    else:
        status = "partially_scored"
    return {
        "hops": row.get("hops", len(edges)),
        "n_edges": len(edges),
        "n_unknown": unknown,
        "status": status,
        "weakest_float": weakest_float,
        "weakest_tier": weakest_tier,
        "n_with_evidence": sum(1 for e in edges if real_evidence(e)),
        "n_quarantine_tagged": sum(1 for e in edges if e.get("quarantine_source")),
    }


def rank_paths(rows):
    """Shorter first, then fewer unknown edges, then more evidence. No weighting by invented scores."""
    out = []
    for r in rows:
        s = summarize_path(r)
        out.append({**r, "summary": s})
    out.sort(key=lambda r: (r["summary"]["hops"], r["summary"]["n_unknown"], -r["summary"]["n_with_evidence"]))
    return out


def _conf_text(e) -> str:
    v, k = confidence_of(e)
    return "unknown" if k == "unknown" else str(v)


def render_markdown(rows, title="Traversal result") -> str:
    ranked = rank_paths(rows)
    if not ranked:
        return f"## {title}\n\nNo path found within the limits. This is a finding about the graph, not a failure: the two ends are not connected by semantic edges inside the hop and hub limits.\n"
    lines = [f"## {title}", ""]
    for i, r in enumerate(ranked, 1):
        s = r["summary"]
        names = " -> ".join(n["name"] for n in r["nodes"])
        lines.append(f"### Path {i}: {names}")
        lines.append(f"Hops {s['hops']}. Status: {s['status']}. Unknown-confidence edges: {s['n_unknown']} of {s['n_edges']}.")
        for e in r["edges"]:
            ev = real_evidence(e)
            ev_txt = f" Evidence: {str(ev)[:160]}" if ev else " Evidence: none stored."
            lines.append(f"- {e['from']} --{e['type']}--> {e['to']} (confidence: {_conf_text(e)}).{ev_txt}")
        if s["n_quarantine_tagged"]:
            lines.append(f"Note: {s['n_quarantine_tagged']} edge(s) carry a quarantine_source tag (bulk import). Treated as present, not as verified.")
        lines.append("")
    return "\n".join(lines)
