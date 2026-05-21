from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class PrivacyMode(str, Enum):
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"


class DisclosureLevel(str, Enum):
    PUBLIC = "public"
    COUNTERPARTY = "counterparty"
    ARBITRATOR = "arbitrator"
    INTERNAL = "internal"
    PAY_TO_PEEK = "pay_to_peek"


class AttestationStatus(str, Enum):
    DRAFT = "draft"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    DISPUTED = "disputed"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class PaymentAction(str, Enum):
    CREATE_LINK = "create_link"
    RELEASE_ESCROW = "release_escrow"
    BATCH_DISTRIBUTE = "batch_distribute"
    REFUND = "refund"
    SETTLE_MICRO_SHARES = "settle_micro_shares"


class EvidenceSource(BaseModel):
    source_id: str = Field(default_factory=lambda: new_id("src"))
    kind: str
    uri: str | None = None
    submitted_by: str | None = None
    captured_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("media"))
    filename: str
    content_type: str
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    raw_sha256: str | None = None
    encrypted_uri: str | None = None
    transcript_id: str | None = None
    uploaded_at: datetime = Field(default_factory=utc_now)


class TranscriptSegment(BaseModel):
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    text: str


class TranscriptionJob(BaseModel):
    job_id: str = Field(default_factory=lambda: new_id("txjob"))
    evidence_id: str
    status: Literal["queued", "processing", "succeeded", "failed"] = "queued"
    transcript_text: str | None = None
    segments: list[TranscriptSegment] = Field(default_factory=list)
    provider: str = "speechmatics"
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpeakerClaim(BaseModel):
    speaker: str | None = None
    claim: str
    confidence: float = Field(ge=0, le=1)
    segment_refs: list[int] = Field(default_factory=list)


class ObligationDetected(BaseModel):
    obligor: str | None = None
    obligee: str | None = None
    action: str
    amount_usdc: float | None = Field(default=None, ge=0)
    deadline: datetime | None = None
    acceptance_language: str | None = None
    confidence: float = Field(ge=0, le=1)


class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: new_id("obs"))
    source: EvidenceSource
    summary: str
    raw_text: str | None = None
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    claims: list[SpeakerClaim] = Field(default_factory=list)
    obligations: list[ObligationDetected] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    observed_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: new_id("trace"))
    agent_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    conclusion: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class IntegrityReport(BaseModel):
    report_id: str = Field(default_factory=lambda: new_id("integrity"))
    observation_id: str
    source_quality: float = Field(ge=0, le=1)
    spoofing_risk: float = Field(ge=0, le=1)
    privacy_risk: float = Field(ge=0, le=1)
    safety_flags: list[str] = Field(default_factory=list)
    approved: bool
    notes: str


class RiskDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: new_id("risk"))
    approved: bool
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)
    payment_authorized: bool = False
    trade_authorized: bool = False
    public_post_authorized: bool = False
    dispute_window_seconds: int = 86_400
    max_payment_usdc: float | None = Field(default=None, ge=0)
    max_trade_usdc: float | None = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list)


class Attestation(BaseModel):
    attestation_id: str = Field(default_factory=lambda: new_id("att"))
    observation_id: str
    statement: str
    evidence_hash: str | None = None
    reasoning_trace_hash: str | None = None
    confidence: float = Field(ge=0, le=1)
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    disclosure_policy_hash: str | None = None
    signer: str | None = None
    signature: str | None = None
    status: AttestationStatus = AttestationStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)


class Prediction(BaseModel):
    prediction_id: str = Field(default_factory=lambda: new_id("pred"))
    question: str
    probability: float = Field(ge=0, le=1)
    horizon: datetime
    rationale: str
    counterarguments: list[str] = Field(default_factory=list)
    resolution_source: str | None = None
    reasoning_trace_hash: str | None = None
    signature: str | None = None
    resolved: bool = False
    outcome: bool | None = None

    @field_validator("horizon")
    @classmethod
    def horizon_must_be_futureish(cls, value: datetime) -> datetime:
        if value < utc_now() - timedelta(minutes=5):
            raise ValueError("prediction horizon is in the past")
        return value


