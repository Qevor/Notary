from notary.crypto.eip712 import EIP712Signer
from notary.app_service import NotaryAppService
from notary.config import Settings
from notary.models.schemas import PartyType, Ruling, VerdictOutcome, WitnessIntakeRequest
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


def test_confidence_varies_and_gates_payment_behavior() -> None:
    pipeline = _pipeline()
    instruction = "Pay Daniel $250 when the design package is complete and I approve"
    base = {
        "instruction": instruction,
        "payer_identity": "maya",
        "payee_identity": "daniel",
        "approver_identity": "maya",
        "submitter_identity": "daniel",
    }
    cases = {
        "high": (
            "Design package completed and approved by Maya. Timestamped file link, signed "
            "approval, invoice receipt, commit hash, and delivery reference confirm completion."
        ),
        "medium": (
            "Design package completed and approved by Maya. The submitted file appears to "
            "satisfy the design package."
        ),
        "low": "Daniel says trust me it is probably done, but there is no proof.",
    }
    verdicts = {}
    instructions = {}
    for label, evidence_text in cases.items():
        request = WitnessIntakeRequest(evidence_text=evidence_text, **base)
        obligation, evidence = pipeline.intake(request)
        integrity = pipeline.verify(obligation, [evidence])
        verdict = pipeline.judge(obligation, [evidence], integrity, [])
        attestation, _ = pipeline.attest(obligation, [evidence], verdict, request.privacy_mode)
        verdicts[label] = verdict
        instructions[label] = pipeline.payment_instruction(
            obligation,
            verdict,
            attestation.attestation_id,
        )

    assert verdicts["high"].confidence > verdicts["medium"].confidence > verdicts["low"].confidence
    assert verdicts["high"].confidence_gate == "release"
    assert verdicts["medium"].confidence_gate == "release_with_dispute_window"
    assert verdicts["medium"].dispute_window_open
    assert verdicts["low"].confidence_gate == "request_more_evidence"
    assert instructions["high"].action == "release_escrow"
    assert instructions["medium"].action == "release_escrow"
    assert instructions["medium"].metadata["disputeWindowOpen"] is True
    assert instructions["low"].action == "hold"


def test_matching_precedent_is_cited_in_reasoning_trace() -> None:
    pipeline = _pipeline()
    prior_request = WitnessIntakeRequest(
        instruction="Pay Daniel $250 when the design package is complete and I approve",
        evidence_text=(
            "Design package completed and approved by Maya. Timestamped file link, signed "
            "approval, invoice receipt, and commit hash confirm completion."
        ),
        payer_identity="maya",
        payee_identity="daniel",
        approver_identity="maya",
        submitter_identity="daniel",
    )
    prior_obligation, prior_evidence = pipeline.intake(prior_request)
    prior_integrity = pipeline.verify(prior_obligation, [prior_evidence])
    prior_verdict = pipeline.judge(prior_obligation, [prior_evidence], prior_integrity, [])
    prior_attestation, _ = pipeline.attest(
        prior_obligation,
        [prior_evidence],
        prior_verdict,
        prior_request.privacy_mode,
    )
    prior = Ruling(
        notary_id="notary_test",
        obligation=prior_obligation,
        evidence=[prior_evidence],
        integrity_report=prior_integrity,
        verdict=prior_verdict,
        attestation=prior_attestation,
    )

    next_request = WitnessIntakeRequest(
        instruction="Pay Priya $300 when the design package is complete and I approve",
        evidence_text=(
            "Design package completed and approved by Aria with timestamped file link, "
            "signed approval, invoice receipt, and commit hash."
        ),
        payer_identity="aria",
        payee_identity="priya",
        approver_identity="aria",
        submitter_identity="priya",
    )
    obligation, evidence = pipeline.intake(next_request)
    integrity = pipeline.verify(obligation, [evidence])
    verdict = pipeline.judge(obligation, [evidence], integrity, [prior])

    assert prior.ruling_id in verdict.precedent_refs
    assert "Matched precedent records consulted" in verdict.reasoning_trace


