from __future__ import annotations

from pathlib import Path
from typing import Any

from notary.config import Settings
from notary.crypto.hashing import sha256_hex
from notary.legal.operating_agreement import generate_operating_agreement
from notary.models.schemas import (
    ArcTransactionPayload,
    DisclosureLevel,
    EvidenceSource,
    EvidenceAccessGrant,
    MediaEvidence,
    NotaryIdentity,
    NotaryState,
    Observation,
    OperatingAgreement,
    PrivacyMode,
    QevorpayPaymentLinkRequest,
    TranscriptionJob,
    ValidationRecord,
    new_id,
    utc_now,
)
from notary.services.arc import ArcClient
from notary.services.circle_agent import CircleAgentClient
from notary.services.evidence_vault import EvidenceVault
from notary.services.qevorpay import QevorpayClient
from notary.services.reasoning import AnthropicReasoner, GroqReasoner, SwarmReasoningEngine
from notary.services.speechmatics import SpeechmaticsClient
from notary.storage.sqlite import SQLiteStore
from notary.swarm.notary_swarm import run_notary_cycle

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
        )
        self.arc = ArcClient(
            rpc_url=settings.arc_rpc_url,
            chain_id=settings.arc_chain_id,
            private_key=settings.arc_operator_private_key,
            demo_mode=settings.arc_demo_mode,
            contract_addresses={
                "NotaryIdentityRegistry": settings.arc_notary_identity_registry or "",
                "AttestationRegistry": settings.arc_attestation_registry or "",
                "HelixAIKarma": settings.arc_karma_registry or "",
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
        self.reasoning = SwarmReasoningEngine(
            groq=GroqReasoner(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                api_base_url=settings.groq_api_base_url,
            )
            if settings.groq_api_key
            else None,
            reflector=AnthropicReasoner(
                api_key=settings.claude_api_key,
                model=settings.claude_model,
                api_base_url=settings.claude_api_base_url,
            )
            if settings.claude_api_key
            else None,
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
                "qevorpay_payment_triggers",
                "arc_attestation_hashing",
                "privacy_modes",
                "micro_shares",
                "treasury_intelligence",
            ],
            endpoint=None,
        )
        wallet = await self.circle.create_agent_wallet(label or identity.notary_id)
        identity.agent_wallet = wallet["address"]
        identity.treasury_address = wallet["address"]
        agreement = generate_operating_agreement(identity.notary_id)
        identity.operating_agreement_hash = agreement.hash
        identity.policy_dna_hash = agreement.hash
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
        return await self.circle.wallet_status()

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

    def get_operating_agreement(self, notary_id: str) -> dict[str, Any] | None:
        agreements = self.store.list("operating_agreements")
        return next((item for item in agreements if item.get("notary_id") == notary_id), None)

    async def ingest_transcript(
        self,
        transcript_text: str,
        privacy_mode: PrivacyMode,
        source_kind: str = "manual_transcript",
        notary_id: str | None = None,
    ) -> dict[str, Any]:
        transcript_record = self.vault.store_text(transcript_text, privacy_mode)
        observation = Observation(
            source=EvidenceSource(
                kind=source_kind,
                uri=transcript_record["encryptedUri"],
                metadata={
                    "vaultEvidenceId": transcript_record["evidenceId"],
                    "transcriptHash": transcript_record["rawHash"],
                },
            ),
            summary=transcript_text[:240],
            raw_text=transcript_text,
            privacy_mode=privacy_mode,
            confidence=0.78,
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
            job = TranscriptionJob(
                evidence_id=evidence.evidence_id,
                status="queued",
                provider="speechmatics",
                metadata={
                    "nextStep": "Configure Speechmatics credentials or submit transcript_text.",
                    "localFile": str(file_path),
                },
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
        state = NotaryState(
            notary_id=notary_id or self._default_notary_id(),
            privacy_mode=observation.privacy_mode,
            observations=[observation],
            metadata={
                "validatorPrivateKey": self.settings.validator_private_key,
                "validatorDomainName": self.settings.validator_eip712_name,
                "validatorDomainVersion": self.settings.validator_eip712_version,
                "arcChainId": self.settings.arc_chain_id,
                "verifyingContracts": {
                    "AttestationRegistry": self.settings.arc_attestation_registry,
                    "HelixAIKarma": self.settings.arc_karma_registry,
                },
            },
        )
        result = await run_notary_cycle(state, reasoning=self.reasoning if self.reasoning.enabled else None)
        await self._submit_arc_payloads(result.arc_payloads)
        await self._execute_payment_triggers(result)
        await self._write_validation_records(result)
        self._persist_state(result)
        return result.model_dump(mode="json")

    async def create_payment_link(self, request: QevorpayPaymentLinkRequest) -> dict[str, Any]:
        result = await self.qevorpay.create_payment_link(request)
        payment_id = result.get("reference") or new_id("payment")
        self.store.put("payments", payment_id, result)
        return result

    def list_bucket(self, bucket: str) -> list[dict[str, Any]]:
        return self.store.list(bucket)

    def dashboard_state(self) -> dict[str, Any]:
        return {
            "notaries": self.store.list("notaries"),
            "attestations": self.store.list("attestations"),
            "predictions": self.store.list("predictions"),
            "payments": self.store.list("payments"),
            "payment_triggers": self.store.list("payment_triggers"),
            "arc_receipts": self.store.list("arc_receipts"),
            "validations": self.store.list("validations"),
            "access_grants": self.store.list("access_grants"),
            "cycles": self.store.list("cycles"),
            "media": self.store.list("media"),
            "transcriptions": self.store.list("transcriptions"),
            "karma": self.store.list("karma"),
            "speechmatics": self.speechmatics_status(),
        }

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

    def _persist_state(self, state: NotaryState) -> None:
        self.store.put("cycles", state.cycle_id, state.model_dump(mode="json"))
        for observation in state.observations:
            self.store.put("observations", observation.observation_id, observation.model_dump(mode="json"))
        for attestation in state.attestations:
            self.store.put("attestations", attestation.attestation_id, attestation.model_dump(mode="json"))
        for prediction in state.predictions:
            self.store.put("predictions", prediction.prediction_id, prediction.model_dump(mode="json"))
        for trigger in state.payment_triggers:
            self.store.put("payment_triggers", trigger.trigger_id, trigger.model_dump(mode="json"))
        if state.karma:
            self.store.put("karma", state.karma.checkpoint_id, state.karma.model_dump(mode="json"))

    def _default_notary_id(self) -> str:
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
                    identity.policy_dna_hash or sha256_hex(""),
                    identity.privacy_policy_hash or sha256_hex(""),
                    identity.parent_notary_id or ZERO_BYTES32,
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
                    sha256_hex({"replicationAllowed": True}),
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

    async def _execute_payment_triggers(self, state: NotaryState) -> None:
        for trigger in state.payment_triggers:
            if not trigger.authorized:
                continue
            receipt = await self.qevorpay.execute_trigger(trigger)
            trigger.qevorpay_reference = receipt.get("reference")
            payment_id = trigger.qevorpay_reference or trigger.trigger_id
            self.store.put(
                "payments",
                payment_id,
                receipt | {"triggerId": trigger.trigger_id, "attestationId": trigger.attestation_id},
            )

    async def _write_validation_records(self, state: NotaryState) -> None:
        records: list[ValidationRecord] = []
        validator_address = self.arc.sender if self.arc.sender.startswith("0x") and len(self.arc.sender) == 42 else ZERO_ADDRESS
        if state.attestations:
            attestation = state.attestations[-1]
            records.append(
                ValidationRecord(
                    notary_id=state.notary_id,
                    kind="attestation_signature",
                    subject_id=attestation.attestation_id,
                    hash=sha256_hex(attestation.model_dump(mode="json")),
                    validator=validator_address,
                )
            )
        if state.karma:
            records.append(
                ValidationRecord(
                    notary_id=state.notary_id,
                    kind="karma_checkpoint",
                    subject_id=state.karma.checkpoint_id,
                    hash=sha256_hex(state.karma.model_dump(mode="json")),
                    validator=validator_address,
                )
            )

        for record in records:
            self.store.put("validations", record.validation_id, record.model_dump(mode="json"))
            receipt = await self.arc.submit_payload(
                ArcTransactionPayload(
                    contract_name="NotaryValidationRegistry",
                    method="recordValidation",
                    args=[
                        record.validation_id,
                        record.notary_id,
                        record.subject_id,
                        record.hash,
                        sha256_hex(record.kind),
                        record.validator or ZERO_ADDRESS,
                    ],
                )
            )
            key = receipt.get("txHash") or record.validation_id
            self.store.put(
                "arc_receipts",
                key,
                receipt
                | {
                    "payload": {
                        "contract_name": "NotaryValidationRegistry",
                        "method": "recordValidation",
                        "subject_id": record.subject_id,
                    }
                },
            )