class PaymentTrigger(BaseModel):
    trigger_id: str = Field(default_factory=lambda: new_id("paytrg"))
    action: PaymentAction
    amount_usdc: float | None = Field(default=None, ge=0)
    recipient: str | None = None
    condition: str
    attestation_id: str | None = None
    qevorpay_reference: str | None = None
    authorized: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class QevorpayPaymentLinkRequest(BaseModel):
    amount_usdc: float = Field(gt=0)
    description: str
    recipient: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QevorpayBatchDistributionRequest(BaseModel):
    batch_id: str = Field(default_factory=lambda: new_id("batch"))
    recipients: list[dict[str, Any]]
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MicroShare(BaseModel):
    share_id: str = Field(default_factory=lambda: new_id("share"))
    notary_id: str
    buyer: str
    target_kind: Literal["prediction", "attestation", "trace", "treasury"]
    target_id: str | None = None
    amount_usdc: float = Field(gt=0)
    price_usdc: float = Field(gt=0)
    created_at: datetime = Field(default_factory=utc_now)


class KarmaCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("karma"))
    notary_id: str
    accuracy: float = Field(default=0.5, ge=0, le=1)
    safety: float = Field(default=1.0, ge=0, le=1)
    payment_reliability: float = Field(default=1.0, ge=0, le=1)
    privacy_score: float = Field(default=1.0, ge=0, le=1)
    dispute_rate: float = Field(default=0.0, ge=0, le=1)
    arbitrage_pnl_usdc: float = 0.0
    score: float = Field(default=0.5, ge=0, le=1)
    signature: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class OperatingAgreement(BaseModel):
    agreement_id: str = Field(default_factory=lambda: new_id("oa"))
    notary_id: str
    legal_framework: str = "Wyoming DAO LLC / Bayern mechanism inspired"
    algorithmic_manager: str = "NOTARY 6-agent swarm"
    permitted_actions: list[str] = Field(default_factory=list)
    treasury_constraints: dict[str, Any] = Field(default_factory=dict)
    privacy_rules: dict[str, Any] = Field(default_factory=dict)
    dispute_rules: dict[str, Any] = Field(default_factory=dict)
    document_uri: str | None = None
    hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceAccessGrant(BaseModel):
    grant_id: str = Field(default_factory=lambda: new_id("grant"))
    evidence_id: str
    grantee: str
    disclosure_level: DisclosureLevel
    purpose: str
    expires_at: datetime | None = None
    revocable: bool = True
    signature: str | None = None


class NotaryIdentity(BaseModel):
    notary_id: str = Field(default_factory=lambda: new_id("notary"))
    agent_wallet: str | None = None
    treasury_address: str | None = None
    endpoint: HttpUrl | None = None
    capabilities: list[str] = Field(default_factory=list)
    operating_agreement_hash: str | None = None
    policy_dna_hash: str | None = None
    privacy_policy_hash: str | None = None
    parent_notary_id: str | None = None
    status: Literal["active", "paused", "retired"] = "active"
    created_at: datetime = Field(default_factory=utc_now)


class ValidationRecord(BaseModel):
    validation_id: str = Field(default_factory=lambda: new_id("val"))
    notary_id: str
    kind: str
    subject_id: str
    hash: str
    validator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ArbitrageOpportunity(BaseModel):
    opportunity_id: str = Field(default_factory=lambda: new_id("arb"))
    route: str
    expected_profit_usdc: float
    max_loss_usdc: float
    confidence: float = Field(ge=0, le=1)
    slippage_bps: int = Field(ge=0)
    approved: bool = False


class ArcTransactionPayload(BaseModel):
    contract_name: str
    method: str
    args: list[Any] = Field(default_factory=list)
    value: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    agent_name: str
    approved: bool
    summary: str
    trace: ReasoningTrace
    payload: dict[str, Any] = Field(default_factory=dict)


class NotaryState(BaseModel):
    notary_id: str = Field(default_factory=lambda: new_id("notary"))
    cycle_id: str = Field(default_factory=lambda: new_id("cycle"))
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    observations: list[Observation] = Field(default_factory=list)
    integrity_reports: list[IntegrityReport] = Field(default_factory=list)
    risk_decisions: list[RiskDecision] = Field(default_factory=list)
    attestations: list[Attestation] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    payment_triggers: list[PaymentTrigger] = Field(default_factory=list)
    arbitrage_opportunities: list[ArbitrageOpportunity] = Field(default_factory=list)
    traces: list[ReasoningTrace] = Field(default_factory=list)
    karma: KarmaCheckpoint | None = None
    arc_payloads: list[ArcTransactionPayload] = Field(default_factory=list)
    should_continue: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
