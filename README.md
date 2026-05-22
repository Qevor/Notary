# NOTARY

**Accountable AI witness and conditional payment release on Arc.**

NOTARY judges whether a real-world obligation was genuinely fulfilled and releases USDC based on that judgment. It is not an escrow app — escrow executes a decision a human or trivial oracle already made. NOTARY itself renders the verdict: graded, confidence-weighted, defensible, and correctable. It signs the verdict, records it on Arc, releases payment through Qevor, adjudicates disputes, and — the centerpiece — **reverses itself on the public record when shown to be wrong**.

> NOTARY decides. Qevor pays. Arc remembers.

## The bigger thesis

NOTARY is the **verification and attestation layer for the agent economy**. Before autonomous firms can be financed — underwritten, rated, lent to — their performance must be *verifiable*. Someone must be able to prove that an agent (or human) actually fulfilled a commercial obligation and that a payment was legitimately owed. NOTARY produces exactly that primitive: a signed, on-chain, dispute-tested, self-correcting record of obligation fulfillment. It is the auditable operating-history layer that agentic capital markets cannot form without.

Two concrete consequences for this build:
- Records are **financial-grade** — clean, machine-readable obligation-and-fulfillment records an underwriter could read.
- NOTARY witnesses **agent-to-agent obligations** on equal footing with human ones. Parties are addressed by identity; `*_type` fields distinguish human from agent everywhere.

## The Witness Pipeline

One orchestrator, six sequential stages. Each stage takes typed input, produces typed output. The orchestrator runs them in order and persists every intermediate artifact.

```
Intake → Verify → Judge → Attest → Pay → Learn
```

**1. Intake** — Reads submitted evidence (text, file, transcript, voice note, programmatic API call) and extracts a structured `Obligation` from the original payment instruction. Turns fuzzy language ("pay Daniel $250 when the design is done") into typed fields: `deliverable`, `acceptance_criterion`, `authorized_approver`, `deadline`, `satisfying_evidence`, plus `payer_type` / `payee_type` / `approver_type` (human or agent). When any element is ambiguous, surfaces it for confirmation rather than guessing. Uses an LLM for extraction; stores both raw instruction and parsed obligation.

**2. Verify** — Heuristic (not forensic) integrity check. Weighs verifiable artifacts (commits, timestamped files, signed messages) above unverifiable assertions. Outputs `evidence_quality_score` and `integrity_flags`. Labeled as heuristic throughout.

**3. Judge** — The core. Renders a **graded verdict**: full release, partial release (with percentage and named deficiency), hold-pending-clarification, or refuse/refund. Attaches a `confidence` score that gates behavior — high confidence releases; medium confidence releases with a dispute window open; low confidence escalates or requests more evidence. Consults the precedent base for consistency and produces a reasoning trace written as testimony: what was asked, what each evidence element established, where confidence was high or low, and the precise basis for the ruling.

**4. Attest** — Signs the verdict EIP-712 and hashes the attestation and reasoning trace to Arc. Stores: attestation hash, reasoning trace hash, evidence commitment hash, confidence, verdict, timestamp, signer, dispute state, party identities and types, and a link to the prior attestation when this is a revision. This on-chain record is what becomes precedent and what serves as the parties' verifiable operating history.

**5. Pay** — Executes the release per the verdict through Qevor's payment rails. NOTARY never calls payment primitives directly from judgment logic — it calls clean Qevor wrappers (release full, release partial amount, hold, refund, batch release). Settlement in USDC on Arc; fees via Paymaster.

**6. Learn** — Improves judgment from outcomes. Maintains and organizes the precedent base used by stage 3, and the per-party operating history. Not gamified scoring — a queryable record of prior verdicts, disputes, reversals, and how each held up. Each ruling feeds the next.

## Funded Conditional Cases

NOTARY now protects the payee before work starts by requiring a funded Qevor reserve before evidence becomes actionable.

Flow:

