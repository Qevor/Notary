import pytest

from notary.models.schemas import EscrowBatchDistributionRequest, EscrowPaymentLinkRequest
from notary.services.escrow import NotaryEscrowClient


@pytest.mark.asyncio
async def test_escrow_demo_payment_link() -> None:
    client = NotaryEscrowClient(demo_mode=True)
    response = await client.create_payment_link(
        EscrowPaymentLinkRequest(amount_usdc=25, description="Verified invoice")
    )
    assert response["status"] == "created"
    assert response["url"].startswith("/pay/")


@pytest.mark.asyncio
async def test_escrow_supabase_batch_contract(monkeypatch) -> None:
    inserts = []
    client = NotaryEscrowClient(
        demo_mode=False,
        supabase_url="https://notary.supabase.co",
        supabase_service_role_key="service-role",
        executor_agent_wallet_id="agent_wallet_id",
        creator_wallet="0x0000000000000000000000000000000000000001",
    )

    async def fake_insert(self, table, payload):
        inserts.append((table, payload))
        if table == "batch_requests":
            return [{"id": "batch_1", **payload}]
        return [{"id": "row_1"}]

    monkeypatch.setattr(NotaryEscrowClient, "_supabase_insert", fake_insert)
    response = await client.create_batch_distribution(
        EscrowBatchDistributionRequest(
            recipients=[
                {"wallet": "0x0000000000000000000000000000000000000002", "amount": 10}
            ],
            reason="NOTARY full release",
        )
    )

    assert response["reference"] == "batch_1"
    assert inserts[0][0] == "batch_requests"
    assert inserts[0][1]["executor_state"] == "pending_evaluation"
    assert inserts[1][0] == "batch_payments"
    assert inserts[1][1][0]["tx_hash"] == "pending_executor"


@pytest.mark.asyncio
async def test_escrow_batch_persists_attestation_envelope(monkeypatch) -> None:
    """The attestation envelope must reach batch_requests so NOTARY's executor
    can independently verify NOTARY's verdict before paying.
    """
    inserts = []
    client = NotaryEscrowClient(
        demo_mode=False,
        supabase_url="https://notary.supabase.co",
        supabase_service_role_key="service-role",
        executor_agent_wallet_id="agent_wallet_id",
        creator_wallet="0x0000000000000000000000000000000000000001",
    )

    async def fake_insert(self, table, payload):
        inserts.append((table, payload))
        if table == "batch_requests":
            return [{"id": "batch_2", **payload}]
        return [{"id": "row_1"}]

    monkeypatch.setattr(NotaryEscrowClient, "_supabase_insert", fake_insert)
    envelope = {
        "attestation_id": "0x" + "a" * 64,
        "notary_id": "0x" + "b" * 64,
        "obligation_id": "obl_123",
        "verdict_hash": "0x" + "c" * 64,
        "evidence_hash": "0x" + "d" * 64,
        "reasoning_trace_hash": "0x" + "e" * 64,
        "confidence_bps": 8700,
        "verdict_signature": "0x" + "f" * 130,
        "attestation_contract": "0x" + "1" * 40,
        "attestation_chain_id": 5042002,
        "notary_identity_registry": "0x" + "2" * 40,
        "attestation_domain_name": "NOTARY",
        "attestation_domain_version": "1",
        "attestation_created_at": 1716354000,
    }
    await client.create_batch_distribution(
        EscrowBatchDistributionRequest(
            recipients=[
                {"wallet": "0x0000000000000000000000000000000000000002", "amount": 10}
            ],
            reason="NOTARY full release",
            metadata={"attestation": envelope},
        )
    )

    row = inserts[0][1]
    for column, expected in envelope.items():
        assert row[column] == expected, f"missing column {column}"


@pytest.mark.asyncio
async def test_escrow_batch_skips_attestation_when_absent(monkeypatch) -> None:
    """Without an envelope (e.g. payment-link flows), no attestation columns
    are written — preserves backwards compatibility with attestation_mode=off
    agent wallets.
    """
    inserts = []
    client = NotaryEscrowClient(
        demo_mode=False,
        supabase_url="https://notary.supabase.co",
        supabase_service_role_key="service-role",
        executor_agent_wallet_id="agent_wallet_id",
        creator_wallet="0x0000000000000000000000000000000000000001",
    )

    async def fake_insert(self, table, payload):
        inserts.append((table, payload))
        if table == "batch_requests":
            return [{"id": "batch_3", **payload}]
        return [{"id": "row_1"}]

    monkeypatch.setattr(NotaryEscrowClient, "_supabase_insert", fake_insert)
    await client.create_batch_distribution(
        EscrowBatchDistributionRequest(
            recipients=[
                {"wallet": "0x0000000000000000000000000000000000000002", "amount": 10}
            ],
            reason="NOTARY full release",
        )
    )
    row = inserts[0][1]
    for column in (
        "attestation_id",
        "notary_id",
        "verdict_signature",
        "attestation_chain_id",
    ):
        assert column not in row


def test_escrow_webhook_signature_verification() -> None:
    import hashlib
    import hmac as hmac_mod

    secret = "test-webhook-secret"
    client = NotaryEscrowClient(demo_mode=False, webhook_secret=secret)
    body = b'{"batch_payment_id":"bp_1","status":"delivered"}'
    good_sig = hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert client.verify_webhook(headers={"x-signature": good_sig}, body=body) is True
    assert client.verify_webhook(headers={"x-signature": "deadbeef"}, body=body) is False
    assert client.verify_webhook(headers={}, body=body) is False
