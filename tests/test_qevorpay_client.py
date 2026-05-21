import pytest

from notary.models.schemas import QevorpayPaymentLinkRequest
from notary.services.qevorpay import QevorpayClient


@pytest.mark.asyncio
async def test_qevorpay_demo_payment_link() -> None:
    client = QevorpayClient(demo_mode=True)
    response = await client.create_payment_link(
        QevorpayPaymentLinkRequest(amount_usdc=25, description="Verified invoice")
    )
    assert response["status"] == "created"
    assert response["url"].startswith("https://pay.qevor.demo/")

