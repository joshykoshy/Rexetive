"""Wallet signature verification (Sui Ed25519 personal message) and the end of header trust."""
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from auth import address_from_pubkey, personal_message_digest, uleb128, verify_personal_message


def wallet():
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return key, pub, address_from_pubkey(pub)


def sign(key, pub, message: str) -> str:
    sig = key.sign(personal_message_digest(message.encode()))
    return base64.b64encode(bytes([0]) + sig + pub).decode()


def test_uleb128():
    assert uleb128(5) == b"\x05" and uleb128(300) == b"\xac\x02"


def test_valid_signature_verifies():
    key, pub, addr = wallet()
    assert verify_personal_message(addr, "hello", sign(key, pub, "hello")) == (True, "ok")


def test_tampered_message_wrong_address_and_bad_flag_fail():
    key, pub, addr = wallet()
    sig = sign(key, pub, "hello")
    assert verify_personal_message(addr, "hellO", sig)[0] is False
    _, _, other = wallet()
    assert verify_personal_message(other, "hello", sig)[1] == "public key does not match the address"
    secp = base64.b64encode(bytes([1]) + base64.b64decode(sig)[1:]).decode()
    assert "Ed25519" in verify_personal_message(addr, "hello", secp)[1]


def test_login_flow_and_header_trust_removed(api):
    client, _ = api
    # v1 trusted this header; v2 ignores it and requires a signed-in token.
    assert client.get("/me", headers={"X-Wallet-Address": "0x" + "1" * 64}).status_code == 401
    key, pub, addr = wallet()
    message = client.get("/auth/nonce", params={"address": addr}).json()["message"]
    body = {"address": addr, "message": message, "signature": sign(key, pub, message)}
    token = client.post("/auth/verify", json=body).json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["wallet_address"] == addr and me["role"] == "contributor"
    assert client.post("/auth/verify", json=body).status_code == 401  # nonce is single-use
