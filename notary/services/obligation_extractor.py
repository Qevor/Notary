from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from notary.models.schemas import Obligation, PartyType, WitnessIntakeRequest


class ExtractedObligation(BaseModel):
    payer_identity: str | None = None
    payee_identity: str | None = None
    approver_identity: str | None = None
    deliverable: str | None = None
    acceptance_criterion: str | None = None
    authorized_approver: str | None = None
    deadline: str | None = None
    satisfying_evidence: list[str] = Field(default_factory=list)
    amount_usdc: float | None = Field(default=None, ge=0)
    clarification_needed: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.5, ge=0, le=1)


_OBLIGATION_SYSTEM = (
    "You are NOTARY Intake. Extract a precise payment obligation from an instruction. "
    "Do not guess missing commercial terms. If payer, payee, deliverable, acceptance criterion, "
    "authorized approver, amount, deadline, or satisfying evidence is ambiguous, set "
    "clarification_needed=true and include concise clarification_questions. "
    "Return a single raw JSON object only — no prose, no markdown, no code fences."
)


def _json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        parts = [part.strip() for part in stripped.split("```")]
        candidates = [part for part in parts if part.startswith("{") and part.endswith("}")]
        if candidates:
            stripped = candidates[0]
    return json.loads(stripped)


@dataclass(slots=True)
class GroqObligationExtractor:
    api_key: str
    model: str
    api_base_url: str = "https://api.groq.com"

    async def extract(self, request: WitnessIntakeRequest) -> Obligation:
        import httpx

        system = _OBLIGATION_SYSTEM
        user = {
            "instruction": request.instruction,
            "evidence_text": request.evidence_text,
            "provided_parties": {
                "payer_identity": request.payer_identity,
                "payee_identity": request.payee_identity,
                "approver_identity": request.approver_identity,
                "payer_type": request.payer_type.value,
                "payee_type": request.payee_type.value,
                "approver_type": request.approver_type.value,
            },
            "provided_amount_usdc": request.amount_usdc,
            "required_json_keys": [
                "payer_identity",
                "payee_identity",
                "approver_identity",
                "deliverable",
                "acceptance_criterion",
                "authorized_approver",
                "deadline",
                "satisfying_evidence",
                "amount_usdc",
                "clarification_needed",
                "clarification_questions",
                "extraction_confidence",
            ],
        }
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=60) as client:
            response = await client.post(
                "/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(user, default=str)},
                    ],
                },
            )
            response.raise_for_status()
        body = response.json()
        extracted = ExtractedObligation.model_validate(
            _json_object(body["choices"][0]["message"]["content"])
        )
        return _build_obligation(request, extracted)


def _build_obligation(request: WitnessIntakeRequest, extracted: ExtractedObligation) -> Obligation:
    questions = list(extracted.clarification_questions)
    for label, value in {
        "payer identity": request.payer_identity or extracted.payer_identity,
        "payee identity": request.payee_identity or extracted.payee_identity,
        "deliverable": extracted.deliverable,
        "acceptance criterion": extracted.acceptance_criterion,
        "USDC amount": request.amount_usdc if request.amount_usdc is not None else extracted.amount_usdc,
    }.items():
        if value in (None, "", []):
            questions.append(f"Confirm {label}.")
    return Obligation(
        raw_instruction=request.instruction,
        payer_identity=request.payer_identity or extracted.payer_identity,
        payee_identity=request.payee_identity or extracted.payee_identity,
        approver_identity=request.approver_identity or extracted.approver_identity,
        deliverable=extracted.deliverable,
        acceptance_criterion=extracted.acceptance_criterion,
        authorized_approver=extracted.authorized_approver or extracted.approver_identity,
        deadline=extracted.deadline,
        satisfying_evidence=extracted.satisfying_evidence or ["submitted evidence"],
        amount_usdc=request.amount_usdc if request.amount_usdc is not None else extracted.amount_usdc,
        payer_type=PartyType(request.payer_type),
        payee_type=PartyType(request.payee_type),
        approver_type=PartyType(request.approver_type),
        clarification_needed=extracted.clarification_needed or bool(questions),
        clarification_questions=sorted(set(questions)),
        extraction_confidence=extracted.extraction_confidence,
        metadata={"batch_recipients": request.batch_recipients},
    )


@dataclass(slots=True)
class ClaudeObligationExtractor:
    api_key: str
    model: str
    api_base_url: str = "https://api.anthropic.com"

    async def extract(self, request: WitnessIntakeRequest) -> Obligation:
        import httpx

        user_content = json.dumps(
            {
                "instruction": request.instruction,
                "evidence_text": request.evidence_text,
                "provided_parties": {
                    "payer_identity": request.payer_identity,
                    "payee_identity": request.payee_identity,
                    "approver_identity": request.approver_identity,
                    "payer_type": request.payer_type.value,
                    "payee_type": request.payee_type.value,
                    "approver_type": request.approver_type.value,
                },
                "provided_amount_usdc": request.amount_usdc,
                "required_json_keys": [
                    "payer_identity", "payee_identity", "approver_identity",
                    "deliverable", "acceptance_criterion", "authorized_approver",
                    "deadline", "satisfying_evidence", "amount_usdc",
                    "clarification_needed", "clarification_questions", "extraction_confidence",
                ],
            },
            default=str,
        )
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=60) as client:
            response = await client.post(
                "/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": _OBLIGATION_SYSTEM,
                    "messages": [{"role": "user", "content": user_content}],
                },
            )
            response.raise_for_status()
        body = response.json()
        raw_text = body["content"][0]["text"]
        extracted = ExtractedObligation.model_validate(_json_object(raw_text))
        return _build_obligation(request, extracted)
