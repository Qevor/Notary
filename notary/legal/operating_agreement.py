from __future__ import annotations

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import OperatingAgreement


def generate_operating_agreement(notary_id: str) -> OperatingAgreement:
    agreement = OperatingAgreement(
        notary_id=notary_id,
        permitted_actions=[
            "extract_obligations",
            "verify_evidence_heuristically",
            "render_graded_verdicts",
            "sign_attestations",
            "trigger_notary_escrow_payments",
            "adjudicate_disputes",
            "issue_linked_reversals",
            "maintain_party_operating_history",
        ],
        treasury_constraints={
            "max_single_payment_usdc": 10_000,
            "treasury_trading_allowed": False,
            "lending_or_underwriting_allowed": False,
        },
        privacy_rules={
            "raw_evidence_onchain": False,
            "default_mode": "protected",
            "public_record_uses_hashes_and_summaries": True,
        },
        dispute_rules={
            "default_dispute_window_seconds": 86_400,
            "arbitrator_access_level": "arbitrator",
        },
    )
    agreement.hash = sha256_hex(agreement.model_dump(mode="json", exclude={"hash"}))
    return agreement
