from __future__ import annotations

from pathlib import Path
from typing import Any

from notary.config import Settings
from notary.legal.operating_agreement import generate_operating_agreement
from notary.models.schemas import (
    EvidenceSource,
    MediaEvidence,
    NotaryIdentity,
    NotaryState,
    Observation,
    PrivacyMode,
    QevorpayPaymentLinkRequest,
    TranscriptionJob,
    new_id,
    utc_now,
)
from notary.services.circle_agent import CircleAgentClient
from notary.services.qevorpay import QevorpayClient
from notary.services.speedmatic import SpeedmaticClient
from notary.storage.sqlite import SQLiteStore
from notary.swarm.notary_swarm import run_notary_cycle


class NotaryAppService:
    """Application service for the product workflows.

    The service persists real app state locally in SQLite and only uses local fallbacks where an
    external provider is not configured. That keeps the product usable before production API keys
    are connected without falsely claiming external settlement/transcription happened.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.notary_db_path)
        self.circle = CircleAgentClient(demo_mode=settings.notary_demo_mode)
        self.qevorpay = QevorpayClient(
            api_base_url=settings.qevorpay_api_base_url,
            api_key=settings.qevorpay_api_key,
            demo_mode=settings.qevorpay_demo_mode,
        )
        self.speedmatic = SpeedmaticClient(
            api_base_url=settings.speedmatic_api_base_url,
            api_key=settings.speedmatic_api_key,
            demo_mode=settings.speedmatic_demo_mode,
        )

    async def create_notary(self, label: str | None = None) -> dict[str, Any]:
        identity = NotaryIdentity(
            capabilities=[
                "witness_to_pay",
                "speedmatic_transcription",
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
        return {
            "identity": identity.model_dump(mode="json"),
            "operatingAgreement": agreement.model_dump(mode="json"),
            "wallet": wallet,
        }

    def list_notaries(self) -> list[dict[str, Any]]:
        return self.store.list("notaries")

    async def ingest_transcript(
        self,
        transcript_text: str,
        privacy_mode: PrivacyMode,
        source_kind: str = "manual_transcript",
        notary_id: str | None = None,
    ) -> dict[str, Any]:
        observation = Observation(
            source=EvidenceSource(kind=source_kind),
            summary=transcript_text[:240],
            raw_text=transcript_text,
            privacy_mode=privacy_mode,
            confidence=0.78,
        )
        return await self.run_cycle(observation, notary_id=notary_id)

    async def upload_media(
        self,
        file_path: Path,
        filename: str,
        content_type: str,
        privacy_mode: PrivacyMode,
        transcript_text: str | None = None,
    ) -> dict[str, Any]:
        evidence = MediaEvidence(
            filename=filename,
            content_type=content_type,
            privacy_mode=privacy_mode,
        )
        self.store.put("media", evidence.evidence_id, evidence.model_dump(mode="json"))

        if transcript_text:
            job = TranscriptionJob(
                evidence_id=evidence.evidence_id,
                status="succeeded",
                transcript_text=transcript_text,
                provider="user_supplied",
                completed_at=utc_now(),
            )
        elif not self.settings.speedmatic_demo_mode and self.settings.speedmatic_api_key:
            job = await self.speedmatic.transcribe_file(file_path, evidence.evidence_id, privacy_mode)
        else:
            job = TranscriptionJob(
                evidence_id=evidence.evidence_id,
                status="queued",
                provider="speedmatic",
                metadata={
                    "nextStep": "Configure Speedmatic credentials or submit transcript_text.",
                    "localFile": str(file_path),
                },
            )

        self.store.put("transcriptions", job.job_id, job.model_dump(mode="json"))
        response: dict[str, Any] = {
            "evidence": evidence.model_dump(mode="json"),
            "transcription": job.model_dump(mode="json"),
        }
        if job.transcript_text:
            observation = self.speedmatic.transcript_to_observation(job, privacy_mode)
            self.store.put("observations", observation.observation_id, observation.model_dump(mode="json"))
            response["observation"] = observation.model_dump(mode="json")
        return response

    async def run_cycle(self, observation: Observation, notary_id: str | None = None) -> dict[str, Any]:
        state = NotaryState(
            notary_id=notary_id or self._default_notary_id(),
            privacy_mode=observation.privacy_mode,
            observations=[observation],
        )
        result = await run_notary_cycle(state)
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
            "cycles": self.store.list("cycles"),
            "media": self.store.list("media"),
            "transcriptions": self.store.list("transcriptions"),
            "karma": self.store.list("karma"),
        }

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
