"""Turn moderator decisions into new labelled eval cases (the learning loop v1 didn't have).

Every human decision is logged in moderation_log with the AI's original verdict. Each one is
a labelled example: the submission text plus the human's final verdict (and adjusted total
when scores were changed). Overrides, where the human disagreed with the AI's proposed
outcome, are the most valuable, because they show where the panel is miscalibrated.

New cases are appended to evals/labels_generated.jsonl with status needs_review (a person
confirms them before they are merged into labels.jsonl and count in calibration).

Run: python -m evals.generate_evals
"""
from __future__ import annotations

import json
from pathlib import Path

import db

OUT = Path(__file__).parent / "labels_generated.jsonl"


def cases_from_moderation(db_path=None) -> list[dict]:
    rows = db.query("SELECT m.*, s.text, s.case_id, s.mode, s.total_score FROM moderation_log m "
                    "JOIN submissions s ON s.id = m.submission_id ORDER BY m.id")
    out = []
    for r in rows:
        final = r["decision"].split("->")[-1]            # e.g. "adjust->accept"
        adjusted = json.loads(r["adjusted_json"] or "{}")
        out.append({"id": f"mod-{r['id']}", "case_id": r["case_id"], "mode": r["mode"], "kind": "from_moderation",
                    "text": r["text"], "label": final, "human_total": r["total_score"],
                    "ai_verdict": r["ai_verdict"], "ai_total": r["ai_total"], "adjusted": adjusted,
                    "override": bool(adjusted) or final != "review", "note": r["note"], "status": "needs_review"})
    return out


def main() -> None:
    existing = set()
    if OUT.exists():
        existing = {json.loads(line)["id"] for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()}
    new = [c for c in cases_from_moderation() if c["id"] not in existing]
    with OUT.open("a", encoding="utf-8") as fh:
        for c in new:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"added {len(new)} labelled cases from moderator decisions to {OUT}")


if __name__ == "__main__":
    main()
