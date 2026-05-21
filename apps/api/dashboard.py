from __future__ import annotations

from html import escape
from typing import Any


def render_dashboard(state: dict[str, list[dict[str, Any]]]) -> str:
    notary_count = len(state["notaries"])
    attestation_count = len(state["attestations"])
    payment_count = len(state["payments"]) + len(state.get("payment_triggers", []))
    karma = state["karma"][-1] if state["karma"] else None
    karma_score = karma.get("score", "n/a") if karma else "n/a"
    speechmatics = state.get("speechmatics", {})
    speechmatics_configured = "configured" if speechmatics.get("configured") else "needs key"

    latest_attestations = "".join(
        f"""
        <article class="item">
          <div class="eyebrow">{escape(item.get("privacy_mode", "protected"))}</div>
          <h3>{escape(item.get("statement", "Attestation"))}</h3>
          <p>Confidence: {escape(str(item.get("confidence", "n/a")))} · Status: {escape(item.get("status", "n/a"))}</p>
          <code>{escape(item.get("attestation_id", ""))}</code>
        </article>
        """
        for item in reversed(state["attestations"][-5:])
    )

    latest_predictions = "".join(
        f"""
        <article class="item">
          <div class="eyebrow">Prediction</div>
          <h3>{escape(item.get("question", "Prediction"))}</h3>
          <p>Probability: {escape(str(item.get("probability", "n/a")))}</p>
        </article>
        """
        for item in reversed(state["predictions"][-5:])
    )
    latest_payments = "".join(
        f"""
        <article class="item">
          <div class="eyebrow">Qevorpay</div>
          <h3>{escape(item.get("request", {}).get("description", "Payment link"))}</h3>
          <p>Status: {escape(item.get("status", "n/a"))}</p>
          <code>{escape(item.get("url", ""))}</code>
        </article>
        """
        for item in reversed(state["payments"][-5:])
    )

    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>NOTARY</title>
        <style>
          :root {{
            color-scheme: light;
            --ink: #151515;
            --muted: #62625f;
            --line: #d8d5cc;
            --paper: #f7f3ea;
            --panel: #fffaf0;
            --accent: #116149;
            --accent-2: #a23b2a;
            --gold: #b98323;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--paper);
            color: var(--ink);
          }}
          header {{
            display: flex;
            justify-content: space-between;
            gap: 24px;
            padding: 28px 36px;
            border-bottom: 1px solid var(--line);
            align-items: center;
          }}
          h1, h2, h3, p {{ margin-top: 0; }}
          h1 {{ font-size: clamp(32px, 5vw, 62px); line-height: .96; margin-bottom: 10px; max-width: 760px; }}
          .tagline {{ color: var(--muted); max-width: 760px; font-size: 18px; }}
          .status {{
            display: grid;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 10px;
            padding: 18px 36px;
            border-bottom: 1px solid var(--line);
          }}
          .metric {{ border: 1px solid var(--line); background: var(--panel); padding: 14px; border-radius: 8px; }}
          .metric strong {{ display: block; font-size: 24px; }}
          main {{ display: grid; grid-template-columns: minmax(320px, 420px) 1fr; gap: 28px; padding: 28px 36px; }}
          section {{ min-width: 0; }}
          .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
          label {{ display: block; font-weight: 700; margin: 12px 0 6px; }}
          input, textarea, select {{
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 10px 12px;
            font: inherit;
            background: white;
          }}
          textarea {{ min-height: 150px; resize: vertical; }}
          button {{
            border: 0;
            background: var(--accent);
            color: white;
            border-radius: 6px;
            padding: 11px 14px;
            font-weight: 800;
            cursor: pointer;
            margin-top: 12px;
            width: 100%;
          }}
          .secondary {{ background: var(--accent-2); }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
          .item {{ border: 1px solid var(--line); border-radius: 8px; background: white; padding: 14px; }}
          .eyebrow {{ color: var(--gold); font-weight: 900; text-transform: uppercase; font-size: 12px; letter-spacing: .06em; }}
          code {{ display: block; overflow: auto; color: var(--muted); font-size: 12px; }}
          @media (max-width: 900px) {{
            header, main, .status {{ padding-left: 18px; padding-right: 18px; }}
            main {{ grid-template-columns: 1fr; }}
            .status {{ grid-template-columns: repeat(2, 1fr); }}
          }}
        </style>
      </head>
      <body>
        <header>
          <div>
            <h1>NOTARY</h1>
            <p class="tagline">Verified payments for the agent economy. Upload proof, choose privacy, produce an attestation, and trigger Qevorpay when the facts check out.</p>
          </div>
        </header>
        <div class="status">
          <div class="metric"><span>Notaries</span><strong>{notary_count}</strong></div>
          <div class="metric"><span>Attestations</span><strong>{attestation_count}</strong></div>
          <div class="metric"><span>Payments</span><strong>{payment_count}</strong></div>
          <div class="metric"><span>Karma</span><strong>{escape(str(karma_score))}</strong></div>
          <div class="metric"><span>Speechmatics</span><strong>{escape(speechmatics_configured)}</strong></div>
        </div>
        <main>
          <section>
            <div class="panel">
              <h2>Create Notary</h2>
              <form method="post" action="/ui/notaries">
                <label for="label">Label</label>
                <input id="label" name="label" placeholder="Client escrow witness" />
                <button>Create Notary</button>
              </form>
            </div>
            <div class="panel">
              <h2>Attest Transcript</h2>
              <form method="post" action="/ui/attest">
                <label for="privacy_mode">Privacy</label>
                <select id="privacy_mode" name="privacy_mode">
                  <option value="protected">Protected</option>
                  <option value="private">Private</option>
                  <option value="public">Public</option>
                </select>
                <label for="transcript_text">Transcript or voice-note text</label>
                <textarea id="transcript_text" name="transcript_text" placeholder="Client: The work is complete. Please release payment."></textarea>
                <button>Run Witness-to-Pay</button>
              </form>
            </div>
            <div class="panel">
              <h2>Upload Audio/Video Evidence</h2>
              <form method="post" action="/ui/media" enctype="multipart/form-data">
                <label for="media_privacy_mode">Privacy</label>
                <select id="media_privacy_mode" name="privacy_mode">
                  <option value="protected">Protected</option>
                  <option value="private">Private</option>
                  <option value="public">Public</option>
                </select>
                <label for="file">Evidence file</label>
                <input id="file" name="file" type="file" />
                <label for="media_transcript_text">Transcript text when Speechmatics is not connected</label>
                <textarea id="media_transcript_text" name="transcript_text" placeholder="Paste transcript or leave blank for Speechmatics processing."></textarea>
                <button>Upload Evidence</button>
              </form>
            </div>
            <div class="panel">
              <h2>Create Qevorpay Link</h2>
              <form method="post" action="/ui/payment-link">
                <label for="amount_usdc">Amount USDC</label>
                <input id="amount_usdc" name="amount_usdc" type="number" min="0.01" step="0.01" value="25" />
                <label for="description">Description</label>
                <input id="description" name="description" value="Verified NOTARY payment" />
                <button class="secondary">Create Payment Link</button>
              </form>
            </div>
          </section>
          <section>
            <div class="panel">
              <h2>Latest Attestations</h2>
              <div class="grid">{latest_attestations or "<p>No attestations yet.</p>"}</div>
            </div>
            <div class="panel">
              <h2>Latest Predictions</h2>
              <div class="grid">{latest_predictions or "<p>No predictions yet.</p>"}</div>
            </div>
            <div class="panel">
              <h2>Qevorpay Links</h2>
              <div class="grid">{latest_payments or "<p>No payment links yet.</p>"}</div>
            </div>
          </section>
        </main>
      </body>
    </html>
    """
