from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from notary.models.schemas import Observation


class ScannerOutput(BaseModel):
    summary: str
    confidence: float = Field(ge=0, le=1)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    obligations: list[dict[str, Any]] = Field(default_factory=list)
    rationale_steps: list[str] = Field(default_factory=list)
    conclusion: str


class SentinelOutput(BaseModel):
    source_quality: float = Field(ge=0, le=1)
    spoofing_risk: float = Field(ge=0, le=1)
    privacy_risk: float = Field(ge=0, le=1)
    safety_flags: list[str] = Field(default_factory=list)
    approved: bool
    notes: str


class RiskOutput(BaseModel):
    approved: bool
    confidence_threshold: float = Field(ge=0, le=1)
    payment_authorized: bool
    trade_authorized: bool
    public_post_authorized: bool
    dispute_window_seconds: int = Field(ge=0)
    max_payment_usdc: float | None = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list)


class StrategyOutput(BaseModel):
    attestation_statement: str
    prediction_question: str
    prediction_probability: float = Field(ge=0, le=1)
    payment_condition: str
    payment_action: str
    rationale_steps: list[str] = Field(default_factory=list)
    conclusion: str


class ReflectorOutput(BaseModel):
    delta: float
    updated_score: float = Field(ge=0, le=1)
    accuracy: float = Field(ge=0, le=1)
    safety: float = Field(ge=0, le=1)
    payment_reliability: float = Field(ge=0, le=1)
    privacy_score: float = Field(ge=0, le=1)
    dispute_rate: float = Field(ge=0, le=1)
    arbitrage_pnl_usdc: float
    critique: str
    policy_updates: list[str] = Field(default_factory=list)


T = TypeVar("T", bound=BaseModel)


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("{") and part.endswith("}"):
                stripped = part
                break
            if "\n{" in part:
                candidate = part.split("\n", 1)[1].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    stripped = candidate
                    break
    return json.loads(stripped)


@dataclass(slots=True)
class GroqReasoner:
    api_key: str
    model: str
    api_base_url: str = "https://api.groq.com"

    async def invoke_json(self, *, system: str, user: str, schema: type[T]) -> T:
        import httpx

        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=60) as client:
            response = await client.post(
                "/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return schema.model_validate(_extract_json_object(content))


@dataclass(slots=True)
class AnthropicReasoner:
    api_key: str
    model: str
    api_base_url: str = "https://api.anthropic.com"

    async def invoke_json(self, *, system: str, user: str, schema: type[T]) -> T:
        import httpx

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
                    "max_tokens": 1200,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            response.raise_for_status()
        body = response.json()
        parts = body.get("content", [])
        text = "".join(part.get("text", "") for part in parts if part.get("type") == "text")
        return schema.model_validate(_extract_json_object(text))


@dataclass(slots=True)
class SwarmReasoningEngine:
    groq: GroqReasoner | None = None
    reflector: AnthropicReasoner | None = None

    @property
    def enabled(self) -> bool:
        return self.groq is not None and self.reflector is not None

    async def scan(self, observation: Observation) -> ScannerOutput:
        assert self.groq is not None
        return await self.groq.invoke_json(
            system=(
                "You are NOTARY Signal Scanner. Read evidence and extract only grounded claims and payment obligations. "
                "Return strict JSON only."
            ),
            user=(
                f"Observation summary: {observation.summary}\n"
                f"Observation text: {observation.raw_text or ''}\n"
                f"Privacy mode: {observation.privacy_mode.value}\n"
                "Return JSON with keys summary, confidence, claims, obligations, rationale_steps, conclusion."
            ),
            schema=ScannerOutput,
        )

    async def sentinel(self, observation: Observation) -> SentinelOutput:
        assert self.groq is not None
        return await self.groq.invoke_json(
            system=(
                "You are NOTARY Guardian Sentinel. Assess source integrity, spoofing risk, privacy leakage risk, "
                "and whether the evidence should proceed. Return strict JSON only."
            ),
            user=(
                f"Observation summary: {observation.summary}\n"
                f"Observation text: {observation.raw_text or ''}\n"
                f"Observation metadata: {json.dumps(observation.metadata, default=str)}\n"
                "Return JSON with keys source_quality, spoofing_risk, privacy_risk, safety_flags, approved, notes."
            ),
            schema=SentinelOutput,
        )

    async def risk(self, observation: Observation, integrity_report: dict[str, Any]) -> RiskOutput:
        assert self.groq is not None
        return await self.groq.invoke_json(
            system=(
                "You are NOTARY Risk Guardian. Decide whether to authorize attestation, payment release, public posting, "
                "and trading. Be conservative. Return strict JSON only."
            ),
            user=(
                f"Observation: {json.dumps(observation.model_dump(mode='json'), default=str)}\n"
                f"Integrity report: {json.dumps(integrity_report, default=str)}\n"
                "Return JSON with keys approved, confidence_threshold, payment_authorized, trade_authorized, "
                "public_post_authorized, dispute_window_seconds, max_payment_usdc, reasons."
            ),
            schema=RiskOutput,
        )

    async def strategy(self, state_snapshot: dict[str, Any]) -> StrategyOutput:
        assert self.groq is not None
        return await self.groq.invoke_json(
            system=(
                "You are NOTARY Strategy Engine. Convert approved decisions into a concrete attestation statement, "
                "payment condition, and prediction framing. Return strict JSON only."
            ),
            user=(
                f"State snapshot: {json.dumps(state_snapshot, default=str)}\n"
                "Return JSON with keys attestation_statement, prediction_question, prediction_probability, "
                "payment_condition, payment_action, rationale_steps, conclusion."
            ),
            schema=StrategyOutput,
        )

    async def reflect(self, state_snapshot: dict[str, Any], previous_score: float) -> ReflectorOutput:
        assert self.reflector is not None
        return await self.reflector.invoke_json(
            system=(
                "You are NOTARY Reflector. Critique the cycle, update karma metrics conservatively, and propose "
                "policy updates. Return strict JSON only."
            ),
            user=(
                f"Previous karma score: {previous_score}\n"
                f"Cycle state: {json.dumps(state_snapshot, default=str)}\n"
                "Return JSON with keys delta, updated_score, accuracy, safety, payment_reliability, privacy_score, "
                "dispute_rate, arbitrage_pnl_usdc, critique, policy_updates."
            ),
            schema=ReflectorOutput,
        )
