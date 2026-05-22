from __future__ import annotations

from html import escape
from typing import Any


def _short(value: Any, length: int = 14) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return f"{text[: length - 3]}..."


def _status(value: Any) -> str:
    return escape(str(value or "n/a").replace("_", " "))


def _attestation_rows(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<tr><td colspan="5" class="empty">No attestations yet.</td></tr>'
    rows = []
    for item in reversed(items[-8:]):
        rows.append(
            f"""
            <tr>
              <td><span class="pill">{escape(item.get("privacy_mode", "protected"))}</span></td>
              <td>{escape(_short(item.get("verdict_hash", "Attestation"), 92))}</td>
              <td><code>{escape(_short(item.get("reasoning_trace_hash", ""), 18))}</code></td>
              <td>{_status(item.get("dispute_state"))}</td>
              <td><code>{escape(_short(item.get("attestation_id", ""), 18))}</code></td>
            </tr>
            """
        )
    return "".join(rows)


def _ruling_rows(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<tr><td colspan="5" class="empty">No witness rulings yet.</td></tr>'
    rows = []
    for item in reversed(items[-8:]):
        rows.append(
            f"""
            <tr>
              <td>{escape(_short(item.get("obligationSummary", "Obligation"), 72))}</td>
              <td>{_status(item.get("verdict"))}</td>
              <td>{escape(str(item.get("releasePct", "n/a")))}</td>
              <td>{_status("reversed" if item.get("reversed") else "current")}</td>
              <td><code>{escape(_short(item.get("attestationId", ""), 18))}</code></td>
            </tr>
            """
        )
    return "".join(rows)


def _payment_rows(links: list[dict[str, Any]], triggers: list[dict[str, Any]]) -> str:
    rows = []
    for item in reversed(links[-4:]):
        request = item.get("request", {})
        rows.append(
            f"""
            <tr>
              <td>Payment link</td>
              <td>{escape(_short(request.get("description", "Qevorpay link"), 64))}</td>
              <td>{escape(str(request.get("amount_usdc", request.get("amountUSDC", "n/a"))))}</td>
              <td>{_status(item.get("status"))}</td>
              <td><a href="{escape(item.get("url", "#"))}">{escape(_short(item.get("reference", ""), 18))}</a></td>
            </tr>
            """
        )
    for item in reversed(triggers[-4:]):
        rows.append(
            f"""
            <tr>
              <td>{escape(str(item.get("action", "trigger")).replace("_", " "))}</td>
              <td>{escape(_short(item.get("reason", "Payment instruction"), 64))}</td>
              <td>{escape(str(item.get("amount_usdc", "n/a")))}</td>
              <td>{_status(item.get("action"))}</td>
              <td><code>{escape(_short(item.get("instruction_id", ""), 18))}</code></td>
            </tr>
            """
        )
    if not rows:
        return '<tr><td colspan="5" class="empty">No payment activity yet.</td></tr>'
    return "".join(rows)


def render_dashboard(state: dict[str, Any]) -> str:
    notary_count = len(state.get("notaries", []))
    rulings = state.get("rulings", [])
    attestation_count = len(state.get("witness_attestations", []))
    dispute_count = len(state.get("disputes", []))
    reversal_count = len(state.get("reversals", []))
    payment_count = len(state.get("payments", [])) + len(state.get("payment_instructions", []))
    speechmatics = state.get("speechmatics", {})
    speechmatics_configured = "Configured" if speechmatics.get("configured") else "Needs key"
    speechmatics_mode = "Live" if not speechmatics.get("demoMode", True) else "Demo"
    arc_receipts = len(state.get("arc_receipts", []))
    validations = len(state.get("validations", []))

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
            --bg: #f4f6f4;
            --surface: #ffffff;
            --surface-2: #eef2ef;
            --ink: #101414;
            --muted: #66716d;
            --line: #d7ddd9;
            --green: #0f5f46;
            --green-2: #0b4736;
            --red: #9d352b;
            --gold: #a97316;
            --blue: #235b83;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            background: var(--bg);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }}
          a {{ color: var(--green); font-weight: 800; text-decoration: none; }}
          header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            padding: 18px 28px;
            background: var(--surface);
            border-bottom: 1px solid var(--line);
            position: sticky;
            top: 0;
            z-index: 2;
          }}
          .brand h1 {{
            margin: 0;
            font-size: 24px;
            letter-spacing: 0;
          }}
          .brand p {{
            margin: 4px 0 0;
            color: var(--muted);
            font-size: 14px;
          }}
          .top-actions {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: flex-end;
          }}
          .top-actions a {{
            border: 1px solid var(--line);
            padding: 9px 11px;
            border-radius: 6px;
            background: var(--surface);
          }}
          .metrics {{
            display: grid;
            grid-template-columns: repeat(7, minmax(120px, 1fr));
            gap: 1px;
            background: var(--line);
            border-bottom: 1px solid var(--line);
          }}
          .metric {{
            background: var(--surface);
            padding: 14px 18px;
            min-height: 76px;
          }}
          .metric span {{
            color: var(--muted);
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
          }}
          .metric strong {{
            display: block;
            margin-top: 7px;
            font-size: 24px;
          }}
          .app {{
            display: grid;
            grid-template-columns: minmax(300px, 380px) 1fr;
            gap: 18px;
            padding: 18px;
          }}
          .panel {{
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 14px;
          }}
          .panel h2 {{
            margin: 0 0 12px;
            font-size: 16px;
          }}
          label {{
            display: block;
            margin: 11px 0 6px;
            font-size: 13px;
            font-weight: 800;
          }}
          input, textarea, select {{
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 10px 11px;
            background: #fff;
            color: var(--ink);
            font: inherit;
          }}
          textarea {{
            min-height: 124px;
            resize: vertical;
          }}
          button {{
            width: 100%;
            min-height: 42px;
            margin-top: 12px;
            border: 0;
            border-radius: 6px;
            background: var(--green);
            color: white;
            cursor: pointer;
            font-weight: 900;
          }}
          button.secondary {{ background: var(--blue); }}
          button.danger {{ background: var(--red); }}
          .workbench {{
            display: grid;
            gap: 14px;
          }}
          .table-panel {{
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
          }}
          .table-title {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 13px 15px;
            border-bottom: 1px solid var(--line);
            background: var(--surface-2);
          }}
          .table-title h2 {{
            margin: 0;
            font-size: 15px;
          }}
          .table-title span {{
            color: var(--muted);
            font-size: 12px;
            font-weight: 800;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
          }}
          th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--line);
            vertical-align: top;
            font-size: 14px;
            overflow-wrap: anywhere;
          }}
          th {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
          }}
          tr:last-child td {{ border-bottom: 0; }}
          code {{
            color: var(--muted);
            font-size: 12px;
          }}
          .pill {{
            display: inline-flex;
            align-items: center;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 3px 8px;
            background: var(--surface-2);
            color: var(--green-2);
            font-size: 12px;
            font-weight: 800;
          }}
          .empty {{
            color: var(--muted);
            text-align: center;
            padding: 24px;
          }}
          @media (max-width: 1100px) {{
            .metrics {{ grid-template-columns: repeat(3, 1fr); }}
            .app {{ grid-template-columns: 1fr; }}
          }}
          @media (max-width: 680px) {{
            header {{ align-items: flex-start; flex-direction: column; padding: 16px; }}
            .metrics {{ grid-template-columns: repeat(2, 1fr); }}
            .app {{ padding: 12px; }}
            th:nth-child(5), td:nth-child(5) {{ display: none; }}
          }}
        </style>
      </head>
      <body>
        <header>
          <div class="brand">
            <h1>NOTARY</h1>
            <p>Single witness pipeline for Qevor payments on Arc</p>
          </div>
          <nav class="top-actions">
            <a href="/state">State JSON</a>
            <a href="/speechmatics/status">Speechmatics</a>
            <a href="/circle/status">Circle</a>
          </nav>
        </header>

        <section class="metrics">
          <div class="metric"><span>Notaries</span><strong>{notary_count}</strong></div>
          <div class="metric"><span>Rulings</span><strong>{len(rulings)}</strong></div>
          <div class="metric"><span>Attestations</span><strong>{attestation_count}</strong></div>
          <div class="metric"><span>Disputes</span><strong>{dispute_count}</strong></div>
          <div class="metric"><span>Reversals</span><strong>{reversal_count}</strong></div>
          <div class="metric"><span>Payments</span><strong>{payment_count}</strong></div>
          <div class="metric"><span>Speechmatics</span><strong>{speechmatics_configured}</strong></div>
        </section>

        <main class="app">
          <aside>
            <div class="panel">
              <h2>Create Notary</h2>
              <form method="post" action="/ui/notaries">
                <label for="label">Label</label>
                <input id="label" name="label" placeholder="Client escrow witness" />
                <button>Create Notary</button>
              </form>
            </div>

            <div class="panel">
              <h2>Witness-to-Pay</h2>
              <form method="post" action="/ui/attest">
                <label for="privacy_mode">Privacy</label>
                <select id="privacy_mode" name="privacy_mode">
                  <option value="protected">Protected</option>
                  <option value="private">Private</option>
                  <option value="public">Public</option>
                </select>
                <label for="transcript_text">Transcript</label>
                <textarea id="transcript_text" name="transcript_text" placeholder="Client: The work is complete. Please release payment."></textarea>
                <button>Run Witness-to-Pay</button>
              </form>
            </div>

            <div class="panel">
              <h2>Evidence Upload</h2>
              <form method="post" action="/ui/media" enctype="multipart/form-data">
                <label for="media_privacy_mode">Privacy</label>
                <select id="media_privacy_mode" name="privacy_mode">
                  <option value="protected">Protected</option>
                  <option value="private">Private</option>
                  <option value="public">Public</option>
                </select>
                <label for="file">Audio or video</label>
                <input id="file" name="file" type="file" />
                <label for="media_transcript_text">Transcript override</label>
                <textarea id="media_transcript_text" name="transcript_text" placeholder="Optional when Speechmatics is connected."></textarea>
                <button>Upload Evidence</button>
              </form>
            </div>

            <div class="panel">
              <h2>Qevorpay Link</h2>
              <form method="post" action="/ui/payment-link">
                <label for="amount_usdc">Amount USDC</label>
                <input id="amount_usdc" name="amount_usdc" type="number" min="0.01" step="0.01" value="25" />
                <label for="description">Description</label>
                <input id="description" name="description" value="Verified NOTARY payment" />
                <button class="secondary">Create Link</button>
              </form>
            </div>
          </aside>

          <section class="workbench">
            <div class="table-panel">
              <div class="table-title"><h2>Payment Activity</h2><span>{payment_count} total</span></div>
              <table>
                <thead><tr><th>Type</th><th>Detail</th><th>USDC</th><th>Status</th><th>Reference</th></tr></thead>
                <tbody>{_payment_rows(state.get("payments", []), state.get("payment_instructions", []))}</tbody>
              </table>
            </div>

            <div class="table-panel">
              <div class="table-title"><h2>Public Ledger</h2><span>{len(rulings)} rulings</span></div>
              <table>
                <thead><tr><th>Obligation</th><th>Verdict</th><th>Release %</th><th>Status</th><th>Attestation</th></tr></thead>
                <tbody>{_ruling_rows(rulings)}</tbody>
              </table>
            </div>

            <div class="table-panel">
              <div class="table-title"><h2>Attestations</h2><span>{attestation_count} signed</span></div>
              <table>
                <thead><tr><th>Privacy</th><th>Verdict Hash</th><th>Trace Hash</th><th>Status</th><th>ID</th></tr></thead>
                <tbody>{_attestation_rows(state.get("witness_attestations", []))}</tbody>
              </table>
            </div>

            <div class="table-panel">
              <div class="table-title"><h2>Validation</h2><span>Arc {arc_receipts} / Validation {validations}</span></div>
              <table>
                <tbody>
                  <tr><th>Speechmatics</th><td>{speechmatics_configured}</td><th>Provider Mode</th><td>{speechmatics_mode}</td></tr>
                  <tr><th>Base URL</th><td>{escape(str(speechmatics.get("baseUrl", "n/a")))}</td><th>Language</th><td>{escape(str(speechmatics.get("language", "n/a")))}</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </body>
    </html>
    """