def test_dashboard_state_does_not_auto_seed_demo_records(tmp_path) -> None:
    settings = Settings(notary_db_path=tmp_path / "notary.sqlite3")
    service = NotaryAppService(settings)
    state = service.dashboard_state()

    assert state["rulings"] == []
    assert state["reversals"] == []


async def test_conditional_case_creates_qevor_reference_and_matches_agent_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(
        notary_db_path=tmp_path / "notary.sqlite3",
        qevorpay_demo_mode=False,
        qevor_supabase_url="https://qevor.supabase.co",
        qevor_supabase_service_role_key="service-role",
    )
    service = NotaryAppService(settings)

    payment_link_requests = []

    async def fake_payment_link(self, request):
        payment_link_requests.append(request)
        return {
            "reference": "qevor_ref_123",
            "url": "/pay/qevor_ref_123",
            "provider": "qevor_supabase",
            "request": request.model_dump(mode="json"),
        }

    async def fake_submit_witness(self, request):
        return {
            "ruling_id": "ruling_case_123",
            "verdict": {"outcome": "full_release"},
        }

    async def fake_resolve_identity(self, identity):
        wallets = {
            "marketing.agent": "0x0000000000000000000000000000000000000a11",
            "logistics.agent": "0x0000000000000000000000000000000000000b22",
        }
        return {
            "identity": identity,
            "wallet": wallets.get(identity, identity),
            "username": identity,
            "resolved": True,
        }

    async def fake_resolve_executor(self, profile_wallet):
        return {"id": "agent_wallet_123", "escrow_address": "0x0000000000000000000000000000000000000c33"}

    from notary.services.qevorpay import QevorpayClient

    monkeypatch.setattr(QevorpayClient, "create_payment_link", fake_payment_link)
    monkeypatch.setattr(QevorpayClient, "resolve_identity_to_wallet", fake_resolve_identity)
    monkeypatch.setattr(QevorpayClient, "resolve_executor_agent_wallet", fake_resolve_executor)
    monkeypatch.setattr(NotaryAppService, "submit_witness_obligation", fake_submit_witness)

    case = await service.create_conditional_case(
        created_by_identity="marketing.agent",
        created_by_type="agent",
        payer_identity="marketing.agent",
        payee_identity="logistics.agent",
        approver_identity="marketing.agent",
        payer_type="agent",
        payee_type="agent",
        approver_type="agent",
        instruction="Pay logistics.agent $600 when the delivery manifest is complete and I approve",
        amount_usdc=600,
    )

    assert case["case_id"].startswith("case_")
    assert case["qevor_payment_reference"] == "qevor_ref_123"
    assert case["status"] == "awaiting_funding"
    assert "evidenceUploadPath" not in case["metadata"]
    assert payment_link_requests[0].recipient == "0x0000000000000000000000000000000000000c33"
    assert case["metadata"]["payerWallet"] == "0x0000000000000000000000000000000000000a11"
    assert case["metadata"]["payeeWallet"] == "0x0000000000000000000000000000000000000b22"
    assert case["metadata"]["executorAgentWalletId"] == "agent_wallet_123"

    blocked = await service.submit_case_evidence(
        case_id=case["case_id"],
        token=case["evidenceInviteToken"],
        evidence_text="Manifest complete, timestamped, hash-linked, and approved.",
        submitter_identity="logistics.agent",
        submitter_type="agent",
    )
    assert blocked["error"] == "case_not_funded"

    funded = service.mark_case_funded_from_qevor("qevor_ref_123", {"status": "paid"})
    assert funded is not None
    assert funded["status"] == "funded_awaiting_evidence"
    assert "/cases/" in funded["metadata"]["evidenceUploadPath"]

    result = await service.submit_case_evidence(
        case_id=case["case_id"],
        token=case["evidenceInviteToken"],
        evidence_text="Manifest complete, timestamped, hash-linked, and approved.",
        submitter_identity="logistics.agent",
        submitter_type="agent",
    )

    assert result["case"]["status"] == "released"
    assert result["case"]["latest_ruling_id"] == "ruling_case_123"
