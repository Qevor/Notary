from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from eth_abi import encode
    from eth_account import Account
    from eth_utils import keccak, to_checksum_address, to_hex
except ModuleNotFoundError:  # pragma: no cover - live Arc mode requires these deps
    encode = None
    Account = None
    keccak = None
    to_checksum_address = None
    to_hex = None

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import ArcTransactionPayload, new_id


MethodSpec = tuple[str, list[str]]
USDC_TOKEN_ADDRESS = "0x3600000000000000000000000000000000000000"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ERC20_TRANSFER_SIGNATURE = "transfer(address,uint256)"


METHOD_SPECS: dict[tuple[str, str], MethodSpec] = {
    ("AttestationRegistry", "recordAttestation"): (
        "recordAttestation(bytes32,bytes32,bytes32,bytes32,bytes32,uint64,uint8,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "uint64", "uint8", "address"],
    ),
    ("NotaryIdentityRegistry", "createNotary"): (
        "createNotary(bytes32,address,address,bytes32,bytes32,bytes32,bytes32)",
        ["bytes32", "address", "address", "bytes32", "bytes32", "bytes32", "bytes32"],
    ),
    ("NotaryValidationRegistry", "recordValidation"): (
        "recordValidation(bytes32,bytes32,bytes32,bytes32,bytes32,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "address"],
    ),
    ("NotaryGovernance", "updateGovernance"): (
        "updateGovernance(bytes32,bytes32,bytes32,bytes32,bytes32,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "address"],
    ),
    ("NotaryKarma", "recordKarma"): (
        "recordKarma(bytes32,bytes32,int256,uint256,bytes32,address)",
        ["bytes32", "bytes32", "int256", "uint256", "bytes32", "address"],
    ),
    ("NotaryAgentIdentity", "registerAgent"): (
        "registerAgent(bytes32,address,bytes32,bytes32,bytes32)",
        ["bytes32", "address", "bytes32", "bytes32", "bytes32"],
    ),
    ("NotaryReplication", "recordReplication"): (
        "recordReplication(bytes32,bytes32,bytes32,bytes32,address)",
        ["bytes32", "bytes32", "bytes32", "bytes32", "address"],
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
        if to_checksum_address is None:
            raise RuntimeError("eth-utils is required for live Arc transaction encoding")
        return to_checksum_address(str(value))
    if arg_type in {"uint64", "uint8", "uint256", "int256"}:
        return int(value)
    return value


def _encode_call(method_signature: str, arg_types: list[str], args: list[Any]) -> str:
    if encode is None or keccak is None or to_hex is None:
        raise RuntimeError("eth-abi and eth-utils are required for live Arc transaction encoding")
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
        if Account is None:
            raise RuntimeError("eth-account is required for live Arc signing")
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
        if to_checksum_address is None or Account is None:
            raise RuntimeError("eth-account and eth-utils are required for live Arc submission")
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

    async def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Live Arc RPC is required to verify transactions")
        return await self._rpc("eth_getTransactionByHash", [tx_hash])

    async def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Live Arc RPC is required to verify transactions")
        receipt = await self._rpc("eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            raise RuntimeError("Arc transaction receipt was not found")
        return receipt

    async def get_usdc_balance(self, address: str, token_address: str = USDC_TOKEN_ADDRESS) -> float:
        if not self.enabled:
            return 1000.0
        clean = address.lower().removeprefix("0x")
        if len(clean) != 40:
            raise RuntimeError(f"Invalid EVM address: {address}")
        data = "0x70a08231" + clean.rjust(64, "0")
        result = await self._rpc(
            "eth_call",
            [
                {
                    "to": to_checksum_address(token_address),
                    "data": data,
                },
                "latest",
            ],
        )
        return int(str(result or "0x0"), 16) / 1_000_000

    async def transfer_usdc_from_key(
        self,
        *,
        private_key: str,
        to_address: str,
        amount_usdc: float,
        token_address: str = USDC_TOKEN_ADDRESS,
    ) -> dict[str, Any]:
        if amount_usdc <= 0:
            raise RuntimeError("Arc USDC transfer requires a positive amount")
        if not self.enabled:
            tx_hash = sha256_hex({"to": to_address, "amount": amount_usdc, "nonce": new_id("yield")})
            return {
                "txHash": tx_hash,
                "status": "simulated",
                "from": Account.from_key(private_key).address if Account is not None else "demo-reserve",
                "to": to_address,
                "amountUSDC": amount_usdc,
                "demo": True,
            }
        if Account is None or encode is None or keccak is None or to_hex is None or to_checksum_address is None:
            raise RuntimeError("eth-account, eth-abi, and eth-utils are required for live Arc transfers")

        sender = Account.from_key(private_key).address
        amount_units = int(round(float(amount_usdc) * 1_000_000))
        data = to_hex(
            keccak(text=ERC20_TRANSFER_SIGNATURE)[:4]
            + encode(["address", "uint256"], [to_checksum_address(to_address), amount_units])
        )
        nonce = await self._rpc("eth_getTransactionCount", [sender, "pending"])
        gas_price = await self._rpc("eth_gasPrice", [])
        tx = {
            "from": sender,
            "to": to_checksum_address(token_address),
            "value": "0x0",
            "data": data,
            "nonce": nonce,
            "chainId": hex(self.chain_id),
            "gasPrice": gas_price,
        }
        estimated_gas = await self._rpc("eth_estimateGas", [tx])
        signed = Account.sign_transaction(
            {
                "from": sender,
                "to": to_checksum_address(token_address),
                "value": 0,
                "data": data,
                "nonce": int(nonce, 16),
                "chainId": self.chain_id,
                "gasPrice": int(gas_price, 16),
                "gas": int(estimated_gas, 16),
            },
            private_key,
        )
        tx_hash = await self._rpc("eth_sendRawTransaction", [signed.raw_transaction.hex()])
        verification = await self.verify_usdc_transfer(
            tx_hash=tx_hash,
            from_address=sender,
            to_address=to_address,
            amount_usdc=amount_usdc,
            token_address=token_address,
        )
        return {
            "txHash": tx_hash,
            "status": "submitted",
            "from": sender,
            "to": to_address,
            "amountUSDC": amount_usdc,
            "verification": verification,
            "demo": False,
        }

    async def verify_usdc_transfer(
        self,
        *,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount_usdc: float,
        token_address: str = USDC_TOKEN_ADDRESS,
    ) -> dict[str, Any]:
        receipt = await self.get_transaction_receipt(tx_hash)
        if str(receipt.get("status", "")).lower() != "0x1":
            raise RuntimeError("Arc transaction did not succeed")

        expected_from = _topic_address(from_address)
        expected_to = _topic_address(to_address)
        token = token_address.lower()
        min_amount = int(round(float(amount_usdc) * 1_000_000))

        for log in receipt.get("logs", []) or []:
            topics = [str(topic).lower() for topic in log.get("topics", [])]
            if len(topics) < 3:
                continue
            if str(log.get("address", "")).lower() != token:
                continue
            if topics[0] != TRANSFER_TOPIC:
                continue
            if topics[1] != expected_from or topics[2] != expected_to:
                continue
            amount = int(str(log.get("data") or "0x0"), 16)
            if amount < min_amount:
                raise RuntimeError(
                    f"Arc USDC transfer amount is too small: expected at least {amount_usdc} USDC"
                )
            return {
                "txHash": tx_hash,
                "status": "verified",
                "token": token_address,
                "from": from_address,
                "to": to_address,
                "amount_usdc": amount / 1_000_000,
                "blockNumber": receipt.get("blockNumber"),
                "logIndex": log.get("logIndex"),
            }

        raise RuntimeError("Arc transaction does not contain the required USDC transfer")

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        if not self.rpc_url:
            raise RuntimeError("ARC RPC URL is not configured")
        import httpx

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


def _topic_address(address: str) -> str:
    clean = address.lower().removeprefix("0x")
    if len(clean) != 40:
        raise RuntimeError(f"Invalid EVM address: {address}")
    return "0x" + clean.rjust(64, "0")
