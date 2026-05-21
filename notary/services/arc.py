from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import ArcTransactionPayload, new_id


@dataclass(slots=True)
class ArcClient:
    cli_path: str = "arc"
    rpc_url: str | None = None
    demo_mode: bool = True

    async def submit_payload(self, payload: ArcTransactionPayload) -> dict[str, Any]:
        if self.demo_mode:
            tx_hash = sha256_hex(payload.model_dump(mode="json") | {"nonce": new_id("arc")})
            return {
                "txHash": tx_hash,
                "status": "submitted",
                "contract": payload.contract_name,
                "method": payload.method,
                "demo": True,
            }
        # TODO: call ARC CLI or web3 provider once testnet deployment addresses are configured.
        raise NotImplementedError("Real Arc submission is not wired yet")

    async def submit_attestation_hash(self, attestation_id: str, attestation_hash: str) -> dict[str, Any]:
        return await self.submit_payload(
            ArcTransactionPayload(
                contract_name="AttestationRegistry",
                method="recordAttestation",
                args=[attestation_id, attestation_hash],
            )
        )

    async def submit_karma_checkpoint(self, notary_id: str, checkpoint_hash: str) -> dict[str, Any]:
        return await self.submit_payload(
            ArcTransactionPayload(
                contract_name="HelixAIKarma",
                method="recordCheckpoint",
                args=[notary_id, checkpoint_hash],
            )
        )

