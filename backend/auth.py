"""Wallet-signature login + JWT, replacing v1's header trust.

v1 problem: every request carried `X-Wallet-Address: 0x...` and the backend believed it. Anyone
could act as any wallet (submit as them, read their reputation) by typing an address.

v2 flow (challenge-response):
  1. GET  /auth/nonce?address=0x..  -> server stores a random nonce and returns a message
     containing it (expires in 5 minutes, single use).
  2. The wallet signs that message (`signPersonalMessage` in @mysten/dapp-kit).
  3. POST /auth/verify {address, message, signature} -> the server checks that the message is
     the one it issued, verifies the signature, and checks that the public key inside the
     signature hashes to the claimed address. Then it issues a JWT (python-jose, HS256, 2 h).
  4. Every protected endpoint requires `Authorization: Bearer <jwt>`.

Sui personal-message signatures (Ed25519): the serialized signature is
base64(flag 0x00 || 64-byte signature || 32-byte public key). The signed bytes are
blake2b-256(intent [3, 0, 0] || BCS(vector<u8> message)), where BCS encodes a byte vector as
a ULEB128 length followed by the bytes. The address is blake2b-256(flag || public key).
Only Ed25519 is implemented; secp256k1/r1 wallets get a clear error.

DEMO_MODE=true adds POST /auth/demo-login, which issues a JWT for a fixed demo moderator
without a wallet. It is labelled as a demo bypass everywhere and is off by default.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time

import db
from config import DEMO_MODE, JWT_ALGORITHM, JWT_MINUTES, JWT_SECRET
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

ED25519_FLAG = 0x00
PERSONAL_MESSAGE_INTENT = bytes([3, 0, 0])
NONCE_TTL_S = 300
DEMO_ADDRESS = "0x" + "d" * 64
bearer = HTTPBearer(auto_error=False)


# --- Sui signature verification ------------------------------------------------------------------
def uleb128(n: int) -> bytes:
    out = bytearray()
    while True:
        byte, n = n & 0x7F, n >> 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def personal_message_digest(message: bytes) -> bytes:
    return hashlib.blake2b(PERSONAL_MESSAGE_INTENT + uleb128(len(message)) + message, digest_size=32).digest()


def address_from_pubkey(pubkey: bytes, flag: int = ED25519_FLAG) -> str:
    return "0x" + hashlib.blake2b(bytes([flag]) + pubkey, digest_size=32).hexdigest()


def verify_personal_message(address: str, message: str, signature_b64: str) -> tuple[bool, str]:
    try:
        raw = base64.b64decode(signature_b64)
    except ValueError:
        return False, "signature is not base64"
    if not raw or raw[0] != ED25519_FLAG:
        return False, "only Ed25519 wallet signatures are supported"
    if len(raw) != 1 + 64 + 32:
        return False, "unexpected signature length"
    sig, pubkey = raw[1:65], raw[65:]
    if address_from_pubkey(pubkey).lower() != address.lower():
        return False, "public key does not match the address"
    try:
        Ed25519PublicKey.from_public_bytes(pubkey).verify(sig, personal_message_digest(message.encode()))
    except InvalidSignature:
        return False, "invalid signature"
    return True, "ok"


# --- challenge / token ------------------------------------------------------------------------------
def issue_nonce(address: str) -> str:
    nonce = secrets.token_hex(16)
    message = (f"Sign in to Rexetive\nAddress: {address}\nNonce: {nonce}\n"
               f"Issued: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    db.execute("INSERT OR REPLACE INTO auth_nonces(address, nonce, message, expires) VALUES (?,?,?,?)",
               (address.lower(), nonce, message, time.time() + NONCE_TTL_S))
    return message


def consume_nonce(address: str, message: str) -> bool:
    rows = db.query("SELECT message, expires FROM auth_nonces WHERE address=?", (address.lower(),))
    db.execute("DELETE FROM auth_nonces WHERE address=?", (address.lower(),))  # single use, even on failure
    return bool(rows) and rows[0]["message"] == message and rows[0]["expires"] > time.time()


def create_token(address: str, role: str, demo: bool = False) -> str:
    claims = {"sub": address, "role": role, "demo": demo, "exp": int(time.time()) + JWT_MINUTES * 60}
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def login_with_signature(address: str, message: str, signature: str) -> dict:
    if not consume_nonce(address, message):
        raise HTTPException(401, "unknown, reused or expired login message")
    ok, reason = verify_personal_message(address, message, signature)
    if not ok:
        raise HTTPException(401, reason)
    user = db.get_or_create_user(address)
    return {"access_token": create_token(address, user["role"]), "token_type": "bearer", "user": user}


def demo_login() -> dict:
    if not DEMO_MODE:
        raise HTTPException(404, "demo login is disabled")
    user = db.get_or_create_user(DEMO_ADDRESS, role="moderator", display_name="demo_moderator")
    return {"access_token": create_token(DEMO_ADDRESS, user["role"], demo=True), "token_type": "bearer",
            "user": user, "warning": "DEMO MODE: signed in without a wallet signature"}


# --- FastAPI dependencies ---------------------------------------------------------------------------
def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(401, "missing bearer token")
    try:
        claims = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as err:
        raise HTTPException(401, f"invalid token: {err}") from err
    user = db.get_or_create_user(claims["sub"])
    return {**user, "demo": claims.get("demo", False)}


def moderator(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "moderator":
        raise HTTPException(403, "moderators only")
    return user
