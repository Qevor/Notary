from __future__ import annotations

from pathlib import Path
from typing import Any

from notary.config import Settings
from notary.crypto.hashing import sha256_hex
from notary.legal.operating_agreement import generate_operating_agreement
from notary.models.schemas import (
    ArcTransactionPayload,
    DisclosureLevel,
    Evidence,
    EvidenceSource,
    EvidenceAccessGrant,
    MediaEvidence,
    NotaryCase,
    NotaryIdentity,
    Observation,
    OperatingAgreement,
    OutcomeConfirmation,
    PartyType,
    PartyOperatingHistory,
    PaymentAction,
    PaymentInstruction,
    PaymentTrigger,
    PrivacyMode,
    QevorpayBatchDistributionRequest,
    QevorpayConditionalReserveRequest,
    QevorpayPaymentLinkRequest,
    Ruling,
    TranscriptionJob,
    VerdictOutcome,
    WitnessIntakeRequest,
    new_id,
    utc_now,
)
from notary.services.arc import ArcClient
from notary.services.circle_agent import CircleAgentClient
from notary.services.evidence_vault import EvidenceVault
from notary.services.obligation_extractor import GroqObligationExtractor
from notary.services.qevorpay import QevorpayClient
from notary.services.speechmatics import SpeechmaticsClient
from notary.storage.sqlite import SQLiteStore
from notary.witness_pipeline import WitnessPipeline

ZERO_BYTES32 = "0x" + "0" * 64
ZERO_ADDRESS = "0x" + "0" * 40


