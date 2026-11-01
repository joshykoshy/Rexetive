"""Aggregation and the policy gate: pure Python, no model.

Why the decision is code, not the LLM: accepting a submission has consequences (a
credential on-chain, reputation points). Those must follow a rule a moderator can read,
test and audit: the same inputs always give the same verdict. The models produce
*evidence-cited scores*; this module turns scores into a decision.

aggregate: total = sum of the four judge scores (out of 40). disagreement = max - min of the
           judges' normalised scores (score / 10). A big spread means the panel is unsure.
decide (first matching rule wins):
  1. unsafe content (toxicity)                              -> reject
  2. total < 26                                             -> reject
  3. prompt injection / near-duplicate / disagreement > 0.4 -> human review
  4. total >= 30 and no uncited critical flag                -> accept
  5. everything else (26-29, or uncited critical flag)      -> human review
(Version 1 of this gate checked rule 3 before rule 2. Calibration against human labels
showed clearly weak submissions being sent to moderators because one judge rated them
high; low totals are now rejected first. See README, "Calibration".)
rank (for the credential): Gold >= 36, Silver >= 33, Bronze >= 30.
"""
from __future__ import annotations

from config import ACCEPT_MIN_TOTAL, MAX_DISAGREEMENT, REJECT_BELOW_TOTAL

from .judges import JUDGES


def aggregate(judges: dict) -> dict:
    scores = {name: judges[name]["score"] for name in JUDGES if name in judges}
    normalised = {k: v / 10 for k, v in scores.items()}
    return {"scores": scores, "total": sum(scores.values()), "max_total": 10 * len(JUDGES),
            "disagreement": round(max(normalised.values()) - min(normalised.values()), 3) if normalised else 0.0}


def uncited_critical(judges: dict) -> list[str]:
    return [f"{name}: {f['text']}" for name, j in judges.items() for f in j.get("flags", [])
            if f.get("severity") == "critical" and f.get("uncited")]


def decide(agg: dict, judges: dict, guard: dict, duplicate: dict) -> dict:
    total, spread = agg["total"], agg["disagreement"]
    if not guard.get("is_safe", True):
        return {"verdict": "reject", "reasons": ["unsafe content: " + ", ".join(guard.get("toxicity", []))]}
    if total < REJECT_BELOW_TOTAL:
        return {"verdict": "reject", "reasons": [f"total {total} < {REJECT_BELOW_TOTAL}"]}
    review = []
    if guard.get("injection"):
        review.append("possible prompt injection: " + "; ".join(guard["injection"]))
    if duplicate.get("is_duplicate"):
        review.append(f"near-duplicate of submission #{duplicate['of']} (similarity {duplicate['similarity']})")
    if spread > MAX_DISAGREEMENT:
        review.append(f"judges disagree (spread {spread} > {MAX_DISAGREEMENT})")
    if review:
        return {"verdict": "review", "reasons": review}
    uncited = uncited_critical(judges)
    if total >= ACCEPT_MIN_TOTAL and not uncited:
        return {"verdict": "accept", "reasons": [f"total {total} >= {ACCEPT_MIN_TOTAL}, safe, no uncited critical flag"]}
    reasons = [f"uncited critical flag: {u}" for u in uncited] or [
        f"borderline total {total} (between {REJECT_BELOW_TOTAL} and {ACCEPT_MIN_TOTAL - 1})"]
    return {"verdict": "review", "reasons": reasons}


def rank(total: float) -> str:
    return "Gold" if total >= 36 else "Silver" if total >= 33 else "Bronze" if total >= ACCEPT_MIN_TOTAL else "None"


def reputation_points(total: float, nft_minted: bool) -> int:
    """v1's point rules, unchanged (main.py on master)."""
    points = 10 if total >= 30 else 5 if total >= 25 else 2 if total >= 20 else 1
    return points + (5 if nft_minted else 0)
