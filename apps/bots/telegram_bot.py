from __future__ import annotations


COMMANDS = {
    "/create_notary": "Create an Arc identity and Qevorpay-ready Notary.",
    "/observe": "Submit an observation.",
    "/upload": "Upload evidence for Speedmatic transcription.",
    "/attest": "Create a signed attestation.",
    "/predict": "Create a prediction.",
    "/pay_when_verified": "Create a Qevorpay conditional payment.",
    "/dispute": "Open a payment dispute.",
    "/karma": "Show Notary karma.",
    "/privacy": "Set privacy mode.",
    "/buy_share": "Buy micro-shares in machine judgment.",
}


def describe_commands() -> dict[str, str]:
    return COMMANDS

