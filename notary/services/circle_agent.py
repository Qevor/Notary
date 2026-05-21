from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notary.models.schemas import new_id


@dataclass(slots=True)
class CircleAgentClient:
    api_key: str | None = None
    demo_mode: bool = True

    async def create_agent_wallet(self, owner_hint: str) -> dict[str, Any]:
        if self.demo_mode:
            wallet_id = new_id("circle_wallet")
            return {
                "walletId": wallet_id,
                "address": "0x" + wallet_id[-40:].rjust(40, "0"),
                "ownerHint": owner_hint,
                "demo": True,
            }
        raise NotImplementedError("Circle Agent Wallet creation is not wired yet")

    async def get_unified_balance(self, wallet_id: str) -> dict[str, Any]:
        return {"walletId": wallet_id, "asset": "USDC", "amount": "1000.00", "demo": True}

    async def prepare_gateway_route(self, wallet_id: str, amount_usdc: float) -> dict[str, Any]:
        return {
            "routeId": new_id("gateway_route"),
            "walletId": wallet_id,
            "asset": "USDC",
            "amount": amount_usdc,
            "destination": "arc",
            "demo": True,
        }

    async def pay_for_data(self, description: str, max_usdc: float) -> dict[str, Any]:
        return {
            "paymentId": new_id("x402"),
            "description": description,
            "amountUSDC": min(max_usdc, 0.01),
            "status": "paid",
            "demo": True,
        }

