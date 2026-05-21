from __future__ import annotations

from typing import Any

from notary.crypto.hashing import sha256_hex


def build_eip712_placeholder(domain: str, message: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic typed-data-like payload until real signer wiring is added."""
    return {
        "domain": {"name": domain, "version": "0.1.0"},
        "message": message,
        "messageHash": sha256_hex(message),
    }


def sign_placeholder(domain: str, message: dict[str, Any], signer: str = "demo-signer") -> str:
    typed = build_eip712_placeholder(domain, message)
    return sha256_hex({"signer": signer, "typed": typed})

