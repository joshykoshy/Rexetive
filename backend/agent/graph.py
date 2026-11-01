"""The review LangGraph: wiring, parallel fan-out/fan-in, checkpointer, service functions.

    input_guard -> dedupe_check -> retrieve_evidence -+-> judge_synopsis  -+-> aggregate -> policy_gate
                                                      +-> judge_logic      -+
                                                      +-> judge_hypothesis -+
                                                      +-> judge_bias       -+
    policy_gate --accept--> issue_credential -> update_reputation -> write_feedback
                --reject--> write_feedback
                --review--> moderator_review (interrupt) --accept--> issue_credential ...
                                                         --reject--> write_feedback
    write_feedback -> update_contributor_memory -> END

The four judges run in the same superstep (parallel); `aggregate` waits for all four. Each
judge writes its own key into `judges` through a merge reducer, so parallel writes don't clash.
The SQLite checkpointer uses thread_id = "sub-<submission id>", so a paused review can be
resumed from the moderation queue at any time, even after a restart.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache

import db
from config import CHECKPOINT_DB, TRACE_LOG
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from ragcore import trace

from . import nodes
from .judges import JUDGES
from .schemas import ReviewState

RECURSION_LIMIT = 25


def build_graph(checkpointer=None):
    g = StateGraph(ReviewState)
    g.add_node("input_guard", nodes.input_guard)
    g.add_node("dedupe_check", nodes.dedupe_check)
    g.add_node("retrieve_evidence", nodes.retrieve_evidence_node)
    judge_nodes = [f"judge_{n}" for n in JUDGES]
    for name in judge_nodes:
        g.add_node(name, getattr(nodes, name))
    for name in ("aggregate", "policy_gate", "moderator_review", "issue_credential", "update_reputation",
                 "write_feedback", "update_contributor_memory"):
        g.add_node(name, getattr(nodes, name))
    g.add_edge(START, "input_guard")
    g.add_edge("input_guard", "dedupe_check")
    g.add_edge("dedupe_check", "retrieve_evidence")
    for name in judge_nodes:
        g.add_edge("retrieve_evidence", name)        # fan-out
    g.add_edge(judge_nodes, "aggregate")             # fan-in: waits for all four
    g.add_edge("aggregate", "policy_gate")
    g.add_conditional_edges("policy_gate", nodes.route_after_gate,
                            ["issue_credential", "write_feedback", "moderator_review"])
    g.add_conditional_edges("moderator_review", nodes.route_after_moderation, ["issue_credential", "write_feedback"])
    g.add_edge("issue_credential", "update_reputation")
    g.add_edge("update_reputation", "write_feedback")
    g.add_edge("write_feedback", "update_contributor_memory")
    g.add_edge("update_contributor_memory", END)
    return g.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_graph():
    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    return build_graph(SqliteSaver(sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)))


def mermaid() -> str:
    return build_graph().get_graph().draw_mermaid()


def thread_id(submission_id: int) -> str:
    return f"sub-{submission_id}"


def _config(submission_id: int) -> dict:
    return {"configurable": {"thread_id": thread_id(submission_id)}, "recursion_limit": RECURSION_LIMIT}


def _run(graph, payload, submission_id: int) -> dict:
    tracer = trace.Tracer(TRACE_LOG, kind="review", request_id=thread_id(submission_id))
    pending = None
    chunks = graph.stream(payload, _config(submission_id), stream_mode="updates")
    while True:
        with trace.tracing(tracer):  # entered per step: safe if a server resumes us on another thread
            chunk = next(chunks, None)
        if chunk is None:
            break
        if "__interrupt__" in chunk:
            pending = chunk["__interrupt__"][0].value
    return {**snapshot(submission_id, graph), "interrupt": pending}


def snapshot(submission_id: int, graph=None) -> dict:
    graph = graph or get_graph()
    state = graph.get_state(_config(submission_id))
    values = dict(state.values or {})
    waiting = list(state.next or [])
    status = "needs_review" if "moderator_review" in waiting else values.get("status", "unknown")
    return {"submission_id": submission_id, "thread_id": thread_id(submission_id), "status": status,
            "next": waiting, "state": values}


def start_review(submission_id: int, graph=None) -> dict:
    sub = db.get_submission(submission_id)
    if not sub:
        raise ValueError(f"unknown submission {submission_id}")
    payload = {"submission_id": submission_id, "case_id": sub["case_id"], "mode": sub["mode"], "text": sub["text"],
               "user_id": sub["user_id"], "author": sub["author"], "events": []}
    return _run(graph or get_graph(), payload, submission_id)


def resume_review(submission_id: int, decision: str, scores: dict | None = None, note: str = "",
                  moderator: str = "moderator", graph=None) -> dict:
    graph = graph or get_graph()
    if "moderator_review" not in (graph.get_state(_config(submission_id)).next or ()):
        raise ValueError(f"submission {submission_id} is not waiting for a moderator")
    return _run(graph, Command(resume={"decision": decision, "scores": scores or {}, "note": note,
                                       "moderator": moderator}), submission_id)
