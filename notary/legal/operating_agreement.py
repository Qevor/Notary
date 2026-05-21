from __future__ import annotations

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import OperatingAgreement


def generate_operating_agreement(notary_id: str) -> OperatingAgreement:
    agreement = OperatingAgreement(
        notary_id=notary_id,
        permitted_actions=[
            "observe_evidence",
            "sign_attestations",
            "publish_predictions",
            "trigger_qevorpay_payments",
            "execute_bounded_treasury_actions",
            "update_karma_checkpoints",
            "spawn_child_notaries_above_karma_threshold",
        ],
        treasury_constraints={
            "max_single_payment_usdc": 10_000,
            "max_arbitrage_exposure_pct": 10,
            "idle_yield_allowed": True,
        },
        privacy_rules={
            "raw_evidence_onchain": False,
            "default_mode": "protected",
            "public_post_requires_public_mode": True,
        },
        dispute_rules={
            "default_dispute_window_seconds": 86_400,
            "arbitrator_access_level": "arbitrator",
        },
    )
    agreement.hash = sha256_hex(agreement.model_dump(mode="json", exclude={"hash"}))
    return agreement

