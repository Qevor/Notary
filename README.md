# NOTARY

### The Autonomous AI Witness Layer for Programmable USDC Payments on Arc

> **Strongest Pitch:** NOTARY turns real-world proof — voice notes, files, videos, work logs, and approvals — into signed AI attestations that trigger programmable USDC payments on Arc.

---

## Core Product Positioning

NOTARY is the **AI witness infrastructure layer for programmable internet payments**. It is no longer a payment side-feature, trading platform, or generic swarm economy experiment. Instead, it is a trust-native witness engine designed to verify real-world proof and trigger instant stablecoin settlement.

Everything revolves around one core primitive:
```text
Proof ──> Verification ──> Attestation ──> Settlement
```

---

## The 3-Layer Product Structure

NOTARY organizes its processing pipeline into three clear layers:

| Layer | Purpose | Technical Components |
|---|---|---|
| **Observation Layer** | Collect evidence from users and the world | Speechmatics batch voice transcription, local encrypted vault, media upload API, Telegram/WhatsApp inputs. |
| **Intelligence Layer** | Verify, reason, score confidence, authorize | LLM obligation extraction, heuristic verification, graded verdict judgment, precedent checks, self-correction/reversals. |
| **Settlement Layer** | Trigger programmable USDC actions | `NotaryEscrowClient` integration, Circle Agent wallets, Gateway routing, Paymaster gas abstraction, Arc Testnet blockchain commitments. |

---

## Core User Roles

1. **Payer (Funder of conditional payments):**
   * *Examples:* Employers, freelancer clients, DAOs, business owners, buyers, team leads, or event organizers.
2. **Payee (Recipient after witness verification):**
   * *Examples:* Freelancers, contractors, contributors, vendors, delivery agents, creators, or consultants.

---

## Main Product Flows

### FLOW 1 — Verified Freelancer Payment
1. **Payer Creates Payment Intent:** A client drafts a natural language contract (e.g. *"Pay Sarah $500 when the final Figma file is uploaded and approved"*).
2. **Circle Embedded Wallet Creation:** NOTARY instantly resolves identities, creating Circle embedded wallets, EIP-712 signing profiles, and Arc identity records.
3. **Escrow Funding:** The payer deposits USDC into a secure conditional vault on Arc (facilitated by Circle USDC, Gateway, and Paymaster).
4. **Evidence Submission:** The payee uploads the final Figma file link, GitHub commit hash, or video walk-through.
5. **AI Witness Analysis:** The scanner scans the signals, the sentinel checks for integrity/anti-spoofing, and the risk guardian computes the confidence verdict.
6. **Attestation Generation:** Validator signs EIP-712 attestation hashes and submits them to the Arc chain registries.
7. **Instant Settlement:** NOTARY strategy engine executes a Circle-backed USDC transfer from the escrow vault to the payee's wallet.

### FLOW 2 — Voice Note to Payment (The Killer Demo)
1. **Voice Note Intake:** User sends a WhatsApp voice note: *"Pay Daniel $250 when he uploads the final animation and I approve it."*
2. **Speechmatics Transcription:** Converts speech to a structured transcript. Legacy Speedmatic env aliases are still accepted for compatibility.
3. **Signal Scanner Extraction:** Pulls payment amount ($250), recipient (@daniel), deliverables (animation), and approval triggers.
4. **Automated Escrow Setup:** NOTARY automatically creates the escrow vault, registers the payment condition, and logs the Arc proof record.

### FLOW 3 — Dispute Resolution
1. **Dispute Ingestion:** Payer claims work is incomplete, or Payee disputes a holding. Both parties upload screenshots, work logs, or transcripts.
2. **Timeline Analysis:** Signal Scanner maps obligations; Reflector analyzes agreement vs outcome.
3. **Resolution Verdict:** Risk Guardian recommends a release, refund, or split settlement. Validator signs the dispute recommendation and Settlement executes.

### FLOW 4 — Verified Invoice ("Trust-Native Invoice")
1. **Invoice Package:** Seller creates an invoice and binds it to a verifiable proof package (e.g., GitHub commit, delivery manifest, or video walk-through).
2. **Trust Evaluation:** Buyer receives the invoice along with the AI witness confidence score, transcript summary, and Arc verification link.

### FLOW 5 — DAO / Team Payouts
1. **Deliverable Tracking:** Signal Scanner monitors contributor activities (GitHub commits, attendance, or work logs).
2. **USDC Batch Distribution:** Strategy Engine triggers batch-payments to all qualified contributors using Circle embedded wallets.

---

## Swarm Agent Architecture

