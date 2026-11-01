"""SQLite schema and small data-access helpers for Rexetive.

Tables
  users(id, wallet_address, display_name, role, created_at)         role: contributor | moderator
  submissions(id, case_id, user_id, mode, text, status, total_score, disagreement,
              duplicate_of, created_at)                               status: pending | accepted |
                                                                      rejected | needs_review
  reviews(id, submission_id, judge, score, rationale, flags_json, created_at)   one row per judge
  credentials(id, submission_id, user_id, digest, chain, created_at)  chain: mock | sui
  reputation(user_id, points, accepted, nft_count, updated_at)
  moderation_log(id, submission_id, moderator, ai_verdict, ai_total, decision, adjusted_json,
                 note, created_at)                                    every human decision, with
                                                                      the AI's original verdict
  contributor_memory(user_id, submissions, accepted, weaknesses_json, updated_at)
  auth_nonces(address, nonce, message, expires)                       wallet login challenges

The first five are what moderators may query through analytics (see config.ANALYTICS_TABLES);
moderation_log and contributor_memory are deliberately not exposed.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, wallet_address TEXT UNIQUE NOT NULL, display_name TEXT,
    role TEXT NOT NULL DEFAULT 'contributor', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    mode TEXT NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', total_score REAL,
    disagreement REAL, duplicate_of INTEGER, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, submission_id INTEGER NOT NULL, judge TEXT NOT NULL,
    score REAL, rationale TEXT, flags_json TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS credentials (id INTEGER PRIMARY KEY, submission_id INTEGER UNIQUE NOT NULL,
    user_id INTEGER NOT NULL, digest TEXT NOT NULL, chain TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reputation (user_id INTEGER PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0,
    accepted INTEGER NOT NULL DEFAULT 0, nft_count INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS moderation_log (id INTEGER PRIMARY KEY, submission_id INTEGER NOT NULL, moderator TEXT,
    ai_verdict TEXT, ai_total REAL, decision TEXT, adjusted_json TEXT, note TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contributor_memory (user_id INTEGER PRIMARY KEY, submissions INTEGER NOT NULL DEFAULT 0,
    accepted INTEGER NOT NULL DEFAULT 0, weaknesses_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT);
CREATE TABLE IF NOT EXISTS auth_nonces (address TEXT PRIMARY KEY, nonce TEXT, message TEXT, expires REAL);
CREATE INDEX IF NOT EXISTS ix_sub_case ON submissions(case_id);
CREATE INDEX IF NOT EXISTS ix_rev_sub ON reviews(submission_id);
"""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def query(sql: str, args: tuple = ()) -> list[dict]:
    with closing(connect()) as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def execute(sql: str, args: tuple = ()) -> int:
    with closing(connect()) as conn, conn:
        return int(conn.execute(sql, args).lastrowid or 0)


# --- users -----------------------------------------------------------------------------------
def get_or_create_user(address: str, role: str = "contributor", display_name: str | None = None) -> dict:
    rows = query("SELECT * FROM users WHERE wallet_address=?", (address,))
    if rows:
        return rows[0]
    uid = execute("INSERT INTO users(wallet_address, display_name, role, created_at) VALUES (?,?,?,?)",
                  (address, display_name or address[:10], role, now()))
    execute("INSERT OR IGNORE INTO reputation(user_id, points, accepted, nft_count, updated_at) VALUES (?,0,0,0,?)",
            (uid, now()))
    return query("SELECT * FROM users WHERE id=?", (uid,))[0]


# --- submissions -----------------------------------------------------------------------------
def create_submission(case_id: int, user_id: int, mode: str, text: str) -> int:
    return execute("INSERT INTO submissions(case_id, user_id, mode, text, status, created_at) VALUES (?,?,?,?,?,?)",
                   (case_id, user_id, mode, text, "pending", now()))


def get_submission(sid: int) -> dict | None:
    rows = query("SELECT s.*, u.wallet_address AS author FROM submissions s JOIN users u ON u.id = s.user_id "
                 "WHERE s.id=?", (sid,))
    return rows[0] if rows else None


def case_submissions(case_id: int, exclude_id: int | None = None) -> list[dict]:
    return query("SELECT id, text FROM submissions WHERE case_id=? AND id != ? AND duplicate_of IS NULL",
                 (case_id, exclude_id or -1))


def update_submission(sid: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE submissions SET {cols} WHERE id=?", (*fields.values(), sid))


def save_reviews(sid: int, judges: dict) -> None:
    execute("DELETE FROM reviews WHERE submission_id=?", (sid,))
    for name, j in judges.items():
        execute("INSERT INTO reviews(submission_id, judge, score, rationale, flags_json, created_at) VALUES (?,?,?,?,?,?)",
                (sid, name, j["score"], j.get("rationale", ""), json.dumps(j.get("flags", [])), now()))


# --- side effects (only called after the policy gate) ----------------------------------------
def add_credential(sid: int, user_id: int, digest: str, chain: str) -> int:
    return execute("INSERT OR IGNORE INTO credentials(submission_id, user_id, digest, chain, created_at) VALUES (?,?,?,?,?)",
                   (sid, user_id, digest, chain, now()))


def add_reputation(user_id: int, points: int, accepted: bool, nft: bool) -> dict:
    execute("INSERT OR IGNORE INTO reputation(user_id, points, accepted, nft_count, updated_at) VALUES (?,0,0,0,?)",
            (user_id, now()))
    execute("UPDATE reputation SET points = points + ?, accepted = accepted + ?, nft_count = nft_count + ?, "
            "updated_at=? WHERE user_id=?", (points, int(accepted), int(nft), now(), user_id))
    return query("SELECT * FROM reputation WHERE user_id=?", (user_id,))[0]


def log_moderation(sid: int, moderator: str, ai_verdict: str, ai_total: float, decision: str,
                   adjusted: dict | None, note: str) -> int:
    return execute("INSERT INTO moderation_log(submission_id, moderator, ai_verdict, ai_total, decision, adjusted_json, "
                   "note, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (sid, moderator, ai_verdict, ai_total, decision, json.dumps(adjusted or {}), note, now()))


# --- contributor memory ----------------------------------------------------------------------
def get_memory(user_id: int) -> dict:
    rows = query("SELECT * FROM contributor_memory WHERE user_id=?", (user_id,))
    if not rows:
        return {"user_id": user_id, "submissions": 0, "accepted": 0, "weaknesses": {}}
    r = rows[0]
    return {"user_id": user_id, "submissions": r["submissions"], "accepted": r["accepted"],
            "weaknesses": json.loads(r["weaknesses_json"] or "{}")}


def save_memory(mem: dict) -> None:
    execute("INSERT OR REPLACE INTO contributor_memory(user_id, submissions, accepted, weaknesses_json, updated_at) "
            "VALUES (?,?,?,?,?)", (mem["user_id"], mem["submissions"], mem["accepted"],
                                   json.dumps(mem["weaknesses"]), now()))
