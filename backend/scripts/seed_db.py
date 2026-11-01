"""Seed data/rexetive.db with synthetic users, ~150 submissions, reviews, credentials and reputation.

The data is synthetic and deterministic (random seed 42). It exists so the moderator
analytics page has something to query, e.g. "acceptance rate per case" or "top contributors".
Scores are drawn per judge and the status follows the same policy thresholds as the real
gate, so the numbers are internally consistent. No real people: display names are invented.

Run: python scripts/seed_db.py [--reset]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db  # noqa: E402
from agent.policy import aggregate, decide, reputation_points  # noqa: E402
from cases import load_cases  # noqa: E402
from config import DB_PATH  # noqa: E402

DEMO_MODERATOR = "0x" + "d" * 64
NAMES = ["amber_fox", "quiet_heron", "tidewatcher", "north_lantern", "copper_kite", "slate_owl", "mossline", "redfern",
         "harbourlight", "juniper_k", "osprey88", "cinder_m", "willowmark", "pinegrove", "saltmarsh", "brightquill",
         "ember_lane", "low_tide", "kestrel_n", "fieldnote", "graywing", "lumen_r", "otterbank", "seastack"]
MODES = ["synopsis", "logic", "hypothesis", "bias"]
OPENERS = ["My reading of the evidence:", "Timeline first.", "Here is what I think happened.", "Looking at the logs,",
           "A cautious theory:", "I think the key is the records."]


def fake_address(name: str) -> str:
    return "0x" + hashlib.sha256(name.encode()).hexdigest()


def synthetic_text(case: dict, rng: random.Random, quality: float) -> str:
    facts = [f["text"] for f in case["key_facts"]]
    used = rng.sample(facts, k=max(1, round(quality * len(facts))))
    cites = [f"[{f['evidence']}]" for f in case["key_facts"] if f["text"] in used]
    body = " ".join(f"{u} {c}." for u, c in zip(used, cites))
    if quality < 0.35:
        body += " " + case["traps"][0]["explanation"].replace("places her elsewhere", "doesn't matter")
    return f"{rng.choice(OPENERS)} {body}"


def seed(reset: bool = False, n_submissions: int = 150) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    rng = random.Random(42)
    cases = load_cases()
    db.get_or_create_user(DEMO_MODERATOR, role="moderator", display_name="demo_moderator")
    users = [db.get_or_create_user(fake_address(n), display_name=n) for n in NAMES]
    start = dt.datetime(2026, 9, 15)
    with closing(db.connect()) as conn, conn:
        if conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0] >= n_submissions:
            print("already seeded")
            return
        for i in range(n_submissions):
            case = cases[rng.choice(list(cases))]
            user = rng.choice(users)
            quality = rng.random()
            base = 3 + quality * 7
            judges = {m: {"score": int(max(0, min(10, round(rng.gauss(base, 1.3))))), "flags": [],
                          "rationale": "synthetic seed review"} for m in MODES}
            agg = aggregate(judges)
            verdict = decide(agg, judges, {"is_safe": True}, {"is_duplicate": False})["verdict"]
            status = {"accept": "accepted", "reject": "rejected", "review": "needs_review"}[verdict]
            if status == "needs_review" and rng.random() < 0.7:  # most past borderline items were already moderated
                status = rng.choice(["accepted", "rejected"])
            created = (start + dt.timedelta(hours=rng.randint(0, 24 * 45))).strftime("%Y-%m-%dT%H:%M:%S")
            sid = conn.execute(
                "INSERT INTO submissions(case_id, user_id, mode, text, status, total_score, disagreement, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (case["id"], user["id"], rng.choice(MODES), synthetic_text(case, rng, quality), status, agg["total"],
                 agg["disagreement"], created)).lastrowid
            for m, j in judges.items():
                conn.execute("INSERT INTO reviews(submission_id, judge, score, rationale, flags_json, created_at) "
                             "VALUES (?,?,?,?,?,?)", (sid, m, j["score"], j["rationale"], "[]", created))
            if status == "accepted":
                conn.execute("INSERT INTO credentials(submission_id, user_id, digest, chain, created_at) VALUES (?,?,?,?,?)",
                             (sid, user["id"], "MOCK-" + hashlib.sha256(str(sid).encode()).hexdigest()[:40], "mock", created))
                conn.execute("UPDATE reputation SET points = points + ?, accepted = accepted + 1, nft_count = nft_count + 1, "
                             "updated_at=? WHERE user_id=?", (reputation_points(agg["total"], True), created, user["id"]))
            elif status == "rejected":
                conn.execute("UPDATE reputation SET points = points + ?, updated_at=? WHERE user_id=?",
                             (reputation_points(agg["total"], False) if agg["total"] >= 20 else 0, created, user["id"]))
        counts = dict(conn.execute("SELECT status, COUNT(*) FROM submissions GROUP BY status").fetchall())
    print(f"seeded {DB_PATH}: {len(users)} users + 1 moderator, submissions by status {json.dumps(counts)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    seed(parser.parse_args().reset)
