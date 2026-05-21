from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from notary.crypto.hashing import sha256_hex


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _normalize_message_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, list):
        return [_normalize_message_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_message_value(item) for key, item in value.items()}
    return value


def build_eip712_payload(
    *,
    domain_name: str,
    domain_version: str,
    chain_id: int | None,
    verifying_contract: str | None,
    primary_type: str,
    message: dict[str, Any],
    message_types: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            **message_types,
        },
        "primaryType": primary_type,
        "domain": {
            "name": domain_name,
            "version": domain_version,
            "chainId": chain_id or 0,
            "verifyingContract": verifying_contract or ZERO_ADDRESS,
        },
        "message": _normalize_message_value(message),
    }


def sign_placeholder(domain: str, message: dict[str, Any], signer: str = "demo-signer") -> str:
    normalized = _normalize_message_value(message)
    return sha256_hex({"domain": domain, "signer": signer, "message": normalized})


@dataclass(slots=True)
class EIP712Signer:
    private_key: str | None = None
    domain_name: str = "NOTARY"
    domain_version: str = "1"
    chain_id: int | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.private_key)

    @property
    def address(self) -> str:
        if not self.private_key:
            return "demo-signer"
        return Account.from_key(self.private_key).address

    def sign_typed_data(
        self,
        *,
        primary_type: str,
        message: dict[str, Any],
        message_types: dict[str, list[dict[str, str]]],
        verifying_contract: str | None = None,
    ) -> str:
        if not self.private_key:
            return sign_placeholder(primary_type, message, self.address)

        payload = build_eip712_payload(
            domain_name=self.domain_name,
            domain_version=self.domain_version,
            chain_id=self.chain_id,
            verifying_contract=verifying_contract,
            primary_type=primary_type,
            message=message,
            message_types=message_types,
        )
        signable = encode_typed_data(full_message=payload)
        signed = Account.sign_message(signable, private_key=self.private_key)
        return signed.signature.hex()
