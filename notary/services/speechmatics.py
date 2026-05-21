from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import (
    EvidenceSource,
    Observation,
    PrivacyMode,
    TranscriptSegment,
    TranscriptionJob,
    utc_now,
)


SPEECHMATICS_DEFAULT_BASE_URL = "https://asr.api.speechmatics.com/v2"


@dataclass(slots=True)
class SpeechmaticsClient:
    api_base_url: str | None = SPEECHMATICS_DEFAULT_BASE_URL
    api_key: str | None = None
    demo_mode: bool = True
    transcriptions_path: str | None = "/jobs"
    transcription_status_path_template: str | None = "/jobs/{job_id}"
    transcript_path_template: str | None = "/jobs/{job_id}/transcript?format=json-v2"
    language: str = "en"
    operating_point: str = "enhanced"
    diarization: str = "speaker"

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
                provider="speechmatics",
            )

        job = await self.submit_transcription(file_path, evidence_id=evidence_id)
        if job.status in {"queued", "processing"}:
            job = await self.poll_transcription(job.job_id, evidence_id=evidence_id)
        return job

    async def submit_transcription(self, file_path: Path, *, evidence_id: str) -> TranscriptionJob:
        try:
            import httpx
        except ModuleNotFoundError:
            return TranscriptionJob(
                evidence_id=evidence_id,
                status="failed",
                provider="speechmatics",
                metadata={
                    "error": "httpx is required for live Speechmatics transcription. Run pip install -e .",
                },
            )

        config = {
            "type": "transcription",
            "transcription_config": {
                "language": self.language,
                "operating_point": self.operating_point,
                "diarization": self.diarization,
            },
        }
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=120) as client:
            with file_path.open("rb") as media:
                response = await client.post(
                    self._required_path(self.transcriptions_path, "SPEECHMATICS_TRANSCRIPTIONS_PATH"),
                    headers=self._headers(),
                    data={"config": json.dumps(config)},
                    files={"data_file": (file_path.name, media)},
                )
            response.raise_for_status()
            payload = response.json()
        return self._normalize_job(payload, evidence_id=evidence_id)

    async def poll_transcription(self, job_id: str, *, evidence_id: str) -> TranscriptionJob:
        try:
            import httpx
        except ModuleNotFoundError:
            return TranscriptionJob(
                job_id=job_id,
                evidence_id=evidence_id,
                status="failed",
                provider="speechmatics",
                metadata={
                    "error": "httpx is required for live Speechmatics transcription. Run pip install -e .",
                },
            )

        status_template = self._required_path(
            self.transcription_status_path_template,
            "SPEECHMATICS_TRANSCRIPTION_STATUS_PATH_TEMPLATE",
        )
        last_job = TranscriptionJob(
            job_id=job_id,
            evidence_id=evidence_id,
            status="processing",
            provider="speechmatics",
        )
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=60) as client:
            for _ in range(60):
                response = await client.get(status_template.format(job_id=job_id), headers=self._headers())
                response.raise_for_status()
                last_job = self._normalize_job(response.json(), evidence_id=evidence_id, job_id=job_id)
                if last_job.status == "succeeded":
                    transcript = await self.fetch_transcript(client, job_id=job_id, evidence_id=evidence_id)
                    return transcript
                if last_job.status == "failed":
                    return last_job
                await asyncio.sleep(2)
        return last_job

    async def fetch_transcript(
        self, client: Any, *, job_id: str, evidence_id: str
    ) -> TranscriptionJob:
        template = self._required_path(
            self.transcript_path_template,
            "SPEECHMATICS_TRANSCRIPT_PATH_TEMPLATE",
        )
        response = await client.get(template.format(job_id=job_id), headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        text, segments = self._extract_transcript(payload)
        return TranscriptionJob(
            job_id=job_id,
            evidence_id=evidence_id,
            status="succeeded",
            transcript_text=text,
            segments=segments,
            provider="speechmatics",
            completed_at=utc_now(),
            metadata={"raw": payload},
        )

    def transcript_to_observation(
        self, job: TranscriptionJob, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    ) -> Observation:
        text = job.transcript_text or ""
        return Observation(
            source=EvidenceSource(
                kind="speechmatics_transcript",
                uri=f"speechmatics://{job.job_id}",
                metadata={"provider": job.provider, "jobStatus": job.status},
            ),
            summary=text[:240] or "Speechmatics transcript observation",
            raw_text=text,
            privacy_mode=privacy_mode,
            confidence=0.82 if text else 0.2,
            metadata={"transcriptionJobId": job.job_id, "evidenceId": job.evidence_id},
        )

    def _normalize_job(
        self, payload: dict[str, Any], *, evidence_id: str, job_id: str | None = None
    ) -> TranscriptionJob:
        payload_job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
        raw_status = str(payload_job.get("status") or payload_job.get("state") or "processing").lower()
        status_map = {
            "running": "processing",
            "done": "succeeded",
            "completed": "succeeded",
            "success": "succeeded",
            "rejected": "failed",
            "error": "failed",
        }
        status = status_map.get(raw_status, raw_status)
        if status not in {"queued", "processing", "succeeded", "failed"}:
            status = "processing"
        return TranscriptionJob(
            job_id=str(
                payload_job.get("id")
                or payload_job.get("job_id")
                or payload.get("id")
                or payload.get("job_id")
                or job_id
                or evidence_id
            ),
            evidence_id=evidence_id,
            status=status,  # type: ignore[arg-type]
            transcript_text=payload.get("transcript_text") or payload.get("text"),
            segments=[],
            provider="speechmatics",
            completed_at=utc_now() if status == "succeeded" else None,
            metadata={"raw": payload},
        )

    def _extract_transcript(self, payload: dict[str, Any]) -> tuple[str, list[TranscriptSegment]]:
        if isinstance(payload.get("transcript"), str):
            return payload["transcript"], []
        results = payload.get("results") or []
        words: list[str] = []
        segments: list[TranscriptSegment] = []
        for item in results:
            alternatives = item.get("alternatives") or []
            content = alternatives[0].get("content") if alternatives else item.get("content")
            if not content:
                continue
            if item.get("type") == "punctuation" and words:
                words[-1] = f"{words[-1]}{content}"
            else:
                words.append(str(content))
            speaker = alternatives[0].get("speaker") if alternatives else item.get("speaker")
            segments.append(
                TranscriptSegment(
                    speaker=speaker,
                    start_seconds=item.get("start_time"),
                    end_seconds=item.get("end_time"),
                    text=str(content),
                )
            )
        return " ".join(words), segments

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("SPEECHMATICS_API_KEY is required in live mode")
        return {"Authorization": f"Bearer {self.api_key}"}

    def _base_url(self) -> str:
        if not self.api_base_url:
            raise RuntimeError("SPEECHMATICS_API_BASE_URL is required in live mode")
        return self.api_base_url

    def _required_path(self, value: str | None, env_name: str) -> str:
        if not value:
            raise RuntimeError(f"{env_name} is required in live mode")
        return value


SpeedmaticClient = SpeechmaticsClient
