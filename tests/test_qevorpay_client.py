import pytest

from notary.models.schemas import QevorpayBatchDistributionRequest, QevorpayPaymentLinkRequest
from notary.services.qevorpay import QevorpayClient


@pytest.mark.asyncio
async def test_qevorpay_demo_payment_link() -> None:
    client = QevorpayClient(demo_mode=True)
    response = await client.create_payment_link(
        QevorpayPaymentLinkRequest(amount_usdc=25, description="Verified invoice")
    )
    assert response["status"] == "created"
    assert response["url"].startswith("/pay/")


@pytest.mark.asyncio
async def test_qevorpay_supabase_batch_contract(monkeypatch) -> None:
    inserts = []
    client = QevorpayClient(
        demo_mode=False,
        supabase_url="https://qevor.supabase.co",
        supabase_service_role_key="service-role",
        executor_agent_wallet_id="agent_wallet_id",
        creator_wallet="0x0000000000000000000000000000000000000001",
    )

    async def fake_insert(self, table, payload):
        inserts.append((table, payload))
        if table == "batch_requests":
            return [{"id": "batch_1", **payload}]
        return [{"id": "row_1"}]

    monkeypatch.setattr(QevorpayClient, "_supabase_insert", fake_insert)
    response = await client.create_batch_distribution(
        QevorpayBatchDistributionRequest(
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
