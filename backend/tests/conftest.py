import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OFFLINE", "1")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SUI_MOCK", "1")


@pytest.fixture
def api(tmp_path, monkeypatch):
    """TestClient on a temp DB, signed in through the DEMO_MODE bypass (moderator)."""
    import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "rexetive.db")
    import auth
    monkeypatch.setattr(auth, "DEMO_MODE", True)
    from fastapi.testclient import TestClient

    import main
    client = TestClient(main.app)
    token = client.post("/auth/demo-login").json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}
