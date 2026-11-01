"""Rexetive v2 API.

    uvicorn main:app --port 8001          (docs at http://localhost:8001/docs)

v1 endpoints keep their paths and response shapes (the React pages still call them), but
now run the review agent instead of one gpt-4 prompt:
  POST /submit_submission/{synopsis|logic|hypothesis|bias}, GET /get_submission/{id},
  GET /get_all_submissions, GET /get_all_submissions/case/{caseId}, GET /me, GET /me/reputation
New:
  GET /auth/nonce, POST /auth/verify, POST /auth/demo-login (DEMO_MODE only)
  GET /cases, GET /cases/{id}             cases + evidence packs
  GET /review/{id}                        node-by-node trace, judges, gate decision
  POST /review/{id}/resume                moderator decision (approve / reject / adjust)
  GET /moderation/queue                   items paused for a moderator
  POST /analytics/ask                     safe text-to-SQL (moderators)
  GET /evals/latest, GET /review-graph, GET /health

Auth: Bearer JWT from a verified wallet signature (auth.py). v1 trusted an
X-Wallet-Address header, which anyone could forge.
"""
from __future__ import annotations

import json
from typing import Literal

import analytics
import db
from agent.graph import mermaid, resume_review, snapshot, start_review
from agent.judges import JUDGES
from agent.policy import rank
from auth import current_user, demo_login, issue_nonce, login_with_signature, moderator
from cases import load_cases, public_case
from config import DEMO_MODE, LOG_DIR, SUI_MOCK
from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ragcore import llm

