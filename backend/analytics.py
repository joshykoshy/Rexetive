"""Moderator analytics: safe text-to-SQL.

Flow: natural-language question -> fast model writes ONE SQLite SELECT from a described,
allowlisted schema (structured output: sql + explanation) -> ragcore.sql_guard.validate_sql
(sqlglot parse, single SELECT, no write/DDL/ATTACH/PRAGMA, allowlisted tables only, LIMIT 200)
-> run_readonly (mode=ro connection, PRAGMA query_only, time budget) -> table.

The response always includes the SQL and the guard's verdict, so a moderator can see exactly
what ran, or exactly why something was blocked. Moderators may also type SQL directly; it
goes through the same guard (that's how the demo shows a blocked `DROP TABLE`).

Offline: a few known intents map to template SQL (still validated by the guard).

Trade-off: the guard makes the *database* safe, not the *answer* correct. The model can still
write a wrong-but-valid query, which is why the SQL is always shown next to the result.
"""
from __future__ import annotations

from config import ANALYTICS_TABLES, DB_PATH
from pydantic import BaseModel
from ragcore import llm, trace
from ragcore.sql_guard import run_readonly, validate_sql

SCHEMA_DOC = """users(id, wallet_address, display_name, role, created_at)
submissions(id, case_id, user_id -> users.id, mode, text, status ['pending','accepted','rejected','needs_review'],
            total_score /40, disagreement 0..1, duplicate_of, created_at ISO text)
reviews(id, submission_id -> submissions.id, judge ['synopsis','logic','hypothesis','bias'], score 0..10, rationale, created_at)
credentials(id, submission_id, user_id, digest, chain ['mock','sui'], created_at)
reputation(user_id -> users.id, points, accepted, nft_count, updated_at)
Cases: 1 = Lantern Street Gallery Theft, 2 = Quiet Readings at Halvard Station, 3 = Missing Ledger at Copperfield Co-op."""

SYSTEM = f"""Write ONE SQLite SELECT statement that answers the moderator's question.
Use only these tables and columns:
{SCHEMA_DOC}
Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH or PRAGMA. Prefer readable column aliases.
Return the SQL and a one-sentence explanation."""


class SQLPlan(BaseModel):
    sql: str
    explanation: str


TEMPLATES: list[tuple[tuple[str, ...], str, str]] = [
    (("acceptance", "accept rate", "accepted per case"),
     "SELECT case_id, COUNT(*) AS submissions, ROUND(100.0 * SUM(status = 'accepted') / COUNT(*), 1) AS acceptance_pct "
     "FROM submissions GROUP BY case_id ORDER BY case_id", "Acceptance rate per case."),
    (("top contributor", "leaderboard", "most reputation", "reputation"),
     "SELECT u.display_name, r.points, r.accepted, r.nft_count FROM reputation r JOIN users u ON u.id = r.user_id "
     "ORDER BY r.points DESC LIMIT 10", "Top 10 contributors by reputation points."),
    (("average score", "judge", "per judge"),
     "SELECT judge, ROUND(AVG(score), 2) AS avg_score, COUNT(*) AS reviews FROM reviews GROUP BY judge ORDER BY avg_score DESC",
     "Average score given by each judge."),
    (("pending", "waiting", "needs review", "queue", "borderline"),
     "SELECT id, case_id, total_score, disagreement, created_at FROM submissions WHERE status = 'needs_review' "
     "ORDER BY created_at", "Submissions waiting for a moderator."),
    (("per day", "daily", "over time", "each day"),
     "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS submissions FROM submissions GROUP BY day ORDER BY day",
     "Submissions per day."),
    (("disagree", "spread"),
     "SELECT id, case_id, total_score, disagreement FROM submissions WHERE disagreement > 0.4 "
     "ORDER BY disagreement DESC", "Submissions where the judges disagreed most."),
    (("credential", "nft"),
     "SELECT chain, COUNT(*) AS credentials FROM credentials GROUP BY chain", "Credentials issued, by chain."),
    (("status", "how many submissions"),
     "SELECT status, COUNT(*) AS submissions FROM submissions GROUP BY status ORDER BY submissions DESC",
     "Submissions by status."),
]


def template_sql(question: str) -> SQLPlan | None:
    q = question.lower()
    for keywords, sql, explanation in TEMPLATES:
        if any(k in q for k in keywords):
            return SQLPlan(sql=sql, explanation=explanation)
    return None


def generate_sql(question: str) -> tuple[SQLPlan | None, str]:
    if not llm.is_offline():
        try:
            return llm.structured(SYSTEM, question, SQLPlan, tier="fast", max_tokens=400), "llm"
        except llm.LLMError:
            pass
    return template_sql(question), "template"


def ask(question: str = "", sql: str = "", db_path=None) -> dict:
    """Answer a moderator question (or run moderator-typed SQL) safely. Never raises on bad SQL."""
    out = {"question": question, "sql": sql, "source": "moderator" if sql else None, "explanation": "",
           "guard": None, "safe_sql": None, "columns": [], "rows": [], "error": None}
    with trace.tracing(trace.Tracer(None, kind="analytics")):
        if not sql:
            with trace.step("text_to_sql"):
                plan, mode = generate_sql(question)
            if plan is None:
                out["error"] = ("Offline mode understands questions about: acceptance rate per case, top contributors, "
                                "average score per judge, pending reviews, submissions per day, judge disagreement, "
                                "credentials, submissions by status.")
                return out
            out.update(sql=plan.sql, explanation=plan.explanation, source=mode)
        ok, reason, safe_sql = validate_sql(out["sql"], ANALYTICS_TABLES)
        out["guard"] = {"ok": ok, "reason": reason}
        if not ok:
            return out
        out["safe_sql"] = safe_sql
        try:
            columns, rows = run_readonly(db_path or DB_PATH, safe_sql)
            out.update(columns=columns, rows=[list(r) for r in rows])
        except Exception as err:  # valid SQL can still fail (unknown column, timeout)
            out["error"] = f"{type(err).__name__}: {err}"
    return out
