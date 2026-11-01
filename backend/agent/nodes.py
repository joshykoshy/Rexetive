"""Review graph nodes. Each node: read state -> one job -> partial update + one progress event.

Order: input_guard -> dedupe_check -> retrieve_evidence -> 4 judges in parallel -> aggregate
-> policy_gate -> (accept) issue_credential -> update_reputation -> write_feedback
               -> (reject) write_feedback
               -> (review) moderator_review [interrupt] -> accept or reject path
-> update_contributor_memory -> END

Side effects (credential, reputation) live in exactly two nodes that are only reachable
after the gate (or a moderator) says "accept".
"""
from __future__ import annotations

import time

import chain
import db
from cases import load_cases, retrieve_evidence
from config import DUPLICATE_SIMILARITY
from langgraph.types import interrupt
from ragcore import llm, trace
from ragcore.dense import embed
from ragcore.guards import check_toxicity, detect_injection, mask_pii

from . import policy
from .judges import JUDGES, run_judge
from .schemas import Feedback, ReviewState


def _event(node: str, summary: str, t0: float, **extra) -> dict:
    return {"node": node, "summary": summary, "ms": round((time.perf_counter() - t0) * 1000, 1), **extra}


# --- input_guard ----------------------------------------------------------------------------------
def input_guard(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    with trace.step("input_guard") as rec:
        masked, pii = mask_pii(state["text"])
        injection = detect_injection(masked)
        tox = check_toxicity(masked)
        guard = {"is_safe": not tox.flagged, "toxicity": tox.reasons, "injection": injection, "pii_masked": pii}
        rec["decision"] = "unsafe" if tox.flagged else "injection" if injection else "clean"
    summary = (f"safe={guard['is_safe']} injection={len(injection)} pii={pii or 'none'}")
    return {"masked_text": masked, "guard": guard, "status": "reviewing",
            "events": [_event("input_guard", summary, t0)]}


# --- dedupe_check -----------------------------------------------------------------------------------
def dedupe_check(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    others = db.case_submissions(state["case_id"], exclude_id=state["submission_id"])
    dup = {"is_duplicate": False, "of": None, "similarity": 0.0}
    if others:
        with trace.step("dedupe_check") as rec:
            vecs = embed([state["masked_text"]] + [o["text"] for o in others])
            sims = vecs[1:] @ vecs[0]
            best = int(sims.argmax())
            dup.update(similarity=round(float(sims[best]), 4), of=others[best]["id"])
            dup["is_duplicate"] = dup["similarity"] >= DUPLICATE_SIMILARITY
            rec["decision"] = f"max sim {dup['similarity']}"
    summary = (f"near-duplicate of #{dup['of']} ({dup['similarity']})" if dup["is_duplicate"]
               else f"unique (closest {dup['similarity']} vs {len(others)} others)")
    return {"duplicate": dup, "events": [_event("dedupe_check", summary, t0)]}


# --- retrieve_evidence -------------------------------------------------------------------------------
def retrieve_evidence_node(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    with trace.step("retrieve_evidence"):
        evidence = retrieve_evidence(state["case_id"], state["masked_text"])
    return {"evidence": evidence, "events": [_event("retrieve_evidence",
                                                    "evidence: " + ", ".join(e["evidence_id"] for e in evidence), t0)]}


# --- the four judges (run in parallel) -------------------------------------------------------------
def _judge_node(name: str):
    def node(state: ReviewState) -> dict:
        t0 = time.perf_counter()
        case = load_cases()[state["case_id"]]
        with trace.step(f"judge_{name}") as rec:
            out, mode = run_judge(name, case, state["evidence"], state["masked_text"])
            rec["decision"] = f"{out['score']}/10 ({mode})"
        return {"judges": {name: out}, "events": [_event(f"judge_{name}", f"{out['score']}/10 ({mode})", t0)]}
    node.__name__ = f"judge_{name}"
    return node


judge_synopsis, judge_logic, judge_hypothesis, judge_bias = (_judge_node(n) for n in JUDGES)


# --- aggregate + policy_gate (pure Python) ---------------------------------------------------------
def aggregate(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    agg = policy.aggregate(state["judges"])
    return {"aggregate": agg, "events": [_event("aggregate", f"total {agg['total']}/40, disagreement {agg['disagreement']}", t0)]}


def policy_gate(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    decision = policy.decide(state["aggregate"], state["judges"], state["guard"], state["duplicate"])
    status = {"accept": "accepted", "reject": "rejected", "review": "needs_review"}[decision["verdict"]]
    db.update_submission(state["submission_id"], status=status, total_score=state["aggregate"]["total"],
                         disagreement=state["aggregate"]["disagreement"],
                         duplicate_of=state["duplicate"]["of"] if state["duplicate"].get("is_duplicate") else None)
    db.save_reviews(state["submission_id"], state["judges"])
    return {"decision": {**decision, "decided_by": "policy"}, "status": status,
            "events": [_event("policy_gate", f"{decision['verdict']}: {'; '.join(decision['reasons'])}", t0)]}


def route_after_gate(state: ReviewState) -> str:
    return {"accept": "issue_credential", "reject": "write_feedback",
            "review": "moderator_review"}[state["decision"]["verdict"]]


# --- moderator_review (interrupt) ------------------------------------------------------------------
def moderator_review(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    answer = interrupt({"submission_id": state["submission_id"], "reasons": state["decision"]["reasons"],
                        "aggregate": state["aggregate"], "options": ["approve", "reject", "adjust"]}) or {}
    choice = answer.get("decision", "reject")
    adjusted = None
    if choice == "adjust":
        adjusted = {k: max(0, min(10, int(v))) for k, v in (answer.get("scores") or {}).items() if k in JUDGES}
        scores = {**state["aggregate"]["scores"], **adjusted}
        total = sum(scores.values())
        verdict = "accept" if total >= policy.ACCEPT_MIN_TOTAL else "reject"
        agg = {**state["aggregate"], "scores": scores, "total": total}
    else:
        verdict, agg = ("accept" if choice == "approve" else "reject"), state["aggregate"]
    moderator = answer.get("moderator", "moderator")
    note = answer.get("note", "")
    db.log_moderation(state["submission_id"], moderator, "review: " + "; ".join(state["decision"]["reasons"]),
                      state["aggregate"]["total"], f"{choice}->{verdict}", adjusted, note)
    status = "accepted" if verdict == "accept" else "rejected"
    db.update_submission(state["submission_id"], status=status, total_score=agg["total"])
    return {"decision": {"verdict": verdict, "reasons": [f"moderator {choice}: {note}".strip()], "decided_by": moderator},
            "aggregate": agg, "moderation": {"choice": choice, "adjusted": adjusted, "note": note, "moderator": moderator},
            "status": status, "events": [_event("moderator_review", f"{choice} -> {verdict}", t0)]}


def route_after_moderation(state: ReviewState) -> str:
    return "issue_credential" if state["decision"]["verdict"] == "accept" else "write_feedback"


# --- side effects: only after accept --------------------------------------------------------------
def issue_credential(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    total = state["aggregate"]["total"]
    summary = state["judges"].get("synopsis", {}).get("rationale", "")
    cred = chain.issue_credential(state["submission_id"], state["user_id"], state["author"], state["case_id"], total,
                                  summary, policy.rank(total), int(time.time()))
    return {"credential": {**cred, "rank": policy.rank(total)},
            "events": [_event("issue_credential", f"{cred['chain']} digest {cred['digest'][:18]}...", t0)]}


def update_reputation(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    nft = bool(state.get("credential", {}).get("nft_minted"))
    points = policy.reputation_points(state["aggregate"]["total"], nft)
    rep = chain.update_reputation(state["user_id"], state["author"], points, True, nft)
    return {"reputation": {**rep, "points_added": points},
            "events": [_event("update_reputation", f"+{points} points (total {rep['points']})", t0)]}


# --- write_feedback -------------------------------------------------------------------------------
FEEDBACK_SYSTEM = ("You write constructive feedback for a contributor whose case analysis was reviewed. Be specific and "
                   "kind. Cite evidence ids like [E4] for every point about the evidence. If the contributor has recurring "
                   "weaknesses, mention one concrete way to improve on them. 4-6 sentences.")


def offline_feedback(state: ReviewState, memory: dict) -> str:
    judges, verdict = state["judges"], state["decision"]["verdict"]
    weakest = min(JUDGES, key=lambda n: judges[n]["score"])
    lines = [f"Decision: {verdict} (total {state['aggregate']['total']}/40)."]
    missed = judges["synopsis"].get("key_points_missed", [])[:2]
    if missed:
        lines.append("Evidence you did not use: " + "; ".join(missed) + ".")
    issues = [f"{f['text']} [{', '.join(f['evidence_ids'])}]" for j in judges.values() for f in j.get("flags", [])
              if f.get("evidence_ids")][:2]
    if issues:
        lines.append("Points the evidence contradicts: " + " ".join(issues))
    lines.append(f"Your weakest dimension this time was {weakest} ({judges[weakest]['score']}/10).")
    recurring = [k for k, v in sorted(memory.get("weaknesses", {}).items(), key=lambda kv: -kv[1]) if v >= 2]
    if recurring:
        lines.append(f"This has come up before ({', '.join(recurring)}): try citing evidence ids for each claim and "
                     f"checking timestamps against the logs before concluding.")
    return " ".join(lines)


def write_feedback(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    memory = db.get_memory(state["user_id"])
    with trace.step("write_feedback") as rec:
        text, mode = None, "offline"
        if not llm.is_offline():
            ctx = (f"Decision: {state['decision']}\nScores: {state['aggregate']['scores']}\n"
                   f"Judges: { {k: {'rationale': v['rationale'], 'flags': v['flags']} for k, v in state['judges'].items()} }\n"
                   f"Contributor history: {memory}\n\n<submission>\n{state['masked_text']}\n</submission>")
            try:
                text, mode = llm.structured(FEEDBACK_SYSTEM, ctx, Feedback, tier="smart", max_tokens=500).text, "llm"
            except llm.LLMError:
                text = None
        text = text or offline_feedback(state, memory)
        rec["decision"] = mode
    return {"feedback": text, "events": [_event("write_feedback", f"{len(text.split())} words ({mode})", t0)]}


# --- update_contributor_memory -------------------------------------------------------------------------
def update_contributor_memory(state: ReviewState) -> dict:
    t0 = time.perf_counter()
    mem = db.get_memory(state["user_id"])
    mem["submissions"] += 1
    mem["accepted"] += int(state["decision"]["verdict"] == "accept")
    for name in JUDGES:
        if state["judges"][name]["score"] < 6:
            mem["weaknesses"][name] = mem["weaknesses"].get(name, 0) + 1
    db.save_memory(mem)
    return {"memory": mem, "events": [_event("update_contributor_memory",
                                             f"{mem['accepted']}/{mem['submissions']} accepted; weaknesses {mem['weaknesses']}", t0)]}
