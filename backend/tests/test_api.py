"""API: demo login, agent-backed v1 endpoint, moderation, analytics guard, role checks."""
import pytest

STRONG = ("Pell requested the evening alarm maintenance [E3] and raised the insurance [E6]; a cloned badge [E4] was used "
          "at 21:42 [E2] while Varga paid at the restaurant (receipt) [E5]. The corridor camera contradicts the guard [E7].")


@pytest.mark.slow
def test_submit_review_and_trace(api):
    client, headers = api
    res = client.post("/submit_submission/synopsis", json={"caseId": 1, "case": "", "theory": STRONG},
                      headers=headers).json()
    assert {"clarity", "consistency", "plausibility", "relevance", "is_valid", "rank", "review"} <= res.keys()
    trace = client.get(f"/review/{res['submission_id']}", headers=headers).json()
    nodes = [e["node"] for e in trace["events"]]
    assert {"judge_synopsis", "judge_logic", "judge_hypothesis", "judge_bias", "policy_gate"} <= set(nodes)
    assert trace["decision"]["verdict"] in ("accept", "review", "reject")


def test_analytics_blocks_drop_and_answers(api):
    client, headers = api
    blocked = client.post("/analytics/ask", json={"sql": "DROP TABLE users"}, headers=headers).json()
    assert blocked["guard"]["ok"] is False and not blocked["rows"]
    ok = client.post("/analytics/ask", json={"question": "submissions by status"}, headers=headers).json()
    assert ok["guard"]["ok"] and "LIMIT 200" in ok["safe_sql"]


def test_contributor_cannot_moderate(api):
    client, _ = api
    import db
    from auth import create_token
    db.get_or_create_user("0x" + "2" * 64)
    h = {"Authorization": f"Bearer {create_token('0x' + '2' * 64, 'contributor')}"}
    assert client.get("/moderation/queue", headers=h).status_code == 403
    assert client.post("/analytics/ask", json={"question": "x"}, headers=h).status_code == 403
