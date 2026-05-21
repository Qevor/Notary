from __future__ import annotations

from datetime import timedelta
from typing import Any

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - allows schema/tests without langgraph installed
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]

from notary.crypto.eip712 import EIP712Signer
from notary.crypto.hashing import sha256_hex
from notary.models.schemas import (
    ArcTransactionPayload,
    Attestation,
    AttestationStatus,
    IntegrityReport,
    KarmaCheckpoint,
    NotaryState,
    ObligationDetected,
    PaymentAction,
    PaymentTrigger,
    Prediction,
    ReasoningTrace,
    RiskDecision,
    SpeakerClaim,
    utc_now,
)
from notary.services.reasoning import SwarmReasoningEngine


PRIVACY_MODE_TO_INT = {"public": 0, "protected": 1, "private": 2}


def _trace(agent_name: str, conclusion: str, confidence: float, **inputs: Any) -> ReasoningTrace:
    trace = ReasoningTrace(
        agent_name=agent_name,
        inputs=inputs,
        steps=[
            "Normalize structured inputs.",
            "Apply NOTARY operating policy.",
            "Return JSON-compatible decision object.",
        ],
        conclusion=conclusion,
        confidence=confidence,
    )
    trace.hash = sha256_hex(trace.model_dump(mode="json", exclude={"hash"}))
    return trace


def _confidence_bps(value: float) -> int:
    return max(0, min(10_000, round(value * 10_000)))


def _signer_from_state(state: NotaryState) -> EIP712Signer:
    metadata = state.metadata
    return EIP712Signer(
        private_key=metadata.get("validatorPrivateKey"),
        domain_name=metadata.get("validatorDomainName", "NOTARY"),
        domain_version=metadata.get("validatorDomainVersion", "1"),
        chain_id=metadata.get("arcChainId"),
    )


def _verifying_contract(state: NotaryState, contract_name: str) -> str | None:
    contracts = state.metadata.get("verifyingContracts", {})
    if isinstance(contracts, dict):
        return contracts.get(contract_name)
    return None


def signal_scanner(state: NotaryState) -> NotaryState:
    if not state.observations:
        return state

    observation = state.observations[-1]
    lower_text = (observation.raw_text or observation.summary).lower()

    if "approved" in lower_text or "complete" in lower_text or "release" in lower_text:
        observation.claims.append(
            SpeakerClaim(
                speaker="detected_speaker",
                claim="Work appears to have been accepted or completed.",
                confidence=0.82,
            )
        )
        observation.obligations.append(
            ObligationDetected(
                obligor="payer",
                obligee="payee",
                action="release_qevorpay_payment_after_verified_acceptance",
                confidence=0.8,
            )
        )
        observation.confidence = max(observation.confidence, 0.82)

    trace = _trace(
        "Signal Scanner",
        "Detected candidate evidence for attestation and payment review.",
        observation.confidence,
        observation=observation.model_dump(mode="json"),
    )
    state.traces.append(trace)
    return state


async def signal_scanner_live(state: NotaryState, reasoning: SwarmReasoningEngine) -> NotaryState:
    if not state.observations:
        return state
    observation = state.observations[-1]
    output = await reasoning.scan(observation)
    observation.summary = output.summary
    observation.confidence = output.confidence
    observation.claims = [SpeakerClaim.model_validate(item) for item in output.claims]
    observation.obligations = [ObligationDetected.model_validate(item) for item in output.obligations]
    state.traces.append(
        _trace(
            "Signal Scanner",
            output.conclusion,
            output.confidence,
            observation=observation.model_dump(mode="json"),
            steps=output.rationale_steps,
        )
    )
    return state


def guardian_sentinel(state: NotaryState) -> NotaryState:
    observation = state.observations[-1]
    source_quality = 0.78 if observation.raw_text else 0.55
    privacy_risk = 0.2 if observation.privacy_mode.value != "public" else 0.45
    report = IntegrityReport(
        observation_id=observation.observation_id,
        source_quality=source_quality,
        spoofing_risk=0.18,
        privacy_risk=privacy_risk,
        safety_flags=[] if source_quality >= 0.7 else ["low_source_context"],
        approved=source_quality >= 0.6 and privacy_risk <= 0.6,
        notes="Evidence passed demo integrity checks. Real deployment should add media provenance.",
    )
    state.integrity_reports.append(report)
    state.traces.append(
        _trace(
            "Guardian Sentinel",
            "Observation integrity approved." if report.approved else "Observation rejected.",
            source_quality,
            report=report.model_dump(mode="json"),
        )
    )
    return state


