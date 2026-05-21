from __future__ import annotations

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

    async def transcribe_file(
        self, file_path: Path, evidence_id: str, privacy_mode: PrivacyMode
    ) -> TranscriptionJob:
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
        if not self.api_base_url or not self.api_key:
            raise RuntimeError("Speedmatic credentials are not configured")
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=60) as client:
            with file_path.open("rb") as media:
                response = await client.post(
                    "/transcriptions",
                    files={"file": (file_path.name, media)},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data={"evidence_id": evidence_id},
                )
            response.raise_for_status()
            return TranscriptionJob.model_validate(response.json())

    def transcript_to_observation(
        self, job: TranscriptionJob, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    ) -> Observation:
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

