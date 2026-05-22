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
    QevorpayPaymentLinkRequest,
    Ruling,
    TranscriptionJob,
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
        wallet = await self.circle.create_agent_wallet(label or identity.notary_id)
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

    async def submit_witness_obligation(self, request: WitnessIntakeRequest) -> dict[str, Any]:
        self._require_live_witness_config(payments=True)
        pipeline = self._witness_pipeline(request.notary_id)
        obligation = await self._extract_obligation_with_llm(request)
        obligation.metadata["batch_recipients"] = request.batch_recipients
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

        payment_instruction = pipeline.payment_instruction(
            obligation,
            verdict,
            attestation.attestation_id,
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
        payment_instruction = pipeline.payment_instruction(
            original.obligation,
            revised_verdict,
            new_attestation.attestation_id,
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
        for ruling in self.store.list("rulings"):
            attestation = ruling.get("attestation", {})
            verdict = ruling.get("verdict", {})
            obligation = ruling.get("obligation", {})
            ledger.append(
                {
                    "rulingId": ruling.get("ruling_id"),
                    "attestationId": attestation.get("attestation_id"),
                    "arcTxHash": attestation.get("arc_tx_hash"),
                    "verdict": verdict.get("outcome"),
                    "releasePct": verdict.get("release_pct"),
                    "confidence": verdict.get("confidence"),
                    "disputed": ruling.get("disputed", False),
                    "reversed": ruling.get("reversed", False),
                    "supersedes": attestation.get("supersedes_ref"),
                    "revises": attestation.get("revises_ref"),
                    "partyIdentities": attestation.get("party_identities", {}),
                    "partyTypes": attestation.get("party_types", {}),
                    "obligationSummary": obligation.get("deliverable"),
                    "evidenceCommitmentHash": attestation.get("evidence_commitment_hash"),
                    "reasoningTraceHash": attestation.get("reasoning_trace_hash"),
                    "reversal": reversals_by_new.get(ruling.get("ruling_id")),
                }
            )
        return ledger

    def party_operating_history(self, party_identity: str) -> dict[str, Any]:
        history: PartyOperatingHistory | None = None
        records = []
        for ruling in self.store.list("rulings"):
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
        return self.store.list(bucket)

    def dashboard_state(self) -> dict[str, Any]:
        return {
            "notaries": self.store.list("notaries"),
            "attestations": self.store.list("attestations"),
            "payments": self.store.list("payments"),
            "payment_instructions": self.store.list("payment_instructions"),
            "arc_receipts": self.store.list("arc_receipts"),
            "validations": self.store.list("validations"),
            "access_grants": self.store.list("access_grants"),
            "media": self.store.list("media"),
            "transcriptions": self.store.list("transcriptions"),
            "witness_attestations": self.store.list("witness_attestations"),
            "speechmatics": self.speechmatics_status(),
            "rulings": self.public_ledger(),
            "disputes": self.store.list("disputes"),
            "reversals": self.store.list("reversals"),
            "outcome_confirmations": self.store.list("outcome_confirmations"),
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
                "QEVOR_CREATOR_WALLET": self.settings.qevor_creator_wallet,
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
                authorized=True,
                metadata=instruction.metadata | {"payerIdentity": instruction.payer_identity},
            )
            receipt = await self.qevorpay.execute_trigger(trigger)
        self.store.put("payments", receipt.get("reference") or instruction.instruction_id, receipt)
        return receipt

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