async def guardian_sentinel_live(state: NotaryState, reasoning: SwarmReasoningEngine) -> NotaryState:
    observation = state.observations[-1]
    output = await reasoning.sentinel(observation)
    report = IntegrityReport(
        observation_id=observation.observation_id,
        source_quality=output.source_quality,
        spoofing_risk=output.spoofing_risk,
        privacy_risk=output.privacy_risk,
        safety_flags=output.safety_flags,
        approved=output.approved,
        notes=output.notes,
    )
    state.integrity_reports.append(report)
    state.traces.append(
        _trace(
            "Guardian Sentinel",
            "Observation integrity approved." if report.approved else "Observation rejected.",
            output.source_quality,
            report=report.model_dump(mode="json"),
        )
    )
    return state


def risk_guardian(state: NotaryState) -> NotaryState:
    observation = state.observations[-1]
    report = state.integrity_reports[-1]
    approved = report.approved and observation.confidence >= 0.7
    has_obligation = bool(observation.obligations)

    decision = RiskDecision(
        approved=approved,
        confidence_threshold=0.7,
        payment_authorized=approved and has_obligation,
        trade_authorized=False,
        public_post_authorized=approved and observation.privacy_mode.value == "public",
        dispute_window_seconds=86_400,
        max_payment_usdc=1_000 if approved else None,
        reasons=[
            "confidence_threshold_met" if approved else "confidence_threshold_or_integrity_failed",
            "payment_obligation_detected" if has_obligation else "no_payment_obligation_detected",
        ],
    )
    state.risk_decisions.append(decision)
    state.traces.append(
        _trace(
            "Risk Guardian",
            "Authorized Witness-to-Pay flow." if decision.payment_authorized else "Payment blocked.",
            observation.confidence,
            decision=decision.model_dump(mode="json"),
        )
    )
    return state


async def risk_guardian_live(state: NotaryState, reasoning: SwarmReasoningEngine) -> NotaryState:
    observation = state.observations[-1]
    report = state.integrity_reports[-1]
    output = await reasoning.risk(observation, report.model_dump(mode="json"))
    decision = RiskDecision(
        approved=output.approved,
        confidence_threshold=output.confidence_threshold,
        payment_authorized=output.payment_authorized,
        trade_authorized=output.trade_authorized,
        public_post_authorized=output.public_post_authorized,
        dispute_window_seconds=output.dispute_window_seconds,
        max_payment_usdc=output.max_payment_usdc,
        reasons=output.reasons,
    )
    state.risk_decisions.append(decision)
    state.traces.append(
        _trace(
            "Risk Guardian",
            "Authorized Witness-to-Pay flow." if decision.payment_authorized else "Payment blocked.",
            observation.confidence,
            decision=decision.model_dump(mode="json"),
        )
    )
    return state


def strategy_engine(state: NotaryState) -> NotaryState:
    observation = state.observations[-1]
    decision = state.risk_decisions[-1]
    statement = (
        f"NOTARY observed and verified: {observation.summary}"
        if decision.approved
        else f"NOTARY could not verify: {observation.summary}"
    )
    trace = _trace(
        "Strategy Engine",
        "Prepared attestation and Qevorpay trigger." if decision.payment_authorized else "Prepared attestation only.",
        observation.confidence,
        observation_id=observation.observation_id,
    )
    state.traces.append(trace)

    attestation = Attestation(
        observation_id=observation.observation_id,
        statement=statement,
        evidence_hash=sha256_hex(observation.model_dump(mode="json")),
        reasoning_trace_hash=trace.hash,
        confidence=observation.confidence,
        privacy_mode=observation.privacy_mode,
        disclosure_policy_hash=sha256_hex(
            {"privacyMode": observation.privacy_mode.value, "disputeWindow": decision.dispute_window_seconds}
        ),
    )
    state.attestations.append(attestation)

    if decision.payment_authorized:
        state.payment_triggers.append(
            PaymentTrigger(
                action=PaymentAction.RELEASE_ESCROW,
                amount_usdc=decision.max_payment_usdc,
                condition="Verified completion or acceptance detected in evidence.",
                attestation_id=attestation.attestation_id,
                authorized=True,
                metadata={"observationId": observation.observation_id},
            )
        )

    state.predictions.append(
        Prediction(
            question="Will this attestation remain undisputed through the dispute window?",
            probability=0.78 if decision.approved else 0.35,
            horizon=utc_now() + timedelta(days=1),
            rationale="Integrity, confidence, and payment-obligation checks were evaluated by the swarm.",
            counterarguments=["Transcript context may be incomplete.", "Counterparty may dispute intent."],
            resolution_source="Qevorpay dispute status and user feedback",
            reasoning_trace_hash=trace.hash,
        )
    )
    return state


