"""Typed contracts for the review agent: one Pydantic schema per judge, plus the graph state.

Why one schema per judge: v1 asked one gpt-4 prompt for eight things and parsed whatever
JSON came back (`json.loads` on free text, no validation). Here each judge has a narrow job
and a narrow schema; the provider constrains decoding to it, Pydantic validates it, and an
invalid response is retried once. Every flag must name the evidence ids it relies on.

Scores are clamped to 0..10 in code (not in the schema) so the schema stays compatible with
strict structured-output modes.
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


class EvidenceFlag(BaseModel):
    text: str = Field(description="The problem, in one sentence")
    severity: Literal["critical", "minor"]
    evidence_ids: list[str] = Field(description="Evidence ids that show the problem, e.g. ['E4']")


class JudgeBase(BaseModel):
    score: int = Field(description="0 to 10")
    rationale: str = Field(description="Two or three sentences, citing evidence ids like [E2]")
    flags: list[EvidenceFlag]


class SynopsisJudgement(JudgeBase):
    key_points_missed: list[str]


class LogicJudgement(JudgeBase):
    inconsistencies: list[str]
    missing_links: list[str]


class HypothesisJudgement(JudgeBase):
    counterpoints: list[str]
    evidence_match: str


class BiasJudgement(JudgeBase):
    detected_biases: list[str]
    challenge_points: list[str]


class Feedback(BaseModel):
    text: str = Field(description="Constructive feedback, 4-6 sentences, citing evidence ids like [E3]")


def merge_dicts(a: dict, b: dict) -> dict:
    """Reducer so the four parallel judges can each write their own key into `judges`."""
    return {**(a or {}), **(b or {})}


class ReviewState(TypedDict, total=False):
    submission_id: int
    case_id: int
    mode: str
    text: str
    user_id: int
    author: str
    masked_text: str
    guard: dict
    duplicate: dict
    evidence: list[dict]
    judges: Annotated[dict, merge_dicts]
    aggregate: dict
    decision: dict
    moderation: dict
    credential: dict
    reputation: dict
    feedback: str
    memory: dict
    status: str
    events: Annotated[list[dict], operator.add]
