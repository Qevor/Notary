import pytest

from notary.app_service import NotaryAppService
from notary.config import Settings
from notary.services.arc import ArcClient
from notary.services.circle_agent import CircleAgentClient
from notary.services.circle_wallets_api import CircleDeveloperWalletClient


@pytest.mark.anyio
async def test_circle_cli_transfer_uses_current_agent_stack_syntax(monkeypatch):
    client = CircleAgentClient(demo_mode=False, chain="ARC-TESTNET", testnet=True)
    captured: dict[str, tuple[str, ...]] = {}

    async def fake_resolve_address(self, wallet_id):
        assert wallet_id == "0x" + "1" * 40
        return wallet_id

    async def fake_run(self, *args):
        captured["args"] = args
        return {"txHash": "0x" + "2" * 64}

    monkeypatch.setattr(CircleAgentClient, "_resolve_address", fake_resolve_address)
    monkeypatch.setattr(CircleAgentClient, "_run", fake_run)

    receipt = await client.transfer_usdc(
        from_wallet_id="0x" + "1" * 40,
        to_address="0x" + "3" * 40,
        amount=0.05,
    )

    args = captured["args"]
    assert args[:3] == ("wallet", "transfer", "0x" + "3" * 40)
    assert "--address" in args
    assert "--token" in args
    assert "--chain" in args
    assert "--from" not in args
    assert "--to" not in args
    assert receipt["status"] == "success"


@pytest.mark.anyio
async def test_circle_x402_paid_data_supports_post_body_and_headers(monkeypatch):
    client = CircleAgentClient(demo_mode=False, chain="ARC-TESTNET", testnet=True)
    captured: dict[str, tuple[str, ...]] = {}

    async def fake_default_agent_address(self):
        return "0x" + "4" * 40

    async def fake_run(self, *args):
        captured["args"] = args
        return {"paymentId": "x402_live_1", "status": "paid"}

    monkeypatch.setattr(CircleAgentClient, "_default_agent_address", fake_default_agent_address)
    monkeypatch.setattr(CircleAgentClient, "_run", fake_run)

    receipt = await client.pay_for_data(
        description="arbitrage scan",
        max_usdc=0.02,
        service_url="https://example.com/x402/arbitrage",
        method="POST",
        request_body='{"chain":"base","limit":5}',
        headers=["Content-Type: application/json"],
    )

    args = captured["args"]
    assert args[:3] == ("services", "pay", "https://example.com/x402/arbitrage")
    assert "-X" in args
    assert "POST" in args
    assert "-d" in args
    assert '{"chain":"base","limit":5}' in args
    assert "-H" in args
    assert "Content-Type: application/json" in args
    assert receipt["paymentId"] == "x402_live_1"


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


@pytest.mark.anyio
async def test_direct_user_send_prefers_circle_wallets_api(tmp_path, monkeypatch):
    settings = Settings(
        notary_db_path=tmp_path / "notary.sqlite3",
        notary_env="development",
        circle_api_key="TEST_API_KEY:abc:def",
        circle_entity_secret="1" * 64,
        circle_wallet_set_id="wallet-set-1",
    )
    service = NotaryAppService(settings)
    service.store.put(
        "profiles",
        "payer",
        {
            "username": "payer",
            "wallet": "0x" + "a" * 40,
            "circle_wallet_id": "circle-dev-wallet-payer",
        },
    )
    service.store.put(
        "profiles",
        "payee",
        {
            "username": "payee",
            "wallet": "0x" + "b" * 40,
            "circle_wallet_id": "circle-dev-wallet-payee",
        },
    )

    calls = []

    def fake_wallets_api_transfer_usdc(
        self,
        *,
        wallet_id,
        wallet_address,
        to_address,
        amount_usdc,
        ref_id=None,
    ):
        calls.append(
            {
                "wallet_id": wallet_id,
                "wallet_address": wallet_address,
                "to_address": to_address,
                "amount_usdc": amount_usdc,
                "ref_id": ref_id,
            }
        )
        return {
            "txHash": "0x" + "8" * 64,
            "status": "complete",
            "provider": "circle_developer_wallets",
            "demo": False,
        }

    async def fail_cli_transfer(*args, **kwargs):
        raise AssertionError("Circle CLI should not move developer-controlled user wallets")

    monkeypatch.setattr(CircleDeveloperWalletClient, "transfer_usdc", fake_wallets_api_transfer_usdc)
    monkeypatch.setattr(CircleAgentClient, "transfer_usdc", fail_cli_transfer)

    result = await service.send_user_funds(
        sender_email_or_id="payer",
        to_identity="payee",
        amount_usdc=3,
    )

    assert result["status"] == "completed"
    assert calls[0]["wallet_id"] == "circle-dev-wallet-payer"
    assert calls[0]["wallet_address"] == "0x" + "a" * 40
    assert calls[0]["to_address"] == "0x" + "b" * 40
    assert calls[0]["amount_usdc"] == 3


@pytest.mark.anyio
async def test_sponsored_yield_pays_from_reserve_and_records_arc_validation(tmp_path, monkeypatch):
    settings = Settings(
        notary_db_path=tmp_path / "notary_yield.sqlite3",
        notary_demo_mode=False,
        arc_demo_mode=False,
        arc_rpc_url="https://rpc.example",
        arc_chain_id=5042002,
        arc_operator_private_key="0x" + "1" * 64,
        validator_private_key="0x" + "2" * 64,
        notary_yield_mode="sponsored_reserve",
        notary_yield_reserve_private_key="0x" + "3" * 64,
        notary_yield_reserve_wallet="0x" + "4" * 40,
        notary_yield_target_apy_bps=1000,
        notary_yield_min_idle_usdc=1,
        notary_yield_payout_interval_seconds=86400,
        notary_yield_min_payout_usdc=0.000001,
        usyc_provider_address="0x9fdF14c5B14173D74C08Af27AebFf39240dC105A",
    )
    service = NotaryAppService(settings)
    service.store.put(
        "notaries",
        "notary_yield",
        {
            "notary_id": "notary_yield",
            "agent_wallet": "0x" + "a" * 40,
            "treasury_address": "0x" + "a" * 40,
            "capabilities": [],
            "status": "active",
        },
    )

    async def fake_get_usdc_balance(self, address, token_address=None):
        if address == settings.notary_yield_reserve_wallet:
            return 5.0
        return 11.0

    async def fake_transfer_usdc_from_key(self, *, private_key, to_address, amount_usdc, token_address=None):
        assert private_key == settings.notary_yield_reserve_private_key
        assert to_address == "0x" + "a" * 40
        assert amount_usdc > 0
        return {
            "txHash": "0x" + "5" * 64,
            "status": "submitted",
            "from": settings.notary_yield_reserve_wallet,
            "to": to_address,
            "amountUSDC": amount_usdc,
            "verification": {"status": "verified"},
            "demo": False,
        }

    monkeypatch.setattr(ArcClient, "get_usdc_balance", fake_get_usdc_balance)
    monkeypatch.setattr(ArcClient, "transfer_usdc_from_key", fake_transfer_usdc_from_key)

    result = await service.process_sponsored_yield(
        target_identity="notary_yield",
        force=True,
    )

    assert result["mode"] == "sponsored_reserve"
    assert result["results"][0]["lastStatus"] == "paid"
    assert result["results"][0]["payment"]["txHash"].startswith("0x")
    assert result["usyc"]["status"] == "awaiting_allowlist"
    assert service.store.list("yield_payouts")
    kinds = {item["kind"] for item in service.store.list("validations")}
    assert {"sponsored_yield_intent", "sponsored_yield_payout"}.issubset(kinds)
