"""Shared pieces: read-only Cypher guard, snapshot graph model, helpers. Standard library only."""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import time
from collections import Counter, defaultdict

DEFAULT_LABELS = ["Framework", "Technique", "Concept", "ProcessStep", "CaseStudy", "DomainConcept"]
# Semantic relationship types between methodology items. Plumbing types (chunks, mentions, sources,
# part-of) are excluded on purpose: they say where text came from, not how ideas relate.
SEMANTIC_TYPES = [
    "FEEDS_INTO", "LEADS_TO", "COMPLEMENTS", "RELATES_TO", "PREREQUISITE", "USES_TECHNIQUE",
    "ENABLES", "CONTRASTS_WITH", "SUPPORTS", "PRECEDES", "PRODUCES_INPUT_FOR", "INCORPORATES",
    "EXTENDS", "APPLIED_IN", "EQUIPS_WITH", "HAS_TECHNIQUE", "RELATED_TO", "LOOPS_TO",
]
DEFAULT_TEXT_KEYS = ("definition", "description", "core_principles", "key_insight", "lesson", "pws_definition")

_WRITE = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|FOREACH|LOAD\s+CSV|GRANT|DENY|REVOKE|ALTER|"
    r"START|STOP|RENAME|TERMINATE)\b|\bCALL\s*\{|\bapoc\.(create|merge|refactor|periodic|trigger|cypher|"
    r"do|load|export|import)\b|\bdbms\.|\bdb\.(create|drop|constraint|clear)|\bdb\.index\.(?!fulltext\.query|vector\.query)|\bgds\.[a-z.]*"
    r"(write|mutate)\b",
    re.I,
)


def strip_cypher_noise(q: str) -> str:
    q = re.sub(r"/\*.*?\*/", " ", q, flags=re.S)
    q = re.sub(r"//[^\n]*", " ", q)
    q = re.sub(r"'(?:\\.|[^'\\])*'", "''", q)
    q = re.sub(r'"(?:\\.|[^"\\])*"', '""', q)
    q = re.sub(r"`[^`]*`", "``", q)
    return q


def assert_read_only(cypher: str) -> str:
    """Raise ValueError if the statement could write. Conservative: false alarms are fine."""
    clean = strip_cypher_noise(cypher)
    m = _WRITE.search(clean)
    if m:
        raise ValueError(f"read-only guard: forbidden token {m.group(0)!r}")
    if ";" in clean.strip().rstrip(";"):
        raise ValueError("read-only guard: multiple statements")
    return cypher


class GraphInputError(ValueError):
    """The supplied graph scope or analysis options are invalid."""


class GraphBudgetError(GraphInputError):
    """The analysis would exceed, or did exceed, its resource budget (size or wall-clock time).

    It subclasses GraphInputError so every workflow path that already reports GraphInputError as
    invalid_input reports a budget stop the same way, with a clear message instead of a hang."""


# Internal default for the wall-clock budget of one analysis call. Tests override it with the
# budget_seconds keyword.
DEFAULT_BUDGET_SECONDS = 120.0
# Upper bound on neighbour pairs that open_triads may enumerate in one call.
MAX_TRIAD_PAIRS = 2_000_000
# Size limits for analyses that run exact betweenness (explore, backtest). They match the limits of
# the standalone bridge service in services.py.
MAX_BRIDGE_NODES = 2500
MAX_BRIDGE_EDGES = 12000


class Deadline:
    """Monotonic wall-clock deadline. check() raises GraphBudgetError after expiry."""

    def __init__(self, seconds=None):
        seconds = DEFAULT_BUDGET_SECONDS if seconds is None else seconds
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise GraphInputError("budget_seconds must be a finite non-negative number")
        self.seconds = float(seconds)
        self.expires = time.monotonic() + self.seconds

    def check(self, what="graph analysis"):
        if time.monotonic() >= self.expires:
            raise GraphBudgetError(
                f"time budget of {self.seconds:g} seconds exceeded during {what}; narrow the authorized snapshot")


def as_deadline(budget):
    """Accept None (default budget), a number of seconds, or an existing Deadline shared across stages."""
    return budget if isinstance(budget, Deadline) else Deadline(budget)


def require_size(g, max_nodes, max_edges, what):
    if len(g.nodes) > max_nodes or len(g.edges) > max_edges:
        raise GraphBudgetError(
            f"{what} is limited to {max_nodes:,} nodes and {max_edges:,} edges "
            f"(received {len(g.nodes):,} nodes and {len(g.edges):,} edges); narrow the authorized snapshot")


