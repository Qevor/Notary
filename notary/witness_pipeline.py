from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from notary.crypto.eip712 import EIP712Signer
from notary.crypto.hashing import sha256_hex
from notary.models.schemas import (
    ArcTransactionPayload,
    CorrectivePaymentAction,
    Dispute,
    DisputeOutcome,
    Evidence,
    IntegrityReport,
    Obligation,
    PaymentAction,
    PaymentInstruction,
    PrivacyMode,
    Reversal,
    Ruling,
    VerdictOutcome,
    WitnessAttestation,
    WitnessIntakeRequest,
    WitnessVerdict,
    utc_now,
)


PRIVACY_MODE_TO_INT = {"public": 0, "protected": 1, "private": 2}


@dataclass(slots=True)
class WitnessPipeline:
    notary_id: str
    signer: EIP712Signer
    attestation_registry: str | None = None

    def intake(
        self,
        request: WitnessIntakeRequest,
        obligation: Obligation | None = None,
    ) -> tuple[Obligation, Evidence]:
        obligation = obligation or self._extract_obligation(request)
        evidence_payload = {
            "type": request.evidence_type,
            "ref": request.evidence_ref,
            "text": request.evidence_text,
            "submitter": request.submitter_identity,
            "submittedAt": utc_now().isoformat(),
        }
        evidence = Evidence(
            type=request.evidence_type,
            ref=request.evidence_ref,
            text=request.evidence_text,
            commitment_hash=sha256_hex(evidence_payload),
            encrypted_blob_ref=request.metadata.get("encrypted_blob_ref"),
            submitter_identity=request.submitter_identity,
            submitter_type=request.submitter_type,
            privacy_mode=request.privacy_mode,
            metadata=request.metadata,
        )
        return obligation, evidence

    def verify(self, obligation: Obligation, evidence: list[Evidence]) -> IntegrityReport:
        text = " ".join(item.text or item.ref or "" for item in evidence).lower()
        elements = {
            "deliverable": obligation.deliverable,
            "acceptance_criterion": obligation.acceptance_criterion,
            "authorized_approver": obligation.authorized_approver,
            "deadline": obligation.deadline,
            "satisfying_evidence": " ".join(obligation.satisfying_evidence),
        }
        element_coverage: dict[str, float] = {}
        for name, value in elements.items():
            element_coverage[name] = _text_overlap(value, text) if value else 1.0
        scored_elements = [
            score
            for name, score in element_coverage.items()
            if elements[name] or name in {"deliverable", "acceptance_criterion", "satisfying_evidence"}
        ]
        coverage_score = sum(scored_elements) / max(1, len(scored_elements))

        verifiable_markers = {
            "commit",
            "hash",
            "signed",
            "timestamp",
            "invoice",
            "receipt",
            "merged",
            "tx",
            "pull request",
            "sha",
            "approval",
            "approved",
            "file",
            "link",
            "reference",
        }
        unverifiable_markers = {
            "trust me",
            "i promise",
            "looks done",
            "probably",
            "should be",
            "no proof",
            "no evidence",
        }
        marker_hits = sum(1 for marker in verifiable_markers if marker in text)
        unverifiable_hits = sum(1 for marker in unverifiable_markers if marker in text)
        corroboration_score = min(1.0, marker_hits / 5)
        unverifiable_score = min(1.0, unverifiable_hits / 3)
        source_quality = max(
            0.05,
            min(
                1.0,
                coverage_score * 0.55
                + corroboration_score * 0.35
                + (0.1 if len(evidence) > 1 else 0)
                - unverifiable_score * 0.25,
            ),
        )
        flags: list[str] = []
        if obligation.clarification_needed:
            flags.append("obligation_ambiguity")
        if coverage_score < 0.5:
            flags.append("evidence_does_not_cover_all_obligation_elements")
        if marker_hits == 0:
            flags.append("mostly_unverifiable_assertions")
        if unverifiable_hits:
            flags.append("contains_unverifiable_assertions")

        return IntegrityReport(
            observation_id=obligation.obligation_id,
            source_quality=source_quality,
            spoofing_risk=max(0.05, 0.38 - corroboration_score * 0.22 + unverifiable_score * 0.18),
            privacy_risk=0.2,
            safety_flags=flags,
            approved=source_quality >= 0.45 and not obligation.clarification_needed,
            notes=(
                "Heuristic integrity review only: evidence was checked for internal consistency, "
                "obligation coverage, and verifiable artifacts. "
                "This is not forensic authentication."
            ),
            metadata={
                "elementCoverage": element_coverage,
                "coverageScore": round(coverage_score, 4),
                "corroborationScore": round(corroboration_score, 4),
                "verifiableMarkerHits": marker_hits,
                "unverifiableScore": round(unverifiable_score, 4),
                "unverifiableMarkerHits": unverifiable_hits,
                "evidenceCount": len(evidence),
            },
        )

    def judge(
        self,
        obligation: Obligation,
        evidence: list[Evidence],
        integrity_report: IntegrityReport,
        precedent: list[Ruling],
    ) -> WitnessVerdict:
        precedent_refs = self._match_precedent(obligation, precedent)
        evidence_text = " ".join(item.text or item.ref or "" for item in evidence).lower()

        evidence_assessment = _assess_evidence_direction(evidence_text)
        confidence = _confidence_from_integrity(
            integrity_report=integrity_report,
            extraction_confidence=obligation.extraction_confidence,
            evidence_assessment=evidence_assessment,
        )
        gate = _confidence_gate(confidence)

        if obligation.clarification_needed:
            outcome = VerdictOutcome.HOLD_PENDING_CLARIFICATION
            release_pct = 0.0
            deficiency = "; ".join(obligation.clarification_questions)
            gate = "request_more_evidence"
        elif not integrity_report.approved or gate == "request_more_evidence":
            outcome = VerdictOutcome.HOLD_PENDING_CLARIFICATION
            release_pct = 0.0
            deficiency = (
                ", ".join(integrity_report.safety_flags)
                or "Evidence quality was insufficient; request more evidence before ruling."
            )
        else:
            complete = evidence_assessment["complete"] > 0
            partial = evidence_assessment["partial"] > 0
            rejected = evidence_assessment["rejected"] > 0
            if complete and not rejected and not partial:
                outcome = VerdictOutcome.FULL_RELEASE
                release_pct = 100.0
                deficiency = None
            elif partial or (complete and rejected):
                outcome = VerdictOutcome.PARTIAL_RELEASE
                release_pct = 50.0
                deficiency = "Evidence supports some performance but leaves a material deficiency."
            else:
                outcome = VerdictOutcome.REFUSE_REFUND
                release_pct = 0.0
                deficiency = "Evidence does not establish that the obligation was satisfied."

        trace = self._testimony_trace(
            obligation=obligation,
            integrity_report=integrity_report,
            outcome=outcome,
            release_pct=release_pct,
            confidence=confidence,
            confidence_gate=gate,
            deficiency=deficiency,
            precedent_refs=precedent_refs,
        )
        return WitnessVerdict(
            obligation_id=obligation.obligation_id,
            outcome=outcome,
            release_pct=release_pct,
            confidence=confidence,
            confidence_gate=gate,
            dispute_window_open=gate == "release_with_dispute_window",
            deficiency=deficiency,
            reasoning_trace=trace,
            precedent_refs=precedent_refs,
            metadata={
                "confidenceGate": gate,
                "evidenceAssessment": evidence_assessment,
                "integrity": integrity_report.metadata,
            },
        )

    def attest(
        self,
        obligation: Obligation,
        evidence: list[Evidence],
        verdict: WitnessVerdict,
        privacy_mode: PrivacyMode,
        *,
        supersedes_ref: str | None = None,
        revises_ref: str | None = None,
    ) -> tuple[WitnessAttestation, ArcTransactionPayload]:
        evidence_hash = sha256_hex([item.model_dump(mode="json") for item in evidence])
        reasoning_hash = sha256_hex(verdict.reasoning_trace)
        verdict_hash = sha256_hex(verdict.model_dump(mode="json"))
        attestation = WitnessAttestation(
            obligation_id=obligation.obligation_id,
            verdict_id=verdict.verdict_id,
            evidence_commitment_hash=evidence_hash,
            reasoning_trace_hash=reasoning_hash,
            verdict_hash=verdict_hash,
            signer=self.signer.address,
            privacy_mode=privacy_mode,
            party_identities={
                "payer": obligation.payer_identity,
                "payee": obligation.payee_identity,
                "approver": obligation.approver_identity,
            },
            party_types={
                "payer": obligation.payer_type,
                "payee": obligation.payee_type,
                "approver": obligation.approver_type,
            },
            supersedes_ref=supersedes_ref,
            revises_ref=revises_ref,
        )
        attestation.signature = self.signer.sign_typed_data(
            primary_type="WitnessAttestation",
            verifying_contract=self.attestation_registry,
            message={
                "attestationId": attestation.attestation_id,
                "notaryId": self.notary_id,
                "obligationId": obligation.obligation_id,
                "verdictHash": verdict_hash,
                "evidenceHash": evidence_hash,
                "reasoningTraceHash": reasoning_hash,
                "confidenceBps": _bps(verdict.confidence),
                "createdAt": int(attestation.timestamp.timestamp()),
            },
            message_types={
                "WitnessAttestation": [
                    {"name": "attestationId", "type": "string"},
                    {"name": "notaryId", "type": "string"},
                    {"name": "obligationId", "type": "string"},
                    {"name": "verdictHash", "type": "bytes32"},
                    {"name": "evidenceHash", "type": "bytes32"},
                    {"name": "reasoningTraceHash", "type": "bytes32"},
                    {"name": "confidenceBps", "type": "uint64"},
                    {"name": "createdAt", "type": "uint256"},
                ]
            },
        )
        payload = ArcTransactionPayload(
            contract_name="AttestationRegistry",
            method="recordAttestation",
            args=[
                attestation.attestation_id,
                self.notary_id,
                evidence_hash,
                reasoning_hash,
                sha256_hex(
                    {
                        "privacyMode": privacy_mode.value,
                        "supersedes": supersedes_ref,
                        "revises": revises_ref,
                    }
                ),
                _bps(verdict.confidence),
                PRIVACY_MODE_TO_INT[privacy_mode.value],
                (
                    self.signer.address
                    if self.signer.address.startswith("0x")
                    else "0x0000000000000000000000000000000000000000"
                ),
            ],
            metadata={
                "verdictHash": verdict_hash,
                "supersedesRef": supersedes_ref,
                "revisesRef": revises_ref,
            },
        )
        return attestation, payload

    def payment_instruction(
        self,
        obligation: Obligation,
        verdict: WitnessVerdict,
        attestation_id: str,
    ) -> PaymentInstruction:
        amount = obligation.amount_usdc
        if amount is not None and verdict.release_pct:
            amount = round(amount * verdict.release_pct / 100, 6)
        recipients = [
            {
                **recipient,
                "amount": round(float(recipient.get("amount", 0)) * verdict.release_pct / 100, 6),
            }
            for recipient in obligation.metadata.get("batch_recipients", [])
            if float(recipient.get("amount", 0)) > 0
        ]
        if verdict.confidence_gate == "request_more_evidence":
            action = PaymentAction.HOLD
        elif recipients and verdict.release_pct > 0:
            action = PaymentAction.BATCH_DISTRIBUTE
        elif verdict.outcome == VerdictOutcome.FULL_RELEASE:
            action = PaymentAction.RELEASE_ESCROW
        elif verdict.outcome == VerdictOutcome.PARTIAL_RELEASE:
            action = PaymentAction.RELEASE_PARTIAL
        elif verdict.outcome == VerdictOutcome.REFUSE_REFUND:
            action = PaymentAction.REFUND
        else:
            action = PaymentAction.HOLD
        return PaymentInstruction(
            action=action,
            amount_usdc=amount,
            release_pct=verdict.release_pct,
            payer_identity=obligation.payer_identity,
            payee_identity=obligation.payee_identity,
            recipients=recipients,
            attestation_id=attestation_id,
            reason=verdict.deficiency or verdict.reasoning_trace[:240],
            metadata={
                "verdictId": verdict.verdict_id,
                "obligationId": obligation.obligation_id,
                "notaryCaseId": obligation.metadata.get("notaryCaseId"),
                "qevorPaymentReference": obligation.metadata.get("qevorPaymentReference"),
                "qevorPaymentUrl": obligation.metadata.get("qevorPaymentUrl"),
                "confidenceGate": verdict.confidence_gate,
                "disputeWindowOpen": verdict.dispute_window_open,
            },
        )

    def adjudicate_dispute(
        self,
        original: Ruling,
        counter_evidence: list[Evidence],
        precedent: list[Ruling],
    ) -> tuple[Dispute, WitnessVerdict, bool]:
        all_evidence = [*original.evidence, *counter_evidence]
        integrity = self.verify(original.obligation, all_evidence)
        revised_verdict = self.judge(original.obligation, all_evidence, integrity, precedent)
        changed = (
            revised_verdict.outcome != original.verdict.outcome
            or abs(revised_verdict.release_pct - original.verdict.release_pct) >= 1
        )
        if changed:
            revised_verdict.reasoning_trace = (
                "SELF-CORRECTION TESTIMONY\n"
                f"Original verdict {original.verdict.verdict_id} got the satisfaction finding wrong "
                "because it did not have the later counter-evidence now in the record. "
                f"The new evidence changed the finding from {original.verdict.outcome.value} "
                f"at {original.verdict.release_pct}% to {revised_verdict.outcome.value} "
                f"at {revised_verdict.release_pct}%. "
                "The revised verdict is correct because it weighs the original evidence and "
                "counter-evidence against the same extracted obligation and records the changed "
                "basis publicly instead of overwriting the first attestation.\n\n"
                f"{revised_verdict.reasoning_trace}"
            )
        dispute = Dispute(
            original_ruling_id=original.ruling_id,
            original_attestation_ref=original.attestation.attestation_id,
            counter_evidence=counter_evidence,
            outcome=DisputeOutcome.REVISED if changed else DisputeOutcome.UPHELD,
            justification=(
                "Counter-evidence changed the material satisfaction finding."
                if changed
                else (
                    "Counter-evidence did not overcome the original "
                    "obligation-by-obligation finding."
                )
            ),
        )
        return dispute, revised_verdict, changed

    def reversal_for(self, original: Ruling, new_ruling: Ruling) -> Reversal:
        old_amount = _settled_amount(original)
        new_amount = _settled_amount(new_ruling)
        delta = round(new_amount - old_amount, 6)
        if delta > 0:
            action = CorrectivePaymentAction.TOP_UP_RELEASE
        elif delta < 0:
            action = CorrectivePaymentAction.PARTIAL_CLAWBACK_REQUEST
        else:
            action = CorrectivePaymentAction.NONE
        return Reversal(
            original_attestation_ref=original.attestation.attestation_id,
            new_attestation_ref=new_ruling.attestation.attestation_id,
            original_ruling_id=original.ruling_id,
            new_ruling_id=new_ruling.ruling_id,
            what_changed=new_ruling.verdict.reasoning_trace[:1000],
            corrective_payment_action=action,
            outstanding_delta=abs(delta),
        )

    def _extract_obligation(self, request: WitnessIntakeRequest) -> Obligation:
        text = request.instruction.strip()
        lower = text.lower()
        amount = request.amount_usdc
        if amount is None:
            match = re.search(r"\$?\b(\d+(?:\.\d+)?)\s*(?:usdc|usd|\$)?", lower)
            amount = float(match.group(1)) if match else None
        payee = request.payee_identity or _match_after(text, ["pay", "to"])
        approver = request.approver_identity or (
            "payer" if "i approve" in lower or "my approval" in lower else None
        )
        deliverable = _extract_deliverable(text)
        acceptance = _extract_acceptance(text)
        satisfying = ["submitted evidence"]
        if "commit" in lower:
            satisfying.append("commit reference")
        if "signed" in lower:
            satisfying.append("signed message")

        questions: list[str] = []
        if not request.payer_identity:
            questions.append("Confirm payer identity.")
        if not payee:
            questions.append("Confirm payee identity.")
        if not deliverable:
            questions.append("Confirm the deliverable being judged.")
        if not acceptance:
            questions.append("Confirm the acceptance criterion.")
        if amount is None:
            questions.append("Confirm the USDC amount.")

        return Obligation(
            raw_instruction=text,
            payer_identity=request.payer_identity,
            payee_identity=payee,
            approver_identity=approver,
            deliverable=deliverable,
            acceptance_criterion=acceptance,
            authorized_approver=request.approver_identity or approver,
            deadline=_extract_deadline(text),
            satisfying_evidence=satisfying,
            amount_usdc=amount,
            payer_type=request.payer_type,
            payee_type=request.payee_type,
            approver_type=request.approver_type,
            clarification_needed=bool(questions),
            clarification_questions=questions,
            extraction_confidence=max(0.2, 1 - len(questions) * 0.16),
            metadata={"batch_recipients": request.batch_recipients},
        )

    def _match_precedent(self, obligation: Obligation, precedent: list[Ruling]) -> list[str]:
        scored: list[tuple[float, str]] = []
        current = f"{obligation.deliverable or ''} {obligation.acceptance_criterion or ''}"
        for ruling in precedent:
            prior = (
                f"{ruling.obligation.deliverable or ''} "
                f"{ruling.obligation.acceptance_criterion or ''}"
            )
            score = SequenceMatcher(None, current.lower(), prior.lower()).ratio()
            if score >= 0.32:
                scored.append((score, ruling.ruling_id))
        scored.sort(reverse=True)
        return [ruling_id for _, ruling_id in scored[:3]]

    def _testimony_trace(
        self,
        *,
        obligation: Obligation,
        integrity_report: IntegrityReport,
        outcome: VerdictOutcome,
        release_pct: float,
        confidence: float,
        confidence_gate: str,
        deficiency: str | None,
        precedent_refs: list[str],
    ) -> str:
        precedent_text = (
            f"Matched precedent records consulted: {', '.join(precedent_refs)}."
            if precedent_refs
            else "No materially similar NOTARY precedent was found."
        )
        return (
            "NOTARY TESTIMONY\n"
            f"Asked to verify: {obligation.raw_instruction}\n"
            f"Parsed obligation: deliverable={obligation.deliverable!r}; "
            f"acceptance_criterion={obligation.acceptance_criterion!r}; "
            f"authorized_approver={obligation.authorized_approver!r}; "
            f"deadline={obligation.deadline!r}; amount_usdc={obligation.amount_usdc!r}.\n"
            f"Parties: payer={obligation.payer_identity} ({obligation.payer_type.value}); "
            f"payee={obligation.payee_identity} ({obligation.payee_type.value}); "
            f"approver={obligation.approver_identity} ({obligation.approver_type.value}).\n"
            f"Evidence review: score={integrity_report.source_quality:.2f}; "
            f"flags={integrity_report.safety_flags}; notes={integrity_report.notes}\n"
            f"Element coverage: {integrity_report.metadata.get('elementCoverage', {})}; "
            f"corroboration_score={integrity_report.metadata.get('corroborationScore')}.\n"
            f"{precedent_text}\n"
            f"Verdict: {outcome.value}; release_pct={release_pct}; confidence={confidence:.2f}; "
            f"confidence_gate={confidence_gate}.\n"
            f"Deficiency: {deficiency or 'none'}.\n"
            "This is an experimental witness attestation, "
            "not legal advice or forensic certification."
        )


