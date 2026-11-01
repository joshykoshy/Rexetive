"""A throwaway database + checkpointer so evals and tests never touch data/rexetive.db."""
from __future__ import annotations

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

import db
from agent.graph import build_graph
from langgraph.checkpoint.sqlite import SqliteSaver


@contextmanager
def sandbox():
    """Yields new_graph(): each call builds a graph on the same temp checkpoint file
    (calling it twice simulates a server restart)."""
    original = db.DB_PATH
    conns: list[sqlite3.Connection] = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db.DB_PATH = Path(tmp) / "rexetive.db"

        def new_graph():
            conn = sqlite3.connect(Path(tmp) / "ckpt.db", check_same_thread=False)
            conns.append(conn)
            return build_graph(SqliteSaver(conn))
        try:
            yield new_graph
        finally:
            for c in conns:
                c.close()
            db.DB_PATH = original


def submit(text: str, case_id: int, mode: str = "synopsis", address: str = "0x" + "e" * 64) -> int:
    user = db.get_or_create_user(address)
    return db.create_submission(case_id, user["id"], mode, text)