async def strategy_engine_live(state: NotaryState, reasoning: SwarmReasoningEngine) -> NotaryState:
    observation = state.observations[-1]
    decision = state.risk_decisions[-1]
    output = await reasoning.strategy(
        {
            "observation": observation.model_dump(mode="json"),
            "riskDecision": decision.model_dump(mode="json"),
            "integrityReport": state.integrity_reports[-1].model_dump(mode="json"),
        }
    )
    trace = _trace(
        "Strategy Engine",
        output.conclusion,
        observation.confidence,
        observation_id=observation.observation_id,
        steps=output.rationale_steps,
    )
    state.traces.append(trace)

    attestation = Attestation(
        observation_id=observation.observation_id,
        statement=output.attestation_statement,
        evidence_hash=sha256_hex(observation.model_dump(mode="json")),
        reasoning_trace_hash=trace.hash,
        confidence=observation.confidence,
        privacy_mode=observation.privacy_mode,
        disclosure_policy_hash=sha256_hex(
            {"privacyMode": observation.privacy_mode.value, "disputeWindow": decision.dispute_window_seconds}
        ),
    )
    state.attestations.append(attestation)

    if decision.payment_authorized:
        state.payment_triggers.append(
            PaymentTrigger(
                action=PaymentAction(output.payment_action),
                amount_usdc=decision.max_payment_usdc,
                condition=output.payment_condition,
                attestation_id=attestation.attestation_id,
                authorized=True,
                metadata={"observationId": observation.observation_id},
            )
        )

    state.predictions.append(
        Prediction(
            question=output.prediction_question,
            probability=output.prediction_probability,
            horizon=utc_now() + timedelta(days=1),
            rationale="LLM strategy output translated to a structured NOTARY prediction.",
            counterarguments=["Evidence may be incomplete.", "Counterparty may dispute intent."],
            resolution_source="Qevorpay dispute status and user feedback",
            reasoning_trace_hash=trace.hash,
        )
    )
    return state


def validator(state: NotaryState) -> NotaryState:
    attestation = state.attestations[-1]
    prediction = state.predictions[-1]
    signer = _signer_from_state(state)
    signer_address = signer.address

    attestation.signer = signer_address
    attestation.signature = signer.sign_typed_data(
        primary_type="Attestation",
        verifying_contract=_verifying_contract(state, "AttestationRegistry"),
        message={
            "attestationId": attestation.attestation_id,
            "notaryId": state.notary_id,
            "observationId": attestation.observation_id,
            "evidenceHash": attestation.evidence_hash or sha256_hex(attestation.observation_id),
            "reasoningTraceHash": attestation.reasoning_trace_hash or sha256_hex(attestation.attestation_id),
            "disclosurePolicyHash": attestation.disclosure_policy_hash or sha256_hex(""),
            "confidenceBps": _confidence_bps(attestation.confidence),
            "privacyMode": PRIVACY_MODE_TO_INT[attestation.privacy_mode.value],
            "createdAt": int(attestation.created_at.timestamp()),
        },
        message_types={
            "Attestation": [
                {"name": "attestationId", "type": "string"},
                {"name": "notaryId", "type": "string"},
                {"name": "observationId", "type": "string"},
                {"name": "evidenceHash", "type": "bytes32"},
                {"name": "reasoningTraceHash", "type": "bytes32"},
                {"name": "disclosurePolicyHash", "type": "bytes32"},
                {"name": "confidenceBps", "type": "uint64"},
                {"name": "privacyMode", "type": "uint8"},
                {"name": "createdAt", "type": "uint256"},
            ]
        },
    )
    attestation.status = AttestationStatus.SIGNED

    prediction.signature = signer.sign_typed_data(
        primary_type="Prediction",
        verifying_contract=_verifying_contract(state, "AttestationRegistry"),
        message={
            "predictionId": prediction.prediction_id,
            "notaryId": state.notary_id,
            "question": prediction.question,
            "probabilityBps": _confidence_bps(prediction.probability),
            "horizon": int(prediction.horizon.timestamp()),
            "reasoningTraceHash": prediction.reasoning_trace_hash or sha256_hex(prediction.prediction_id),
        },
        message_types={
            "Prediction": [
                {"name": "predictionId", "type": "string"},
                {"name": "notaryId", "type": "string"},
                {"name": "question", "type": "string"},
                {"name": "probabilityBps", "type": "uint64"},
                {"name": "horizon", "type": "uint256"},
                {"name": "reasoningTraceHash", "type": "bytes32"},
            ]
        },
    )

    state.arc_payloads.append(
        ArcTransactionPayload(
            contract_name="AttestationRegistry",
            method="recordAttestation",
            args=[
                attestation.attestation_id,
                state.notary_id,
                attestation.evidence_hash,
                attestation.reasoning_trace_hash,
                attestation.disclosure_policy_hash,
                _confidence_bps(attestation.confidence),
                PRIVACY_MODE_TO_INT[attestation.privacy_mode.value],
                signer_address,
            ],
        )
    )
    state.arc_payloads.append(
        ArcTransactionPayload(
            contract_name="AttestationRegistry",
            method="recordPrediction",
            args=[prediction.prediction_id, sha256_hex(prediction.model_dump(mode="json"))],
        )
    )
    state.traces.append(
        _trace(
            "Validator",
            "Signed attestation, prediction, and prepared Arc payloads.",
            attestation.confidence,
            attestation_id=attestation.attestation_id,
            prediction_id=prediction.prediction_id,
        )
    )
    return state


