from apps.api.dashboard import render_public_ledger


def test_public_ledger_links_trace_hashes_to_arcscan_search(monkeypatch):
    monkeypatch.setenv("ARC_EXPLORER_BASE_URL", "https://testnet.arcscan.app")
    trace_hash = "0x" + "a" * 64
    arc_tx = "0x" + "b" * 64

    html = render_public_ledger(
        {
            "rulings": [
                {
                    "rulingId": "ruling_1",
                    "attestationId": "att_1",
                    "arcTxHash": arc_tx,
                    "verdict": "hold_pending_clarification",
                    "releasePct": 0,
                    "confidence": 0.5,
                    "confidenceGate": "request_more_evidence",
                    "reasoningTrace": "trace",
                    "reasoningTraceHash": trace_hash,
                    "obligation": {
                        "deliverable": "delivery",
                        "acceptance_criterion": "approval",
                    },
                    "obligationSummary": "delivery",
                    "partyIdentities": {"payer": "@payer", "payee": "@payee"},
                }
            ]
        }
    )

    assert f"https://testnet.arcscan.app/search?q={trace_hash}" in html
    assert f"https://testnet.arcscan.app/tx/{arc_tx}" in html
