"""Credential + reputation side effects, with a mock chain for demos.

v1 called Sui directly (blockchain_utils.py, kept unchanged) and created the Sui client at
import time, so the backend could not even start without a funded testnet key. v2 imports
blockchain_utils only when SUI_MOCK=0. With SUI_MOCK=1 (default) a deterministic fake digest
is returned and the action is logged with the prefix "MOCK CHAIN", so nobody mistakes a demo
credential for a real one.

Reputation is always recorded in SQLite (fast reads for the UI and analytics); on a real
chain it is also written on-chain with v1's Move call.
"""
from __future__ import annotations

import hashlib
import logging

import db
from config import SUI_MOCK

log = logging.getLogger("rexetive.chain")


def issue_credential(submission_id: int, user_id: int, author: str, case_id: int, total: int,
                     summary: str, rank: str, timestamp: int) -> dict:
    if SUI_MOCK:
        digest = "MOCK-" + hashlib.sha256(f"{submission_id}:{author}:{total}".encode()).hexdigest()[:40]
        log.warning("MOCK CHAIN: credential for submission %s -> %s", submission_id, digest)
        chain = "mock"
    else:
        import blockchain_utils  # needs SUI_* env vars and a funded key
        result = blockchain_utils.mint_nft(case_id, author, int(total), summary[:200], rank, timestamp)
        digest, chain = result["tx_digest"], "sui"
    db.add_credential(submission_id, user_id, digest, chain)
    return {"digest": digest, "chain": chain, "nft_minted": True}


def update_reputation(user_id: int, author: str, points: int, accepted: bool, nft_minted: bool) -> dict:
    rep = db.add_reputation(user_id, points, accepted, nft_minted)
    if not SUI_MOCK:
        import asyncio

        import blockchain_utils
        asyncio.run(blockchain_utils.update_user_reputation(author, points, nft_minted))
    else:
        log.warning("MOCK CHAIN: +%s reputation for user %s", points, user_id)
    return rep