def reflector(state: NotaryState) -> NotaryState:
    previous_score = state.karma.score if state.karma else 0.5
    latest_risk = state.risk_decisions[-1]
    delta = 0.03 if latest_risk.approved else -0.02
    score = min(1.0, max(0.0, previous_score + delta))
    checkpoint = KarmaCheckpoint(
        notary_id=state.notary_id,
        accuracy=0.75 if latest_risk.approved else 0.45,
        safety=0.95,
        payment_reliability=1.0 if latest_risk.payment_authorized else 0.9,
        privacy_score=0.98,
        dispute_rate=0.0,
        arbitrage_pnl_usdc=0.0,
        score=score,
    )
    signer = _signer_from_state(state)
    checkpoint.signature = signer.sign_typed_data(
        primary_type="KarmaCheckpoint",
        verifying_contract=_verifying_contract(state, "HelixAIKarma"),
        message={
            "checkpointId": checkpoint.checkpoint_id,
            "notaryId": state.notary_id,
            "accuracyBps": _confidence_bps(checkpoint.accuracy),
            "safetyBps": _confidence_bps(checkpoint.safety),
            "paymentReliabilityBps": _confidence_bps(checkpoint.payment_reliability),
            "privacyScoreBps": _confidence_bps(checkpoint.privacy_score),
            "arbitragePnlUsdc": int(round(checkpoint.arbitrage_pnl_usdc)),
            "createdAt": int(checkpoint.created_at.timestamp()),
        },
        message_types={
            "KarmaCheckpoint": [
                {"name": "checkpointId", "type": "string"},
                {"name": "notaryId", "type": "string"},
                {"name": "accuracyBps", "type": "uint64"},
                {"name": "safetyBps", "type": "uint64"},
                {"name": "paymentReliabilityBps", "type": "uint64"},
                {"name": "privacyScoreBps", "type": "uint64"},
                {"name": "arbitragePnlUsdc", "type": "int256"},
                {"name": "createdAt", "type": "uint256"},
            ]
        },
    )
    state.karma = checkpoint
    state.arc_payloads.append(
        ArcTransactionPayload(
            contract_name="HelixAIKarma",
            method="recordCheckpoint",
            args=[
                state.notary_id,
                sha256_hex(checkpoint.model_dump(mode="json")),
                _confidence_bps(checkpoint.accuracy),
                _confidence_bps(checkpoint.safety),
                _confidence_bps(checkpoint.payment_reliability),
                _confidence_bps(checkpoint.privacy_score),
                int(round(checkpoint.arbitrage_pnl_usdc)),
                signer.address,
            ],
        )
    )
    state.traces.append(
        _trace(
            "Reflector",
            "Updated karma and policy recommendations.",
            score,
            checkpoint=checkpoint.model_dump(mode="json"),
        )
    )
    state.should_continue = False
    return state


