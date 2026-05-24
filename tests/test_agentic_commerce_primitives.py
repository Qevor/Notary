import pytest

from notary.app_service import NotaryAppService
from notary.config import Settings
from notary.services.arc import ArcClient
from notary.services.circle_agent import CircleAgentClient
from notary.services.circle_wallets_api import CircleDeveloperWalletClient


@pytest.mark.anyio
async def test_agentic_commerce_primitives_are_operational(tmp_path):
    settings = Settings(
        notary_db_path=tmp_path / "notary_commerce.sqlite3",
        notary_demo_mode=True,
        arc_demo_mode=True,
    )
    service = NotaryAppService(settings)

    notary = await service.create_notary("commerce-agent")
    notary_id = notary["identity"]["notary_id"]

    coverage = await service.feature_coverage()
    assert coverage["notary"]["tradeableIntelligence"]["route"] == "/commerce/micro-shares"
    assert coverage["arc"]["eip712"]["domain"] == "NOTARY"

    prediction = await service.create_prediction(
        question="Will the submitted work be accepted within 24 hours?",
        probability_bps=7200,
        horizon="24h",
        rationale="Evidence quality and prior acceptance history are strong.",
        notary_id=notary_id,
    )
    assert prediction["reasoningTraceHash"].startswith("0x")

    share = await service.buy_micro_share(
        prediction_id=prediction["predictionId"],
        buyer_identity="alice",
        amount_usdc=0.25,
    )
    assert share["predictionId"] == prediction["predictionId"]

    service.store.put(
        "rulings",
        "ruling_market_1",
        {
            "ruling_id": "ruling_market_1",
            "notary_id": notary_id,
            "attestation": {"reasoning_trace_hash": "0x" + "a" * 64},
        },
    )
    peek = await service.create_reasoning_pay_to_peek(
        ruling_id="ruling_market_1",
        buyer_identity="alice",
        amount_usdc=0.01,
    )
    assert peek["reasoningTraceHash"] == "0x" + "a" * 64

    karma = await service.record_karma_checkpoint(
        notary_id=notary_id,
        delta=12,
        reason="Accurate funded ruling",
    )
    assert karma["score"] == 12

    identity = await service.register_agent_identity_erc8004(
        notary_id=notary_id,
        service_endpoint="https://notaryonarc.com/agents/commerce-agent",
    )
    assert identity["serviceHash"].startswith("0x")

    replication = await service.replicate_notary(
        parent_notary_id=notary_id,
        mutation_prompt="Specialize in invoice evidence",
        min_karma=10,
    )
    assert replication["parentNotaryId"] == notary_id
    assert replication["policyDnaHash"].startswith("0x")

    usyc = await service.create_usyc_intent(
        notary_id=notary_id,
        amount_usdc=100,
    )
    assert usyc["status"] == "demo_intent"

    arb = await service.analyze_arbitrage(
        base_asset="USDC",
        quote_asset="USD",
        amount_usdc=1000,
        venues=[
            {"venue": "VenueA", "bid": 1.002, "ask": 1.000, "feeBps": 3},
            {"venue": "VenueB", "bid": 1.010, "ask": 1.006, "feeBps": 3},
        ],
    )
    assert arb["safeToExecute"] is True
    assert arb["estimatedProfitUSDC"] > 0

    validations = service.store.list("validations")
    kinds = {item["kind"] for item in validations}
    assert {
        "prediction_commitment",
        "micro_share_purchase",
        "pay_to_peek_reasoning",
        "karma_checkpoint",
        "erc8004_agent_identity",
        "notary_replication",
        "usyc_treasury_intent",
        "arbitrage_signal",
    }.issubset(kinds)


@pytest.mark.anyio
async def test_live_commerce_primitives_auto_pay_with_circle(tmp_path, monkeypatch):
    settings = Settings(
        notary_db_path=tmp_path / "notary_live_commerce.sqlite3",
        notary_demo_mode=False,
        arc_demo_mode=False,
        arc_rpc_url="https://rpc.example",
        arc_chain_id=5042002,
        arc_operator_private_key="0x" + "1" * 64,
        validator_private_key="0x" + "2" * 64,
        circle_api_key="TEST_API_KEY:abc:def",
        circle_entity_secret="1" * 64,
        circle_wallet_set_id="wallet-set-1",
        usyc_provider_address="0x" + "9" * 40,
    )
    service = NotaryAppService(settings)
    service.store.put(
        "notaries",
        "notary_live",
        {
            "notary_id": "notary_live",
            "agent_wallet": "0x" + "a" * 40,
            "treasury_address": "0x" + "a" * 40,
            "capabilities": [],
            "status": "active",
        },
    )
    service.store.put(
        "profiles",
        "alice",
        {
            "username": "alice",
            "wallet": "0x" + "b" * 40,
            "circle_wallet_id": "circle-dev-wallet-alice",
        },
    )

    async def fake_transfer_usdc(self, *, from_wallet_id, to_address, amount):
        return {
            "txHash": "0x" + "c" * 64,
            "from": from_wallet_id,
            "to": to_address,
            "amount": amount,
            "status": "success",
            "demo": False,
        }

    def fake_wallets_api_transfer_usdc(
        self,
        *,
        wallet_id,
        wallet_address,
        to_address,
        amount_usdc,
        ref_id=None,
    ):
        return {
            "id": "circle-tx-1",
            "transactionId": "circle-tx-1",
            "txHash": "0x" + "c" * 64,
            "fromWalletId": wallet_id,
            "fromWalletAddress": wallet_address,
            "to": to_address,
            "amount": amount_usdc,
            "status": "submitted",
            "provider": "circle_developer_wallets",
            "demo": False,
        }

    async def fake_verify_usdc_transfer(self, *, tx_hash, from_address, to_address, amount_usdc, token_address=None):
        return {
            "txHash": tx_hash,
            "status": "verified",
            "from": from_address,
            "to": to_address,
            "amount_usdc": amount_usdc,
        }

    monkeypatch.setattr(CircleAgentClient, "transfer_usdc", fake_transfer_usdc)
    monkeypatch.setattr(CircleDeveloperWalletClient, "transfer_usdc", fake_wallets_api_transfer_usdc)
    monkeypatch.setattr(ArcClient, "verify_usdc_transfer", fake_verify_usdc_transfer)

    prediction = await service.create_prediction(
        question="Will live users buy a NOTARY prediction share?",
        probability_bps=6100,
        horizon="48h",
        rationale="The live app now executes Circle transfers when no tx hash is supplied.",
        notary_id="notary_live",
    )
    share = await service.buy_micro_share(
        prediction_id=prediction["predictionId"],
        buyer_identity="@alice",
        amount_usdc=0.25,
    )
    assert share["payment"]["mode"] == "circle_wallets_api_transfer"
    assert share["paymentVerification"]["status"] == "verified"

    service.store.put(
        "rulings",
        "ruling_live_market",
        {
            "ruling_id": "ruling_live_market",
            "notary_id": "notary_live",
            "attestation": {"reasoning_trace_hash": "0x" + "d" * 64},
        },
    )
    peek = await service.create_reasoning_pay_to_peek(
        ruling_id="ruling_live_market",
        buyer_identity="@alice",
        amount_usdc=0.01,
    )
    assert peek["payment"]["mode"] == "circle_wallets_api_transfer"

    usyc = await service.create_usyc_intent(
        notary_id="notary_live",
        amount_usdc=1,
    )
    assert usyc["status"] == "submitted_to_usyc_provider"
    assert usyc["payment"]["to"] == settings.usyc_provider_address