app = FastAPI(title="Rexetive v2", version="2.0",
              description="Evidence-grounded AI review with a code policy gate and human moderation.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# --- request bodies ----------------------------------------------------------------------------------
class SubmissionRequest(BaseModel):  # v1 shape
    caseId: int
    case: str = ""            # v1 sent the case text; v2 ignores it and uses the evidence pack
    theory: str = Field(min_length=10, max_length=6000)


class VerifyIn(BaseModel):
    address: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    message: str
    signature: str


class ResumeIn(BaseModel):
    decision: Literal["approve", "reject", "adjust"]
    scores: dict[str, int] = {}
    note: str = ""


class AnalyticsIn(BaseModel):
    question: str = ""
    sql: str = ""


# --- helpers -------------------------------------------------------------------------------------------
def _v1_view(sub: dict, state: dict | None = None) -> dict:
    """v1 ViewSubmission shape from v2 data. Mapping: clarity=synopsis judge,
    consistency=logic, plausibility=hypothesis, relevance=bias (objectivity)."""
    reviews = {r["judge"]: r for r in db.query("SELECT * FROM reviews WHERE submission_id=?", (sub["id"],))}
    score = lambda j: int(reviews[j]["score"]) if j in reviews else 0  # noqa: E731
    flags = [f["text"] for r in reviews.values() for f in json.loads(r["flags_json"] or "[]")]
    total = sub.get("total_score") or 0
    feedback = (state or {}).get("feedback") or (reviews.get("synopsis") or {}).get("rationale", "")
    return {"caseId": sub["case_id"], "author": sub["author"], "clarity": score("synopsis"),
            "consistency": score("logic"), "plausibility": score("hypothesis"), "relevance": score("bias"),
            "is_safe": not (state or {}).get("guard", {}).get("toxicity"), "flag": "; ".join(flags)[:500],
            "theory": sub["text"], "summary": feedback, "rank": rank(total), "is_valid": sub["status"] == "accepted",
            "submission_id": sub["id"], "timestamp": sub["created_at"], "status": sub["status"], "total_score": total}


def _all_submissions(case_id: int | None = None) -> list[dict]:
    sql = "SELECT s.*, u.wallet_address AS author FROM submissions s JOIN users u ON u.id = s.user_id"
    args: tuple = ()
    if case_id is not None:
        sql += " WHERE s.case_id = ?"
        args = (case_id,)
    return [_v1_view(s) for s in db.query(sql + " ORDER BY s.id DESC", args)]


def _review_payload(snap: dict) -> dict:
    st = snap["state"]
    return {"submission_id": snap["submission_id"], "thread_id": snap["thread_id"], "status": snap["status"],
            "waiting_for": snap["next"], "events": st.get("events", []), "guard": st.get("guard"),
            "duplicate": st.get("duplicate"), "evidence": st.get("evidence", []), "judges": st.get("judges", {}),
            "aggregate": st.get("aggregate"), "decision": st.get("decision"), "moderation": st.get("moderation"),
            "credential": st.get("credential"), "reputation": st.get("reputation"), "feedback": st.get("feedback"),
            "memory": st.get("memory")}


async def _submit(mode: str, req: SubmissionRequest, user: dict) -> dict:
    if req.caseId not in load_cases():
        raise HTTPException(404, f"unknown case {req.caseId}")
    sid = db.create_submission(req.caseId, user["id"], mode, req.theory)
    run = await run_in_threadpool(start_review, sid)
    st = run["state"]
    view = _v1_view(db.get_submission(sid), st)
    judge = st["judges"].get({"synopsis": "synopsis", "logic": "logic", "hypothesis": "hypothesis", "bias": "bias"}[mode], {})
    mode_fields = {
        "synopsis": {},
        "logic": {"inconsistencies": judge.get("inconsistencies", []), "missing_links": judge.get("missing_links", []),
                  "timeline_validity": judge.get("score", 0), "conflict_summary": judge.get("rationale", ""),
                  "correction_suggestions": st.get("feedback", "")},
        "hypothesis": {"plausibility_assessment": judge.get("score", 0), "counterpoints": judge.get("counterpoints", []),
                       "evidence_match": judge.get("evidence_match", ""),
                       "suggest_further_investigation": st.get("feedback", "")},
        "bias": {"detected_biases": judge.get("detected_biases", []), "objectivity_score": judge.get("score", 0),
                 "challenge_points": judge.get("challenge_points", []), "bias_impact_summary": judge.get("rationale", "")},
    }[mode]
    cred = st.get("credential") or {}
    return {**view, **mode_fields, "review_status": run["status"], "review": _review_payload(run),
            "blockchain_tx": cred or None, "nft_minted": bool(cred), "reputation_updated": bool(st.get("reputation"))}


# --- auth --------------------------------------------------------------------------------------------------
@app.get("/auth/nonce")
def auth_nonce(address: str) -> dict:
    return {"message": issue_nonce(address)}


@app.post("/auth/verify")
def auth_verify(body: VerifyIn) -> dict:
    return login_with_signature(body.address, body.message, body.signature)


@app.post("/auth/demo-login")
def auth_demo() -> dict:
    return demo_login()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": llm.badge(), "offline": llm.is_offline(), "demo_mode": DEMO_MODE,
            "chain": "MOCK CHAIN" if SUI_MOCK else "sui"}


# --- cases -------------------------------------------------------------------------------------------------
@app.get("/cases")
def cases() -> list[dict]:
    return [public_case(c) for c in load_cases().values()]


@app.get("/cases/{case_id}")
def case(case_id: int) -> dict:
    if case_id not in load_cases():
        raise HTTPException(404, "unknown case")
    return public_case(load_cases()[case_id])


# --- v1 endpoints (now agent-backed) ------------------------------------------------------------------------
@app.post("/submit_submission/synopsis")
async def submit_synopsis(req: SubmissionRequest, user: dict = Depends(current_user)):
    return await _submit("synopsis", req, user)


@app.post("/submit_submission/logic")
async def submit_logic(req: SubmissionRequest, user: dict = Depends(current_user)):
    return await _submit("logic", req, user)


@app.post("/submit_submission/hypothesis")
async def submit_hypothesis(req: SubmissionRequest, user: dict = Depends(current_user)):
    return await _submit("hypothesis", req, user)