async def reflector_live(state: NotaryState, reasoning: SwarmReasoningEngine) -> NotaryState:
    previous_score = state.karma.score if state.karma else 0.5
    output = await reasoning.reflect(state.model_dump(mode="json"), previous_score)
    checkpoint = KarmaCheckpoint(
        notary_id=state.notary_id,
        accuracy=output.accuracy,
        safety=output.safety,
        payment_reliability=output.payment_reliability,
        privacy_score=output.privacy_score,
        dispute_rate=output.dispute_rate,
        arbitrage_pnl_usdc=output.arbitrage_pnl_usdc,
        score=output.updated_score,
    )
    signer = _signer_from_state(state)
    checkpoint.signature = signer.sign_typed_data(
        primary_type="KarmaCheckpoint",
        verifying_contract=_verifying_contract(state, "HelixAIKarma"),
        message={
            "checkpointId": checkpoint.checkpoint_id,
            "notaryId": state.notary_id,
            "accuracyBps": _confidence_bps(checkpoint.accuracy),
            "safetyBps": _confidence_bps(checkpoint.safety),
            "paymentReliabilityBps": _confidence_bps(checkpoint.payment_reliability),
            "privacyScoreBps": _confidence_bps(checkpoint.privacy_score),
            "arbitragePnlUsdc": int(round(checkpoint.arbitrage_pnl_usdc)),
            "createdAt": int(checkpoint.created_at.timestamp()),
        },
        message_types={
            "KarmaCheckpoint": [
                {"name": "checkpointId", "type": "string"},
                {"name": "notaryId", "type": "string"},
                {"name": "accuracyBps", "type": "uint64"},
                {"name": "safetyBps", "type": "uint64"},
                {"name": "paymentReliabilityBps", "type": "uint64"},
                {"name": "privacyScoreBps", "type": "uint64"},
                {"name": "arbitragePnlUsdc", "type": "int256"},
                {"name": "createdAt", "type": "uint256"},
            ]
        },
    )
    state.karma = checkpoint
    state.arc_payloads.append(
        ArcTransactionPayload(
            contract_name="HelixAIKarma",
            method="recordCheckpoint",
            args=[
                state.notary_id,
                sha256_hex(checkpoint.model_dump(mode="json")),
                _confidence_bps(checkpoint.accuracy),
                _confidence_bps(checkpoint.safety),
                _confidence_bps(checkpoint.payment_reliability),
                _confidence_bps(checkpoint.privacy_score),
                int(round(checkpoint.arbitrage_pnl_usdc)),
                signer.address,
            ],
        )
    )
    state.traces.append(
        _trace(
            "Reflector",
            output.critique,
            output.updated_score,
            checkpoint=checkpoint.model_dump(mode="json"),
            policyUpdates=output.policy_updates,
        )
    )
    state.should_continue = False
    return state


def build_graph():
    if StateGraph is None:
        raise RuntimeError("langgraph is not installed")
    graph = StateGraph(NotaryState)
    graph.add_node("scanner", signal_scanner)
    graph.add_node("sentinel", guardian_sentinel)
    graph.add_node("risk", risk_guardian)
    graph.add_node("strategy", strategy_engine)
    graph.add_node("validator", validator)
    graph.add_node("reflector", reflector)

    graph.set_entry_point("scanner")
    graph.add_edge("scanner", "sentinel")
    graph.add_edge("sentinel", "risk")
    graph.add_edge("risk", "strategy")
    graph.add_edge("strategy", "validator")
    graph.add_edge("validator", "reflector")
    graph.add_conditional_edges(
        "reflector",
        lambda state: "scanner" if state.should_continue else END,
        {"scanner": "scanner", END: END},
    )
    return graph.compile()


async def run_notary_cycle(state: NotaryState, reasoning: SwarmReasoningEngine | None = None) -> NotaryState:
    """Run one deterministic cycle.

    The implementation uses pure functions so tests and demo mode work even before cloud LLM
    credentials are configured. `build_graph()` is available when LangGraph is installed.
    """
    if reasoning and reasoning.enabled:
        state = await signal_scanner_live(state, reasoning)
        state = await guardian_sentinel_live(state, reasoning)
        state = await risk_guardian_live(state, reasoning)
        state = await strategy_engine_live(state, reasoning)
        state = validator(state)
        state = await reflector_live(state, reasoning)
        return state

    for step in (signal_scanner, guardian_sentinel, risk_guardian, strategy_engine, validator, reflector):
        state = step(state)
    return state
