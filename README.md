# NOTARY

NOTARY is a Witness-to-Pay service on Arc. It judges whether a real-world obligation was fulfilled, signs the verdict, records the proof on Arc, and calls Qevor to move USDC.

> NOTARY decides. Qevor pays. Arc remembers.

NOTARY is not an escrow UI and not a multi-agent system. It is one sequential witness pipeline:

```text
Intake -> Verify -> Judge -> Attest -> Pay -> Learn
```

## What It Does

- Extracts a structured obligation from payment instructions.
- Captures human and agent counterparties with `human | agent` party types.
- Checks evidence coverage and integrity heuristically.
- Produces graded verdicts: full release, partial release, hold for clarification, or refund/refusal.
- Signs verdict attestations with EIP-712 and records Arc commitments.
- Calls Qevor wrappers for USDC release, partial release, hold, or refund.
- Re-opens disputed rulings, considers counter-evidence, and either upholds or revises itself.
- Issues linked reversal attestations when the original verdict was wrong.
- Maintains a public ledger and per-party operating history.

Evidence checks are heuristic, not forensic. NOTARY attestations are experimental and are not legal advice, legal certification, or a guarantee of admissibility.

## API

- `POST /witness/obligations` - submit an instruction and evidence.
- `POST /witness/rulings/{ruling_id}/dispute` - submit counter-evidence.
- `GET /witness/ledger` - inspect public ruling records.
- `GET /witness/parties/{party_identity}/history` - view a party operating history.
- `POST /media/transcribe` - upload audio/video evidence for Speechmatics transcription.
- `GET /state` - inspect local service state.

`POST /observations/cycle` is a compatibility intake surface, but it now adapts into the same witness pipeline.

## Required Live Configuration

Demo mode is disabled by default. Fill `.env` from `.env.example`.

Required for signed witness flow:

```env
VALIDATOR_PRIVATE_KEY=
ARC_DEMO_MODE=false
ARC_RPC_URL=
ARC_CHAIN_ID=
ARC_OPERATOR_PRIVATE_KEY=
ARC_ATTESTATION_REGISTRY=
QEVORPAY_DEMO_MODE=false
QEVORPAY_API_BASE_URL=
QEVORPAY_API_KEY=
QEVORPAY_RELEASE_ESCROW_PATH=
QEVORPAY_REFUND_PATH=
```

Required for recording transcription when no transcript is supplied:

```env
SPEECHMATICS_DEMO_MODE=false
SPEECHMATICS_API_KEY=
```

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn apps.api.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Tests

```bash
python3 -m pytest
```

## Privacy Model

Arc stores commitments: hashes, timestamps, signatures, verdict metadata, confidence, party identities/types, and revision links. Raw evidence stays off-chain in the evidence vault. Protected mode is the default.

## Out Of Scope

NOTARY intentionally does not implement multi-agent orchestration, social auto-posting, tokenized claim sales, treasury trading, ratings, underwriting, lending, or tranching.
