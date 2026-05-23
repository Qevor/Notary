from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any

from notary.models.schemas import (
    PaymentAction,
    PaymentTrigger,
    EscrowBatchDistributionRequest,
    EscrowConditionalReserveRequest,
    EscrowPaymentLinkRequest,
    new_id,
)


@dataclass(slots=True)
class NotaryEscrowClient:
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
    store: Any = None
    allow_local_fallback: bool = False

    async def resolve_identity_to_wallet(self, identity: str | None) -> dict[str, Any]:
        if not identity:
            return {"identity": identity, "wallet": identity, "username": None, "resolved": False}
        value = identity.strip()
        if self._is_evm_address(value):
            return {"identity": identity, "wallet": value, "username": None, "resolved": True}
        username = value.removeprefix("@").strip().lower()
        if not username:
            return {"identity": identity, "wallet": identity, "username": None, "resolved": False}

        # Check local SQLite store first (works without Supabase)
        if self.store is not None:
            local = self.store.get("profiles", username)
            if local and local.get("wallet"):
                return {
                    "identity": identity,
                    "wallet": local["wallet"],
                    "username": username,
                    "resolved": True,
                }

        # Fallback: check Supabase
        rows = await self._supabase_select(
            "profiles",
            select="wallet,username",
            filters={"username": f"eq.{username}"},
            limit=1,
        )
        if not rows:
            raise RuntimeError(f"NOTARY identity @{username} is not registered")
        wallet = rows[0].get("wallet")
        if not wallet:
            raise RuntimeError(f"NOTARY identity @{username} has no wallet")
        return {"identity": identity, "wallet": wallet, "username": username, "resolved": True}

    async def resolve_executor_agent_wallet(self, profile_wallet: str | None) -> dict[str, Any] | None:
        if not profile_wallet:
            return None
        if self.store is not None:
            local_rows = [
                row
                for row in self.store.list("agent_wallets")
                if str(row.get("profile_wallet", "")).lower() == profile_wallet.lower()
                and row.get("chain") == "ARC-TESTNET"
                and row.get("status") == "active"
            ]
            if local_rows:
                escrow_rows = [row for row in local_rows if row.get("executor_mode") == "escrow"]
                with_escrow = [row for row in escrow_rows if row.get("escrow_address")]
                return (with_escrow or escrow_rows or local_rows)[0]

        rows = await self._supabase_select(
            "agent_wallets",
            select="id,profile_wallet,wallet_address,chain,status,executor_mode,escrow_address,attestation_mode,label",
            filters={
                "profile_wallet": f"eq.{profile_wallet}",
                "chain": "eq.ARC-TESTNET",
                "status": "eq.active",
            },
            limit=10,
        )
        if not rows:
            return None
        escrow_rows = [row for row in rows if row.get("executor_mode") == "escrow"]
        with_escrow = [row for row in escrow_rows if row.get("escrow_address")]
        return (with_escrow or escrow_rows or rows)[0]

    async def create_payment_link(self, request: EscrowPaymentLinkRequest) -> dict[str, Any]:
        if self.demo_mode:
            ref = new_id("notary_link")
            return {
                "reference": ref,
                "url": f"/pay/{ref}",
                "status": "created",
                "provider": "notary_local",
                "request": request.model_dump(mode="json"),
            }
        if not self.payment_link_path and self.supabase_url:
            recipient = request.recipient or self.creator_wallet
            if not recipient:
                raise ValueError("recipient wallet is required but not provided (and creator_wallet is not set)")
            rows = await self._supabase_insert(
                "payment_links",
                {
                    "receiver_wallet": recipient,
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
                "provider": "notary_supabase",
                "request": request.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.payment_link_path, "NOTARY_ESCROW_PAYMENT_LINK_PATH"),
            request.model_dump(mode="json"),
        )

    async def create_conditional_reserve(self, request: EscrowConditionalReserveRequest) -> dict[str, Any]:
        if self.demo_mode:
            return self._local_conditional_reserve(request)
        if self.supabase_url:
            try:
                return await self._create_supabase_reserve(request)
            except Exception as exc:
                if self.allow_local_fallback:
                    return self._local_conditional_reserve(request, fallback_reason=str(exc))
                raise
        if not self.batch_distribution_path and self.allow_local_fallback:
            return self._local_conditional_reserve(request)
        return await self._post(
            self._required_path(self.batch_distribution_path, "NOTARY_ESCROW_BATCH_PATH"),
            request.model_dump(mode="json"),
        )

    async def create_batch_distribution(self, request: EscrowBatchDistributionRequest) -> dict[str, Any]:
        if self.demo_mode:
            return self._local_batch_distribution(request)
        if not self.batch_distribution_path and self.supabase_url:
            try:
                return await self._create_supabase_batch(request)
            except Exception as exc:
                if self.allow_local_fallback:
                    return self._local_batch_distribution(request, fallback_reason=str(exc))
                raise
        if not self.batch_distribution_path and self.allow_local_fallback:
            return self._local_batch_distribution(request)
        return await self._post(
            self._required_path(self.batch_distribution_path, "NOTARY_ESCROW_BATCH_PATH"),
            request.model_dump(mode="json"),
        )

    async def release_escrow(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("notary_release"),
                "status": "released",
                "trigger": trigger.model_dump(mode="json"),
            }
        if not self.release_escrow_path and self.supabase_url:
            recipient = trigger.recipient
            if not recipient:
                raise RuntimeError("NOTARY escrow release requires a recipient wallet/identity")
            amount = trigger.amount_usdc
            if not amount or amount <= 0:
                raise RuntimeError("NOTARY escrow release requires a positive amount_usdc")
            return await self.create_batch_distribution(
                EscrowBatchDistributionRequest(
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
            self._required_path(self.release_escrow_path, "NOTARY_ESCROW_RELEASE_PATH"),
            trigger.model_dump(mode="json"),
        )

    async def refund_payment(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("notary_refund"),
                "status": "refunded",
                "trigger": trigger.model_dump(mode="json"),
            }
        if not self.refund_path and self.supabase_url:
            refund_recipient = trigger.metadata.get("payerIdentity")
            if not refund_recipient:
                raise RuntimeError("NOTARY escrow refund requires payerIdentity metadata")
            return await self.create_batch_distribution(
                EscrowBatchDistributionRequest(
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
            self._required_path(self.refund_path, "NOTARY_ESCROW_REFUND_PATH"),
            trigger.model_dump(mode="json"),
        )

    async def hold_payment(self, trigger: PaymentTrigger) -> dict[str, Any]:
        if self.demo_mode:
            return {
                "reference": new_id("notary_hold"),
                "status": "held",
                "trigger": trigger.model_dump(mode="json"),
            }
        if not self.release_escrow_path and self.allow_local_fallback:
            return {
                "reference": new_id("notary_hold"),
                "status": "held",
                "provider": "notary_local_fallback",
                "trigger": trigger.model_dump(mode="json"),
            }
        return await self._post(
            self._required_path(self.release_escrow_path, "NOTARY_ESCROW_RELEASE_PATH"),
            trigger.model_dump(mode="json"),
        )

    async def get_payment_status(self, reference: str) -> dict[str, Any]:
        if self.demo_mode:
            return {"reference": reference, "status": "created", "demo": True}
        template = self._required_path(self.payment_status_path_template, "NOTARY_ESCROW_STATUS_PATH_TEMPLATE")
        return await self._get(template.format(reference=reference))

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        if self.demo_mode:
            return True
        if not self.webhook_secret:
            raise RuntimeError("NOTARY_ESCROW_WEBHOOK_SECRET is required to verify live NOTARY escrow webhooks")
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
                EscrowPaymentLinkRequest(
                    amount_usdc=trigger.amount_usdc or 1,
                    description=trigger.condition,
                    recipient=trigger.recipient,
                    metadata=trigger.metadata,
                )
            )
        raise RuntimeError(f"Unsupported NOTARY escrow action in live mode: {trigger.action}")

    def _local_conditional_reserve(
        self,
        request: EscrowConditionalReserveRequest,
        *,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        ref = new_id("notary_reserve")
        result = {
            "reference": ref,
            "url": f"/request/{ref}",
            "status": "pending_reserve",
            "provider": "notary_local_fallback" if fallback_reason else "notary_local",
            "request": request.model_dump(mode="json"),
        }
        if fallback_reason:
            result["fallbackReason"] = "remote escrow provider unavailable; using local development checkout"
        return result

    def _local_batch_distribution(
        self,
        request: EscrowBatchDistributionRequest,
        *,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        result = {
            "reference": new_id("notary_batch"),
            "status": "queued",
            "provider": "notary_local_fallback" if fallback_reason else "notary_local",
            "request": request.model_dump(mode="json"),
        }
        if fallback_reason:
            result["fallbackReason"] = "remote escrow provider unavailable; using local development receipt"
        return result

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

    async def _create_supabase_batch(self, request: EscrowBatchDistributionRequest) -> dict[str, Any]:
        creator_identity = (
            request.metadata.get("creator_wallet")
            or request.metadata.get("payerIdentity")
            or self.creator_wallet
        )
        creator = await self.resolve_identity_to_wallet(creator_identity)
        creator_wallet = creator.get("wallet")
        if not creator_wallet:
            raise RuntimeError(
                "NOTARY escrow batch execution requires a creator wallet. "
                "Pass payer_identity as a wallet address or set NOTARY_CREATOR_WALLET."
            )
        resolved_recipients = []
        for item in request.recipients:
            recipient_identity = item.get("wallet") or item.get("recipient") or item.get("recipient_wallet")
            recipient = await self.resolve_identity_to_wallet(recipient_identity)
            resolved_recipients.append(
                {
                    "wallet": recipient.get("wallet"),
                    "amount": float(item.get("amount") or item.get("amount_usdc") or 0),
                    "label": item.get("label") or recipient.get("username") or recipient_identity,
                    "username": recipient.get("username"),
                    "identity": recipient_identity,
                }
            )
        recipients = resolved_recipients
        recipients = [item for item in recipients if item["wallet"] and item["amount"] > 0]
        if not recipients:
            raise RuntimeError("Batch distribution requires at least one recipient")
        executor_agent_wallet_id = request.metadata.get("executor_agent_wallet_id") or self.executor_agent_wallet_id
        if not executor_agent_wallet_id:
            executor_wallet = await self.resolve_executor_agent_wallet(creator_wallet)
            if executor_wallet:
                executor_agent_wallet_id = executor_wallet.get("id")
        total = round(sum(item["amount"] for item in recipients), 6)
        batch_row: dict[str, Any] = {
            "creator_wallet": creator_wallet,
            "title": request.metadata.get("title", "NOTARY verdict release"),
            "description": request.reason,
            "recipients": recipients,
            "total_amount": total,
            "status": "pending",
            "executor_agent_wallet_id": executor_agent_wallet_id,
            "executor_state": (
                "pending_evaluation"
                if executor_agent_wallet_id
                else "manual"
            ),
        }
        envelope = request.metadata.get("attestation") or {}
        # 14 columns from supabase/migrations/03_notary_attestation.sql. NOTARY's
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
            "provider": "notary_supabase",
            "request": request.model_dump(mode="json"),
            "batchRequest": batch,
        }

    async def _create_supabase_reserve(self, request: EscrowConditionalReserveRequest) -> dict[str, Any]:
        batch_row: dict[str, Any] = {
            "creator_wallet": request.payer_wallet,
            "title": "NOTARY conditional reserve",
            "description": request.instruction,
            "recipients": [
                {
                    "wallet": request.payee_wallet,
                    "amount": request.amount_usdc,
                    "label": request.payee_identity,
                }
            ],
            "total_amount": request.amount_usdc,
            "status": "pending",
            "executor_agent_wallet_id": request.executor_agent_wallet_id,
            "executor_state": "pending_reserve",
            "notary_case_id": request.notary_case_id,
            "reserve_wallet": request.reserve_wallet,
            "reserve_source_wallet": request.payer_wallet,
            "reserve_amount_usdc": request.amount_usdc,
        }
        batch_rows = await self._supabase_insert("batch_requests", batch_row)
        batch = batch_rows[0]
        payment_rows = await self._supabase_insert(
            "batch_payments",
            [
                {
                    "batch_request_id": batch["id"],
                    "payer_wallet": request.payer_wallet,
                    "recipient_wallet": request.reserve_wallet,
                    "amount": request.amount_usdc,
                    "tx_hash": "pending_reserve",
                    "status": "pending_reserve",
                }
            ],
        )
        return {
            "reference": batch["id"],
            "url": f"/request/{batch['id']}",
            "status": "pending_reserve",
            "provider": "notary_supabase_reserve",
            "request": request.model_dump(mode="json"),
            "batchRequest": batch,
            "batchPayment": payment_rows[0],
        }

    async def _supabase_insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        import httpx

        if not self.supabase_url or not self.supabase_service_role_key:
            raise RuntimeError(
                "NOTARY_SUPABASE_URL and NOTARY_SUPABASE_SERVICE_ROLE_KEY are required "
                "for NOTARY Supabase integration"
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

    async def _supabase_select(
        self,
        table: str,
        *,
        select: str,
        filters: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        import httpx

        if not self.supabase_url or not self.supabase_service_role_key:
            raise RuntimeError(
                "NOTARY_SUPABASE_URL and NOTARY_SUPABASE_SERVICE_ROLE_KEY are required "
                "to resolve NOTARY identities"
            )
        params: dict[str, str | int] = {"select": select}
        if filters:
            params.update(filters)
        if limit:
            params["limit"] = limit
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                params=params,
                headers={
                    "apikey": self.supabase_service_role_key,
                    "Authorization": f"Bearer {self.supabase_service_role_key}",
                },
            )
            response.raise_for_status()
            body = response.json()
        return body if isinstance(body, list) else [body]

    async def _supabase_update(
        self,
        table: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        import httpx

        if not self.supabase_url or not self.supabase_service_role_key:
            raise RuntimeError(
                "NOTARY_SUPABASE_URL and NOTARY_SUPABASE_SERVICE_ROLE_KEY are required "
                "for NOTARY Supabase integration"
            )
        params = {}
        params.update(filters)
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                url,
                json=payload,
                params=params,
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

    def _is_evm_address(self, value: str) -> bool:
        return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value))

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("NOTARY_ESCROW_API_KEY is required in live mode")
        return {"Authorization": f"Bearer {self.api_key}"}

    def _base_url(self) -> str:
        if not self.api_base_url:
            raise RuntimeError("NOTARY_ESCROW_API_BASE_URL is required in live mode")
        return self.api_base_url

    def _required_path(self, value: str | None, env_name: str) -> str:
        if not value:
            raise RuntimeError(f"{env_name} is required in live mode because NOTARY escrow endpoint paths are provider-specific")
        return value
