"""Judge calibration: does the AI panel + policy gate agree with human labels?

For each of the 30 hand-labelled submissions (evals/labels.jsonl), run the real review graph
in a sandbox and record the gate's verdict *before* any moderator acts (accept / reject /
review). Then compare with the human label:

  * accuracy (exact verdict match) and Cohen's kappa (agreement corrected for chance:
    kappa = (p_o - p_e) / (1 - p_e); 0 = chance, 1 = perfect);
  * mean absolute error between the panel total and the human total (both /40);
  * % sent to a moderator;
  * critical errors: auto-accepting something a human would reject, or auto-rejecting
    something a human would accept. These matter far more than "review" vs "reject"
    mismatches, which only cost a moderator a minute.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .sandbox import sandbox, submit

LABELS = Path(__file__).parent / "labels.jsonl"
CLASSES = ("accept", "review", "reject")


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    p_e = sum(ca[c] * cb[c] for c in set(a) | set(b)) / (n * n)
    return 0.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


def load_labels() -> list[dict]:
    return [json.loads(line) for line in LABELS.read_text(encoding="utf-8").splitlines() if line.strip()]


def run() -> dict:
    from agent.graph import start_review
    labels = load_labels()
    rows = []
    with sandbox() as new_graph:
        graph = new_graph()
        for lab in labels:  # in order, so duplicates see their originals
            sid = submit(lab["text"], lab["case_id"], lab["mode"])
            st = start_review(sid, graph=graph)["state"]
            rows.append({"id": lab["id"], "kind": lab["kind"], "label": lab["label"], "ai": st["decision"]["verdict"],
                         "human_total": lab["human_total"], "ai_total": st["aggregate"]["total"],
                         "scores": st["aggregate"]["scores"], "reasons": st["decision"]["reasons"],
                         "modes": sorted({j["mode"] for j in st["judges"].values()})})
    human, ai = [r["label"] for r in rows], [r["ai"] for r in rows]
    critical = [r for r in rows if (r["ai"] == "accept" and r["label"] == "reject") or
                (r["ai"] == "reject" and r["label"] == "accept")]
    confusion = {h: {a: sum(1 for r in rows if r["label"] == h and r["ai"] == a) for a in CLASSES} for h in CLASSES}
    return {"n": len(rows), "accuracy": sum(h == a for h, a in zip(human, ai)) / len(rows),
            "kappa": cohen_kappa(human, ai),
            "mae_total": sum(abs(r["ai_total"] - r["human_total"]) for r in rows) / len(rows),
            "to_moderator": sum(a == "review" for a in ai) / len(rows), "critical_errors": critical,
            "confusion": confusion, "rows": rows, "judge_mode": rows[0]["modes"] if rows else []}


def markdown(res: dict) -> str:
    lines = [f"n = {res['n']} hand-labelled submissions; judges ran in mode {res['judge_mode']}.", "",
             "| metric | value |", "|---|---|",
             f"| verdict accuracy | {res['accuracy']:.3f} |", f"| Cohen's kappa | {res['kappa']:.3f} |",
             f"| mean absolute error, total /40 | {res['mae_total']:.2f} |",
             f"| sent to moderator | {res['to_moderator']:.0%} |",
             f"| critical errors (auto-accept a human reject, or auto-reject a human accept) | {len(res['critical_errors'])} |",
             "", "Confusion (rows = human label, columns = AI gate):", "",
             "| human \\ AI | accept | review | reject |", "|---|---|---|---|"]
    lines += [f"| {h} | " + " | ".join(str(res["confusion"][h][a]) for a in CLASSES) + " |" for h in CLASSES]
    lines += ["", "| id | kind | human | AI | human total | AI total | why |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['kind']} | {r['label']} | {r['ai']} | {r['human_total']} | {r['ai_total']} | "
              f"{'; '.join(r['reasons'])[:90]} |" for r in res["rows"]]
    return "\n".join(lines)


if __name__ == "__main__":
    print(markdown(run()))
