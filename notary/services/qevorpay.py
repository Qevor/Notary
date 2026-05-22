from __future__ import annotations

import hashlib
import hmac
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
    payment_link_path: str | None = None
    batch_distribution_path: str | None = None
    release_escrow_path: str | None = None
    refund_path: str | None = None
    payment_status_path_template: str | None = None
    webhook_secret: str | None = None
    webhook_signature_header: str = "x-signature"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    executor_agent_wallet_id: str | None = None
    creator_wallet: str | None = None

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
        if not self.payment_link_path and self.supabase_url:
            rows = await self._supabase_insert(
                "payment_links",
                {
                    "receiver_wallet": request.recipient,
                    "amount": request.amount_usdc,
                    "expires_at": request.metadata.get("expires_at"),
                    "max_uses": request.metadata.get("max_uses"),
                    "group_id": request.metadata.get("group_id"),
                },
            )
            row = rows[0]
            return {
                "reference": row["id"],
                "url": f"/pay/{row['id']}",
                "status": "created",
                "provider": "qevor_supabase",
                "request": request.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.payment_link_path, "QEVORPAY_PAYMENT_LINK_PATH"),
            request.model_dump(mode="json"),
        )

    async def create_batch_distribution(self, request: QevorpayBatchDistributionRequest) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_batch"),
                "status": "queued",
                "request": request.model_dump(mode="json"),
            }
        if not self.batch_distribution_path and self.supabase_url:
            return await self._create_supabase_batch(request)
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
        if not self.release_escrow_path and self.supabase_url:
            recipient = trigger.recipient
            if not recipient:
                raise RuntimeError("Qevor release requires a recipient wallet/identity")
            amount = trigger.amount_usdc
            if not amount or amount <= 0:
                raise RuntimeError("Qevor release requires a positive amount_usdc")
            return await self.create_batch_distribution(
                QevorpayBatchDistributionRequest(
                    recipients=[
                        {
                            "wallet": recipient,
                            "amount": amount,
                            "label": "NOTARY release",
                        }
                    ],
                    reason=trigger.condition,
                    metadata=trigger.metadata | {"attestationId": trigger.attestation_id},
                )
            )
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
        if not self.refund_path and self.supabase_url:
            refund_recipient = trigger.metadata.get("payerIdentity")
            if not refund_recipient:
                raise RuntimeError("Qevor refund requires payerIdentity metadata")
            return await self.create_batch_distribution(
                QevorpayBatchDistributionRequest(
                    recipients=[
                        {
                            "wallet": refund_recipient,
                            "amount": trigger.amount_usdc or 0,
                            "label": "NOTARY refund",
                        }
                    ],
                    reason=trigger.condition,
                    metadata=trigger.metadata | {"attestationId": trigger.attestation_id},
                )
            )
        return await self._post(
            self._required_path(self.refund_path, "QEVORPAY_REFUND_PATH"),
            trigger.model_dump(mode="json"),
        )

    async def hold_payment(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("qevor_hold"),
                "status": "held",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.release_escrow_path, "QEVORPAY_RELEASE_ESCROW_PATH"),
            trigger.model_dump(mode="json"),
        )

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
        if trigger.action in {PaymentAction.RELEASE_ESCROW, PaymentAction.RELEASE_PARTIAL}:
            return await self.release_escrow(trigger)
        if trigger.action == PaymentAction.REFUND:
            return await self.refund_payment(trigger)
        if trigger.action == PaymentAction.HOLD:
            return await self.hold_payment(trigger)
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
        import httpx

        async with httpx.AsyncClient(base_url=self._base_url(), timeout=30) as client:
            response = await client.post(
                path,
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def _get(self, path: str) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(base_url=self._base_url(), timeout=30) as client:
            response = await client.get(path, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def _create_supabase_batch(self, request: QevorpayBatchDistributionRequest) -> dict[str, Any]:
        creator_wallet = (
            request.metadata.get("creator_wallet")
            or request.metadata.get("payerIdentity")
            or self.creator_wallet
        )
        if not creator_wallet:
            raise RuntimeError(
                "Qevor Supabase batch execution requires a creator wallet. "
                "Pass payer_identity as a wallet address or set QEVOR_CREATOR_WALLET."
            )
        recipients = [
            {
                "wallet": item.get("wallet") or item.get("recipient") or item.get("recipient_wallet"),
                "amount": float(item.get("amount") or item.get("amount_usdc") or 0),
                "label": item.get("label"),
            }
            for item in request.recipients
        ]
        recipients = [item for item in recipients if item["wallet"] and item["amount"] > 0]
        if not recipients:
            raise RuntimeError("Batch distribution requires at least one recipient")
        total = round(sum(item["amount"] for item in recipients), 6)
        batch_row: dict[str, Any] = {
            "creator_wallet": creator_wallet,
            "title": request.metadata.get("title", "NOTARY verdict release"),
            "description": request.reason,
            "recipients": recipients,
            "total_amount": total,
            "status": "pending",
            "executor_agent_wallet_id": (
                request.metadata.get("executor_agent_wallet_id")
                or self.executor_agent_wallet_id
            ),
            "executor_state": (
                "pending_evaluation"
                if request.metadata.get("executor_agent_wallet_id")
                or self.executor_agent_wallet_id
                else "manual"
            ),
        }
        envelope = request.metadata.get("attestation") or {}
        # 14 columns from supabase/migrations/03_notary_attestation.sql. Qevor's
        # batch executor (notary-attestation.ts) reads these to recover the
        # EIP-712 signer, look up the on-chain AttestationRegistry record, and
        # gate the payment fail-closed before any USDC moves.
        for column in (
            "attestation_id",
            "notary_id",
            "obligation_id",
            "verdict_hash",
            "evidence_hash",
            "reasoning_trace_hash",
            "confidence_bps",
            "verdict_signature",
            "attestation_contract",
            "attestation_chain_id",
            "notary_identity_registry",
            "attestation_domain_name",
            "attestation_domain_version",
            "attestation_created_at",
        ):
            value = envelope.get(column)
            if value is not None:
                batch_row[column] = value
        batch_rows = await self._supabase_insert("batch_requests", batch_row)
        batch = batch_rows[0]
        payment_rows = [
            {
                "batch_request_id": batch["id"],
                "payer_wallet": creator_wallet,
                "recipient_wallet": item["wallet"],
                "amount": item["amount"],
                "tx_hash": "pending_executor",
                "status": "pending",
            }
            for item in recipients
        ]
        await self._supabase_insert("batch_payments", payment_rows)
        return {
            "reference": batch["id"],
            "status": "queued",
            "provider": "qevor_supabase",
            "request": request.model_dump(mode="json"),
            "batchRequest": batch,
        }

    async def _supabase_insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        import httpx

        if not self.supabase_url or not self.supabase_service_role_key:
            raise RuntimeError(
                "QEVOR_SUPABASE_URL and QEVOR_SUPABASE_SERVICE_ROLE_KEY are required "
                "for Qevor Supabase integration"
            )
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "apikey": self.supabase_service_role_key,
                    "Authorization": f"Bearer {self.supabase_service_role_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
            )
            response.raise_for_status()
            body = response.json()
        return body if isinstance(body, list) else [body]

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