@app.post("/submit_submission/bias")
async def submit_bias(req: SubmissionRequest, user: dict = Depends(current_user)):
    return await _submit("bias", req, user)


@app.get("/get_submission/{submission_id}")
def get_submission(submission_id: int, user: dict = Depends(current_user)):
    sub = db.get_submission(submission_id)
    if not sub:
        raise HTTPException(404, "Submission not found")
    return _v1_view(sub, snapshot(submission_id)["state"])


@app.get("/get_all_submissions")
def get_all_submissions(user: dict = Depends(current_user)):
    return _all_submissions()


@app.get("/get_all_submissions/case/{caseId}")
def get_all_by_case(caseId: int, user: dict = Depends(current_user)):
    return _all_submissions(caseId)


@app.get("/me")
def me(user: dict = Depends(current_user)):
    return user


@app.get("/me/reputation")
def me_reputation(user: dict = Depends(current_user)):
    rows = db.query("SELECT * FROM reputation WHERE user_id=?", (user["id"],))
    rep = rows[0] if rows else {"points": 0, "accepted": 0, "nft_count": 0}
    return {"reputation_points": rep["points"], "nft_count": rep["nft_count"], "submissions_accepted": rep["accepted"],
            "wallet": user["wallet_address"], "role": user["role"]}


# --- v2: review trace, moderation, analytics, evals ----------------------------------------------------------
@app.get("/review/{submission_id}")
def review(submission_id: int, user: dict = Depends(current_user)):
    snap = snapshot(submission_id)
    if not snap["state"]:
        raise HTTPException(404, "no review for this submission")
    return _review_payload(snap) | {"text": snap["state"].get("masked_text")}


@app.post("/review/{submission_id}/resume")
async def review_resume(submission_id: int, body: ResumeIn, mod: dict = Depends(moderator)):
    unknown = set(body.scores) - set(JUDGES)
    if unknown:
        raise HTTPException(422, f"unknown judges: {sorted(unknown)}")
    try:
        snap = await run_in_threadpool(resume_review, submission_id, body.decision, body.scores, body.note,
                                       mod["display_name"] or mod["wallet_address"])
    except ValueError as err:
        raise HTTPException(409, str(err)) from err
    return _review_payload(snap)


@app.get("/moderation/queue")
def moderation_queue(mod: dict = Depends(moderator)):
    rows = db.query("SELECT s.id, s.case_id, s.mode, s.text, s.total_score, s.disagreement, s.duplicate_of, s.created_at, "
                    "u.display_name FROM submissions s JOIN users u ON u.id = s.user_id "
                    "WHERE s.status = 'needs_review' ORDER BY s.id DESC")
    out = []
    for r in rows:
        snap = snapshot(r["id"])
        st = snap["state"]
        out.append({**r, "resumable": "moderator_review" in snap["next"],
                    "reasons": (st.get("decision") or {}).get("reasons", ["seeded example (no live review thread)"]),
                    "scores": (st.get("aggregate") or {}).get("scores")})
    return out


@app.post("/analytics/ask")
async def analytics_ask(body: AnalyticsIn, mod: dict = Depends(moderator)):
    if not (body.question or body.sql):
        raise HTTPException(422, "ask a question or provide SQL")
    return await run_in_threadpool(analytics.ask, body.question, body.sql)


@app.get("/evals/latest")
def evals_latest():
    report, results = LOG_DIR / "eval_report.md", LOG_DIR / "eval_results.json"
    if not report.exists():
        raise HTTPException(404, "no eval report yet: run python -m evals.run_all")
    data = json.loads(results.read_text(encoding="utf-8")) if results.exists() else {}
    return {"markdown": report.read_text(encoding="utf-8"), "results": data}


@app.get("/review-graph")
def review_graph():
    return {"mermaid": mermaid()}
