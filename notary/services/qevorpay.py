from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

import httpx

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
    payment_link_path: str | None = None
    batch_distribution_path: str | None = None
    release_escrow_path: str | None = None
    refund_path: str | None = None
    payment_status_path_template: str | None = None
    webhook_secret: str | None = None
    webhook_signature_header: str = "x-signature"

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
        return await self._post(self._required_path(self.payment_link_path, "QEVORPAY_PAYMENT_LINK_PATH"), request.model_dump(mode="json"))

    async def create_batch_distribution(self, request: QevorpayBatchDistributionRequest) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_batch"),
                "status": "queued",
                "request": request.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.batch_distribution_path, "QEVORPAY_BATCH_DISTRIBUTION_PATH"),
            request.model_dump(mode="json"),
        )

    async def release_escrow(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_release"),
                "status": "released",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.release_escrow_path, "QEVORPAY_RELEASE_ESCROW_PATH"),
            trigger.model_dump(mode="json"),
        )

    async def refund_payment(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_refund"),
                "status": "refunded",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post(self._required_path(self.refund_path, "QEVORPAY_REFUND_PATH"), trigger.model_dump(mode="json"))

    async def get_payment_status(self, reference: str) -> dict[str, Any]:
        if self.demo_mode:
            return {"reference": reference, "status": "created", "demo": True}
        template = self._required_path(self.payment_status_path_template, "QEVORPAY_PAYMENT_STATUS_PATH_TEMPLATE")
        return await self._get(template.format(reference=reference))

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        if self.demo_mode:
            return True
        if not self.webhook_secret:
            raise RuntimeError("QEVORPAY_WEBHOOK_SECRET is required to verify live Qevorpay webhooks")
        signature = headers.get(self.webhook_signature_header) or headers.get(self.webhook_signature_header.title())
        if not signature:
            return False
        expected = hmac.new(self.webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

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
        raise RuntimeError(f"Unsupported Qevorpay action in live mode: {trigger.action}")

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=30) as client:
            response = await client.post(
                path,
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def _get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=30) as client:
            response = await client.get(path, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("QEVORPAY_API_KEY is required in live mode")
        return {"Authorization": f"Bearer {self.api_key}"}

    def _base_url(self) -> str:
        if not self.api_base_url:
            raise RuntimeError("QEVORPAY_API_BASE_URL is required in live mode")
        return self.api_base_url

    def _required_path(self, value: str | None, env_name: str) -> str:
        if not value:
            raise RuntimeError(f"{env_name} is required in live mode because Qevorpay endpoint contracts are provider-specific")
        return value
