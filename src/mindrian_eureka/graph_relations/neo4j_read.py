"""Optional read-only Neo4j snapshot adapter. MindrianOS must authorize the connection and scope."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .common import DEFAULT_LABELS, SEMANTIC_TYPES, assert_read_only, build_snapshot

_QUERY_DIR = Path(__file__).resolve().parents[1] / "data" / "graph_relations"


def read_snapshot(*, labels: list[str] | None = None, types: list[str] | None = None) -> dict[str, Any]:
    try:
        from neo4j import GraphDatabase, READ_ACCESS
    except ImportError as exc:
        raise RuntimeError("Neo4j support is optional; install mindrian-eureka[neo4j]") from exc
    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not all((uri, user, password)):
        raise RuntimeError("Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in the local process environment")
    label_filter, type_filter = labels or DEFAULT_LABELS, types or SEMANTIC_TYPES
    node_query = assert_read_only((_QUERY_DIR / "snapshot_nodes.cypher").read_text(encoding="utf-8"))
    edge_query = assert_read_only((_QUERY_DIR / "snapshot_edges.cypher").read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=os.environ.get("NEO4J_DATABASE"), default_access_mode=READ_ACCESS) as session:
            nodes = [r.data() for r in session.run(node_query, labels=label_filter)]
            if len(nodes) > 10_000:
                raise ValueError("Neo4j snapshot exceeds the 10,000-node analysis limit; narrow labels or scope")
            edges = [r.data() for r in session.run(edge_query, labels=label_filter, types=type_filter)]
            if len(edges) > 50_000:
                raise ValueError("Neo4j snapshot exceeds the 50,000-edge analysis limit; narrow types or scope")
    finally:
        driver.close()
    return build_snapshot(nodes, edges, meta={"source": "neo4j_read_only", "labels": label_filter,
                                              "types": type_filter, "database": os.environ.get("NEO4J_DATABASE"),
                                              "id_policy": "node.id or node.uuid, falling back to Neo4j elementId"})
