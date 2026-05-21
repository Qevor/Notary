from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import (
    EvidenceSource,
    Observation,
    PrivacyMode,
    TranscriptSegment,
    TranscriptionJob,
    utc_now,
)


@dataclass(slots=True)
class SpeedmaticClient:
    api_base_url: str | None = None
    api_key: str | None = None
    demo_mode: bool = True
    transcriptions_path: str | None = None
    transcription_status_path_template: str | None = None

    async def transcribe_file(self, file_path: Path, evidence_id: str, privacy_mode: PrivacyMode) -> TranscriptionJob:
        if self.demo_mode:
            text = (
                "Client: The final design is approved and the work is complete. "
                "Please release the payment to Daniel today."
            )
            return TranscriptionJob(
                evidence_id=evidence_id,
                status="succeeded",
                transcript_text=text,
                segments=[
                    TranscriptSegment(
                        speaker="Client",
                        start_seconds=0,
                        end_seconds=7.5,
                        text=text,
                    )
                ],
                completed_at=utc_now(),
                metadata={"fileHash": sha256_hex(file_path.name), "privacyMode": privacy_mode.value},
            )

        path = self._required_path(self.transcriptions_path, "SPEEDMATIC_TRANSCRIPTIONS_PATH")
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=60) as client:
            with file_path.open("rb") as media:
                response = await client.post(
                    path,
                    files={"file": (file_path.name, media)},
                    headers=self._headers(),
                    data={"evidence_id": evidence_id, "privacy_mode": privacy_mode.value},
                )
            response.raise_for_status()
            body = response.json()

        job = self._normalize_job(body, evidence_id=evidence_id)
        if job.status in {"queued", "processing"} and self.transcription_status_path_template:
            job = await self.poll_transcription(job.job_id, evidence_id=evidence_id)
        return job

    async def poll_transcription(self, job_id: str, *, evidence_id: str) -> TranscriptionJob:
        template = self._required_path(
            self.transcription_status_path_template,
            "SPEEDMATIC_TRANSCRIPTION_STATUS_PATH_TEMPLATE",
        )
        last_job = TranscriptionJob(job_id=job_id, evidence_id=evidence_id, status="processing")
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=60) as client:
            for _ in range(30):
                response = await client.get(template.format(job_id=job_id), headers=self._headers())
                response.raise_for_status()
                last_job = self._normalize_job(response.json(), evidence_id=evidence_id, job_id=job_id)
                if last_job.status in {"succeeded", "failed"}:
                    return last_job
                await asyncio.sleep(2)
        return last_job

    def transcript_to_observation(self, job: TranscriptionJob, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED) -> Observation:
        text = job.transcript_text or ""
        return Observation(
            source=EvidenceSource(
                kind="speedmatic_transcript",
                uri=f"speedmatic://{job.job_id}",
                metadata={"provider": job.provider, "jobStatus": job.status},
            ),
            summary=text[:240] or "Speedmatic transcript observation",
            raw_text=text,
            privacy_mode=privacy_mode,
            confidence=0.82 if text else 0.2,
            metadata={"transcriptionJobId": job.job_id, "evidenceId": job.evidence_id},
        )

    def _normalize_job(self, payload: dict[str, Any], *, evidence_id: str, job_id: str | None = None) -> TranscriptionJob:
        transcript_text = (
            payload.get("transcript_text")
            or payload.get("transcript")
            or payload.get("text")
            or payload.get("result", {}).get("text")
        )
        segments_payload = payload.get("segments") or payload.get("result", {}).get("segments") or []
        segments = [TranscriptSegment.model_validate(segment) for segment in segments_payload]
        status = str(payload.get("status") or payload.get("state") or "processing").lower()
        if status not in {"queued", "processing", "succeeded", "failed"}:
            status = "succeeded" if transcript_text else "processing"
        return TranscriptionJob(
            job_id=str(payload.get("job_id") or payload.get("id") or job_id or payload.get("request_id") or evidence_id),
            evidence_id=evidence_id,
            status=status,  # type: ignore[arg-type]
            transcript_text=transcript_text,
            segments=segments,
            provider="speedmatic",
            completed_at=utc_now() if status == "succeeded" else None,
            metadata={"raw": payload},
        )

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("SPEEDMATIC_API_KEY is required in live mode")
        return {"Authorization": f"Bearer {self.api_key}"}

    def _base_url(self) -> str:
        if not self.api_base_url:
            raise RuntimeError("SPEEDMATIC_API_BASE_URL is required in live mode")
        return self.api_base_url

    def _required_path(self, value: str | None, env_name: str) -> str:
        if not value:
            raise RuntimeError(f"{env_name} is required in live mode because Speedmatic endpoint contracts are provider-specific")
        return value