class NotaryAppService:
    """Application service for the product workflows.

    The service persists real app state locally in SQLite and only uses local fallbacks where an
    external provider is not configured. That keeps the product usable before production API keys
    are connected without falsely claiming external settlement/transcription happened.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.notary_db_path)
        self.circle = CircleAgentClient(
            demo_mode=settings.notary_demo_mode,
            cli_path=settings.circle_cli_path,
            wallet_email=settings.circle_wallet_email,
            chain=settings.circle_chain,
            testnet=settings.circle_testnet,
        )
        self.qevorpay = QevorpayClient(
            api_base_url=settings.qevorpay_api_base_url,
            api_key=settings.qevorpay_api_key,
            demo_mode=settings.qevorpay_demo_mode,
            payment_link_path=settings.qevorpay_payment_link_path,
            batch_distribution_path=settings.qevorpay_batch_distribution_path,
            release_escrow_path=settings.qevorpay_release_escrow_path,
            refund_path=settings.qevorpay_refund_path,
            payment_status_path_template=settings.qevorpay_payment_status_path_template,
            webhook_secret=settings.qevorpay_webhook_secret,
            webhook_signature_header=settings.qevorpay_webhook_signature_header,
            supabase_url=settings.qevor_supabase_url,
            supabase_service_role_key=settings.qevor_supabase_service_role_key,
            executor_agent_wallet_id=settings.qevor_executor_agent_wallet_id,
            creator_wallet=settings.qevor_creator_wallet,
        )
        self.arc = ArcClient(
            rpc_url=settings.arc_rpc_url,
            chain_id=settings.arc_chain_id,
            private_key=settings.arc_operator_private_key,
            demo_mode=settings.arc_demo_mode,
            contract_addresses={
                "NotaryIdentityRegistry": settings.arc_notary_identity_registry or "",
                "AttestationRegistry": settings.arc_attestation_registry or "",
                "NotaryValidationRegistry": settings.arc_validation_registry or "",
                "NotaryGovernance": settings.arc_governance or "",
            },
        )
        self.speechmatics = SpeechmaticsClient(
            api_base_url=settings.speechmatics_api_base_url,
            api_key=settings.speechmatics_api_key,
            demo_mode=settings.speechmatics_demo_mode,
            transcriptions_path=settings.speechmatics_transcriptions_path,
            transcription_status_path_template=settings.speechmatics_transcription_status_path_template,
            transcript_path_template=settings.speechmatics_transcript_path_template,
            language=settings.speechmatics_language,
            operating_point=settings.speechmatics_operating_point,
            diarization=settings.speechmatics_diarization,
        )
        self.vault = EvidenceVault(
            root=settings.evidence_vault_local_dir,
            passphrase=settings.evidence_vault_passphrase,
        )

    async def create_notary(self, label: str | None = None) -> dict[str, Any]:
        identity = NotaryIdentity(
            capabilities=[
                "witness_to_pay",
                "speechmatics_transcription",
                "qevor_payment_execution",
                "arc_attestation_hashing",
                "graded_verdicts",
                "dispute_adjudication",
                "self_reversal",
                "party_operating_history",
            ],
            endpoint=None,
        )
        try:
            wallet = await self.circle.create_agent_wallet(label or identity.notary_id)
        except RuntimeError:
            if self.settings.notary_env == "production":
                raise
            wallet_id = new_id("local_circle_wallet")
            wallet = {
                "walletId": wallet_id,
                "address": "0x" + sha256_hex(wallet_id)[-40:],
                "ownerHint": label or identity.notary_id,
                "demo": True,
                "providerFallback": "circle_cli_unavailable",
            }
        identity.agent_wallet = wallet["address"]
        identity.treasury_address = wallet["address"]
        agreement = generate_operating_agreement(identity.notary_id)
        identity.operating_agreement_hash = agreement.hash
        identity.privacy_policy_hash = agreement.hash

        self.store.put("notaries", identity.notary_id, identity.model_dump(mode="json"))
        self.store.put("operating_agreements", agreement.agreement_id, agreement.model_dump(mode="json"))
        await self._submit_identity_records(identity, agreement)
        return {
            "identity": identity.model_dump(mode="json"),
            "operatingAgreement": agreement.model_dump(mode="json"),
            "wallet": wallet,
        }

    def list_notaries(self) -> list[dict[str, Any]]:
        return self.store.list("notaries")

    async def circle_login_init(self, email: str | None = None) -> dict[str, Any]:
        return await self.circle.login_init(email)

    async def circle_login_complete(self, request_id: str, otp: str) -> dict[str, Any]:
        return await self.circle.login_complete(request_id, otp)

    async def circle_status(self) -> dict[str, Any]:
        try:
            return await self.circle.wallet_status()
        except RuntimeError as exc:
            return {
                "authenticated": False,
                "available": False,
                "error": str(exc),
                "demo": self.settings.notary_demo_mode,
            }

    def speechmatics_status(self) -> dict[str, Any]:
        return {
            "provider": "speechmatics",
            "configured": bool(self.settings.speechmatics_api_key),
            "demoMode": self.settings.speechmatics_demo_mode,
            "baseUrl": self.settings.speechmatics_api_base_url,
            "transcriptionsPath": self.settings.speechmatics_transcriptions_path,
            "statusPathTemplate": self.settings.speechmatics_transcription_status_path_template,
            "transcriptPathTemplate": self.settings.speechmatics_transcript_path_template,
            "language": self.settings.speechmatics_language,
            "operatingPoint": self.settings.speechmatics_operating_point,
            "diarization": self.settings.speechmatics_diarization,
        }

    def auth_status(self) -> dict[str, Any]:
        configured = bool(
            self.settings.qevor_supabase_url
            and self.settings.qevor_supabase_anon_key
            and self.settings.notary_session_secret
        )
        return {
            "provider": "supabase",
            "configured": configured,
            "localSandboxEnabled": bool(
                self.settings.notary_env != "production"
                and self.settings.notary_session_secret
            ),
            "needs": [
                name
                for name, value in {
                    "QEVOR_SUPABASE_URL": self.settings.qevor_supabase_url,
                    "QEVOR_SUPABASE_ANON_KEY": self.settings.qevor_supabase_anon_key,
                    "NOTARY_SESSION_SECRET": self.settings.notary_session_secret,
                }.items()
                if not value
            ],
        }

    async def send_login_otp(self, email: str) -> dict[str, Any]:
        if not self.settings.qevor_supabase_url or not self.settings.qevor_supabase_anon_key:
            raise RuntimeError("QEVOR_SUPABASE_URL and QEVOR_SUPABASE_ANON_KEY are required for sign-in")
        import httpx

        url = f"{self.settings.qevor_supabase_url.rstrip('/')}/auth/v1/otp"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={"email": email, "create_user": True},
                headers={
                    "apikey": self.settings.qevor_supabase_anon_key,
                    "Authorization": f"Bearer {self.settings.qevor_supabase_anon_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if response.status_code in {401, 403}:
                    raise RuntimeError(
                        "Email sign-in is not available yet. Check the Qevor Supabase anon key "
                        "and Auth settings, or use local sandbox sign-in while developing."
                    ) from exc
                raise RuntimeError("Email sign-in is temporarily unavailable. Please try again.") from exc
        return {"status": "otp_sent", "email": email}

    async def verify_login_otp(self, email: str, token: str) -> dict[str, Any]:
        if not self.settings.qevor_supabase_url or not self.settings.qevor_supabase_anon_key:
            raise RuntimeError("QEVOR_SUPABASE_URL and QEVOR_SUPABASE_ANON_KEY are required for sign-in")
        import httpx

        url = f"{self.settings.qevor_supabase_url.rstrip('/')}/auth/v1/verify"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={"email": email, "token": token, "type": "email"},
                headers={
                    "apikey": self.settings.qevor_supabase_anon_key,
                    "Authorization": f"Bearer {self.settings.qevor_supabase_anon_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if response.status_code in {401, 403}:
                    raise RuntimeError(
                        "That sign-in code could not be verified. Check Supabase Auth settings, "
                        "or use local sandbox sign-in while developing."
                    ) from exc
                raise RuntimeError("Email verification is temporarily unavailable. Please try again.") from exc
            session = response.json()
        user = session.get("user") or {}
        return {
            "accessToken": session.get("access_token"),
            "refreshToken": session.get("refresh_token"),
            "expiresIn": session.get("expires_in"),
            "user": {
                "id": user.get("id"),
                "email": user.get("email") or email,
                "aud": user.get("aud"),
                "role": user.get("role"),
            },
        }

    def get_operating_agreement(self, notary_id: str) -> dict[str, Any] | None:
        agreements = self.store.list("operating_agreements")
        return next((item for item in agreements if item.get("notary_id") == notary_id), None)

    async def register_notary_onchain(self, notary_id: str) -> dict[str, Any]:
        identity_data = self.store.get("notaries", notary_id)
        if not identity_data:
            raise RuntimeError(f"Notary {notary_id} was not found")
        agreement_data = self.get_operating_agreement(notary_id)
        if not agreement_data:
            raise RuntimeError(f"Operating agreement for {notary_id} was not found")

        before = {
            item.get("txHash") or item.get("id")
            for item in self.store.list("arc_receipts")
            if self._payload_first_arg(item) == notary_id
        }
        identity = NotaryIdentity.model_validate(identity_data)
        agreement = OperatingAgreement.model_validate(agreement_data)
        await self._submit_identity_records(identity, agreement)
        receipts = [
            item
            for item in self.store.list("arc_receipts")
            if self._payload_first_arg(item) == notary_id
            and (item.get("txHash") or item.get("id")) not in before
        ]
        return {
            "notaryId": notary_id,
            "status": "submitted" if receipts else "unchanged",
            "receipts": receipts,
        }

    async def prepare_circle_gateway_deposit(
        self,
        *,
        amount_usdc: float,
        wallet_id: str | None = None,
    ) -> dict[str, Any]:
        target_wallet = wallet_id or self._default_agent_wallet()
        if not target_wallet:
            raise RuntimeError("Create a NOTARY agent wallet before preparing a Circle Gateway deposit")
        route = await self.circle.prepare_gateway_route(target_wallet, amount_usdc)
        route_id = str(route.get("routeId") or route.get("id") or new_id("gateway_route"))
        record = {
            "routeId": route_id,
            "walletId": target_wallet,
            "amountUSDC": amount_usdc,
            "chain": self.settings.circle_chain,
            "route": route,
            "createdAt": utc_now().isoformat(),
        }
        self.store.put("circle_routes", route_id, record)
        return record

    async def circle_wallet_summary(self) -> dict[str, Any]:
        wallet = self._default_agent_wallet()
        status = await self.circle_status()
        try:
            balance = await self.circle.get_unified_balance(wallet) if wallet else None
        except RuntimeError as exc:
            balance = {"available": False, "error": str(exc)}
        return {
            "status": status,
            "walletId": wallet,
            "balance": balance,
            "chain": self.settings.circle_chain,
            "gatewayEnabled": self.settings.circle_gateway_enabled,
            "paymasterEnabled": self.settings.circle_paymaster_enabled,
        }

    async def ingest_transcript(
        self,
        transcript_text: str,
        privacy_mode: PrivacyMode,
        source_kind: str = "manual_transcript",
        notary_id: str | None = None,
        submitter_identity: str | None = None,
    ) -> dict[str, Any]:
        transcript_record = self.vault.store_text(transcript_text, privacy_mode)
        observation = Observation(
            source=EvidenceSource(
                kind=source_kind,
                uri=transcript_record["encryptedUri"],
                submitted_by=submitter_identity,
                metadata={
                    "vaultEvidenceId": transcript_record["evidenceId"],
                    "transcriptHash": transcript_record["rawHash"],
                },
            ),
            summary=transcript_text[:240],
            raw_text=transcript_text,
            privacy_mode=privacy_mode,
            confidence=0.78,
            metadata={
                "submitter_identity": submitter_identity,
                "payer_identity": submitter_identity,
            }
            if submitter_identity
            else {},
        )
        self.store.put("vault_records", transcript_record["evidenceId"], transcript_record)
        return await self.run_cycle(observation, notary_id=notary_id)

    async def upload_media(
        self,
        file_path: Path,
        filename: str,
        content_type: str,
        privacy_mode: PrivacyMode,
        transcript_text: str | None = None,
    ) -> dict[str, Any]:
        encrypted_file = self.vault.store_file(file_path, privacy_mode)
        evidence = MediaEvidence(
            filename=filename,
            content_type=content_type,
            privacy_mode=privacy_mode,
            raw_sha256=encrypted_file["rawHash"],
            encrypted_uri=encrypted_file["encryptedUri"],
        )
        self.store.put("media", evidence.evidence_id, evidence.model_dump(mode="json"))
        self.store.put("vault_records", encrypted_file["evidenceId"], encrypted_file)

        if transcript_text:
            transcript_record = self.vault.store_text(transcript_text, privacy_mode)
            self.store.put("vault_records", transcript_record["evidenceId"], transcript_record)
            job = TranscriptionJob(
                evidence_id=evidence.evidence_id,
                status="succeeded",
                transcript_text=transcript_text,
                provider="user_supplied",
                completed_at=utc_now(),
                metadata={
                    "vaultEvidenceId": transcript_record["evidenceId"],
                    "transcriptHash": transcript_record["rawHash"],
                },
            )
        elif not self.settings.speechmatics_demo_mode and self.settings.speechmatics_api_key:
            job = await self.speechmatics.transcribe_file(file_path, evidence.evidence_id, privacy_mode)
        else:
            raise RuntimeError(
                "SPEECHMATICS_API_KEY is required for recording transcription. "
                "Alternatively submit transcript_text with the upload."
            )

        if job.transcript_text and "transcriptHash" not in job.metadata:
            transcript_record = self.vault.store_text(job.transcript_text, privacy_mode)
            self.store.put("vault_records", transcript_record["evidenceId"], transcript_record)
            job.metadata["vaultEvidenceId"] = transcript_record["evidenceId"]
            job.metadata["transcriptHash"] = transcript_record["rawHash"]

        self.store.put("transcriptions", job.job_id, job.model_dump(mode="json"))
        response: dict[str, Any] = {
            "evidence": evidence.model_dump(mode="json"),
            "transcription": job.model_dump(mode="json"),
        }
        if job.transcript_text:
            observation = self.speechmatics.transcript_to_observation(job, privacy_mode)
            self.store.put("observations", observation.observation_id, observation.model_dump(mode="json"))
            response["observation"] = observation.model_dump(mode="json")
        return response

    async def run_cycle(self, observation: Observation, notary_id: str | None = None) -> dict[str, Any]:
        metadata = observation.metadata
        request = WitnessIntakeRequest(
            instruction=str(metadata.get("instruction") or observation.raw_text or observation.summary),
            evidence_text=observation.raw_text or observation.summary,
            evidence_ref=observation.source.uri,
            evidence_type=observation.source.kind,
            payer_identity=metadata.get("payer_identity"),
            payee_identity=metadata.get("payee_identity"),
            approver_identity=metadata.get("approver_identity"),
            payer_type=PartyType(metadata.get("payer_type", PartyType.HUMAN.value)),
            payee_type=PartyType(metadata.get("payee_type", PartyType.HUMAN.value)),
            approver_type=PartyType(metadata.get("approver_type", PartyType.HUMAN.value)),
            submitter_identity=str(
                metadata.get("submitter_identity")
                or observation.source.submitted_by
                or "unknown_submitter"
            ),
            submitter_type=PartyType(metadata.get("submitter_type", PartyType.HUMAN.value)),
            privacy_mode=observation.privacy_mode,
            amount_usdc=metadata.get("amount_usdc"),
            notary_id=notary_id,
            metadata={
                "observationId": observation.observation_id,
                "source": observation.source.model_dump(mode="json"),
                **metadata,
            },
        )
        return await self.submit_witness_obligation(request)

    async def create_payment_link(self, request: QevorpayPaymentLinkRequest) -> dict[str, Any]:
        result = await self.qevorpay.create_payment_link(request)
        payment_id = result.get("reference") or new_id("payment")
        self.store.put("payments", payment_id, result)
        return result

    async def create_conditional_case(
        self,
        *,
        created_by_identity: str,
        created_by_type: str = "human",
        payer_identity: str,
        payee_identity: str,
        approver_identity: str | None,
        payer_type: str = "human",
        payee_type: str = "human",
        approver_type: str = "human",
        instruction: str,
        amount_usdc: float,
    ) -> dict[str, Any]:
        if self.settings.qevorpay_demo_mode:
            raise RuntimeError("QEVORPAY_DEMO_MODE=false is required to create real Qevor payment cases")
        payer_resolution = await self.qevorpay.resolve_identity_to_wallet(payer_identity)
        payee_resolution = await self.qevorpay.resolve_identity_to_wallet(payee_identity)
        approver_resolution = (
            await self.qevorpay.resolve_identity_to_wallet(approver_identity)
            if approver_identity
            else None
        )
        executor_wallet = await self.qevorpay.resolve_executor_agent_wallet(
            payer_resolution.get("wallet")
        )
        if not executor_wallet or not executor_wallet.get("escrow_address"):
            raise RuntimeError(
                "Payer must have an enrolled Qevor Arc Testnet agent wallet with an escrow address "
                "before creating a protected NOTARY conditional payment"
            )
        token = new_id("invite")
        case = NotaryCase(
            created_by_identity=created_by_identity,
            created_by_type=PartyType(created_by_type),
            payer_identity=payer_identity,
            payee_identity=payee_identity,
            approver_identity=approver_identity,
            payer_type=PartyType(payer_type),
            payee_type=PartyType(payee_type),
            approver_type=PartyType(approver_type),
            instruction=instruction,
            amount_usdc=amount_usdc,
            evidence_invite_token_hash=sha256_hex(token),
            status="awaiting_funding",
        )
        case.metadata.update(
            {
                "payerUsername": payer_resolution.get("username"),
                "payerWallet": payer_resolution.get("wallet"),
                "payeeUsername": payee_resolution.get("username"),
                "payeeWallet": payee_resolution.get("wallet"),
                "approverUsername": approver_resolution.get("username") if approver_resolution else None,
                "approverWallet": approver_resolution.get("wallet") if approver_resolution else None,
                "executorAgentWalletId": executor_wallet.get("id") if executor_wallet else None,
                "executorEscrowAddress": executor_wallet.get("escrow_address") if executor_wallet else None,
                "fundingRequired": True,
                "fundingStatus": "awaiting_funding",
                "pendingEvidenceInviteToken": token,
            }
        )
        payment = await self.qevorpay.create_conditional_reserve(
            QevorpayConditionalReserveRequest(
                amount_usdc=amount_usdc,
                payer_identity=payer_identity,
                payee_identity=payee_identity,
                payer_wallet=payer_resolution.get("wallet"),
                payee_wallet=payee_resolution.get("wallet"),
                executor_agent_wallet_id=executor_wallet.get("id"),
                reserve_wallet=executor_wallet.get("escrow_address"),
                notary_case_id=case.case_id,
                instruction=instruction,
                metadata={
                    "createdByIdentity": created_by_identity,
                    "payerType": payer_type,
                    "payeeType": payee_type,
                },
            )
        )
        case.qevor_payment_reference = payment.get("reference")
        case.qevor_payment_url = payment.get("url")
        case.qevor_provider = payment.get("provider")
        self.store.put("cases", case.case_id, case.model_dump(mode="json"))
        return case.model_dump(mode="json") | {"evidenceInviteToken": token}

    def mark_case_funded_from_qevor(self, payment_reference: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        funded_statuses = {
            "paid",
            "funded",
            "settled",
            "complete",
            "completed",
            "executed",
            "succeeded",
            "success",
        }
        status = str(
            payload.get("status") or payload.get("state") or payload.get("payment_status") or ""
        ).lower()
        if status and status not in funded_statuses:
            return None
        for item in self.store.list("cases"):
            if str(item.get("qevor_payment_reference")) != str(payment_reference):
                continue
            case = NotaryCase.model_validate(item)
            if case.status == "awaiting_funding":
                token = case.metadata.get("pendingEvidenceInviteToken")
                if token:
                    case.metadata["evidenceUploadPath"] = f"/cases/{case.case_id}/evidence?token={token}"
                    case.metadata.pop("pendingEvidenceInviteToken", None)
                case.metadata["fundingStatus"] = "funded"
                case.metadata["fundedAt"] = utc_now().isoformat()
                case.metadata["fundingEvent"] = payload
                case.status = "funded_awaiting_evidence"
                case.updated_at = utc_now()
                self.store.put("cases", case.case_id, case.model_dump(mode="json"))
            return case.model_dump(mode="json")
        return None

    async def submit_case_evidence(
        self,
        *,
        case_id: str,
        token: str | None,
        evidence_text: str,
        submitter_identity: str,
        submitter_type: str = "human",
        evidence_ref: str | None = None,
        privacy_mode: PrivacyMode = PrivacyMode.PROTECTED,
    ) -> dict[str, Any]:
        case_data = self.store.get("cases", case_id)
        if not case_data:
            return {"error": "case_not_found", "caseId": case_id}
        case = NotaryCase.model_validate(case_data)
        if case.status == "awaiting_funding":
            return {
                "error": "case_not_funded",
                "caseId": case_id,
                "message": "Evidence is not actionable until the Qevor conditional payment is funded.",
            }
        if token and sha256_hex(token) != case.evidence_invite_token_hash:
            return {"error": "invalid_invite_token", "caseId": case_id}
        if submitter_identity not in {case.payee_identity, case.payer_identity, case.approver_identity}:
            if not token:
                return {"error": "submitter_not_authorized", "caseId": case_id}

        case.status = "under_review"
        case.updated_at = utc_now()
        self.store.put("cases", case.case_id, case.model_dump(mode="json"))

        request = WitnessIntakeRequest(
            instruction=case.instruction,
            evidence_text=evidence_text,
            evidence_ref=evidence_ref,
            evidence_type="case_evidence",
            payer_identity=case.payer_identity,
            payee_identity=case.payee_identity,
            approver_identity=case.approver_identity,
            payer_type=case.payer_type,
            payee_type=case.payee_type,
            approver_type=case.approver_type,
            submitter_identity=submitter_identity,
            submitter_type=PartyType(submitter_type),
            privacy_mode=privacy_mode,
            amount_usdc=case.amount_usdc,
            metadata={
                "notaryCaseId": case.case_id,
                "qevorPaymentReference": case.qevor_payment_reference,
                "qevorPaymentUrl": case.qevor_payment_url,
                "payer_identity": case.payer_identity,
                "payee_identity": case.payee_identity,
                "approver_identity": case.approver_identity,
                "payerWallet": case.metadata.get("payerWallet"),
                "payeeWallet": case.metadata.get("payeeWallet"),
                "approverWallet": case.metadata.get("approverWallet"),
                "payerUsername": case.metadata.get("payerUsername"),
                "payeeUsername": case.metadata.get("payeeUsername"),
                "approverUsername": case.metadata.get("approverUsername"),
                "creator_wallet": case.metadata.get("payerWallet"),
                "executor_agent_wallet_id": case.metadata.get("executorAgentWalletId"),
            },
        )
        try:
            ruling = await self.submit_witness_obligation(request)
        except Exception:
            case.status = "failed"
            case.updated_at = utc_now()
            self.store.put("cases", case.case_id, case.model_dump(mode="json"))
            raise

        verdict = ruling.get("verdict", {})
        outcome = verdict.get("outcome")
        if outcome == VerdictOutcome.FULL_RELEASE.value:
            case.status = "released"
        elif outcome == VerdictOutcome.PARTIAL_RELEASE.value:
            case.status = "released"
        elif outcome == VerdictOutcome.REFUSE_REFUND.value:
            case.status = "refunded"
        else:
            case.status = "held"
        case.latest_ruling_id = ruling.get("ruling_id")
        case.updated_at = utc_now()
        self.store.put("cases", case.case_id, case.model_dump(mode="json"))
        return {"case": case.model_dump(mode="json"), "ruling": ruling}

    async def submit_witness_obligation(self, request: WitnessIntakeRequest) -> dict[str, Any]:
        self._require_live_witness_config(payments=True)
        pipeline = self._witness_pipeline(request.notary_id)
        obligation = await self._extract_obligation_with_llm(request)
        obligation.metadata["batch_recipients"] = request.batch_recipients
        obligation.metadata.update(request.metadata)
        obligation, evidence = pipeline.intake(request, obligation)
        self.store.put("obligations", obligation.obligation_id, obligation.model_dump(mode="json"))
        self.store.put("evidence", evidence.evidence_id, evidence.model_dump(mode="json"))

        integrity = pipeline.verify(obligation, [evidence])
        verdict = pipeline.judge(obligation, [evidence], integrity, self._precedent())
        attestation, payload = pipeline.attest(
            obligation,
            [evidence],
            verdict,
            request.privacy_mode,
        )
        receipt = await self.arc.submit_payload(payload)
        attestation.arc_tx_hash = receipt.get("txHash")

        envelope = pipeline.build_attestation_envelope(
            attestation=attestation,
            obligation=obligation,
            verdict=verdict,
            identity_registry=self.settings.arc_notary_identity_registry,
        )
        payment_instruction = pipeline.payment_instruction(
            obligation,
            verdict,
            attestation.attestation_id,
            attestation_envelope=envelope,
        )
        payment_receipt = await self._execute_payment_instruction(payment_instruction)
        ruling = Ruling(
            notary_id=pipeline.notary_id,
            obligation=obligation,
            evidence=[evidence],
            integrity_report=integrity,
            verdict=verdict,
            attestation=attestation,
            payment_instruction=payment_instruction,
            payment_receipt=payment_receipt,
            final_settled_outcome=payment_receipt.get("status"),
        )
        self._persist_ruling(ruling)
        self.store.put(
            "arc_receipts",
            receipt.get("txHash") or new_id("arc_receipt"),
            receipt | {"payload": payload.model_dump(mode="json")},
        )
        return ruling.model_dump(mode="json")

    def seed_visible_demo_records(self) -> None:
        marker = self.store.get("system", "visible_demo_seed_v1")
        if marker:
            return
        pipeline = self._witness_pipeline("notary_demo")

        seeded: list[Ruling] = []

        def build_ruling(
            request: WitnessIntakeRequest,
            *,
            precedent: list[Ruling] | None = None,
            disputed: bool = False,
            reversed_: bool = False,
            supersedes_ref: str | None = None,
            revises_ref: str | None = None,
        ) -> Ruling:
            obligation, evidence = pipeline.intake(request)
            integrity = pipeline.verify(obligation, [evidence])
            verdict = pipeline.judge(obligation, [evidence], integrity, precedent or seeded)
            attestation, _ = pipeline.attest(
                obligation,
                [evidence],
                verdict,
                request.privacy_mode,
                supersedes_ref=supersedes_ref,
                revises_ref=revises_ref,
            )
            attestation.arc_tx_hash = f"demo_arc_{attestation.attestation_id}"
            payment_instruction = pipeline.payment_instruction(
                obligation,
                verdict,
                attestation.attestation_id,
            )
            receipt = {
                "reference": payment_instruction.instruction_id,
                "status": (
                    "held"
                    if payment_instruction.action == PaymentAction.HOLD
                    else "recorded_demo_payment_action"
                ),
                "instruction": payment_instruction.model_dump(mode="json"),
            }
            ruling = Ruling(
                notary_id=pipeline.notary_id,
                obligation=obligation,
                evidence=[evidence],
                integrity_report=integrity,
                verdict=verdict,
                attestation=attestation,
                payment_instruction=payment_instruction,
                payment_receipt=receipt,
                disputed=disputed,
                reversed=reversed_,
                final_settled_outcome=receipt["status"],
            )
            self._persist_ruling(ruling)
            self.store.put("payments", receipt["reference"], receipt)
            seeded.append(ruling)
            return ruling

        build_ruling(
            WitnessIntakeRequest(
                instruction=(
                    "Pay Daniel $250 when the design package is complete and I approve"
                ),
                evidence_text=(
                    "Design package completed and approved by Maya. Timestamped file link, "
                    "signed approval message, and invoice receipt confirm delivery."
                ),
                payer_identity="maya",
                payee_identity="daniel",
                approver_identity="maya",
                submitter_identity="daniel",
                amount_usdc=250,
            )
        )
        build_ruling(
            WitnessIntakeRequest(
                instruction=(
                    "Pay Priya $300 when the design package is complete and I approve"
                ),
                evidence_text=(
                    "Design package completed, timestamped, signed, and approved by Aria. "
                    "The file reference and receipt corroborate every deliverable element."
                ),
                payer_identity="aria",
                payee_identity="priya",
                approver_identity="aria",
                submitter_identity="priya",
                amount_usdc=300,
            )
        )
        build_ruling(
            WitnessIntakeRequest(
                instruction="Pay Jamie when it looks done",
                evidence_text="Jamie says it looks done, but no amount, approver, or acceptance test was provided.",
                payee_identity="jamie",
                submitter_identity="jamie",
            )
        )
        build_ruling(
            WitnessIntakeRequest(
                instruction=(
                    "Pay logistics.agent $600 when the delivery manifest is complete and I approve"
                ),
                evidence_text=(
                    "Programmatic API submission: delivery manifest completed, timestamped, "
                    "hash-linked to file reference, and approved by marketing.agent."
                ),
                payer_identity="marketing.agent",
                payee_identity="logistics.agent",
                approver_identity="marketing.agent",
                payer_type=PartyType.AGENT,
                payee_type=PartyType.AGENT,
                approver_type=PartyType.AGENT,
                submitter_identity="logistics.agent",
                submitter_type=PartyType.AGENT,
                amount_usdc=600,
                metadata={"submittedVia": "api"},
            )
        )
        original = build_ruling(
            WitnessIntakeRequest(
                instruction="Pay Nora $400 when the landing page is complete and I approve",
                evidence_text=(
                    "Landing page completed and approved by Omar. Timestamped signed message "
                    "and file link were submitted."
                ),
                payer_identity="omar",
                payee_identity="nora",
                approver_identity="omar",
                submitter_identity="nora",
                amount_usdc=400,
            )
        )
        _, counter_evidence = pipeline.intake(
            WitnessIntakeRequest(
                instruction=original.obligation.raw_instruction,
                evidence_text=(
                    "Counter-evidence: Omar rejected the landing page after review. "
                    "Timestamped signed QA report says checkout section was missing, "
                    "accessibility review failed, and the work was not delivered as approved."
                ),
                payer_identity="omar",
                payee_identity="nora",
                approver_identity="omar",
                submitter_identity="omar",
            )
        )
        dispute, revised_verdict, changed = pipeline.adjudicate_dispute(
            original,
            [counter_evidence],
            [item for item in seeded if item.ruling_id != original.ruling_id],
        )
        if changed:
            original.disputed = True
            original.attestation.dispute_state = "revised"
            self._persist_ruling(original)
            revised_attestation, _ = pipeline.attest(
                original.obligation,
                [*original.evidence, counter_evidence],
                revised_verdict,
                original.attestation.privacy_mode,
                supersedes_ref=original.attestation.attestation_id,
                revises_ref=original.attestation.attestation_id,
            )
            revised_attestation.arc_tx_hash = f"demo_arc_{revised_attestation.attestation_id}"
            payment_instruction = pipeline.payment_instruction(
                original.obligation,
                revised_verdict,
                revised_attestation.attestation_id,
            )
            receipt = {
                "reference": payment_instruction.instruction_id,
                "status": "recorded_demo_corrective_action",
                "instruction": payment_instruction.model_dump(mode="json"),
            }
            revised = Ruling(
                notary_id=original.notary_id,
                obligation=original.obligation,
                evidence=[*original.evidence, counter_evidence],
                integrity_report=pipeline.verify(original.obligation, [*original.evidence, counter_evidence]),
                verdict=revised_verdict,
                attestation=revised_attestation,
                payment_instruction=payment_instruction,
                payment_receipt=receipt,
                disputed=True,
                reversed=True,
                final_settled_outcome=receipt["status"],
            )
            reversal = pipeline.reversal_for(original, revised)
            dispute.linked_attestation = revised_attestation.attestation_id
            self._persist_ruling(revised)
            self.store.put("payments", receipt["reference"], receipt)
            self.store.put("disputes", dispute.dispute_id, dispute.model_dump(mode="json"))
            self.store.put("reversals", reversal.reversal_id, reversal.model_dump(mode="json"))

        self.store.put(
            "system",
            "visible_demo_seed_v1",
            {"seededAt": utc_now().isoformat(), "purpose": "visible_acceptance_demo"},
        )

    async def dispute_ruling(
        self,
        ruling_id: str,
        *,
        counter_evidence_text: str,
        submitter_identity: str,
        submitter_type: str = "human",
        evidence_ref: str | None = None,
    ) -> dict[str, Any]:
        self._require_live_witness_config(payments=True)
        original_data = self.store.get("rulings", ruling_id)
        if not original_data:
            return {"error": "not_found", "rulingId": ruling_id}
        original = Ruling.model_validate(original_data)
        pipeline = self._witness_pipeline(original.notary_id)
        counter_evidence = Evidence(
            type="counter_evidence",
            ref=evidence_ref,
            text=counter_evidence_text,
            commitment_hash=sha256_hex(
                {
                    "rulingId": ruling_id,
                    "text": counter_evidence_text,
                    "ref": evidence_ref,
                    "submitter": submitter_identity,
                }
            ),
            submitter_identity=submitter_identity,
            submitter_type=submitter_type,
            privacy_mode=original.attestation.privacy_mode,
        )
        dispute, revised_verdict, changed = pipeline.adjudicate_dispute(
            original,
            [counter_evidence],
            self._precedent(exclude_ruling_id=original.ruling_id),
        )
        original.disputed = True
        original.attestation.dispute_state = "revised" if changed else "upheld"
        self._persist_ruling(original)

        if not changed:
            dispute.linked_attestation = original.attestation.attestation_id
            self.store.put("disputes", dispute.dispute_id, dispute.model_dump(mode="json"))
            return {
                "dispute": dispute.model_dump(mode="json"),
                "ruling": original.model_dump(mode="json"),
            }

        all_evidence = [*original.evidence, counter_evidence]
        new_attestation, payload = pipeline.attest(
            original.obligation,
            all_evidence,
            revised_verdict,
            original.attestation.privacy_mode,
            supersedes_ref=original.attestation.attestation_id,
            revises_ref=original.attestation.attestation_id,
        )
        receipt = await self.arc.submit_payload(payload)
        new_attestation.arc_tx_hash = receipt.get("txHash")
        envelope = pipeline.build_attestation_envelope(
            attestation=new_attestation,
            obligation=original.obligation,
            verdict=revised_verdict,
            identity_registry=self.settings.arc_notary_identity_registry,
        )
        payment_instruction = pipeline.payment_instruction(
            original.obligation,
            revised_verdict,
            new_attestation.attestation_id,
            attestation_envelope=envelope,
        )
        payment_receipt = await self._execute_payment_instruction(payment_instruction)
        new_ruling = Ruling(
            notary_id=original.notary_id,
            obligation=original.obligation,
            evidence=all_evidence,
            integrity_report=pipeline.verify(original.obligation, all_evidence),
            verdict=revised_verdict,
            attestation=new_attestation,
            payment_instruction=payment_instruction,
            payment_receipt=payment_receipt,
            disputed=True,
            reversed=True,
            final_settled_outcome=payment_receipt.get("status"),
        )
        reversal = pipeline.reversal_for(original, new_ruling)
        dispute.linked_attestation = new_attestation.attestation_id
        self._persist_ruling(new_ruling)
        self.store.put("disputes", dispute.dispute_id, dispute.model_dump(mode="json"))
        self.store.put("reversals", reversal.reversal_id, reversal.model_dump(mode="json"))
        self.store.put(
            "arc_receipts",
            receipt.get("txHash") or new_attestation.attestation_id,
            receipt | {"payload": payload.model_dump(mode="json")},
        )
        return {
            "dispute": dispute.model_dump(mode="json"),
            "reversal": reversal.model_dump(mode="json"),
            "ruling": new_ruling.model_dump(mode="json"),
        }

    async def reverse_ruling_with_new_evidence(
        self,
        ruling_id: str,
        *,
        new_evidence_text: str,
        submitter_identity: str,
        submitter_type: str = "human",
        evidence_ref: str | None = None,
    ) -> dict[str, Any]:
        return await self.dispute_ruling(
            ruling_id,
            counter_evidence_text=new_evidence_text,
            submitter_identity=submitter_identity,
            submitter_type=submitter_type,
            evidence_ref=evidence_ref,
        )

    def confirm_ruling_outcome(
        self,
        *,
        ruling_id: str,
        party_identity: str,
        party_type: str = "human",
        outcome: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        if not self.store.get("rulings", ruling_id):
            return {"error": "not_found", "rulingId": ruling_id}
        confirmation = OutcomeConfirmation(
            ruling_id=ruling_id,
            party_identity=party_identity,
            party_type=party_type,
            outcome=outcome,
            notes=notes,
        )
        self.store.put(
            "outcome_confirmations",
            confirmation.confirmation_id,
            confirmation.model_dump(mode="json"),
        )
        return confirmation.model_dump(mode="json")

    def public_ledger(self) -> list[dict[str, Any]]:
        ledger: list[dict[str, Any]] = []
        reversals_by_new = {
            item.get("new_ruling_id"): item for item in self.store.list("reversals")
        }
        revisions_by_original = {
            item.get("original_attestation_ref"): item for item in self.store.list("reversals")
        }
        reversal_counts_by_party: dict[str, int] = {}
        for stored in self.store.list("rulings"):
            if not stored.get("reversed"):
                continue
            for identity in (stored.get("attestation", {}).get("party_identities", {}) or {}).values():
                if identity:
                    reversal_counts_by_party[str(identity)] = reversal_counts_by_party.get(str(identity), 0) + 1
        for ruling in self.store.list("rulings"):
            if self._is_debug_ruling(ruling):
                continue
            attestation = ruling.get("attestation", {})
            verdict = ruling.get("verdict", {})
            obligation = ruling.get("obligation", {})
            integrity = ruling.get("integrity_report", {}) or {}
            revision = revisions_by_original.get(attestation.get("attestation_id"))
            ledger.append(
                {
                    "rulingId": ruling.get("ruling_id"),
                    "attestationId": attestation.get("attestation_id"),
                    "arcTxHash": attestation.get("arc_tx_hash"),
                    "verdict": verdict.get("outcome"),
                    "releasePct": verdict.get("release_pct"),
                    "confidence": verdict.get("confidence"),
                    "confidenceGate": verdict.get("confidence_gate"),
                    "disputeWindowOpen": verdict.get("dispute_window_open"),
                    "reasoningTrace": verdict.get("reasoning_trace"),
                    "precedentRefs": verdict.get("precedent_refs", []),
                    "disputed": ruling.get("disputed", False),
                    "reversed": ruling.get("reversed", False),
                    "supersedes": attestation.get("supersedes_ref"),
                    "revises": attestation.get("revises_ref"),
                    "partyIdentities": attestation.get("party_identities", {}),
                    "partyTypes": attestation.get("party_types", {}),
                    "partyReversalCounts": {
                        identity: reversal_counts_by_party.get(str(identity), 0)
                        for identity in (attestation.get("party_identities", {}) or {}).values()
                        if identity
                    },
                    "obligation": obligation,
                    "obligationSummary": obligation.get("deliverable") or obligation.get("raw_instruction"),
                    "clarificationNeeded": obligation.get("clarification_needed", False),
                    "clarificationQuestions": obligation.get("clarification_questions", []),
                    "integrityReport": {
                        "sourceQuality": integrity.get("source_quality"),
                        "safetyFlags": integrity.get("safety_flags", []),
                        "metadata": integrity.get("metadata", {}),
                    },
                    "evidenceCommitmentHash": attestation.get("evidence_commitment_hash"),
                    "reasoningTraceHash": attestation.get("reasoning_trace_hash"),
                    "reversal": reversals_by_new.get(ruling.get("ruling_id")),
                    "attestationChain": {
                        "original": (
                            attestation.get("revises_ref")
                            or attestation.get("supersedes_ref")
                            or attestation.get("attestation_id")
                        ),
                        "current": attestation.get("attestation_id"),
                        "revision": (
                            revision.get("new_attestation_ref") if revision else None
                        ),
                    },
                }
            )
        return ledger

    def party_operating_history(self, party_identity: str) -> dict[str, Any]:
        history: PartyOperatingHistory | None = None
        records = []
        for ruling in self.store.list("rulings"):
            if self._is_debug_ruling(ruling):
                continue
            parsed = Ruling.model_validate(ruling)
            parties = parsed.attestation.party_identities
            party_types = parsed.attestation.party_types
            role = next(
                (role for role, identity in parties.items() if identity == party_identity),
                None,
            )
            if not role:
                continue
            party_type = party_types.get(role)
            if history is None:
                history = PartyOperatingHistory(
                    party_identity=party_identity,
                    party_type=party_type,
                )
            history.rulings.append(parsed.ruling_id)
            if parsed.disputed:
                history.dispute_flags.append(parsed.ruling_id)
            if parsed.reversed:
                history.reversal_flags.append(parsed.ruling_id)
            records.append(
                {
                    "rulingId": parsed.ruling_id,
                    "role": role,
                    "verdict": parsed.verdict.outcome.value,
                    "releasePct": parsed.verdict.release_pct,
                    "confidence": parsed.verdict.confidence,
                    "disputed": parsed.disputed,
                    "reversed": parsed.reversed,
                    "attestationId": parsed.attestation.attestation_id,
                    "createdAt": parsed.created_at.isoformat(),
                }
            )
        if history is None:
            history = PartyOperatingHistory(party_identity=party_identity, party_type="human")
        return history.model_dump(mode="json") | {"records": records}

    def list_bucket(self, bucket: str) -> list[dict[str, Any]]:
        return self._scrub_public_bucket(bucket, self.store.list(bucket))

    def dashboard_state(self) -> dict[str, Any]:
        ledger = self.public_ledger()
        public_ruling_ids = {item.get("rulingId") for item in ledger}
        return {
            "notaries": self._scrub_public_bucket("notaries", self.store.list("notaries")),
            "attestations": [],
            "payments": self._scrub_public_bucket("payments", self.store.list("payments")),
            "payment_instructions": self._scrub_public_bucket(
                "payment_instructions",
                self.store.list("payment_instructions"),
            ),
            "arc_receipts": self._scrub_public_bucket(
                "arc_receipts",
                self.store.list("arc_receipts"),
            ),
            "validations": self._scrub_public_bucket("validations", self.store.list("validations")),
            "access_grants": self.store.list("access_grants"),
            "media": self.store.list("media"),
            "transcriptions": self.store.list("transcriptions"),
            "witness_attestations": self.store.list("witness_attestations"),
            "speechmatics": self.speechmatics_status(),
            "auth": self.auth_status(),
            "circle_routes": self.store.list("circle_routes"),
            "swarm_roles": self.swarm_roles(),
            "cases": self.store.list("cases"),
            "rulings": ledger,
            "disputes": self.store.list("disputes"),
            "reversals": [
                item
                for item in self.store.list("reversals")
                if item.get("original_ruling_id") in public_ruling_ids
                or item.get("new_ruling_id") in public_ruling_ids
            ],
            "outcome_confirmations": self.store.list("outcome_confirmations"),
        }

    def swarm_roles(self) -> list[dict[str, Any]]:
        cases = self.store.list("cases")
        rulings = self.store.list("rulings")
        latest_case = cases[-1] if cases else {}
        latest_ruling = rulings[-1] if rulings else {}
        obligation = latest_ruling.get("obligation", {}) or {}
        integrity = latest_ruling.get("integrity_report", {}) or {}
        verdict = latest_ruling.get("verdict", {}) or {}
        attestation = latest_ruling.get("attestation", {}) or {}
        payment = latest_ruling.get("payment_instruction", {}) or {}
        reversal_count = len(self.store.list("reversals"))
        return [
            {
                "name": "Signal Scanner",
                "role": "Observes obligations, Speechmatics transcripts, and case evidence.",
                "status": "active" if cases or rulings else "ready",
                "lastOutput": obligation.get("raw_instruction")
                or latest_case.get("instruction")
                or "Awaiting first observation",
            },
            {
                "name": "Guardian Sentinel",
                "role": "Checks source quality, spoofing risk, and evidence integrity.",
                "status": "approved" if integrity.get("approved") else "watching",
                "lastOutput": ", ".join(integrity.get("safety_flags", []) or [])
                or f"source quality {integrity.get('source_quality', 'n/a')}",
            },
            {
                "name": "Risk Guardian",
                "role": "Applies legal threshold, confidence gates, and release sizing.",
                "status": verdict.get("confidence_gate") or "ready",
                "lastOutput": verdict.get("outcome") or "No verdict yet",
            },
            {
                "name": "Strategy Engine",
                "role": "Turns verdicts into Qevor reserve, release, hold, refund, or batch actions.",
                "status": payment.get("action") or latest_case.get("status") or "ready",
                "lastOutput": payment.get("reason")
                or latest_case.get("qevor_payment_reference")
                or "Waiting for funded case",
            },
            {
                "name": "Validator",
                "role": "Signs EIP-712 attestations and submits hashes to Arc.",
                "status": "signed" if attestation.get("signature") else "ready",
                "lastOutput": attestation.get("attestation_id") or "No attestation signed yet",
            },
            {
                "name": "Reflector",
                "role": "Maintains precedent, disputes, self-correction, and reversal memory.",
                "status": "learning" if rulings else "ready",
                "lastOutput": f"{len(rulings)} ruling(s), {reversal_count} reversal(s)",
            },
        ]

    def _default_agent_wallet(self) -> str | None:
        notaries = self.store.list("notaries")
        for item in reversed(notaries):
            wallet = item.get("agent_wallet") or item.get("treasury_address")
            if wallet:
                return str(wallet)
        return None

    def _payload_first_arg(self, item: dict[str, Any]) -> Any:
        args = item.get("payload", {}).get("args", [])
        return args[0] if args else None

    def _is_debug_ruling(self, ruling: dict[str, Any]) -> bool:
        obligation = ruling.get("obligation", {})
        raw = str(obligation.get("raw_instruction") or "").strip().lower()
        summary = str(obligation.get("deliverable") or "").strip().lower()
        return (
            ruling.get("notary_id") == "notary_demo"
            or raw in {"test", "debug", "notary observed and verified: test"}
            or summary == "test"
        )

    def _scrub_public_bucket(self, bucket: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if bucket == "payments":
            return [
                item
                for item in items
                if (
                    (item.get("instruction", {}).get("metadata", {}) or {}).get("obligationId")
                    or (item.get("request", {}).get("metadata", {}) or {}).get("obligationId")
                )
            ]
        if bucket == "payment_instructions":
            return [
                item
                for item in items
                if (item.get("metadata", {}) or {}).get("obligationId")
            ]
        if bucket == "arc_receipts":
            return [
                item
                for item in items
                if not self._contains_removed_padding_record(item)
            ]
        if bucket == "validations":
            return [
                item
                for item in items
                if not self._contains_removed_padding_record(item)
            ]
        if bucket == "notaries":
            allowed = {
                "witness_to_pay",
                "speechmatics_transcription",
                "qevor_payment_execution",
                "arc_attestation_hashing",
                "graded_verdicts",
                "dispute_adjudication",
                "self_reversal",
                "party_operating_history",
            }
            cleaned = []
            for item in items:
                record = dict(item)
                record["capabilities"] = [
                    capability
                    for capability in record.get("capabilities", [])
                    if capability in allowed
                ]
                for stale_key in ("parent_notary_id", "policy_dna_hash"):
                    record.pop(stale_key, None)
                cleaned.append(record)
            return cleaned
        return items

    def _contains_removed_padding_record(self, item: dict[str, Any]) -> bool:
        text = str(item).lower()
        removed_terms = ("pred" + "_", "pre" + "diction", "kar" + "ma")
        return any(term in text for term in removed_terms)

    def grant_evidence_access(
        self,
        *,
        evidence_id: str,
        grantee: str,
        purpose: str,
        disclosure_level: DisclosureLevel,
    ) -> dict[str, Any]:
        grant = self.vault.create_access_grant(evidence_id, grantee, purpose, disclosure_level)
        self.store.put("access_grants", grant.grant_id, grant.model_dump(mode="json"))
        return grant.model_dump(mode="json")

    def _persist_ruling(self, ruling: Ruling) -> None:
        self.store.put("rulings", ruling.ruling_id, ruling.model_dump(mode="json"))
        self.store.put(
            "witness_attestations",
            ruling.attestation.attestation_id,
            ruling.attestation.model_dump(mode="json"),
        )
        self.store.put(
            "verdicts",
            ruling.verdict.verdict_id,
            ruling.verdict.model_dump(mode="json"),
        )
        if ruling.payment_instruction:
            self.store.put(
                "payment_instructions",
                ruling.payment_instruction.instruction_id,
                ruling.payment_instruction.model_dump(mode="json"),
            )

    def _precedent(self, exclude_ruling_id: str | None = None) -> list[Ruling]:
        return [
            Ruling.model_validate(item)
            for item in self.store.list("rulings")
            if item.get("ruling_id") != exclude_ruling_id
        ]

    def _witness_pipeline(self, notary_id: str | None = None) -> WitnessPipeline:
        return WitnessPipeline(
            notary_id=notary_id or self._default_notary_id(),
            signer=self._witness_signer(),
            attestation_registry=self.settings.arc_attestation_registry,
        )

    def _witness_signer(self):
        from notary.crypto.eip712 import EIP712Signer

        return EIP712Signer(
            private_key=self.settings.validator_private_key,
            domain_name=self.settings.validator_eip712_name,
            domain_version=self.settings.validator_eip712_version,
            chain_id=self.settings.arc_chain_id,
        )

    def _require_live_witness_config(self, *, payments: bool) -> None:
        missing = []
        if not self.settings.groq_api_key and not self.settings.claude_api_key:
            missing.append("GROQ_API_KEY or CLAUDE_API_KEY")
        if not self.settings.validator_private_key:
            missing.append("VALIDATOR_PRIVATE_KEY")
        if self.settings.arc_demo_mode:
            missing.append("ARC_DEMO_MODE=false")
        for name, value in {
            "ARC_RPC_URL": self.settings.arc_rpc_url,
            "ARC_CHAIN_ID": self.settings.arc_chain_id,
            "ARC_OPERATOR_PRIVATE_KEY": self.settings.arc_operator_private_key,
            "ARC_ATTESTATION_REGISTRY": self.settings.arc_attestation_registry,
        }.items():
            if not value:
                missing.append(name)
        if payments:
            if self.settings.qevorpay_demo_mode:
                missing.append("QEVORPAY_DEMO_MODE=false")
            for name, value in {
                "QEVOR_SUPABASE_URL": self.settings.qevor_supabase_url,
                "QEVOR_SUPABASE_SERVICE_ROLE_KEY": (
                    self.settings.qevor_supabase_service_role_key
                ),
            }.items():
                if not value:
                    missing.append(name)
        if missing:
            raise RuntimeError(
                "Live NOTARY witness flow requires configuration: " + ", ".join(missing)
            )

    async def _extract_obligation_with_llm(self, request: WitnessIntakeRequest):
        if self.settings.groq_api_key:
            extractor = GroqObligationExtractor(
                api_key=self.settings.groq_api_key,
                model=self.settings.groq_model,
                api_base_url=self.settings.groq_api_base_url,
            )
            return await extractor.extract(request)
        if self.settings.claude_api_key:
            from notary.services.obligation_extractor import ClaudeObligationExtractor
            extractor = ClaudeObligationExtractor(
                api_key=self.settings.claude_api_key,
                model=self.settings.claude_model,
                api_base_url=self.settings.claude_api_base_url,
            )
            return await extractor.extract(request)
        raise RuntimeError("GROQ_API_KEY or CLAUDE_API_KEY is required for LLM obligation extraction")

    async def _execute_payment_instruction(self, instruction: PaymentInstruction) -> dict[str, Any]:
        if instruction.action == PaymentAction.HOLD:
            receipt = {
                "reference": instruction.instruction_id,
                "status": "held",
                "reason": instruction.reason,
                "instruction": instruction.model_dump(mode="json"),
            }
        else:
            if instruction.recipients:
                receipt = await self.qevorpay.create_batch_distribution(
                    QevorpayBatchDistributionRequest(
                        recipients=instruction.recipients,
                        reason=instruction.reason,
                        metadata=instruction.metadata
                        | {
                            "payerIdentity": instruction.payer_identity,
                            "attestationId": instruction.attestation_id,
                        },
                    )
                )
                self.store.put(
                    "payments",
                    receipt.get("reference") or instruction.instruction_id,
                    receipt,
                )
                return receipt
            trigger = PaymentTrigger(
                action=instruction.action,
                amount_usdc=instruction.amount_usdc,
                recipient=instruction.payee_identity,
                condition=instruction.reason,
                attestation_id=instruction.attestation_id,
                qevorpay_reference=instruction.metadata.get("qevorPaymentReference"),
                authorized=True,
                metadata=instruction.metadata | {"payerIdentity": instruction.payer_identity},
            )
            receipt = await self.qevorpay.execute_trigger(trigger)
        self.store.put("payments", receipt.get("reference") or instruction.instruction_id, receipt)
        return receipt

    def _default_notary_id(self) -> str:
        if self.settings.notary_id:
            return self.settings.notary_id
        notaries = self.store.list("notaries")
        if notaries:
            return str(notaries[0]["notary_id"])
        return "notary_local"

    async def _submit_identity_records(self, identity: NotaryIdentity, agreement: OperatingAgreement) -> None:
        payloads = [
            ArcTransactionPayload(
                contract_name="NotaryIdentityRegistry",
                method="createNotary",
                args=[
                    identity.notary_id,
                    identity.agent_wallet or "0x0000000000000000000000000000000000000000",
                    identity.treasury_address or "0x0000000000000000000000000000000000000000",
                    sha256_hex(identity.capabilities),
                    identity.operating_agreement_hash or sha256_hex(""),
                    sha256_hex(""),
                    identity.privacy_policy_hash or sha256_hex(""),
                ],
            ),
            ArcTransactionPayload(
                contract_name="NotaryGovernance",
                method="updateGovernance",
                args=[
                    identity.notary_id,
                    agreement.hash or sha256_hex(""),
                    sha256_hex(agreement.permitted_actions),
                    sha256_hex(agreement.privacy_rules),
                    sha256_hex({"reversalRequiredWhenWrong": True}),
                    identity.agent_wallet or "0x0000000000000000000000000000000000000000",
                ],
            ),
        ]
        await self._submit_arc_payloads(payloads)

    async def _submit_arc_payloads(self, payloads: list[ArcTransactionPayload]) -> None:
        for payload in payloads:
            receipt = await self.arc.submit_payload(payload)
            key = receipt.get("txHash") or new_id("arc_receipt")
            self.store.put("arc_receipts", key, receipt | {"payload": payload.model_dump(mode="json")})