def _bps(value: float) -> int:
    return max(0, min(10_000, round(value * 10_000)))


def _text_overlap(needle: str, haystack: str) -> float:
    words = {word for word in re.split(r"\W+", needle.lower()) if len(word) > 2}
    if not words:
        return 0
    return len([word for word in words if word in haystack]) / len(words)


def _match_after(text: str, markers: list[str]) -> str | None:
    for marker in markers:
        match = re.search(rf"{marker}\s+([A-Za-z0-9_.:@-]+)", text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if (
                not candidate.replace(".", "", 1).isdigit()
                and candidate.lower() not in {"when", "if"}
            ):
                return candidate
    return None


def _extract_deliverable(text: str) -> str | None:
    match = re.search(
        r"(?:when|after|if)\s+(.+?)(?:\s+and\s+i\s+approve|\s+by\s+|\s+before\s+|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" .")
    return None


def _extract_acceptance(text: str) -> str | None:
    lower = text.lower()
    if "i approve" in lower:
        return "payer approval"
    if "approved" in lower:
        return "approval recorded in evidence"
    if "complete" in lower or "completed" in lower:
        return "deliverable completed"
    return None


def _extract_deadline(text: str) -> str | None:
    match = re.search(r"\b(?:by|before|deadline)\s+([^.;,]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _assess_evidence_direction(text: str) -> dict[str, int]:
    complete_terms = ("complete", "completed", "delivered", "approved", "accepted", "merged")
    partial_terms = ("partial", "partly", "incomplete", "missing", "defect", "deficiency")
    rejected_terms = ("rejected", "failed", "not delivered", "fraud", "invalid", "did not deliver")
    return {
        "complete": sum(1 for term in complete_terms if term in text),
        "partial": sum(1 for term in partial_terms if term in text),
        "rejected": sum(1 for term in rejected_terms if term in text),
    }


def _confidence_from_integrity(
    *,
    integrity_report: IntegrityReport,
    extraction_confidence: float,
    evidence_assessment: dict[str, int],
) -> float:
    coverage = float(integrity_report.metadata.get("coverageScore", 0))
    corroboration = float(integrity_report.metadata.get("corroborationScore", 0))
    unverifiable = float(integrity_report.metadata.get("unverifiableScore", 0))
    directional_strength = min(
        1.0,
        (
            evidence_assessment.get("complete", 0)
            + evidence_assessment.get("partial", 0)
            + evidence_assessment.get("rejected", 0)
        )
        / 3,
    )
    confidence = (
        coverage * 0.36
        + integrity_report.source_quality * 0.28
        + corroboration * 0.18
        + extraction_confidence * 0.1
        + directional_strength * 0.08
        - integrity_report.spoofing_risk * 0.12
        - unverifiable * 0.16
    )
    if "obligation_ambiguity" in integrity_report.safety_flags:
        confidence -= 0.18
    return round(max(0.05, min(0.98, confidence)), 2)


def _confidence_gate(confidence: float) -> str:
    if confidence >= 0.72:
        return "release"
    if confidence >= 0.55:
        return "release_with_dispute_window"
    return "request_more_evidence"


def _settled_amount(ruling: Ruling) -> float:
    amount = ruling.obligation.amount_usdc or 0
    return round(amount * ruling.verdict.release_pct / 100, 6)
