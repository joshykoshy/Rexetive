"""Run every Rexetive eval and write data/logs/eval_report.md (+ eval_results.json).

    python -m evals.run_all

Sections: judge calibration vs human labels, red team (injection, toxic, duplicates, SQL
attacks), agent trajectories, evidence retrieval (20 golden questions). All run in sandbox
databases, so data/rexetive.db is never modified.
"""
from __future__ import annotations

import datetime as dt
import json

from config import LOG_DIR
from ragcore import llm
from ragcore.evals import markdown_table

from . import calibration, checks

REPORT = LOG_DIR / "eval_report.md"
RESULTS = LOG_DIR / "eval_results.json"


def main() -> dict:
    out = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "model": llm.badge()}
    md = ["# Rexetive eval report", "", f"Generated {out['generated']} | brain: {out['model']}", "",
          "## Judge calibration (AI panel + policy gate vs 30 human labels)", ""]
    cal = calibration.run()
    out["calibration"] = {k: v for k, v in cal.items() if k != "rows"} | {"rows": cal["rows"]}
    md.append(calibration.markdown(cal))

    rt = checks.redteam()
    out["redteam"] = rt
    sql_ok = sum(r["ok"] for r in rt["sql"])
    md += ["", "## Red team", "", "| attack | blocked / handled | detail |", "|---|---|---|",
           f"| prompt injection in submission | {sum(r['ok'] for r in rt['injection'])}/{len(rt['injection'])} | flagged by guard, never auto-accepted ({', '.join(r['verdict'] for r in rt['injection'])}) |",
           f"| toxic submission | {sum(r['ok'] for r in rt['toxic'])}/{len(rt['toxic'])} | rejected as unsafe |",
           f"| near-duplicate resubmission | {sum(r['ok'] for r in rt['duplicate'])}/{len(rt['duplicate'])} | similarity {', '.join(str(r['similarity']) for r in rt['duplicate'])}; distinct analyses wrongly flagged: {rt['distinct_wrongly_flagged_as_duplicate']} |",
           f"| SQL attacks (typed + model-generated) | {sql_ok}/{len(rt['sql'])} | users table intact: {rt['users_table_intact']} |", ""]
    md += [f"- `{r['attack']}` ({r['path']}): {r['reason']}" for r in rt["sql"]]

    traj = checks.trajectories()
    out["trajectories"] = traj
    md += ["", "## Agent trajectories", "", "| test | result | detail |", "|---|---|---|"]
    md += [f"| {t['name']} | {'PASS' if t['ok'] else 'FAIL'} | {t['detail']} |" for t in traj]

    ret = checks.retrieval()
    out["retrieval"] = {k: {"overall": v["overall"]} for k, v in ret.items()}
    md += ["", "## Evidence retrieval (20 golden questions, filtered to the case)", "", markdown_table(ret)]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")
    RESULTS.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("\n".join(md))
    print(f"\nwrote {REPORT}")
    return out


if __name__ == "__main__":
    main()
