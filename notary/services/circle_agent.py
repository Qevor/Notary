from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from dataclasses import dataclass
from typing import Any

from notary.models.schemas import new_id


def _first_mapping_with_keys(payload: Any, keys: set[str]) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        if keys.issubset(payload.keys()):
            return payload
        for value in payload.values():
            found = _first_mapping_with_keys(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _first_mapping_with_keys(item, keys)
            if found:
                return found
    return None


def _all_mappings_with_key(payload: Any, key: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        if key in payload:
            matches.append(payload)
        for value in payload.values():
            matches.extend(_all_mappings_with_key(value, key))
    elif isinstance(payload, list):
        for item in payload:
            matches.extend(_all_mappings_with_key(item, key))
    return matches


@dataclass(slots=True)
class CircleAgentClient:
    api_key: str | None = None
    demo_mode: bool = True
    cli_path: str = "circle"
    wallet_email: str | None = None
    chain: str = "ARC-TESTNET"
    testnet: bool = True
    rpc_url: str | None = None

    async def login_init(self, email: str | None = None) -> dict[str, Any]:
        if self.demo_mode:
            return {"requestId": new_id("circle_login"), "email": email or self.wallet_email, "demo": True}
        login_email = email or self.wallet_email
        if not login_email:
            raise RuntimeError("CIRCLE_WALLET_EMAIL is required for Circle CLI OTP login")
        return await self._run("wallet", "login", login_email, "--init")

    async def login_complete(self, request_id: str, otp: str) -> dict[str, Any]:
        if self.demo_mode:
            return {"requestId": request_id, "status": "authenticated", "demo": True}
        return await self._run("wallet", "login", "--request", request_id, "--otp", otp)

    async def wallet_status(self) -> dict[str, Any]:
        if self.demo_mode:
            return {"authenticated": False, "demo": True}
        return await self._run("wallet", "status", "--type", "agent")

    async def create_agent_wallet(self, owner_hint: str) -> dict[str, Any]:
        if self.demo_mode:
            wallet_id = new_id("circle_wallet")
            return {
                "walletId": wallet_id,
                "address": "0x" + wallet_id[-40:].rjust(40, "0"),
                "ownerHint": owner_hint,
                "demo": True,
            }

        await self._ensure_authenticated()
        before = await self._list_agent_wallets()
        before_addresses = {str(wallet["address"]).lower() for wallet in before}
        idempotency_key = "notary-" + hashlib.sha256(owner_hint.encode("utf-8")).hexdigest()[:32]
        create_result = await self._run(
            "wallet",
            "create",
            "--type",
            "agent",
            "--idempotency-key",
            idempotency_key,
        )
        created = await self._list_agent_wallets()
        if not created:
            raise RuntimeError("Circle CLI did not return an agent wallet after creation")
        new_wallets = [
            wallet
            for wallet in created
            if str(wallet["address"]).lower() not in before_addresses
        ]
        if new_wallets:
            wallet = new_wallets[0]
        else:
            created_from_response = self._normalize_wallets(create_result)
            wallet = created_from_response[0] if created_from_response else created[-1]
        return wallet | {
            "ownerHint": owner_hint,
            "idempotencyKey": idempotency_key,
            "demo": False,
        }

    async def get_unified_balance(self, wallet_id: str) -> dict[str, Any]:
        # Try to resolve or deduce the address first
        address = None
        try:
            address = await self._resolve_address(wallet_id)
        except Exception:
            if wallet_id and wallet_id.startswith("0x"):
                address = wallet_id

        # Query blockchain balance via RPC if configured
        if address and self.rpc_url:
            try:
                import httpx
                # Query USDC balance via standard JSON-RPC eth_call (balanceOf selector = 0x70a08231)
                addr_clean = address[2:].lower()
                data = "0x70a08231" + addr_clean.rjust(64, "0")
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.post(
                        self.rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "eth_call",
                            "params": [
                                {
                                    "to": "0x3600000000000000000000000000000000000000",
                                    "data": data
                                },
                                "latest"
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        res_json = resp.json()
                        if "result" in res_json and res_json["result"] != "0x":
                            val_hex = res_json["result"]
                            val_dec = int(val_hex, 16)
                            balance_usdc = f"{val_dec / 1_000_000:.2f}"
                            return {
                                "walletId": wallet_id,
                                "address": address,
                                "amount": balance_usdc,
                                "walletBalance": {"amount": balance_usdc},
                                "demo": False,
                            }
            except Exception as e:
                print(f"[CircleAgentClient] Direct blockchain balance query failed: {e}")

        if self.demo_mode:
            return {"walletId": wallet_id, "asset": "USDC", "amount": "1000.00", "demo": True}

        # Live mode CLI execution
        try:
            address = address or await self._resolve_address(wallet_id)
            wallet_balance = await self._run("wallet", "balance", "--address", address, "--chain", self.chain)
            gateway_balance = await self._run("gateway", "balance", "--address", address, "--chain", self.chain)
            return {
                "walletId": wallet_id,
                "address": address,
                "walletBalance": wallet_balance,
                "gatewayBalance": gateway_balance,
                "demo": False,
            }
        except Exception as e:
            # Fallback when Circle CLI is not installed or fails
            print(f"[CircleAgentClient] Circle CLI balance command failed: {e}")
            return {
                "walletId": wallet_id,
                "address": address or "",
                "amount": "0.00",
                "walletBalance": {"amount": "0.00"},
                "demo": False,
            }

    async def prepare_gateway_route(self, wallet_id: str, amount_usdc: float) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "routeId": new_id("gateway_route"),
                "walletId": wallet_id,
                "asset": "USDC",
                "amount": amount_usdc,
                "destination": "arc",
                "demo": True,
            }
        address = await self._resolve_address(wallet_id)
        result = await self._run(
            "gateway",
            "deposit",
            "--amount",
            str(amount_usdc),
            "--address",
            address,
            "--chain",
            self.chain,
            "--method",
            "direct",
        )
        return {"walletId": wallet_id, "address": address, "amount": amount_usdc, "gateway": result, "demo": False}

    async def pay_for_data(self, description: str, max_usdc: float, service_url: str | None = None, wallet_id: str | None = None) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "paymentId": new_id("x402"),
                "description": description,
                "amountUSDC": min(max_usdc, 0.01),
                "status": "paid",
                "demo": True,
            }
        if not service_url:
            raise RuntimeError("A Circle x402 service URL is required to pay for data in live mode")
        address = await self._resolve_address(wallet_id) if wallet_id else await self._default_agent_address()
        result = await self._run(
            "services",
            "pay",
            service_url,
            "--address",
            address,
            "--chain",
            self.chain,
            "--max-amount",
            str(max_usdc),
        )
        return {
            "paymentId": result.get("paymentId") or result.get("id") or new_id("x402"),
            "description": description,
            "serviceUrl": service_url,
            "address": address,
            "raw": result,
            "demo": False,
        }

    async def search_services(self, query: str) -> dict[str, Any]:
        if self.demo_mode:
            return {"query": query, "services": [], "demo": True}
        return await self._run("services", "search", query)

    async def inspect_service(self, service_url: str) -> dict[str, Any]:
        if self.demo_mode:
            return {"serviceUrl": service_url, "demo": True}
        return await self._run("services", "inspect", service_url)

    async def _ensure_authenticated(self) -> None:
        status = await self.wallet_status()
        status_text = json.dumps(status).lower()
        if not any(
            marker in status_text
            for marker in (
                "authenticated",
                "active",
                '"tokenstatus": "valid"',
                '"tokenstatus":"valid"',
            )
        ):
            raise RuntimeError(
                "Circle CLI is not authenticated. Run login_init/login_complete or `circle wallet login` first."
            )

    async def _list_agent_wallets(self) -> list[dict[str, Any]]:
        payload = await self._run("wallet", "list", "--chain", self.chain, "--type", "agent")
        return self._normalize_wallets(payload)

    def _normalize_wallets(self, payload: Any) -> list[dict[str, Any]]:
        wallets = _all_mappings_with_key(payload, "address")
        normalized: list[dict[str, Any]] = []
        for wallet in wallets:
            address = wallet.get("address")
            if isinstance(address, str) and address.startswith("0x"):
                normalized.append(
                    {
                        "walletId": str(wallet.get("walletId") or wallet.get("id") or wallet.get("address")),
                        "address": address,
                        "raw": wallet,
                    }
                )
        return normalized

    async def _default_agent_address(self) -> str:
        wallets = await self._list_agent_wallets()
        if not wallets:
            raise RuntimeError("No Circle agent wallet is available for the configured account and chain")
        return str(wallets[0]["address"])

    async def transfer_usdc(
        self,
        *,
        from_wallet_id: str | None = None,
        to_address: str,
        amount: float,
    ) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "txHash": "0x" + sha256_hex(new_id("tx"))[-64:],
                "from": from_wallet_id or "demo-sender",
                "to": to_address,
                "amount": amount,
                "status": "success",
                "demo": True,
            }
        from_address = await self._resolve_address(from_wallet_id)
        result = await self._run(
            "wallet",
            "transfer",
            "--from",
            from_address,
            "--to",
            to_address,
            "--amount",
            str(amount),
            "--chain",
            self.chain,
        )
        return {
            "txHash": result.get("txHash") or result.get("id") or "executed",
            "from": from_address,
            "to": to_address,
            "amount": amount,
            "status": "success",
            "raw": result,
            "demo": False,
        }

    async def _resolve_address(self, wallet_id: str | None) -> str:
        if not wallet_id:
            return await self._default_agent_address()
        if wallet_id.startswith("0x"):
            return wallet_id
        wallets = await self._list_agent_wallets()
        for wallet in wallets:
            if wallet["walletId"] == wallet_id:
                return str(wallet["address"])
        raise RuntimeError(f"Could not resolve Circle wallet address for {wallet_id}")

    async def _run(self, *args: str) -> dict[str, Any]:
        if not shutil.which(self.cli_path):
            raise RuntimeError(
                f"Circle CLI not found at `{self.cli_path}`. Install with `npm install -g @circle-fin/cli`."
            )

        command = [self.cli_path, *args, "--output", "json"]
        if self.testnet and "--testnet" not in command and self._supports_testnet(args):
            command.append("--testnet")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="ignore").strip() or stdout.decode("utf-8", errors="ignore").strip())

        text = stdout.decode("utf-8", errors="ignore").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    def _supports_testnet(self, args: tuple[str, ...]) -> bool:
        joined = " ".join(args)
        return any(
            joined.startswith(prefix)
            for prefix in (
                "wallet login",
                "wallet create",
                "wallet list",
                "wallet balance",
                "wallet fund",
                "wallet transfer",
                "services pay",
                "services search",
                "services inspect",
                "gateway balance",
                "gateway deposit",
                "gateway withdraw",
            )
        )
