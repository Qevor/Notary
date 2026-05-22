from notary.crypto.eip712 import EIP712Signer
from notary.models.schemas import PartyType, VerdictOutcome, WitnessIntakeRequest
from notary.witness_pipeline import WitnessPipeline


def _pipeline() -> WitnessPipeline:
    return WitnessPipeline(notary_id="notary_test", signer=EIP712Signer())


def test_witness_pipeline_captures_agent_party_types_and_full_release() -> None:
    request = WitnessIntakeRequest(
        instruction="Pay logistics.agent $250 when the delivery manifest is complete and I approve",
        evidence_text="The delivery manifest is complete, timestamped, and approved by payer.",
        payer_identity="marketing.agent",
        payee_identity="logistics.agent",
        payer_type=PartyType.AGENT,
        payee_type=PartyType.AGENT,
        submitter_identity="logistics.agent",
        submitter_type=PartyType.AGENT,
    )

    pipeline = _pipeline()
    obligation, evidence = pipeline.intake(request)
    integrity = pipeline.verify(obligation, [evidence])
    verdict = pipeline.judge(obligation, [evidence], integrity, [])

    assert obligation.payer_type == PartyType.AGENT
    assert obligation.payee_type == PartyType.AGENT
    assert not obligation.clarification_needed
    assert verdict.outcome == VerdictOutcome.FULL_RELEASE
    assert "NOTARY TESTIMONY" in verdict.reasoning_trace


def test_dispute_revision_produces_self_correction_and_reversal() -> None:
    pipeline = _pipeline()
    request = WitnessIntakeRequest(
        instruction="Pay Daniel $250 when the design is complete and I approve",
        evidence_text="The design is complete, timestamped, and approved by payer.",
        payer_identity="maya",
        payee_identity="daniel",
        submitter_identity="daniel",
    )
    obligation, evidence = pipeline.intake(request)
    integrity = pipeline.verify(obligation, [evidence])
    verdict = pipeline.judge(obligation, [evidence], integrity, [])
    attestation, _ = pipeline.attest(obligation, [evidence], verdict, request.privacy_mode)
    from notary.models.schemas import Ruling

    payment_instruction = pipeline.payment_instruction(
        obligation,
        verdict,
        attestation.attestation_id,
    )
    original = Ruling(
        notary_id="notary_test",
        obligation=obligation,
        evidence=[evidence],
        integrity_report=integrity,
        verdict=verdict,
        attestation=attestation,
        payment_instruction=payment_instruction,
    )

    counter = WitnessIntakeRequest(
        instruction=request.instruction,
        evidence_text="Counter-evidence: the design was rejected and not delivered.",
        payer_identity="maya",
        payee_identity="daniel",
        submitter_identity="maya",
    )
    _, counter_evidence = pipeline.intake(counter)
    dispute, revised_verdict, changed = pipeline.adjudicate_dispute(
        original,
        [counter_evidence],
        [],
    )

    assert changed
    assert dispute.outcome == "revised"
    assert "SELF-CORRECTION TESTIMONY" in revised_verdict.reasoning_trace

    revised_attestation, _ = pipeline.attest(
        obligation,
        [evidence, counter_evidence],
        revised_verdict,
        request.privacy_mode,
        supersedes_ref=attestation.attestation_id,
        revises_ref=attestation.attestation_id,
    )
    revised = original.model_copy(deep=True)
    revised.ruling_id = "ruling_revised"
    revised.verdict = revised_verdict
    revised.attestation = revised_attestation
    reversal = pipeline.reversal_for(original, revised)

    assert reversal.original_attestation_ref == attestation.attestation_id
    assert reversal.new_attestation_ref == revised_attestation.attestation_id
    assert reversal.corrective_payment_action == "partial_clawback_request"