def distinct_pairs(g):
    """Sorted list of distinct undirected node pairs in the graph."""
    return sorted({pair_key(e["s"], e["t"]) for e in g.edges})


def require_rewirable(pairs, what):
    """A double edge swap needs two distinct edges. Fewer cannot be analysed, so say so clearly."""
    if len(pairs) < 2:
        raise GraphInputError(
            f"{what} needs at least 2 distinct edges between different nodes; "
            f"the snapshot has {len(pairs)}. Supply a larger authorized snapshot.")


def pair_key(a, b):
    return (a, b) if a <= b else (b, a)


def stable_id(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " ".join(as_text(x) for x in v)
    return str(v)


class Graph:
    """Snapshot graph. nodes: id, labels[], name, attrs{}, text. edges: s, t, type, created_at."""

    def __init__(self, nodes, edges, meta=None):
        self.nodes = {n["id"]: n for n in nodes}
        seen, self.edges = set(), []
        for e in edges:
            s, t = e["s"], e["t"]
            if s == t or s not in self.nodes or t not in self.nodes:
                continue
            k = (s, t, e.get("type"))
            if k in seen:
                continue
            seen.add(k)
            self.edges.append(e)
        self.meta = meta or {}
        self.adj = defaultdict(set)
        self.out = defaultdict(set)
        for e in self.edges:
            self.adj[e["s"]].add(e["t"])
            self.adj[e["t"]].add(e["s"])
            self.out[e["s"]].add(e["t"])

    def __len__(self):
        return len(self.nodes)

    def deg(self, n):
        return len(self.adj[n])

    def name(self, n):
        return self.nodes[n].get("name") or n

    def label(self, n):
        ls = self.nodes[n].get("labels") or []
        return ls[0] if ls else ""

    def attr(self, n, key):
        v = (self.nodes[n].get("attrs") or {}).get(key)
        if isinstance(v, list):
            v = v[0] if v else None
        return None if v in (None, "") else str(v)

    def has_edge(self, a, b):
        return b in self.adj[a]

    def filtered(self, keep_edge):
        return Graph(list(self.nodes.values()), [e for e in self.edges if keep_edge(e)], self.meta)

    def before(self, cutoff: str):
        """Edges created before cutoff (ISO string). Undated edges count as old."""
        return self.filtered(lambda e: not e.get("created_at") or e["created_at"] < cutoff)

    def type_prior(self):
        """Counter of relationship types per (label_a, label_b), used to suggest a type."""
        prior = defaultdict(Counter)
        for e in self.edges:
            prior[pair_key(self.label(e["s"]), self.label(e["t"]))][e["type"]] += 1
        return prior

    def suggest_type(self, a, b, prior=None):
        prior = prior or self.type_prior()
        c = prior.get(pair_key(self.label(a), self.label(b)))
        return c.most_common(1)[0][0] if c else "RELATES_TO"


def load_snapshot(path) -> Graph:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return Graph(d["nodes"], d["edges"], d.get("meta"))


def build_snapshot(node_rows, edge_rows, text_keys=DEFAULT_TEXT_KEYS, meta=None):
    """Assemble a snapshot from query rows. Node rows: id, labels, name, plus any other columns (kept
    as attrs); a 'text' column is used if present."""
    nodes = []
    for r in node_rows:
        attrs = {k: v for k, v in r.items() if k not in ("id", "labels", "name", "text")}
        nodes.append({"id": r["id"], "labels": r.get("labels") or [], "name": r.get("name") or r["id"],
                      "attrs": attrs, "text": as_text(r.get("text"))})
    edges = [{"s": r["s"], "t": r["t"], "type": r["type"], "created_at": r.get("created_at")} for r in edge_rows]
    return {"nodes": nodes, "edges": edges, "meta": meta or {}}


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def rank_norm(values):
    """Map scores to 0..1 by rank (best = 1). Used to combine incomparable scores."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    out = [0.0] * len(values)
    n = max(1, len(values) - 1)
    for r, i in enumerate(order):
        out[i] = 1.0 - r / n if len(values) > 1 else 1.0
    return out


def hypergeom_z(k, n_a, n_b, n_total):
    """z-score of k shared items between a set of size n_a and one of size n_b out of n_total."""
    if n_total < 3:
        return 0.0
    e = n_a * n_b / (n_total - 1)
    var = n_a * (n_b / (n_total - 1)) * (1 - n_b / (n_total - 1)) * ((n_total - 1 - n_a) / max(1, n_total - 2))
    return (k - e) / math.sqrt(var) if var > 1e-12 else 0.0


def rng(seed):
    return random.Random(seed)
