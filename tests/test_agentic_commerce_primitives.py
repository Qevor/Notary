import pytest

from notary.app_service import NotaryAppService
from notary.config import Settings


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
