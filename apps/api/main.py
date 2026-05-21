from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, UploadFile

from notary.config import get_settings
from notary.legal.operating_agreement import generate_operating_agreement
from notary.models.schemas import (
    EvidenceSource,
    MediaEvidence,
    NotaryIdentity,
    NotaryState,
    Observation,
    PrivacyMode,
    QevorpayPaymentLinkRequest,
)
from notary.services.qevorpay import QevorpayClient
from notary.services.speedmatic import SpeedmaticClient
from notary.swarm.notary_swarm import run_notary_cycle

app = FastAPI(title="NOTARY", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "notary"}


@app.post("/notaries")
async def create_notary() -> dict:
    identity = NotaryIdentity(
        capabilities=[
            "witness_to_pay",
            "speedmatic_transcription",
            "qevorpay_payment_triggers",
            "arc_attestation_hashing",
            "micro_shares",
        ]
    )
    agreement = generate_operating_agreement(identity.notary_id)
    identity.operating_agreement_hash = agreement.hash
    return {"identity": identity.model_dump(mode="json"), "operatingAgreement": agreement.model_dump(mode="json")}


@app.post("/observations/cycle")
async def submit_observation_and_run_cycle(observation: Observation) -> dict:
    state = NotaryState(privacy_mode=observation.privacy_mode, observations=[observation])
    result = await run_notary_cycle(state)
    return result.model_dump(mode="json")


@app.post("/media/transcribe")
async def transcribe_media(file: UploadFile, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED) -> dict:
    settings = get_settings()
    upload_dir = Path("media/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    file_path.write_bytes(await file.read())

    evidence = MediaEvidence(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        privacy_mode=privacy_mode,
    )
    speedmatic = SpeedmaticClient(
        api_base_url=settings.speedmatic_api_base_url,
        api_key=settings.speedmatic_api_key,
        demo_mode=settings.speedmatic_demo_mode,
    )
    job = await speedmatic.transcribe_file(file_path, evidence.evidence_id, privacy_mode)
    observation = speedmatic.transcript_to_observation(job, privacy_mode)
    return {
        "evidence": evidence.model_dump(mode="json"),
        "transcription": job.model_dump(mode="json"),
        "observation": observation.model_dump(mode="json"),
    }


@app.post("/media/attest")
async def attest_transcript(transcript_text: str, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED) -> dict:
    observation = Observation(
        source=EvidenceSource(kind="manual_transcript"),
        summary=transcript_text[:240],
        raw_text=transcript_text,
        privacy_mode=privacy_mode,
        confidence=0.78,
    )
    state = await run_notary_cycle(NotaryState(privacy_mode=privacy_mode, observations=[observation]))
    return state.model_dump(mode="json")


@app.post("/qevorpay/payment-link")
async def create_payment_link(request: QevorpayPaymentLinkRequest) -> dict:
    settings = get_settings()
    client = QevorpayClient(
        api_base_url=settings.qevorpay_api_base_url,
        api_key=settings.qevorpay_api_key,
        demo_mode=settings.qevorpay_demo_mode,
    )
    return await client.create_payment_link(request)

