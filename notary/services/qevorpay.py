from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notary.models.schemas import (
    PaymentAction,
    PaymentTrigger,
    QevorpayBatchDistributionRequest,
    QevorpayPaymentLinkRequest,
    new_id,
)


@dataclass(slots=True)
class QevorpayClient:
    api_base_url: str | None = None
    api_key: str | None = None
    demo_mode: bool = True

    async def create_payment_link(self, request: QevorpayPaymentLinkRequest) -> dict[str, Any]:
        if self.demo_mode:
            ref = new_id("qevor_link")
            return {
                "reference": ref,
                "url": f"/pay/{ref}",
                "status": "created",
                "provider": "local_qevorpay",
                "request": request.model_dump(mode="json"),
            }
        return await self._post("/payment-links", request.model_dump(mode="json"))

    async def create_batch_distribution(
        self, request: QevorpayBatchDistributionRequest
    ) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_batch"),
                "status": "queued",
                "request": request.model_dump(mode="json"),
            }
        return await self._post("/batch-distributions", request.model_dump(mode="json"))

    async def release_escrow(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_release"),
                "status": "released",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post("/escrow/release", trigger.model_dump(mode="json"))

    async def refund_payment(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_refund"),
                "status": "refunded",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post("/refunds", trigger.model_dump(mode="json"))

    async def execute_trigger(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if trigger.action == PaymentAction.RELEASE_ESCROW:
            return await self.release_escrow(trigger)
        if trigger.action == PaymentAction.REFUND:
            return await self.refund_payment(trigger)
        if trigger.action == PaymentAction.CREATE_LINK:
            return await self.create_payment_link(
                QevorpayPaymentLinkRequest(
                    amount_usdc=trigger.amount_usdc or 1,
                    description=trigger.condition,
                    recipient=trigger.recipient,
                    metadata=trigger.metadata,
                )
            )
        return {"reference": new_id("qevor_action"), "status": "mocked", "action": trigger.action}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_base_url or not self.api_key:
            raise RuntimeError("Qevorpay credentials are not configured")
        import httpx

        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=30) as client:
            response = await client.post(
                path,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()
