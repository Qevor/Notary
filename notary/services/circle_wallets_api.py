from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4, uuid5, NAMESPACE_URL


_CHAIN_TO_BLOCKCHAIN = {
    "ARC-TESTNET": "ARC_MINUS_TESTNET",
    "ETH-SEPOLIA": "ETH_MINUS_SEPOLIA",
    "BASE-SEPOLIA": "BASE_MINUS_SEPOLIA",
    "ARB-SEPOLIA": "ARB_MINUS_SEPOLIA",
    "OP-SEPOLIA": "OP_MINUS_SEPOLIA",
    "POLY-AMOY": "MATIC_MINUS_AMOY",
}

USDC_TOKEN_ADDRESS = "0x3600000000000000000000000000000000000000"


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

    def transfer_usdc(
        self,
        *,
        wallet_id: str | None,
        wallet_address: str | None,
        to_address: str,
        amount_usdc: float,
        ref_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError(
                "CIRCLE_API_KEY, CIRCLE_ENTITY_SECRET, and CIRCLE_WALLET_SET_ID are required "
                "for developer-controlled wallet transfers"
            )
        if amount_usdc <= 0:
            raise RuntimeError("Circle Wallets API transfer requires a positive USDC amount")

        try:
            from circle.web3 import utils
            from circle.web3.developer_controlled_wallets import (
                CreateTransferTransactionForDeveloperRequest,
                TransactionsApi,
            )
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency issue
            raise RuntimeError("circle-developer-controlled-wallets is not installed") from exc

        blockchain = self.chain.upper()
        payload: dict[str, Any] = {
            "idempotencyKey": str(uuid4()),
            "entitySecretCiphertext": utils.generate_entity_secret_ciphertext(
                self.api_key,
                self.entity_secret,
            ),
            "destinationAddress": to_address,
            "amounts": [format(float(amount_usdc), ".6f").rstrip("0").rstrip(".")],
            "feeLevel": "MEDIUM",
            "tokenAddress": USDC_TOKEN_ADDRESS,
            "blockchain": blockchain,
            "refId": ref_id or f"notary_transfer_{uuid4().hex[:16]}",
        }
        if wallet_id and not wallet_id.startswith("0x"):
            payload["walletId"] = wallet_id
        elif wallet_address:
            payload["walletAddress"] = wallet_address
        elif wallet_id:
            payload["walletAddress"] = wallet_id
        else:
            raise RuntimeError("Circle Wallets API transfer requires wallet_id or wallet_address")

        request = CreateTransferTransactionForDeveloperRequest.from_dict(payload)
        api = TransactionsApi(
            utils.init_developer_controlled_wallets_client(
                api_key=self.api_key,
                entity_secret=self.entity_secret,
            )
        )
        method = getattr(api, "create_developer_transaction_transfer", None) or getattr(
            api,
            "create_transfer_transaction_for_developer",
        )
        response = method(request)
        body = response.to_dict() if hasattr(response, "to_dict") else response
        data = body.get("data", body) if isinstance(body, dict) else {}
        data = data if isinstance(data, dict) else {}
        return {
            "id": data.get("id") or (body.get("id") if isinstance(body, dict) else None),
            "transactionId": data.get("id"),
            "state": data.get("state"),
            "txHash": data.get("txHash") or data.get("transactionHash"),
            "fromWalletId": wallet_id,
            "fromWalletAddress": wallet_address,
            "to": to_address,
            "amount": amount_usdc,
            "status": "submitted",
            "provider": "circle_developer_wallets",
            "raw": body,
            "demo": False,
        }
