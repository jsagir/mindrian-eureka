"""Durable local job lifecycle for the Eureka MCP facade."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .algorithm import RunCancelled
from .runner import run_document, task_snapshot_id, validate_document


TERMINAL = {"completed", "completed_empty", "failed", "blocked", "cancelled", "expired"}
RETENTION_SECONDS = 30 * 24 * 60 * 60
MAX_ACTIVE_JOBS = 8


def default_data_dir() -> Path:
    override = os.environ.get("MINDRIAN_EUREKA_DATA_DIR")
    return Path(override).expanduser() if override else Path.home() / ".local" / "share" / "mindrian-eureka"


class JobStore:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or default_data_dir()).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.data_dir, 0o700)
        except OSError:
            pass
        self.db_path = self.data_dir / "jobs.sqlite3"
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                request_hash TEXT NOT NULL,
                request_json TEXT,
                result_json TEXT,
                status TEXT NOT NULL,
                progress TEXT NOT NULL,
                scope_id TEXT,
                snapshot_id TEXT,
                failure_code TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                cancel_requested INTEGER NOT NULL DEFAULT 0
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                at REAL NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS reviews (
                job_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                useful INTEGER NOT NULL,
                direction_correct INTEGER NOT NULL,
                already_known INTEGER NOT NULL,
                note TEXT NOT NULL,
                reviewed_at REAL NOT NULL,
                PRIMARY KEY(job_id,candidate_id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status,created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS jobs_expiry ON jobs(expires_at)")
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass
        self.expire_old()
        self._recover_interrupted()

    def _event(self, db: sqlite3.Connection, job_id: str, status: str, detail: str) -> None:
        db.execute("INSERT INTO job_events(job_id,at,status,detail) VALUES(?,?,?,?)",
                   (job_id, time.time(), status, detail[:300]))

    def _recover_interrupted(self) -> None:
        with self._connect() as db:
            rows = db.execute("SELECT job_id,status FROM jobs WHERE status IN ('running','queued')").fetchall()
            for row in rows:
                if row["status"] == "running":
                    db.execute("UPDATE jobs SET status='failed',progress='interrupted',failure_code='server_restarted',request_json=NULL,updated_at=? WHERE job_id=?",
                               (time.time(), row["job_id"]))
                    self._event(db, row["job_id"], "failed", "Server restarted while this run was active; start a new run.")

    def expire_old(self) -> int:
        now = time.time()
        with self._connect() as db:
            rows = db.execute("SELECT job_id FROM jobs WHERE expires_at<?", (now,)).fetchall()
            db.execute("DELETE FROM jobs WHERE expires_at<?", (now,))
        return len(rows)

    def create(self, request: dict[str, Any], idempotency_key: str | None) -> tuple[str, bool]:
        self.expire_old()
        validate_document({
            key: request[key]
            for key in ("objective", "mode", "artifacts", "scope_id", "research_grant_id")
            if key in request
        })
        request_json = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(request_json.encode()).hexdigest()
        snapshot_id = request.get("snapshot_id") or task_snapshot_id(request)
        now = time.time()
        with self._lock, self._connect() as db:
            if idempotency_key:
                existing = db.execute("SELECT job_id,request_hash FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if existing:
                    if existing["request_hash"] != request_hash:
                        raise ValueError("idempotency_key was already used with a different request")
                    return str(existing["job_id"]), False
            active = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if active >= MAX_ACTIVE_JOBS:
                raise ValueError(f"Local job queue is full (limit {MAX_ACTIVE_JOBS})")
            job_id = "eureka-" + uuid.uuid4().hex
            scope_id = request.get("scope_id")
            db.execute("""INSERT INTO jobs(job_id,idempotency_key,request_hash,request_json,status,progress,
                         scope_id,snapshot_id,created_at,updated_at,expires_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                       (job_id, idempotency_key, request_hash, request_json, "queued", "queued",
                        scope_id, snapshot_id, now, now, now + RETENTION_SECONDS))
            self._event(db, job_id, "queued", "Job accepted; only the supplied artifact bundle will be analyzed.")
        return job_id, True

    def get(self, job_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row and row["expires_at"] < time.time():
                db.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
                row = None
        return dict(row) if row else None

    def queued(self) -> list[str]:
        with self._connect() as db:
            return [str(row[0]) for row in db.execute("SELECT job_id FROM jobs WHERE status='queued' ORDER BY created_at")]

    def request(self, job_id: str) -> dict:
        row = self.get(job_id)
        if not row or not row["request_json"]:
            raise KeyError(job_id)
        return json.loads(row["request_json"])

    def transition(self, job_id: str, status: str, *, progress: str | None = None,
                   result: dict | None = None, failure_code: str | None = None,
                   clear_request: bool = False) -> None:
        now = time.time()
        with self._connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                return
            db.execute("""UPDATE jobs SET status=?,progress=?,result_json=COALESCE(?,result_json),
                         failure_code=?,request_json=CASE WHEN ? THEN NULL ELSE request_json END,updated_at=?
                         WHERE job_id=?""",
                       (status, progress or status,
                        json.dumps(result, ensure_ascii=False, separators=(",", ":")) if result is not None else None,
                        failure_code, int(clear_request), now, job_id))
            self._event(db, job_id, status, progress or status)
            if result and result.get("scope", {}).get("snapshot_id"):
                db.execute("UPDATE jobs SET snapshot_id=? WHERE job_id=?",
                           (result["scope"]["snapshot_id"], job_id))

    def request_cancel(self, job_id: str) -> str:
        with self._connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            if row["status"] in TERMINAL:
                return "already_terminal"
            db.execute("UPDATE jobs SET cancel_requested=1,updated_at=? WHERE job_id=?", (time.time(), job_id))
            return str(row["status"])

    def clear_cancel(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE jobs SET cancel_requested=0 WHERE job_id=?", (job_id,))

    def result(self, job_id: str) -> dict:
        row = self.get(job_id)
        if not row:
            raise KeyError(job_id)
        if not row["result_json"]:
            return {"job_id": job_id, "status": row["status"], "progress": row["progress"], "failure_code": row["failure_code"]}
        return json.loads(row["result_json"])

    def delete(self, job_id: str) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                return False
            if row["status"] not in TERMINAL:
                raise ValueError("Cancel and wait for a running job before deleting it")
            db.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
        with self._connect() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            db.execute("VACUUM")
        return True

    def record_review(self, job_id: str, candidate_id: str, *, useful: bool,
                      direction_correct: bool, already_known: bool, note: str = "") -> dict:
        row = self.get(job_id)
        if not row or not row["result_json"]:
            raise ValueError("Review requires a completed result")
        result = json.loads(row["result_json"])
        candidate_ids = {item.get("id") for item in result.get("outputs", [])}
        if candidate_id not in candidate_ids:
            raise ValueError("candidate_id does not belong to this job")
        with self._connect() as db:
            db.execute("""INSERT INTO reviews(job_id,candidate_id,useful,direction_correct,already_known,note,reviewed_at)
                         VALUES(?,?,?,?,?,?,?) ON CONFLICT(job_id,candidate_id) DO UPDATE SET
                         useful=excluded.useful,direction_correct=excluded.direction_correct,
                         already_known=excluded.already_known,note=excluded.note,reviewed_at=excluded.reviewed_at""",
                       (job_id, candidate_id, int(useful), int(direction_correct), int(already_known), note[:1000], time.time()))
        return {"job_id": job_id, "candidate_id": candidate_id, "saved": True,
                "automatically_applied_to_future_ranking": False}

    def review_summary(self, job_id: str | None = None) -> dict:
        query = "SELECT * FROM reviews" + (" WHERE job_id=?" if job_id else "")
        params = (job_id,) if job_id else ()
        with self._connect() as db:
            reviews = [dict(row) for row in db.execute(query, params)]
            jobs = {row["job_id"]: row["result_json"] for row in db.execute(
                "SELECT job_id,result_json FROM jobs WHERE result_json IS NOT NULL"
            )}
        direction_by_candidate: dict[tuple[str, str], str] = {}
        for review_job, encoded in jobs.items():
            try:
                result = json.loads(encoded)
            except (TypeError, json.JSONDecodeError):
                continue
            for candidate in result.get("outputs", []):
                direction_by_candidate[(review_job, candidate.get("id", ""))] = candidate.get("payload", {}).get("direction", "unknown")
        by_direction: dict[str, dict[str, int]] = {}
        for review in reviews:
            direction = direction_by_candidate.get((review["job_id"], review["candidate_id"]), "unknown")
            aggregate = by_direction.setdefault(direction, {"n": 0, "useful": 0, "direction_correct": 0})
            aggregate["n"] += 1
            aggregate["useful"] += review["useful"]
            aggregate["direction_correct"] += review["direction_correct"]
        n = len(reviews)
        useful_count = sum(item["useful"] for item in reviews)
        direction_count = sum(item["direction_correct"] for item in reviews)
        known_count = sum(item["already_known"] for item in reviews)
        return {
            "job_id": job_id,
            "reviewed_candidates": n,
            "useful_rate": float(useful_count) / n if n else None,
            "direction_accuracy": float(direction_count) / n if n else None,
            "already_known_rate": float(known_count) / n if n else None,
            "by_direction": [dict(direction=direction, **counts,
                                  useful_rate=counts["useful"] / counts["n"] if counts["n"] else None)
                             for direction, counts in sorted(by_direction.items())],
            "warning": "Human ratings are descriptive feedback; they do not automatically change engine behavior.",
        }

    def evaluation_report(self) -> dict:
        """Summarize human-rated results by method configuration and fixed task snapshot."""
        with self._connect() as db:
            rows = [dict(row) for row in db.execute("""SELECT r.*,j.result_json,j.request_hash,j.snapshot_id
                    FROM reviews r JOIN jobs j USING(job_id) WHERE j.result_json IS NOT NULL""")]
        outputs_by_job: dict[str, dict[str, dict]] = {}
        configs: dict[str, dict] = {}
        for row in rows:
            job_id = row["job_id"]
            if job_id not in outputs_by_job:
                result = json.loads(row["result_json"])
                details = result.get("method_details", {})
                encoder = details.get("encoder", {})
                configs[job_id] = {
                    "mode": details.get("mode"),
                    "encoder": encoder.get("name"),
                    "model": encoder.get("model"),
                    "revision": encoder.get("revision"),
                    "snapshot_id": result.get("scope", {}).get("snapshot_id"),
                    "objective": details.get("input_objective"),
                }
                outputs_by_job[job_id] = {item.get("id"): item for item in result.get("outputs", [])}
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            cfg = configs[row["job_id"]]
            # Keep each task snapshot/objective separate; otherwise ratings for
            # different discovery problems could be pooled as if comparable.
            group_key = json.dumps({
                **{key: cfg[key] for key in ("mode", "encoder", "model", "revision")},
                "snapshot_id": cfg["snapshot_id"],
                "objective": cfg["objective"],
            }, sort_keys=True)
            candidate = outputs_by_job[row["job_id"]].get(row["candidate_id"], {})
            grouped.setdefault(group_key, []).append({
                "useful": bool(row["useful"]),
                "direction_correct": bool(row["direction_correct"]),
                "already_known": bool(row["already_known"]),
                "rank": candidate.get("rank"),
                "snapshot_id": cfg["snapshot_id"],
                "objective": cfg["objective"],
            })
        variants = []
        for group_key, judgments in grouped.items():
            cfg = json.loads(group_key)
            n = len(judgments)
            sorted_judgments = sorted(judgments, key=lambda item: (item["rank"] is None, item["rank"] or 0))
            top10 = [item for item in sorted_judgments if item["rank"] is not None and item["rank"] <= 10]
            variants.append({
                **cfg,
                "reviewed_candidates": n,
                "useful_rate": sum(item["useful"] for item in judgments) / n,
                "direction_accuracy": sum(item["direction_correct"] for item in judgments) / n,
                "already_known_rate": sum(item["already_known"] for item in judgments) / n,
                "useful_at_10": sum(item["useful"] for item in top10) / len(top10) if top10 else None,
                "reviewed_snapshot_ids": sorted({item["snapshot_id"] for item in judgments if item["snapshot_id"]}),
                "reviewed_objectives": sorted({item["objective"] for item in judgments if item["objective"]}),
            })
        return {
            "variants": sorted(variants, key=lambda item: (item["mode"] or "", item["encoder"] or "", item["model"] or "")),
            "interpretation": "Descriptive human ratings only. Compare variants as an experiment only when input snapshot, objective, review rubric, budget, and scope match.",
            "automatic_learning": False,
        }

    def events(self, job_id: str) -> list[dict]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT at,status,detail FROM job_events WHERE job_id=? ORDER BY event_id", (job_id,))]


class JobManager:
    def __init__(self, data_dir: str | Path | None = None, *, workers: int = 1):
        self.store = JobStore(data_dir)
        self.executor = ThreadPoolExecutor(max_workers=max(1, min(workers, 2)), thread_name_prefix="eureka-rs")
        self._lock = threading.RLock()
        self._events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future] = {}
        for job_id in self.store.queued():
            self._submit(job_id)

    def start(self, request: dict, idempotency_key: str | None = None) -> dict:
        job_id, created = self.store.create(request, idempotency_key)
        if created:
            self._submit(job_id)
        current = self.status(job_id)
        return {"job_id": job_id, "status": current["status"], "created": created,
                "scope_id": request.get("scope_id"), "retention_days": 30}

    def _submit(self, job_id: str) -> None:
        with self._lock:
            event = threading.Event()
            self._events[job_id] = event
            self._futures[job_id] = self.executor.submit(self._execute, job_id, event)

    def _execute(self, job_id: str, cancel_event: threading.Event) -> None:
        try:
            request = self.store.request(job_id)
            self.store.transition(job_id, "running", progress="validating-input")
            self.store.clear_cancel(job_id)
            stage = lambda name: self.store.transition(job_id, "running", progress=name)
            if request.get("capability_id") == "opportunity.synthesize_discovery_signals":
                from ..opportunity_discovery import run_signal_synthesis

                result = run_signal_synthesis(
                    request, data_dir=self.store.data_dir, job_id=job_id,
                    cancel_check=cancel_event.is_set, stage_callback=stage,
                )
            elif request.get("capability_id") == "opportunity.run_pair_screen":
                from ..host_run.execute import run_pair_screen_job

                result = run_pair_screen_job(
                    request, data_dir=self.store.data_dir, job_id=job_id,
                    cancel_check=cancel_event.is_set, stage_callback=stage,
                )
            else:
                result = run_document(
                    request, encoder_name=request["encoder"], model_path=request["model_path"],
                    model_revision=request.get("model_revision"), top_k=request.get("top_k", 20),
                    scoring=request.get("scoring", "hybrid_2026"),
                    lex_weight=request.get("lex_weight", 0.5),
                    min_percentile=request.get("min_percentile", 0.9),
                    job_id=job_id, cache_path=self.store.data_dir / "embeddings.sqlite3",
                    cancel_check=cancel_event.is_set, stage_callback=stage,
                )
            if cancel_event.is_set():
                raise RunCancelled("Run cancelled")
            from ..contracts import validate_result
            validate_result(request.get("capability_id", "opportunity.find_cross_domain_pairs"), result)
            status = result["status"]
            self.store.transition(job_id, status, progress="complete", result=result, clear_request=True)
        except RunCancelled:
            self.store.transition(job_id, "cancelled", progress="cancelled", failure_code="cancelled", clear_request=True)
        except Exception as exc:
            if cancel_event.is_set():
                self.store.transition(job_id, "cancelled", progress="cancelled", failure_code="cancelled", clear_request=True)
                return
            # Error text may contain machine-specific paths or provider details;
            # keep the wire result to a stable category and put diagnostics on stderr.
            import logging
            logging.getLogger(__name__).exception("Eureka job %s failed", job_id)
            detail = str(exc).lower()
            code = ("model_unavailable" if any(marker in detail for marker in
                    ("model", "optional extra", "sentence_transformers", "transformers"))
                    else "run_failed")
            self.store.transition(job_id, "failed", progress="failed", failure_code=code, clear_request=True)
        finally:
            with self._lock:
                self._events.pop(job_id, None)
                self._futures.pop(job_id, None)

    def status(self, job_id: str) -> dict:
        row = self.store.get(job_id)
        if not row:
            raise KeyError(job_id)
        return {key: row[key] for key in ("job_id", "status", "progress", "scope_id", "snapshot_id", "failure_code", "created_at", "updated_at", "expires_at")} | {"events": self.store.events(job_id)}

    def result(self, job_id: str) -> dict:
        return self.store.result(job_id)

    def cancel(self, job_id: str) -> dict:
        state = self.store.request_cancel(job_id)
        with self._lock:
            event = self._events.get(job_id)
            future = self._futures.get(job_id)
            if event:
                event.set()
            if future and future.cancel():
                self.store.transition(job_id, "cancelled", progress="cancelled-before-start", failure_code="cancelled", clear_request=True)
                self._events.pop(job_id, None)
                self._futures.pop(job_id, None)
                return {"job_id": job_id, "status": "cancelled"}
        return {"job_id": job_id, "status": state, "cancel_requested": state != "already_terminal"}