1. The payer creates a NOTARY case using Qevor usernames for payer and payee.
2. NOTARY resolves those usernames through Qevor's `profiles` table to wallet addresses.
3. NOTARY requires the payer to have an enrolled Qevor `ARC-TESTNET` agent wallet with an escrow address.
4. NOTARY creates a Qevor **conditional reserve** request, not a direct payee payment link.
5. Qevor's executor runs the `pending_reserve` state and, if payer policy allows it, moves USDC from the payer's agent wallet into the payer's escrow wallet.
6. Qevor sends NOTARY a signed settlement webhook with `state: funded`.
7. Only then does NOTARY expose the evidence invite link and move the case to `funded_awaiting_evidence`.
8. After the payee submits evidence, NOTARY judges and sends a signed post-verdict release/refund instruction to Qevor.

This separates **pre-work reserve funding** from **post-verdict release**. The payee is not asked to work against an unfunded promise, and Qevor still owns the actual USDC movement.

## The Reversal (centerpiece)

This is the single distinguishing capability. **NOTARY can reverse its own prior verdict, on the public record, when shown it was wrong — and must defend the reversal.**

A basic escrow app cannot be wrong because it never judged. NOTARY's trustworthiness comes precisely from being *correctable*: its mistakes and corrections are both permanent, both public, both signed.

- A reversal is triggered when dispute adjudication results in `revised`, or when new evidence after settlement materially changes the verdict.
- The reversal produces a **second attestation that explicitly references the original** (`supersedes` / `revises` link). Both are retained on Arc — the original is never deleted or overwritten. The chain is permanent and inspectable.
- The second attestation's reasoning trace states what the original verdict got wrong, what new evidence changed it, and why the new verdict is correct.
- If money already moved, the reversal computes the corrective payment action (top-up, partial clawback request, or refund) and routes it through Qevor wrappers. Where a clawback is not enforceable, the corrected verdict and outstanding delta are recorded honestly.
- Reversals are **first-class in the public ledger and per-party operating history**. A NOTARY that has reversed itself, with reasoning, is presented as *more* credible — surfaced as accountability, not failure.

Demo path: initial ruling → appeal with counter-evidence → NOTARY changes its mind under evidence → linked second attestation on Arc → corrective payment → reversal shown as a trust mark in the record.

## Dispute Adjudication

When a verdict is contested, NOTARY re-opens the evidence, weighs the disputing party's counter-evidence, and either upholds or revises the original ruling — defending the change or the consistency in its reasoning trace. The original on-chain attestation is the record it is held to. NOTARY is the arbiter, not a punt to a human or DAO.

Flow: dispute intake → counter-evidence ingestion → re-judgment against the same obligation → `upheld | revised` outcome with written justification → new signed attestation linked to the original.

## Data Models

```python
Obligation(deliverable, acceptance_criterion, authorized_approver, deadline,
           satisfying_evidence, payer_type, payee_type, approver_type,
           clarification_needed)

Evidence(type, ref, commitment_hash, encrypted_blob_ref,
         submitter_identity, submitter_type)

IntegrityReport(source_quality, integrity_flags, approved, notes)

Verdict(outcome, release_pct, confidence, deficiency, reasoning_trace,
        precedent_refs)

Attestation(hashes, signer, timestamp, dispute_state, privacy_mode,
            party_identities, supersedes_ref, revises_ref)

Dispute(counter_evidence, outcome, justification, linked_attestation)

Reversal(original_attestation_ref, new_attestation_ref, what_changed,
         corrective_payment_action, outstanding_delta)

PartyOperatingHistory(party_identity, party_type, rulings[],
                      dispute_flags, reversal_flags)

PaymentInstruction  # Qevor wrapper request
```

## Privacy Model

Public proof, private evidence. Arc stores commitments only — hashes, timestamps, signatures, verdict, confidence, party identities, attestation links. Raw evidence (audio, transcripts, files, full reasoning) is stored off-chain and encrypted, never on-chain. Default disclosure: public sees hash and verdict summary; counterparties see relevant excerpts; a dispute-unlock process grants arbitrator access to the full bundle.

## Public Ledger

Browsable, inspectable record of verdicts, reasoning traces, dispute outcomes, and reversals. Privacy-respecting: only hashes and summaries public by default. This is where precedent lives, where reversals are surfaced as credibility, and where the witness earns trust — the civic notary's public book of judgments.

## Circle + Arc Stack