The NOTARY swarm is a **6-agent LangGraph network** focused entirely on machine verification and settlement:

```text
       ┌──────────────┐     ┌───────────┐     ┌─────────────┐
 Entry │    Signal    │ ──> │ Guardian  │ ──> │    Risk     │
 ─────>│   Scanner    │     │ Sentinel  │     │   Guardian  │
       └──────────────┘     └───────────┘     └─────────────┘
              ▲                                      │
              │                                      ▼
       ┌──────────────┐     ┌───────────┐     ┌─────────────┐
       │  Reflector   │ <── │ Validator │ <── │  Strategy   │
       │ (KarmaForge) │     │ (EIP-712) │     │   Engine    │
       └──────────────┘     └───────────┘     └─────────────┘
```

1. **Signal Scanner:** Observes evidence (voice notes, PDFs, commits, sentiment signals) and extracts structured facts and conditions.
2. **Guardian Sentinel:** Protects the system against fake evidence, prompt injection, spoofed approvals, and malicious code/drains.
3. **Risk Guardian:** Calculates confidence scores, release thresholds, safety risk, and dispute windows.
4. **Strategy Engine:** Executes conditional escrow creation, USDC releases, refunds, milestone payouts, and batch distributions via Circle & Arc.
5. **Validator:** Cryptographically signs EIP-712 attestations, verdicts, and proof commitments for Arc chain storage.
6. **Reflector:** A self-critique engine that evaluates disputes and outcomes, updating on-chain karma and refining judgment rules.

---

## Arc + Circle Integration Stack

### Circle Stack Usage
- **Circle Wallets:** Embedded agent wallets for payer, payee, and executor.
- **USDC:** Core stablecoin for escrow funding and payment settlement.
- **Gateway & CCTP:** Cross-chain routing to fetch USDC from outside chains.
- **Paymaster:** Abstracting gas fees so users settle without holding native gas tokens.
- **App Kit:** User onboarding and secure wallet login UX.
- **USYC:** Generating yield on idle escrow reserves.

### Arc Chain Usage
- **Identity Layer:** Mapping usernames to EVM addresses via `NotaryIdentityRegistry`.
- **Attestation Layer:** Committing verdict hashes, evidence signatures, and reasoning traces to `AttestationRegistry`.
- **Settlement Layer:** On-chain validation rules and trigger logic.
- **Reputation Layer:** Recording validator performance and karma checks via `HelixAIKarma`.
- **Governance:** Operating agreements and permissions via `NotaryGovernance`.

### Verifiability Rule
NOTARY fails closed on payment state. A case can exist as an off-chain work request, but it is not marked funded, released, refunded, or paid unless the backend can verify the relevant Arc transaction through RPC.

Funding verification requires a successful Arc USDC `Transfer` log from the payer wallet to the case reserve wallet for at least the case amount. The checkout page therefore asks for an Arc transaction hash and unlocks evidence only after that hash is verified against the expected wallets and amount.

In live mode (`NOTARY_DEMO_MODE=false`), user onboarding also requires real Circle agent wallet provisioning. The app does not silently invent local wallets when Circle CLI/operator authentication is unavailable.

### Arc + Circle Coverage
NOTARY now exposes its full hackathon surface through executable routes instead of README-only claims:

- Arc registries: identity, attestation, validation, governance, karma, ERC-8004-style agent identity, and replication contract sources.
- Circle stack: agent-wallet onboarding, Gateway deposit preparation, Paymaster-aware USDC UX, x402 paid-data calls, and unified-balance lookups.
- Intelligence layer: Speechmatics/Speedmatic-compatible media observation, obligation extraction, Guardian/Risk/Strategy/Validator/Reflector flow, graded verdicts, disputes, reversals, and reasoning trace hashes.
- Commerce layer: Pay-to-Peek reasoning access, prediction commitments, micro-share purchases, USYC allocation intents, arbitrage signal analysis, karma checkpoints, policy DNA, and self-replication.

Use `GET /coverage` to inspect the current configured/live status of each primitive.

---

## Project Setup & Running

### Requirements
* Python 3.11+
* Foundry (`forge`) for smart contract compilation
* ARC CLI for Arc Testnet RPC access
* Supabase Account & Database tables

### Setup Instructions
```bash
# Clone the repository
git clone <repo-url> && cd NOTARY

# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install package dependencies
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env
```

### Running the Server
```bash
# Start the FastAPI dashboard & API server
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000` to interact with the console.

### Deploying Arc Contracts
```bash
# Build contracts
forge build

# Run deployment script
.venv\Scripts\python scripts/deploy_arc.py
```
