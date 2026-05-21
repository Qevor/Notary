from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from eth_abi import encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address, to_hex

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import ArcTransactionPayload, new_id


MethodSpec = tuple[str, list[str]]


METHOD_SPECS: dict[tuple[str, str], MethodSpec] = {
    ("AttestationRegistry", "recordAttestation"): (
        "recordAttestation(bytes32,bytes32,bytes32,bytes32,bytes32,uint64,uint8,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "uint64", "uint8", "address"],
    ),
    ("AttestationRegistry", "recordPrediction"): (
        "recordPrediction(bytes32,bytes32)",
        ["bytes32", "bytes32"],
    ),
    ("HelixAIKarma", "recordCheckpoint"): (
        "recordCheckpoint(bytes32,bytes32,uint64,uint64,uint64,uint64,int256,address)",
        ["bytes32", "bytes32", "uint64", "uint64", "uint64", "uint64", "int256", "address"],
    ),
    ("NotaryIdentityRegistry", "createNotary"): (
        "createNotary(bytes32,address,address,bytes32,bytes32,bytes32,bytes32,bytes32)",
        ["bytes32", "address", "address", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32"],
    ),
    ("NotaryValidationRegistry", "recordValidation"): (
        "recordValidation(bytes32,bytes32,bytes32,bytes32,bytes32,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "address"],
    ),
    ("NotaryGovernance", "updateGovernance"): (
        "updateGovernance(bytes32,bytes32,bytes32,bytes32,bytes32,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "address"],
    ),
}


def _bytes32_from_text(value: str) -> bytes:
    clean = value[2:] if value.startswith("0x") else value
    if len(clean) == 64 and all(char in "0123456789abcdefABCDEF" for char in clean):
        return bytes.fromhex(clean)
    return bytes.fromhex(sha256_hex(value)[2:])


def _convert_arg(arg_type: str, value: Any) -> Any:
    if arg_type == "bytes32":
        return _bytes32_from_text(str(value))
    if arg_type == "address":
        return to_checksum_address(str(value))
    if arg_type in {"uint64", "uint8", "uint256", "int256"}:
        return int(value)
    return value


def _encode_call(method_signature: str, arg_types: list[str], args: list[Any]) -> str:
    selector = keccak(text=method_signature)[:4]
    encoded_args = encode(arg_types, [_convert_arg(arg_type, arg) for arg_type, arg in zip(arg_types, args, strict=True)])
    return to_hex(selector + encoded_args)


@dataclass(slots=True)
class ArcClient:
    rpc_url: str | None = None
    chain_id: int | None = None
    private_key: str | None = None
    demo_mode: bool = True
    contract_addresses: dict[str, str] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return (
            not self.demo_mode
            and bool(self.rpc_url)
            and bool(self.private_key)
            and bool(self.chain_id)
        )

    @property
    def sender(self) -> str:
        if not self.private_key:
            return "demo-arc-sender"
        return Account.from_key(self.private_key).address

    async def submit_payload(self, payload: ArcTransactionPayload) -> dict[str, Any]:
        if not self.enabled:
            tx_hash = sha256_hex(payload.model_dump(mode="json") | {"nonce": new_id("arc")})
            return {
                "txHash": tx_hash,
                "status": "simulated",
                "contract": payload.contract_name,
                "method": payload.method,
                "demo": True,
            }

        contract_address = self.contract_addresses.get(payload.contract_name)
        if not contract_address:
            raise RuntimeError(f"Arc contract address is not configured for {payload.contract_name}")

        spec = METHOD_SPECS.get((payload.contract_name, payload.method))
        if spec is None:
            raise RuntimeError(f"Unsupported Arc payload: {payload.contract_name}.{payload.method}")

        method_signature, arg_types = spec
        if len(arg_types) != len(payload.args):
            raise RuntimeError(
                f"Argument mismatch for {payload.contract_name}.{payload.method}: "
                f"expected {len(arg_types)}, got {len(payload.args)}"
            )

        data = _encode_call(method_signature, arg_types, payload.args)
        nonce = await self._rpc("eth_getTransactionCount", [self.sender, "pending"])
        gas_price = await self._rpc("eth_gasPrice", [])
        tx = {
            "from": self.sender,
            "to": to_checksum_address(contract_address),
            "value": hex(payload.value),
            "data": data,
            "nonce": nonce,
            "chainId": hex(self.chain_id),
            "gasPrice": gas_price,
        }
        estimated_gas = await self._rpc("eth_estimateGas", [tx])
        tx["gas"] = estimated_gas

        signed = Account.sign_transaction(
            {
                "from": self.sender,
                "to": to_checksum_address(contract_address),
                "value": int(payload.value),
                "data": data,
                "nonce": int(nonce, 16),
                "chainId": self.chain_id,
                "gasPrice": int(gas_price, 16),
                "gas": int(estimated_gas, 16),
            },
            self.private_key,
        )
        tx_hash = await self._rpc("eth_sendRawTransaction", [signed.raw_transaction.hex()])
        return {
            "txHash": tx_hash,
            "status": "submitted",
            "contract": payload.contract_name,
            "method": payload.method,
            "from": self.sender,
            "to": to_checksum_address(contract_address),
        }

    async def submit_attestation_hash(self, attestation_id: str, attestation_hash: str) -> dict[str, Any]:
        return await self.submit_payload(
            ArcTransactionPayload(
                contract_name="AttestationRegistry",
                method="recordPrediction",
                args=[attestation_id, attestation_hash],
            )
        )

    async def submit_karma_checkpoint(self, notary_id: str, checkpoint_hash: str) -> dict[str, Any]:
        return await self.submit_payload(
            ArcTransactionPayload(
                contract_name="HelixAIKarma",
                method="recordCheckpoint",
                args=[notary_id, checkpoint_hash, 0, 0, 0, 0, 0, self.sender],
            )
        )

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        if not self.rpc_url:
            raise RuntimeError("ARC RPC URL is not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            response.raise_for_status()
            body = response.json()
        if body.get("error"):
            raise RuntimeError(f"ARC RPC error for {method}: {body['error']}")
        return body["result"]