- **USDC** — unit of settlement.
- **Circle Agent Wallet / App Kit** — NOTARY's wallet and execution surface (Qevor already integrates App Kit; reused here).
- **Paymaster** — fees in USDC; users never touch a gas token.
- **Arc Testnet** — attestation, precedent, and reversal records; EIP-712 signatures; deterministic sub-second finality; low per-ruling USDC fees that make per-ruling and per-reversal on-chain records economical.
- **Gateway / CCTP** — path to bring user USDC from another chain to Arc when NOTARY needs to act.

## Architecture

NOTARY is a separate service that consumes Qevor's API. It owns: obligation extraction, the pipeline, verdicts, reasoning traces, precedent base, dispute logic, reversal logic, and per-party operating history. Qevor owns: identity, payment execution, settlement. The seam — NOTARY decides → calls Qevor to execute — is the load-bearing integration.

```
flowchart LR
  API[FastAPI + Telegram] --> Intake
  Intake --> Verify
  Verify --> Judge
  Judge --> Attest
  Attest --> Pay
  Pay --> Learn

  Intake --> Speechmatics[Speechmatics / mock]
  Attest --> Arc[Arc Testnet Contracts]
  Pay --> Qevor[Qevor Payment Rails]
  Judge --> Precedent[(Precedent Base)]
  Learn --> Precedent
  Attest --> Vault[Encrypted Evidence Vault]
  Judge --> OperatingHistory[(Party Operating History)]
```

## Contracts

Five Solidity contracts deployed to Arc Testnet via Foundry:

- `NotaryIdentityRegistry.sol` — ERC-8004-style identity records for machine witnesses (human or agent parties).
- `AttestationRegistry.sol` — verdict hashes, reasoning trace hashes, evidence commitments, and revision links.
- `NotaryValidationRegistry.sol` — transcript, payment, dispute, and external validation records.
- `HelixAIKarma.sol` — signed performance checkpoints; queryable operating history.
- `NotaryGovernance.sol` — operating agreement, permitted actions, and upgrade records.

## Setup

### Requirements

- Python 3.12+
- Foundry (`forge`) for contract deployment
- Circle CLI (`npm install -g @circle-fin/cli`) for live Circle Agent Wallet operations
- ARC CLI (`uv tool install git+https://github.com/the-canteen-dev/ARC-cli`) for Arc Testnet RPC access
- Qevor credentials (existing deployed app on Arc Testnet)
- Speechmatics credentials (or use the local mock fallback)

### Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env
```

### Environment

See `.env.example` for all settings. The full pipeline runs locally with SQLite and local demo stubs before any external credentials are connected:

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

When real credentials are added, set the relevant `*_DEMO_MODE` to `false` and configure the matching API keys, base URLs, and paths.

**LLM reasoning** — set `GROQ_API_KEY` or `CLAUDE_API_KEY` (either alone is sufficient) to enable live LLM-powered judgment. When both are set, Groq handles obligation extraction and Claude handles the reflector stage.

**Arc signing** — set `VALIDATOR_PRIVATE_KEY` for real EIP-712 signatures on attestations, verdicts, and reversals.

**Arc submission** — set `ARC_RPC_URL`, `ARC_CHAIN_ID`, `ARC_OPERATOR_PRIVATE_KEY`, and the five contract addresses to submit attestation and validation records to the testnet.

**Circle** — set `CIRCLE_WALLET_EMAIL` and authenticate the session (see Circle CLI section below).

**Qevor paths** — `QEVORPAY_*_PATH` values are required in live mode because Qevor's endpoint contracts are project-specific.

**Qevor Supabase integration** — live conditional reserves use Qevor Supabase tables directly when no HTTP endpoint is configured. Required server-side values:

```env
QEVOR_SUPABASE_URL=
QEVOR_SUPABASE_SERVICE_ROLE_KEY=
QEVORPAY_WEBHOOK_SECRET=
```

Qevor must have migrations `03_notary_attestation.sql` and `04_conditional_reserves.sql` applied before live funded cases work.

**Speechmatics** — uses the documented Batch API defaults (`https://asr.api.speechmatics.com/v2`). Set `SPEECHMATICS_API_KEY` to enable real transcription; without it the pipeline accepts a pasted transcript or runs with a mock.

**Evidence vault** — set `EVIDENCE_VAULT_PASSPHRASE` for deterministic encryption. If omitted, a local vault key file is generated on first run.

### Circle CLI

```bash
npm install -g @circle-fin/cli
```

Authenticate the agent wallet session:

