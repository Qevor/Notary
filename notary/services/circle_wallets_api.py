from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL


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


def _transaction_data(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    if isinstance(data, dict) and isinstance(data.get("transaction"), dict):
        return data["transaction"]
    return data if isinstance(data, dict) else {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


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
        data = _transaction_data(body)
        final_body = body
        transaction_id = data.get("id")
        if transaction_id:
            for _ in range(15):
                state = str(data.get("state") or "").upper()
                tx_hash = data.get("txHash") or data.get("transactionHash")
                if tx_hash or state in {"COMPLETE", "FAILED", "CANCELLED", "DENIED"}:
                    break
                time.sleep(2)
                poll_response = api.get_transaction(UUID(str(transaction_id)))
                final_body = poll_response.to_dict() if hasattr(poll_response, "to_dict") else poll_response
                data = _transaction_data(final_body)
            if str(data.get("state") or "").upper() in {"FAILED", "CANCELLED", "DENIED"}:
                raise RuntimeError(f"Circle Wallets API transfer did not complete: {data.get('state')}")

        tx_hash = data.get("txHash") or data.get("transactionHash")
        return {
            "id": data.get("id") or (body.get("id") if isinstance(body, dict) else None),
            "transactionId": data.get("id"),
            "state": data.get("state"),
            "txHash": tx_hash,
            "fromWalletId": wallet_id,
            "fromWalletAddress": data.get("sourceAddress") or wallet_address,
            "to": data.get("destinationAddress") or to_address,
            "amount": amount_usdc,
            "status": "complete" if tx_hash else "submitted",
            "provider": "circle_developer_wallets",
            "raw": _jsonable(final_body),
            "demo": False,
        }
