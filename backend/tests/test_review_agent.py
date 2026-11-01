"""Offline judges + full trajectories of the review graph."""
import pytest

from agent.judges import offline_judge
from cases import load_cases


def test_trap_claim_gets_critical_flag_citing_evidence():
    case = load_cases()[1]
    out = offline_judge("logic", case, [], "Varga did it, the guard saw Ilse in the corridor.")
    crit = [f for f in out["flags"] if f["severity"] == "critical"]
    assert crit and all(f["evidence_ids"] for f in crit) and out["score"] < 5


def test_bias_markers_lower_objectivity():
    case = load_cases()[2]
    biased = offline_judge("bias", case, [], "Halden is obviously lying, no doubt about it.")
    neutral = offline_judge("bias", case, [], "The reset [E5] and the manifest [E4] suggest Halden, though unconfirmed.")
    assert biased["score"] < neutral["score"]


@pytest.mark.slow
def test_trajectories():
    from evals.checks import trajectories
    failed = [t for t in trajectories() if not t["ok"]]
    assert not failed, failed


@pytest.mark.slow
def test_redteam_all_blocked():
    from evals.checks import redteam
    rt = redteam()
    assert all(r["ok"] for k in ("injection", "toxic", "duplicate", "sql") for r in rt[k])
    assert rt["distinct_wrongly_flagged_as_duplicate"] == 0 and rt["users_table_intact"]
