from __future__ import annotations

from html import escape
from typing import Any


def _short(value: Any, length: int = 18) -> str:
    text = str(value or "")
    return text if len(text) <= length else f"{text[: length - 3]}..."


def _text(value: Any) -> str:
    return escape(str(value or ""))


def _label(value: Any) -> str:
    return escape(str(value or "n/a").replace("_", " "))


def _tone(item: dict[str, Any]) -> str:
    if item.get("reversed"):
        return "warn"
    if item.get("verdict") == "hold_pending_clarification":
        return "hold"
    if item.get("verdict") == "refuse_refund":
        return "bad"
    return "good"


def _badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge {tone}">{escape(text)}</span>'


def _css() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f6f2ea;
      --ink: #111512;
      --muted: #667069;
      --surface: #fffdf8;
      --surface-2: #f1ece2;
      --line: #ddd6c8;
      --green: #13654c;
      --green-2: #0d4333;
      --amber: #9b6818;
      --red: #9e3b31;
      --blue: #285e78;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    a { color: inherit; text-decoration: none; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 18px 30px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,253,248,.94);
      position: sticky;
      top: 0;
      z-index: 4;
    }
    h1, h2, h3, p { margin-top: 0; }
    .brand strong { display: block; font-size: 25px; letter-spacing: 0; }
    .brand span { color: var(--muted); }
    nav { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; justify-content: flex-end; }
    .nav-link, .pill, .mini-form button {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--surface);
      color: var(--green-2);
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 900;
    }
    .nav-link.primary, .mini-form button { background: var(--green); color: white; border-color: var(--green); }
    .mini-form { margin: 0; }
    .shell { padding: 28px 30px; }
    .hero {
      min-height: 520px;
      display: grid;
      grid-template-columns: minmax(340px, 1.1fr) minmax(320px, .9fr);
      gap: 22px;
      align-items: stretch;
    }
    .hero-copy {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 30px;
      background:
        linear-gradient(135deg, rgba(19,101,76,.14), rgba(155,104,24,.12)),
        var(--surface);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .eyebrow { color: var(--amber); font-size: 12px; font-weight: 950; text-transform: uppercase; letter-spacing: .04em; }
    .hero h1 { font-size: 54px; line-height: .98; letter-spacing: 0; max-width: 820px; margin: 12px 0 16px; }
    .hero p { color: var(--muted); font-size: 17px; line-height: 1.55; max-width: 760px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      border-radius: 6px;
      border: 1px solid var(--green);
      background: var(--green);
      color: white;
      padding: 0 16px;
      font-weight: 950;
    }
    .button.secondary { background: var(--surface); color: var(--green-2); border-color: var(--line); }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)); gap: 10px; margin-top: 28px; }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,253,248,.78);
      padding: 14px;
    }
    .metric span, .fact span { display: block; color: var(--muted); font-size: 12px; font-weight: 950; text-transform: uppercase; }
    .metric strong { display: block; margin-top: 6px; font-size: 25px; }
    .flow {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .flow h2 { margin-bottom: 2px; font-size: 20px; }
    .flow-step, .record, .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 16px;
    }
    .flow-step { display: grid; grid-template-columns: 34px 1fr auto; gap: 13px; align-items: start; }
    .number {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--surface-2);
      color: var(--green-2);
      font-weight: 950;
    }
    .flow-step strong { display: block; margin-bottom: 4px; }
    .flow-step p, .record p, .panel-copy { color: var(--muted); line-height: 1.45; margin-bottom: 0; }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 9px;
      border: 1px solid var(--line);
      background: var(--surface-2);
      color: var(--green-2);
      font-size: 12px;
      font-weight: 950;
      white-space: nowrap;
    }
    .badge.good { background: #e4f1eb; border-color: #c6dfd3; color: var(--green-2); }
    .badge.warn, .badge.hold { background: #fff2d8; border-color: #e8cc93; color: #76500f; }
    .badge.bad { background: #f9e3df; border-color: #e9beb7; color: var(--red); }
    .section { margin-top: 22px; }
    .section-head { display: flex; justify-content: space-between; gap: 12px; align-items: end; margin-bottom: 12px; }
    .section-head h2 { margin-bottom: 3px; font-size: 24px; }
    .section-head p { margin-bottom: 0; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 12px; }
    .record-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; margin-bottom: 12px; }
    .record h3 { margin: 3px 0 5px; font-size: 19px; line-height: 1.15; }
    .kicker { color: var(--muted); font-size: 12px; font-weight: 950; text-transform: uppercase; }
    .facts { display: grid; grid-template-columns: repeat(3, minmax(100px, 1fr)); gap: 8px; margin-top: 13px; }
    .fact { border-top: 1px solid var(--line); padding-top: 9px; min-width: 0; }
    .fact strong, .fact code { display: block; margin-top: 4px; font-size: 13px; overflow-wrap: anywhere; }
    details { border-top: 1px dashed var(--line); margin-top: 13px; padding-top: 11px; }
    summary { cursor: pointer; color: var(--green-2); font-weight: 950; }
    pre {
      white-space: pre-wrap;
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      max-height: 320px;
      overflow: auto;
      font-size: 12px;
      line-height: 1.45;
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(340px, 430px) 1fr;
      gap: 18px;
      align-items: start;
    }
    .panel { margin-bottom: 14px; }
    label { display: block; margin: 12px 0 6px; font-size: 13px; font-weight: 950; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 11px 12px;
      font: inherit;
    }
    textarea { min-height: 118px; resize: vertical; }
    button {
      min-height: 43px;
      border: 0;
      border-radius: 6px;
      background: var(--green);
      color: white;
      cursor: pointer;
      font-weight: 950;
    }
    button.danger { background: var(--red); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
    .status-line { color: var(--muted); font-size: 13px; margin-top: 10px; min-height: 18px; }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 24px;
      color: var(--muted);
      background: rgba(255,253,248,.66);
      text-align: center;
    }
    .notice {
      border-left: 3px solid var(--green);
      background: #eef6f1;
      padding: 10px 12px;
      margin: 12px 0;
      font-weight: 800;
    }
    .notice.bad { border-left-color: var(--red); background: #fae6e2; }
    .signin {
      min-height: calc(100vh - 82px);
      display: grid;
      place-items: center;
      padding: 24px;
    }
    .signin-card { width: min(520px, 100%); }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    @media (max-width: 1120px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      header { align-items: flex-start; flex-direction: column; padding: 16px; }
      .shell { padding: 16px; }
      .hero h1 { font-size: 38px; }
      .metrics, .grid, .facts, .split { grid-template-columns: 1fr; }
      .flow-step { grid-template-columns: 34px 1fr; }
      .flow-step .badge { grid-column: 2; width: max-content; }
    }
    """


def _page(title: str, body: str, user: dict[str, Any] | None = None) -> str:
    auth_link = (
        f"""
        <span class="pill">{escape(str(user.get("email") or user.get("id")))}</span>
        <a class="nav-link primary" href="/app">Workspace</a>
        <form class="mini-form" method="post" action="/auth/logout"><button>Sign out</button></form>
        """
        if user
        else '<a class="nav-link primary" href="/login">Sign in</a>'
    )
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{escape(title)}</title>
        <style>{_css()}</style>
      </head>
      <body>
        <header>
          <a class="brand" href="/">
            <strong>NOTARY</strong>
            <span>NOTARY decides. Qevor pays. Arc remembers.</span>
          </a>
          <nav>
            <a class="nav-link" href="/ledger">Public ledger</a>
            {auth_link}
          </nav>
        </header>
        {body}
      </body>
    </html>
    """


def _public_flow_items(rulings: list[dict[str, Any]]) -> str:
    release = next((item for item in reversed(rulings) if item.get("releasePct") == 100.0), None)
    hold = next((item for item in reversed(rulings) if item.get("confidenceGate") == "request_more_evidence"), None)
    reversal = next((item for item in reversed(rulings) if item.get("reversed")), None)
    cases = [
        ("Settled", release, "Evidence satisfied the obligation, so Qevor receives a release instruction."),
        ("Held", hold, "Ambiguity or weak evidence stops payment and asks for clarification."),
        ("Revised", reversal, "Counter-evidence can force NOTARY to correct itself publicly."),
    ]
    html: list[str] = []
    for index, (label, item, fallback) in enumerate(cases, start=1):
        tone = _tone(item or {})
        summary = (item or {}).get("obligationSummary") or fallback
        confidence = (item or {}).get("confidence", "pending")
        html.append(
            f"""
            <div class="flow-step">
              <div class="number">{index}</div>
              <div>
                <strong>{escape(label)}</strong>
                <p>{escape(str(summary))}</p>
              </div>
              {_badge(f"confidence {confidence}", tone)}
            </div>
            """
        )
    return "".join(html)


def _record_cards(items: list[dict[str, Any]], *, limit: int | None = None, compact: bool = False) -> str:
    visible = list(reversed(items[-limit:])) if limit else list(reversed(items))
    if not visible:
        return '<div class="empty">No records for this view yet.</div>'
    cards: list[str] = []
    for item in visible:
        obligation = item.get("obligation", {}) or {}
        parties = item.get("partyIdentities", {}) or {}
        precedent = ", ".join(item.get("precedentRefs", []) or []) or "none"
        reasoning = escape(str(item.get("reasoningTrace") or "No reasoning trace recorded."))
        reversal = item.get("reversal") or {}
        reversal_note = ""
        if item.get("reversed") or item.get("supersedes"):
            reversal_note = (
                f'<div class="notice">Reversal action: '
                f'{_label(reversal.get("corrective_payment_action", "recorded"))}</div>'
            )
        details = ""
        if not compact:
            details = f"""
            <details>
              <summary>View reasoning and hashes</summary>
              <div class="facts">
                <div class="fact"><span>Deliverable</span><strong>{_text(obligation.get("deliverable"))}</strong></div>
                <div class="fact"><span>Acceptance</span><strong>{_text(obligation.get("acceptance_criterion"))}</strong></div>
                <div class="fact"><span>Trace hash</span><code>{escape(_short(item.get("reasoningTraceHash"), 30))}</code></div>
              </div>
              <pre>{reasoning}</pre>
            </details>
            """
        cards.append(
            f"""
            <article class="record">
              <div class="record-head">
                <div>
                  <div class="kicker">Obligation</div>
                  <h3>{_text(item.get("obligationSummary") or "Untitled obligation")}</h3>
                  <p>payer {_text(parties.get("payer"))} · payee {_text(parties.get("payee"))}</p>
                </div>
                <div>
                  {_badge(_label(item.get("verdict")), _tone(item))}
                  {_badge(f"confidence {item.get('confidence', 'n/a')}", _tone(item))}
                </div>
              </div>
              {reversal_note}
              <div class="facts">
                <div class="fact"><span>Release</span><strong>{_text(item.get("releasePct"))}%</strong></div>
                <div class="fact"><span>Gate</span><strong>{_label(item.get("confidenceGate"))}</strong></div>
                <div class="fact"><span>Precedent</span><strong>{escape(_short(precedent, 32))}</strong></div>
              </div>
              {details}
            </article>
            """
        )
    return "".join(cards)


def _case_cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<div class="empty">No cases yet. Create a conditional payment case to invite evidence.</div>'
    cards: list[str] = []
    for item in reversed(items):
        upload = item.get("metadata", {}).get("evidenceUploadPath")
        upload_link = f'<a class="button secondary" href="{escape(upload)}">Evidence link</a>' if upload else ""
        cards.append(
            f"""
            <article class="record">
              <div class="record-head">
                <div>
                  <div class="kicker">Case {escape(_short(item.get("case_id"), 20))}</div>
                  <h3>{_text(item.get("instruction"))}</h3>
                  <p>payer {_text(item.get("payer_identity"))} · payee {_text(item.get("payee_identity"))}</p>
                </div>
                {_badge(_label(item.get("status")), "good" if item.get("status") == "released" else "hold")}
              </div>
              <div class="facts">
                <div class="fact"><span>Amount</span><strong>{_text(item.get("amount_usdc"))} USDC</strong></div>
                <div class="fact"><span>Qevor ref</span><code>{escape(_short(item.get("qevor_payment_reference"), 28))}</code></div>
                <div class="fact"><span>Latest ruling</span><code>{escape(_short(item.get("latest_ruling_id"), 28))}</code></div>
              </div>
              <div class="actions" style="margin-top:12px">{upload_link}</div>
            </article>
            """
        )
    return "".join(cards)


def render_landing(state: dict[str, Any], user: dict[str, Any] | None = None) -> str:
    rulings = state.get("rulings", [])
    confidence_values = [
        float(item.get("confidence"))
        for item in rulings
        if isinstance(item.get("confidence"), (int, float))
    ]
    average_confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else "n/a"
    body = f"""
    <main class="shell">
      <section class="hero">
        <div class="hero-copy">
          <div>
            <div class="eyebrow">Witness-to-pay on Arc</div>
            <h1>Public proof that payment was earned or refused.</h1>
            <p>NOTARY reads the obligation, checks the evidence, renders a confidence-gated verdict, signs an attestation, and sends Qevor the release, hold, refund, or corrective payment action.</p>
            <div class="actions">
              <a class="button" href="/app">Open workspace</a>
              <a class="button secondary" href="/ledger">View all public records</a>
            </div>
          </div>
          <div class="metrics">
            <div class="metric"><span>Public rulings</span><strong>{len(rulings)}</strong></div>
            <div class="metric"><span>Avg confidence</span><strong>{escape(str(average_confidence))}</strong></div>
            <div class="metric"><span>Disputes</span><strong>{len(state.get("disputes", []))}</strong></div>
            <div class="metric"><span>Reversals</span><strong>{len(state.get("reversals", []))}</strong></div>
          </div>
        </div>
        <div class="flow">
          <div>
            <div class="eyebrow">Settlement flow</div>
            <h2>Release, hold, or correct on the record</h2>
          </div>
          {_public_flow_items(rulings)}
        </div>
      </section>
      <section class="section">
        <div class="section-head">
          <div>
            <h2>Recent public records</h2>
            <p>Summaries and commitments are public. Raw evidence remains private.</p>
          </div>
          <a class="button secondary" href="/ledger">See all</a>
        </div>
        <div class="grid">{_record_cards(rulings, limit=3, compact=True)}</div>
      </section>
    </main>
    """
    return _page("NOTARY", body, user)


def render_public_ledger(state: dict[str, Any], user: dict[str, Any] | None = None) -> str:
    body = f"""
    <main class="shell">
      <div class="section-head">
        <div>
          <div class="eyebrow">Public ledger</div>
          <h2>Inspectable rulings, reversals, and reasoning</h2>
          <p>Only summaries, verdicts, hashes, and attestation chains are public by default.</p>
        </div>
        <a class="button secondary" href="/">Back home</a>
      </div>
      <div class="grid">{_record_cards(state.get("rulings", []))}</div>
    </main>
    """
    return _page("Public ledger · NOTARY", body, user)


def render_sign_in(
    *,
    auth: dict[str, Any],
    email: str | None = None,
    message: str | None = None,
    error: str | None = None,
) -> str:
    configured = bool(auth.get("configured"))
    missing = ", ".join(auth.get("needs", []))
    disabled = "" if configured else "disabled"
    notice = ""
    if message:
        notice = f'<div class="notice">{escape(message)}</div>'
    if error:
        notice = f'<div class="notice bad">{escape(error)}</div>'
    config_notice = ""
    if not configured:
        config_notice = (
            '<div class="notice bad">'
            f"Auth is not configured. Add {escape(missing)} to .env, then restart."
            "</div>"
        )
    if email:
        form = f"""
        <form method="post" action="/auth/verify-code">
          <input name="email" type="hidden" value="{escape(email)}" />
          <div class="notice">Code sent to {escape(email)}. Check inbox and spam. If Supabase sends a magic-link email instead of a numeric code, update the Supabase Auth email template to include the OTP token.</div>
          <label for="token">Code</label>
          <input id="token" name="token" inputmode="numeric" autocomplete="one-time-code" required autofocus />
          <button {disabled}>Verify and enter</button>
        </form>
        <form method="get" action="/login">
          <button class="secondary" type="submit">Use a different email</button>
        </form>
        """
    else:
        form = f"""
        <form method="post" action="/auth/send-code">
          <label for="email">Email</label>
          <input id="email" name="email" type="email" autocomplete="email" required autofocus />
          <button class="submit-code" {disabled}>Send sign-in code</button>
        </form>
        """
    body = f"""
    <main class="signin">
      <section class="panel signin-card">
        <div class="eyebrow">Private workspace</div>
        <h1>Sign in to use NOTARY</h1>
        <p class="panel-copy">Each payer, payee, approver, or agent counterparty gets its own workspace. Public records stay on the landing page; your evidence and actions stay here.</p>
        {config_notice}
        {notice}
        {form}
      </section>
    </main>
    <script>
      document.querySelectorAll("form").forEach(form => {{
        form.addEventListener("submit", () => {{
          const button = form.querySelector("button[type='submit'], button:not([type])");
          if (button && !button.disabled) {{
            button.dataset.originalText = button.textContent || "";
            button.textContent = button.classList.contains("submit-code") ? "Sending code..." : "Submitting...";
            button.disabled = true;
          }}
        }});
      }});
    </script>
    """
    return _page("Sign in · NOTARY", body)


def _workspace_scripts() -> str:
    return """
    <script>
      const startButton = document.getElementById("start_recording");
      const stopButton = document.getElementById("stop_recording");
      const statusLine = document.getElementById("recording_status");
      let recorder = null;
      let chunks = [];
      startButton?.addEventListener("click", async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          chunks = [];
          recorder = new MediaRecorder(stream);
          recorder.ondataavailable = event => {
            if (event.data.size > 0) chunks.push(event.data);
          };
          recorder.onstop = async () => {
            statusLine.textContent = "Sending recording to Speechmatics...";
            const blob = new Blob(chunks, { type: "audio/webm" });
            const form = new FormData();
            form.append("file", blob, "notary-recording.webm");
            form.append("privacy_mode", document.getElementById("record_privacy_mode").value);
            const response = await fetch("/media/transcribe", { method: "POST", body: form });
            if (!response.ok) {
              statusLine.textContent = "Transcription failed. Check your Speechmatics key.";
              return;
            }
            const result = await response.json();
            if (result.observation) {
              statusLine.textContent = "Running witness pipeline...";
              await fetch("/observations/cycle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(result.observation)
              });
            }
            statusLine.textContent = "Evidence processed.";
            window.location.reload();
          };
          recorder.start();
          startButton.disabled = true;
          stopButton.disabled = false;
          statusLine.textContent = "Recording...";
        } catch (error) {
          statusLine.textContent = "Microphone access was not available.";
        }
      });
      stopButton?.addEventListener("click", () => {
        if (recorder && recorder.state !== "inactive") {
          recorder.stop();
          recorder.stream.getTracks().forEach(track => track.stop());
          startButton.disabled = false;
          stopButton.disabled = true;
        }
      });
    </script>
    """


def render_workspace(state: dict[str, Any], user: dict[str, Any], error: str | None = None) -> str:
    user_label = escape(str(user.get("email") or user.get("id")))
    error_html = f'<div class="notice bad">{escape(error)}</div>' if error else ""
    body = f"""
    <main class="shell">
      <div class="section-head">
        <div>
          <div class="eyebrow">Signed-in workspace</div>
          <h2>{user_label}</h2>
          <p>Only records connected to this identity are shown here.</p>
        </div>
      </div>
      <section class="workspace">
        <aside>
          <div class="panel">
            <h2>Create conditional payment case</h2>
            <p class="panel-copy">This creates the shared case ID, Qevor payment reference, and evidence invite link that Daniel or an agent uses to submit evidence against the exact obligation.</p>
            {error_html}
            <form method="post" action="/ui/cases">
              <label for="instruction">Obligation</label>
              <textarea id="instruction" name="instruction" required placeholder="Pay Daniel $250 when the design package is complete and I approve."></textarea>
              <label for="payee_identity">Payee identity</label>
              <input id="payee_identity" name="payee_identity" required placeholder="daniel@example.com or logistics.agent" />
              <label for="amount_usdc">Amount USDC</label>
              <input id="amount_usdc" name="amount_usdc" type="number" min="0.01" step="0.01" required />
              <label for="payee_type">Payee type</label>
              <select id="payee_type" name="payee_type">
                <option value="human">Human</option>
                <option value="agent">Agent</option>
              </select>
              <button>Create case and Qevor reference</button>
            </form>
          </div>
          <div class="panel">
            <h2>Capture evidence</h2>
            <p class="panel-copy">Record in the browser or upload an audio/video file. Speechmatics transcribes it, then NOTARY runs the witness pipeline under your identity.</p>
            <label for="record_privacy_mode">Privacy</label>
            <select id="record_privacy_mode">
              <option value="protected">Protected</option>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
            <div class="button-row">
              <button id="start_recording" type="button">Start recording</button>
              <button id="stop_recording" class="danger" type="button" disabled>Stop & transcribe</button>
            </div>
            <p id="recording_status" class="status-line">Microphone ready.</p>
            <form method="post" action="/ui/media" enctype="multipart/form-data">
              <label for="file">Upload recording</label>
              <input id="file" name="file" type="file" accept="audio/*,video/*" />
              <input name="privacy_mode" type="hidden" value="protected" />
              <label for="media_transcript_text">Transcript override</label>
              <textarea id="media_transcript_text" name="transcript_text" placeholder="Optional if you already have a transcript."></textarea>
              <button>Upload and run witness</button>
            </form>
          </div>
          <div class="panel">
            <h2>Manual transcript</h2>
            <p class="panel-copy">Paste a payment instruction, work call, or evidence summary.</p>
            <form method="post" action="/ui/attest">
              <label for="privacy_mode">Privacy</label>
              <select id="privacy_mode" name="privacy_mode">
                <option value="protected">Protected</option>
                <option value="private">Private</option>
                <option value="public">Public</option>
              </select>
              <label for="transcript_text">Transcript</label>
              <textarea id="transcript_text" name="transcript_text" placeholder="Pay Daniel $250 when the design is complete and I approve. Evidence: timestamped signed approval and final file link."></textarea>
              <button>Run witness pipeline</button>
            </form>
          </div>
        </aside>
        <section>
          <div class="section-head">
            <div>
              <h2>My cases</h2>
              <p>{len(state.get("cases", []))} conditional payment case(s) connected to this account.</p>
            </div>
          </div>
          <div class="grid">{_case_cards(state.get("cases", []))}</div>
          <div class="section-head" style="margin-top:22px">
            <div>
              <h2>My rulings</h2>
              <p>{len(state.get("rulings", []))} ruling(s) connected to this account.</p>
            </div>
          </div>
          <div class="grid">{_record_cards(state.get("rulings", []))}</div>
        </section>
      </section>
    </main>
    {_workspace_scripts()}
    """
    return _page("Workspace · NOTARY", body, user)


def render_case_evidence(case: dict[str, Any], token: str | None, user: dict[str, Any] | None) -> str:
    hidden_token = f'<input name="token" type="hidden" value="{escape(token)}" />' if token else ""
    body = f"""
    <main class="signin">
      <section class="panel signin-card">
        <div class="eyebrow">Evidence submission</div>
        <h1>{_text(case.get("instruction"))}</h1>
        <p class="panel-copy">Case {escape(_short(case.get("case_id"), 24))}. Evidence submitted here is matched by case ID, not by name matching or free text.</p>
        <div class="facts">
          <div class="fact"><span>Payer</span><strong>{_text(case.get("payer_identity"))}</strong></div>
          <div class="fact"><span>Payee</span><strong>{_text(case.get("payee_identity"))}</strong></div>
          <div class="fact"><span>Qevor ref</span><code>{escape(_short(case.get("qevor_payment_reference"), 28))}</code></div>
        </div>
        <form method="post" action="/cases/{escape(case.get("case_id"))}/evidence">
          {hidden_token}
          <label for="submitter_identity">Submitter identity</label>
          <input id="submitter_identity" name="submitter_identity" value="{escape(str((user or {}).get("email") or case.get("payee_identity") or ""))}" required />
          <label for="submitter_type">Submitter type</label>
          <select id="submitter_type" name="submitter_type">
            <option value="human">Human</option>
            <option value="agent">Agent</option>
          </select>
          <label for="evidence_text">Evidence</label>
          <textarea id="evidence_text" name="evidence_text" required placeholder="Timestamped file link, signed approval, commit hash, invoice receipt, delivery notes..."></textarea>
          <button>Submit evidence to NOTARY</button>
        </form>
      </section>
    </main>
    """
    return _page("Submit evidence · NOTARY", body, user)