1. `POST /circle/login/init`
2. Check the configured Circle wallet email for the OTP.
3. `POST /circle/login/complete`
4. Verify with `GET /circle/status`.

### Run

```bash
# Fastest path — stdlib server, no dependencies beyond the package
python main.py

# FastAPI with hot-reload
uvicorn apps.api.main:app --reload

# Open
open http://127.0.0.1:8000
```

The dashboard shows the NOTARY pipeline state: active obligations, attestations, verdicts, disputes, reversals, payment status, and the public ledger.

### Deploy Arc Contracts

```bash
forge build
python scripts/deploy_arc.py
```

Requires: `ARC_RPC_URL`, `ARC_OPERATOR_PRIVATE_KEY`.

## API Surfaces

All endpoints callable programmatically so an agent counterparty can submit obligations and evidence without a human UI.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/notaries` | Register a new NOTARY identity on Arc |
| `POST` | `/observations/cycle` | Submit evidence + run the full pipeline |
| `POST` | `/media/transcribe` | Upload audio/video; transcribe and run pipeline |
| `POST` | `/media/attest` | Paste transcript; run pipeline |
| `POST` | `/qevorpay/payment-link` | Create a conditional Qevor payment link |
| `POST` | `/evidence/grants` | Grant evidence access to a counterparty or arbitrator |
| `GET` | `/attestations` | Public ledger of signed verdicts |
| `GET` | `/karma` | Signed performance checkpoints |
| `GET` | `/payments` | Payment links and trigger history |
| `GET` | `/state` | Full dashboard state |
| `GET` | `/circle/status` | Circle wallet session state |
| `GET` | `/speechmatics/status` | Speechmatics provider config |

## Intake Surfaces

- **Web dashboard** — paste a transcript, upload a voice note or work-call recording, choose privacy mode, run Witness-to-Pay.
- **Telegram bot** — send a voice note or message; NOTARY transcribes, extracts the obligation, judges, and returns the verdict.
- **Programmatic API** — any endpoint above is callable by an agent counterparty with no human UI required.

## Implementation Status

### Implemented

- Sequential witness pipeline (Intake → Verify → Judge → Attest → Pay → Learn), demo + live paths
- EIP-712 signing on verdicts, attestations, and karma checkpoints via `eth-account`
- Arc RPC submission for all five contracts; direct JSON-RPC encoding without CLI dependency
- Qevor wrappers: create payment link, release escrow, batch distribution, refund
- Circle Agent Wallet CLI adapter: login, wallet creation/discovery, Gateway balance/deposit, x402 service payments
- Speechmatics Batch API adapter with local mock fallback
- Encrypted local evidence vault (openssl-backed)
- SQLite persistence for all pipeline artifacts
- FastAPI with live dashboard, media upload, transcript attestation, and payment link UI
- Telegram bot surface
- Contract deployment helper via Foundry (`scripts/deploy_arc.py`)
- Privacy modes (public / protected / private) with evidence access grants
- Claude API as drop-in LLM fallback when no Groq key is set

### In Progress / Next

- Structured `Obligation` extraction with typed fields (`deliverable`, `acceptance_criterion`, `deadline`, `payer_type`, `payee_type`) and ambiguity-surfacing
- Graded verdict: partial release with percentage and named deficiency; confidence-gated hold/escalate path
- Dispute adjudication: counter-evidence intake, re-judgment, `upheld | revised` outcome, linked second attestation
- **The Reversal**: superseding attestation chain on Arc, self-correction reasoning trace, corrective payment routing, reversal surfaced as credibility in operating history
- `PartyOperatingHistory` view: queryable per-party record of obligations, verdicts, disputes, and reversals
- `supersedes_ref` / `revises_ref` links in `Attestation` model
- Precedent base: similarity-match over stored rulings exposed in reasoning trace
- Public ledger UI: browsable verdicts, disputes, reversals with privacy-respecting summaries
- Agent-to-agent party type fields wired end-to-end

## Legal Notice

NOTARY produces evidence-grade signed attestations modeled on structured obligation-fulfillment records. This is experimental and not legal advice. Records are auditable in structure; they are not legally certified documents, guaranteed-admissible evidence, or regulated financial instruments.

The Wyoming DAO LLC / Bayern mechanism operating agreement module is an experimental legal-operational framework and is not legal advice.
