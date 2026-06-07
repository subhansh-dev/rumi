"""Persistent hypothesis memory — SQLite-backed, cross-session."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hypothesis_memory.db"


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            pattern_type TEXT,
            confidence REAL,
            novelty TEXT,
            status TEXT DEFAULT 'draft',
            provider TEXT,
            topic TEXT,
            domain TEXT,
            run_id TEXT,
            prompt_tokens INTEGER,
            testability TEXT,
            critique TEXT,
            critique_weaknesses TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hypothesis_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id TEXT REFERENCES hypotheses(id) ON DELETE CASCADE,
            name TEXT, type TEXT, definition TEXT, conditions TEXT
        );
        CREATE TABLE IF NOT EXISTS hypothesis_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id TEXT REFERENCES hypotheses(id) ON DELETE CASCADE,
            source TEXT, relation TEXT, target TEXT,
            definition TEXT, papers TEXT
        );
        CREATE TABLE IF NOT EXISTS novelty_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id TEXT REFERENCES hypotheses(id) ON DELETE CASCADE,
            in_pubmed INTEGER, similar_papers TEXT,
            novelty_probability REAL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_hypotheses_topic ON hypotheses(topic);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON hypotheses(status);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_domain ON hypotheses(domain);
    """)


class HypothesisMemory:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or DB_PATH)

    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_schema(conn)
        return conn

    def save_hypothesis(self, hypothesis, run_id=""):
        conn = self._conn()
        try:
            hid = hypothesis.get("id") or str(uuid.uuid4())
            hypothesis["id"] = hid
            now = datetime.utcnow().isoformat()

            conn.execute(
                """INSERT OR REPLACE INTO hypotheses
                   (id, title, description, pattern_type, confidence, novelty,
                    status, provider, topic, domain, run_id, testability,
                    critique, critique_weaknesses, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (hid, hypothesis.get("title"), hypothesis.get("description"),
                 hypothesis.get("pattern_type"), hypothesis.get("confidence"),
                 hypothesis.get("novelty"), hypothesis.get("status", "draft"),
                 hypothesis.get("provider"), hypothesis.get("topic"),
                 hypothesis.get("domain"), run_id,
                 hypothesis.get("testability"), hypothesis.get("critique"),
                 hypothesis.get("critique_weaknesses"),
                 hypothesis.get("created_at", now), now)
            )

            for n in (hypothesis.get("nodes") or []):
                if not isinstance(n, dict):
                    continue
                conn.execute(
                    "INSERT INTO hypothesis_nodes (hypothesis_id, name, type, definition, conditions) VALUES (?,?,?,?,?)",
                    (hid, n.get("name"), n.get("type"), n.get("definition"), n.get("conditions"))
                )

            for e in (hypothesis.get("edges") or []):
                conn.execute(
                    "INSERT INTO hypothesis_edges (hypothesis_id, source, relation, target, definition, papers) VALUES (?,?,?,?,?,?)",
                    (hid, e.get("source"), e.get("relation"), e.get("target"),
                     e.get("definition"), json.dumps(e.get("papers", [])))
                )

            conn.commit()
            return hid
        finally:
            conn.close()

    def get_hypothesis(self, hid):
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM hypotheses WHERE id=?", (hid,)).fetchone()
            if not row:
                return None
            h = dict(row)
            h["nodes"] = [dict(r) for r in conn.execute(
                "SELECT name, type, definition, conditions FROM hypothesis_nodes WHERE hypothesis_id=?", (hid,))]
            h["edges"] = [dict(r) for r in conn.execute(
                "SELECT source, relation, target, definition, papers FROM hypothesis_edges WHERE hypothesis_id=?", (hid,))]
            for e in h["edges"]:
                try:
                    e["papers"] = json.loads(e["papers"])
                except (json.JSONDecodeError, TypeError):
                    e["papers"] = []
            nc = conn.execute("SELECT * FROM novelty_checks WHERE hypothesis_id=?", (hid,)).fetchone()
            if nc:
                h["novelty_check"] = dict(nc)
            return h
        finally:
            conn.close()

    def find_similar(self, title, threshold=0.7):
        """Find hypotheses with similar titles using simple overlap."""
        conn = self._conn()
        try:
            keywords = set(title.lower().split())
            if not keywords:
                return []
            candidates = conn.execute("SELECT id, title FROM hypotheses").fetchall()
            similar = []
            for row in candidates:
                if not row["title"]:
                    continue
                other_words = set(row["title"].lower().split())
                if not other_words:
                    continue
                overlap = len(keywords & other_words) / max(len(keywords | other_words), 1)
                if overlap >= threshold:
                    similar.append({"id": row["id"], "title": row["title"], "similarity": round(overlap, 3)})
            return sorted(similar, key=lambda x: -x["similarity"])
        finally:
            conn.close()

    def get_all(self, domain=None, status=None, limit=50, offset=0):
        conn = self._conn()
        try:
            where = []
            params = []
            if domain:
                where.append("domain=?")
                params.append(domain)
            if status:
                where.append("status=?")
                params.append(status)
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            rows = conn.execute(
                f"SELECT * FROM hypotheses {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_status(self, hid, status):
        conn = self._conn()
        try:
            conn.execute("UPDATE hypotheses SET status=?, updated_at=? WHERE id=?",
                        (status, datetime.utcnow().isoformat(), hid))
            conn.commit()
        finally:
            conn.close()

    def update_critique(self, hid, critique, weaknesses):
        conn = self._conn()
        try:
            conn.execute("UPDATE hypotheses SET critique=?, critique_weaknesses=?, updated_at=? WHERE id=?",
                        (critique, weaknesses, datetime.utcnow().isoformat(), hid))
            conn.commit()
        finally:
            conn.close()

    def count_by_status(self):
        conn = self._conn()
        try:
            rows = conn.execute("SELECT status, COUNT(*) as cnt FROM hypotheses GROUP BY status").fetchall()
            return {r["status"]: r["cnt"] for r in rows}
        finally:
            conn.close()

    def save_novelty_check(self, hid, in_pubmed, similar_papers, probability):
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO novelty_checks (hypothesis_id, in_pubmed, similar_papers, novelty_probability) VALUES (?,?,?,?)",
                (hid, 1 if in_pubmed else 0, json.dumps(similar_papers), probability)
            )
            conn.commit()
        finally:
            conn.close()
