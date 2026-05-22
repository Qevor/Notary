from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


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
    RELEASE_PARTIAL = "release_partial"
    HOLD = "hold"
    BATCH_DISTRIBUTE = "batch_distribute"
    REFUND = "refund"


class PartyType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"


class VerdictOutcome(str, Enum):
    FULL_RELEASE = "full_release"
    PARTIAL_RELEASE = "partial_release"
    HOLD_PENDING_CLARIFICATION = "hold_pending_clarification"
    REFUSE_REFUND = "refuse_refund"


class DisputeOutcome(str, Enum):
    UPHELD = "upheld"
    REVISED = "revised"


class CorrectivePaymentAction(str, Enum):
    NONE = "none"
    TOP_UP_RELEASE = "top_up_release"
    PARTIAL_CLAWBACK_REQUEST = "partial_clawback_request"
    REFUND = "refund"


class EvidenceSource(BaseModel):
    source_id: str = Field(default_factory=lambda: new_id("src"))
    kind: str
    uri: str | None = None
    submitted_by: str | None = None
    captured_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Obligation(BaseModel):
    obligation_id: str = Field(default_factory=lambda: new_id("obl"))
    raw_instruction: str
    payer_identity: str | None = None
    payee_identity: str | None = None
    approver_identity: str | None = None
    deliverable: str | None = None
    acceptance_criterion: str | None = None
    authorized_approver: str | None = None
    deadline: str | None = None
    satisfying_evidence: list[str] = Field(default_factory=list)
    amount_usdc: float | None = Field(default=None, ge=0)
    payer_type: PartyType = PartyType.HUMAN
    payee_type: PartyType = PartyType.HUMAN
    approver_type: PartyType = PartyType.HUMAN
    clarification_needed: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.5, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    type: str
    ref: str | None = None
    text: str | None = None
    commitment_hash: str
    encrypted_blob_ref: str | None = None
    submitter_identity: str
    submitter_type: PartyType = PartyType.HUMAN
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    submitted_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WitnessIntakeRequest(BaseModel):
    instruction: str
    evidence_text: str | None = None
    evidence_ref: str | None = None
    evidence_type: str = "text"
    payer_identity: str | None = None
    payee_identity: str | None = None
    approver_identity: str | None = None
    payer_type: PartyType = PartyType.HUMAN
    payee_type: PartyType = PartyType.HUMAN
    approver_type: PartyType = PartyType.HUMAN
    submitter_identity: str = "unknown_submitter"
    submitter_type: PartyType = PartyType.HUMAN
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    amount_usdc: float | None = Field(default=None, ge=0)
    batch_recipients: list[dict[str, Any]] = Field(default_factory=list)
    notary_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WitnessVerdict(BaseModel):
    verdict_id: str = Field(default_factory=lambda: new_id("verdict"))
    obligation_id: str
    outcome: VerdictOutcome
    release_pct: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    confidence_gate: Literal[
        "release",
        "release_with_dispute_window",
        "request_more_evidence",
    ] = "request_more_evidence"
    dispute_window_open: bool = False
    deficiency: str | None = None
    reasoning_trace: str
    precedent_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class WitnessAttestation(BaseModel):
    attestation_id: str = Field(default_factory=lambda: new_id("watt"))
    obligation_id: str
    verdict_id: str
    evidence_commitment_hash: str
    reasoning_trace_hash: str
    verdict_hash: str
    signer: str | None = None
    signature: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    dispute_state: Literal["none", "open", "upheld", "revised"] = "none"
    privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    party_identities: dict[str, str | None] = Field(default_factory=dict)
    party_types: dict[str, PartyType] = Field(default_factory=dict)
    supersedes_ref: str | None = None
    revises_ref: str | None = None
    arc_tx_hash: str | None = None


class Ruling(BaseModel):
    ruling_id: str = Field(default_factory=lambda: new_id("ruling"))
    notary_id: str
    obligation: Obligation
    evidence: list[Evidence] = Field(default_factory=list)
    integrity_report: "IntegrityReport | None" = None
    verdict: WitnessVerdict
    attestation: WitnessAttestation
    payment_instruction: "PaymentInstruction | None" = None
    payment_receipt: dict[str, Any] | None = None
    disputed: bool = False
    reversed: bool = False
    final_settled_outcome: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Dispute(BaseModel):
    dispute_id: str = Field(default_factory=lambda: new_id("disp"))
    original_ruling_id: str
    original_attestation_ref: str
    counter_evidence: list[Evidence] = Field(default_factory=list)
    outcome: DisputeOutcome
    justification: str
    linked_attestation: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Reversal(BaseModel):
    reversal_id: str = Field(default_factory=lambda: new_id("rev"))
    original_attestation_ref: str
    new_attestation_ref: str
    original_ruling_id: str
    new_ruling_id: str
    what_changed: str
    corrective_payment_action: CorrectivePaymentAction
    outstanding_delta: float = 0
    created_at: datetime = Field(default_factory=utc_now)


class PartyOperatingHistory(BaseModel):
    party_identity: str
    party_type: PartyType
    rulings: list[str] = Field(default_factory=list)
    dispute_flags: list[str] = Field(default_factory=list)
    reversal_flags: list[str] = Field(default_factory=list)


class PaymentInstruction(BaseModel):
    instruction_id: str = Field(default_factory=lambda: new_id("payins"))
    action: PaymentAction
    amount_usdc: float | None = Field(default=None, ge=0)
    release_pct: float = Field(default=0, ge=0, le=100)
    payer_identity: str | None = None
    payee_identity: str | None = None
    recipients: list[dict[str, Any]] = Field(default_factory=list)
    attestation_id: str | None = None
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotaryCase(BaseModel):
    case_id: str = Field(default_factory=lambda: new_id("case"))
    created_by_identity: str
    created_by_type: PartyType = PartyType.HUMAN
    payer_identity: str
    payee_identity: str
    approver_identity: str | None = None
    payer_type: PartyType = PartyType.HUMAN
    payee_type: PartyType = PartyType.HUMAN
    approver_type: PartyType = PartyType.HUMAN
    instruction: str
    amount_usdc: float = Field(gt=0)
    qevor_payment_reference: str | None = None
    qevor_payment_url: str | None = None
    qevor_provider: str | None = None
    evidence_invite_token_hash: str
    status: Literal[
        "awaiting_evidence",
        "under_review",
        "released",
        "held",
        "refunded",
        "revised",
        "failed",
    ] = "awaiting_evidence"
    latest_ruling_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutcomeConfirmation(BaseModel):
    confirmation_id: str = Field(default_factory=lambda: new_id("confirm"))
    ruling_id: str
    party_identity: str
    party_type: PartyType = PartyType.HUMAN
    outcome: Literal["confirmed", "contested", "settled_outside_notary"]
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


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
    metadata: dict[str, Any] = Field(default_factory=dict)


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


class OperatingAgreement(BaseModel):
    agreement_id: str = Field(default_factory=lambda: new_id("oa"))
    notary_id: str
    legal_framework: str = "Wyoming DAO LLC / Bayern mechanism inspired"
    algorithmic_manager: str = "NOTARY witness pipeline"
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
    privacy_policy_hash: str | None = None
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


class ArcTransactionPayload(BaseModel):
    contract_name: str
    method: str
    args: list[Any] = Field(default_factory=list)
    value: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
