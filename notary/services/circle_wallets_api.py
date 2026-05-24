from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid5, NAMESPACE_URL


_CHAIN_TO_BLOCKCHAIN = {
    "ARC-TESTNET": "ARC_MINUS_TESTNET",
    "ETH-SEPOLIA": "ETH_MINUS_SEPOLIA",
    "BASE-SEPOLIA": "BASE_MINUS_SEPOLIA",
    "ARB-SEPOLIA": "ARB_MINUS_SEPOLIA",
    "OP-SEPOLIA": "OP_MINUS_SEPOLIA",
    "POLY-AMOY": "MATIC_MINUS_AMOY",
}


def _first_wallet(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        wallets = payload.get("wallets")
        if isinstance(wallets, list) and wallets:
            item = wallets[0]
            return item if isinstance(item, dict) else None
        data = payload.get("data")
        if data is not None:
            found = _first_wallet(data)
            if found:
                return found
        for value in payload.values():
            found = _first_wallet(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _first_wallet(item)
            if found:
                return found
    return None


@dataclass(slots=True)
class CircleDeveloperWalletClient:
    api_key: str | None = None
    entity_secret: str | None = None
    wallet_set_id: str | None = None
    chain: str = "ARC-TESTNET"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.entity_secret and self.wallet_set_id)

    def create_user_wallet(self, username: str) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError(
                "CIRCLE_API_KEY, CIRCLE_ENTITY_SECRET, and CIRCLE_WALLET_SET_ID are required "
                "for scalable user wallet provisioning"
            )

        try:
            from circle.web3 import utils
            from circle.web3.developer_controlled_wallets import (
                AccountType,
                Blockchain,
                CreateWalletRequest,
                WalletMetadata,
                WalletsApi,
            )
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency issue
            raise RuntimeError("circle-developer-controlled-wallets is not installed") from exc

        blockchain_name = _CHAIN_TO_BLOCKCHAIN.get(self.chain.upper(), "ARC_MINUS_TESTNET")
        blockchain = getattr(Blockchain, blockchain_name)
        ciphertext = utils.generate_entity_secret_ciphertext(self.api_key, self.entity_secret)
        client = utils.init_developer_controlled_wallets_client(
            api_key=self.api_key,
            entity_secret=self.entity_secret,
        )
        request = CreateWalletRequest(
            idempotencyKey=str(uuid5(NAMESPACE_URL, f"notary:{self.wallet_set_id}:{username}")),
            accountType=AccountType.SCA,
            blockchains=[blockchain],
            count=1,
            entitySecretCiphertext=ciphertext,
            walletSetId=self.wallet_set_id,
            metadata=[
                WalletMetadata(
                    name=f"NOTARY @{username}",
                    refId=f"notary_user_{username}",
                )
            ],
        )
        response = WalletsApi(client).create_wallet(request)
        body = response.to_dict() if hasattr(response, "to_dict") else response
        wallet = _first_wallet(body)
        if not wallet or not wallet.get("address"):
            raise RuntimeError("Circle Wallets API did not return a wallet address")
        return {
            "walletId": wallet.get("id") or wallet.get("walletId") or wallet.get("address"),
            "address": wallet["address"],
            "walletSetId": wallet.get("walletSetId") or self.wallet_set_id,
            "blockchain": wallet.get("blockchain") or self.chain,
            "custodyType": wallet.get("custodyType") or "DEVELOPER",
            "accountType": wallet.get("accountType") or "SCA",
            "ownerHint": username,
            "provider": "circle_developer_wallets",
            "demo": False,
            "raw": wallet,
        }
