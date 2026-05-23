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


def _payload_first_arg(item: dict[str, Any]) -> Any:
    args = item.get("payload", {}).get("args", [])
    return args[0] if args else None


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
      color-scheme: dark;
      --bg: #060a08;
      --ink: #e2e8f0;
      --muted: #94a3b8;
      --surface: rgba(15, 23, 20, 0.7);
      --surface-2: rgba(30, 41, 35, 0.45);
      --line: rgba(255, 255, 255, 0.08);
      --line-hover: rgba(255, 255, 255, 0.16);
      --green: #10b981;
      --green-glow: rgba(16, 185, 129, 0.2);
      --green-2: #059669;
      --amber: #f59e0b;
      --amber-glow: rgba(245, 158, 11, 0.15);
      --red: #ef4444;
      --red-glow: rgba(239, 68, 68, 0.15);
      --blue: #3b82f6;
      --black: #020403;
      --mint: rgba(16, 185, 129, 0.1);
      --shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      background-image: radial-gradient(circle at 50% -20%, #0d281a 0%, #060a08 100%);
      background-attachment: fixed;
      color: var(--ink);
      font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    a { color: inherit; text-decoration: none; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 16px 36px;
      border-bottom: 1px solid var(--line);
      background: rgba(2, 4, 3, 0.8);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1, h2, h3, h4, p { margin-top: 0; }
    h1, h2, h3, h4 {
      font-family: 'Outfit', sans-serif;
      font-weight: 700;
    }
    .brand {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .brand strong {
      font-size: 24px;
      font-family: 'Outfit', sans-serif;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: #fff;
      text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }
    .brand span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 500;
    }
    nav { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
    .nav-link, .pill, .mini-form button {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.03);
      color: var(--muted);
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .nav-link:hover, .mini-form button:hover {
      border-color: var(--line-hover);
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }
    .nav-link.primary {
      background: var(--green);
      color: #fff;
      border-color: var(--green);
      font-weight: 700;
      box-shadow: 0 4px 12px var(--green-glow);
    }
    .nav-link.primary:hover {
      background: var(--green-2);
      border-color: var(--green-2);
      transform: translateY(-1px);
    }
    .mini-form { margin: 0; }
    .mini-form button {
      background: transparent;
      border: 1px solid rgba(239, 68, 68, 0.2);
      color: #ef4444;
      min-height: auto;
    }
    .mini-form button:hover {
      background: rgba(239, 68, 68, 0.1);
      border-color: #ef4444;
      color: #fff;
    }
    .shell { padding: 36px; max-width: 1400px; margin: 0 auto; }
    .hero {
      min-height: 480px;
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 28px;
      align-items: stretch;
      margin-bottom: 40px;
    }
    .hero-copy {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 40px;
      background: var(--surface);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .eyebrow {
      color: var(--green);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      display: inline-block;
    }
    .hero h1 {
      font-size: 48px;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 12px 0 16px;
      color: #fff;
    }
    .hero p {
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
      max-width: 700px;
      margin-bottom: 24px;
    }
    .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px; }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 46px;
      border-radius: 8px;
      border: 1px solid var(--green);
      background: var(--green);
      color: white;
      padding: 0 24px;
      font-weight: 700;
      font-size: 14px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      box-shadow: 0 4px 12px var(--green-glow);
      width: 100%;
    }
    .button:hover {
      background: var(--green-2);
      border-color: var(--green-2);
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
    }
    .button.secondary {
      background: var(--surface-2);
      color: #fff;
      border-color: var(--line);
      box-shadow: none;
      width: auto;
    }
    .button.secondary:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: var(--line-hover);
      transform: translateY(-1px);
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-top: 36px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 16px;
      text-align: center;
      transition: all 0.2s ease;
    }
    .metric:hover {
      border-color: var(--line-hover);
      background: rgba(255, 255, 255, 0.05);
      transform: translateY(-2px);
    }
    .metric span, .fact span {
      display: block;
      color: var(--muted);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .metric strong {
      display: block;
      margin-top: 8px;
      font-size: 28px;
      color: #fff;
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
    }
    .flow {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: 32px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .flow h2 {
      margin-bottom: 4px;
      font-size: 24px;
      color: #fff;
    }
    .flow-step, .record, .panel {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 20px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .flow-step {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 16px;
      align-items: center;
      background: rgba(255, 255, 255, 0.02);
    }
    .flow-step:hover {
      background: rgba(255, 255, 255, 0.04);
      border-color: var(--line-hover);
      transform: translateX(4px);
    }
    .number {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--mint);
      color: var(--green);
      font-weight: 800;
      font-size: 15px;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .flow-step strong {
      display: block;
      margin-bottom: 4px;
      font-size: 16px;
      color: #fff;
    }
    .flow-step p, .record p, .panel-copy {
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 0;
      font-size: 14px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.04);
      color: var(--ink);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .badge.good {
      background: rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.3);
      color: #34d399;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.05);
    }
    .badge.warn, .badge.hold {
      background: rgba(245, 158, 11, 0.1);
      border-color: rgba(245, 158, 11, 0.3);
      color: #fbbf24;
    }
    .badge.bad {
      background: rgba(239, 68, 68, 0.1);
      border-color: rgba(239, 68, 68, 0.3);
      color: #f87171;
    }
    .section { margin-top: 40px; }
    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 20px;
    }
    .section-head h2 {
      margin-bottom: 6px;
      font-size: 32px;
      color: #fff;
      letter-spacing: -0.01em;
    }
    .section-head p { margin-bottom: 0; color: var(--muted); font-size: 15px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .grid.two { grid-template-columns: repeat(2, 1fr); }
    .ops-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 24px; }
    .agent-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .agent-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 16px;
      min-width: 0;
      transition: all 0.2s ease;
    }
    .agent-card:hover {
      border-color: var(--line-hover);
      background: rgba(255, 255, 255, 0.04);
      transform: translateY(-2px);
    }
    .agent-card h3 { font-size: 16px; margin-bottom: 6px; color: #fff; }
    .agent-card p { color: var(--muted); font-size: 13px; line-height: 1.45; margin-bottom: 12px; }
    .agent-card code {
      display: block;
      overflow-wrap: anywhere;
      font-size: 11px;
      color: var(--green);
      background: rgba(16, 185, 129, 0.05);
      padding: 6px 8px;
      border-radius: 4px;
    }
    .record {
      background: var(--surface);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .record:hover {
      transform: translateY(-2px);
      border-color: rgba(16, 185, 129, 0.3);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    }
    .record-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .record h3 {
      margin: 4px 0 6px;
      font-size: 20px;
      line-height: 1.25;
      color: #fff;
    }
    .kicker {
      color: var(--green);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .facts {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 16px;
    }
    .fact {
      border-top: 1px solid var(--line);
      padding-top: 12px;
      min-width: 0;
    }
    .fact strong {
      display: block;
      margin-top: 6px;
      font-size: 14px;
      color: #fff;
    }
    .fact code {
      display: block;
      margin-top: 6px;
      font-size: 11px;
      overflow-wrap: anywhere;
      color: var(--muted);
    }
    details {
      border-top: 1px dashed var(--line);
      margin-top: 16px;
      padding-top: 12px;
    }
    summary {
      cursor: pointer;
      color: var(--green);
      font-weight: 600;
      font-size: 13px;
      user-select: none;
    }
    summary:hover {
      color: #34d399;
    }
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
      grid-template-columns: minmax(360px, 520px) 1fr;
      gap: 18px;
      align-items: start;
    }
    .workspace-intro {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      box-shadow: var(--shadow);
      padding: 18px;
      margin-bottom: 16px;
    }
    .workspace-intro h2 { margin-bottom: 6px; font-size: 25px; }
    .steps { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 10px; margin-top: 14px; }
    .step {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface-2);
      padding: 12px;
      transition: all 0.2s ease;
    }
    .step:hover { border-color: var(--green); background: rgba(16,185,129,0.06); }
    .step strong { display: block; margin-bottom: 4px; color: #fff; }
    .step span { color: var(--muted); line-height: 1.35; display: block; font-size: 13px; }
    .advanced-stack {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      padding: 16px;
      margin-top: 18px;
    }
    .advanced-stack > summary {
      cursor: pointer;
      color: var(--green-2);
      font-weight: 950;
      font-size: 18px;
    }
    .panel { margin-bottom: 14px; }
    label { display: block; margin: 12px 0 6px; font-size: 13px; font-weight: 700; color: var(--muted); letter-spacing: 0.01em; text-transform: uppercase; font-size: 11px; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,0.04);
      color: var(--ink);
      padding: 11px 14px;
      font: inherit;
      font-size: 14px;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    input::placeholder, textarea::placeholder { color: rgba(148,163,184,0.5); }
    input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--green);
      box-shadow: 0 0 0 3px rgba(16,185,129,0.15);
      background: rgba(16,185,129,0.04);
    }
    select option { background: #0f1714; color: var(--ink); }
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
    .inline-form { margin-top: 12px; display: grid; gap: 8px; }
    .inline-form.compact { grid-template-columns: 1fr auto; align-items: end; }
    .inline-form.compact label { margin: 0; }
    .inline-form.compact input { min-width: 0; }
    .status-line { color: var(--muted); font-size: 13px; margin-top: 10px; min-height: 18px; }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 6px;
      padding: 24px;
      color: var(--muted);
      background: rgba(255,255,255,0.02);
      text-align: center;
      font-size: 14px;
    }
    .notice {
      border: 1px solid rgba(16,185,129,0.3);
      border-left: 4px solid var(--green);
      border-radius: 8px;
      background: rgba(16,185,129,0.08);
      padding: 12px 14px;
      margin: 12px 0;
      font-weight: 600;
      font-size: 14px;
      overflow-wrap: anywhere;
      color: #a7f3d0;
    }
    .notice.bad { border-color: rgba(239,68,68,0.3); border-left-color: var(--red); background: rgba(239,68,68,0.08); color: #fca5a5; }
    .signin {
      min-height: calc(100vh - 82px);
      display: grid;
      place-items: center;
      padding: 28px;
      background:
        linear-gradient(180deg, rgba(8,17,13,.05), rgba(8,17,13,0) 34%),
        var(--bg);
    }
    .signin-card { width: min(560px, 100%); box-shadow: var(--shadow); }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    @media (max-width: 1120px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr 1fr; }
      .ops-grid, .agent-grid, .steps { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      header { align-items: flex-start; flex-direction: column; padding: 16px; }
      .shell { padding: 16px; }
      .hero h1 { font-size: 38px; }
      .metrics, .grid, .grid.two, .ops-grid, .agent-grid, .steps, .facts, .split, .inline-form.compact { grid-template-columns: 1fr; }
      .flow-step { grid-template-columns: 34px 1fr; }
      .flow-step .badge { grid-column: 2; width: max-content; }
    }
    .tabs-header {
      display: flex;
      gap: 6px;
      margin: 16px 0 0;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }
    .tab-btn {
      flex: 1;
      background: transparent;
      border: none;
      color: var(--muted);
      font-weight: 700;
      font-size: 13px;
      padding: 9px 12px;
      border-radius: 6px 6px 0 0;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
    }
    .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.04); }
    .tab-btn.active {
      color: var(--green);
      background: rgba(16,185,129,0.08);
      border-bottom: 2px solid var(--green);
    }
    .tab-content { display: none; padding-top: 12px; }
    .tab-content.active { display: block; }
    .sandbox-divider {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 20px 0 0;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .sandbox-divider::before, .sandbox-divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--line);
    }
    .sandbox-section {
      border: 1px solid rgba(245,158,11,0.2);
      border-radius: 8px;
      background: rgba(245,158,11,0.04);
      padding: 14px;
      margin-top: 10px;
    }
    .login-section { margin-top: 4px; }
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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>{_css()}</style>
      </head>
      <body>
        <header>
          <a class="brand" href="/">
            <strong>NOTARY</strong>
            <span>The Autonomous AI Witness Layer for Programmable USDC Payments on Arc</span>
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
        ("Settled", release, "Evidence satisfied the obligation, so NOTARY releases the escrowed USDC."),
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
        funding_url = item.get("escrow_payment_url")
        funding_link = (
            f'<a class="button secondary" href="{escape(str(funding_url))}">Fund conditional payment</a>'
            if funding_url and item.get("status") == "awaiting_funding"
            else ""
        )
        upload_link = (
            f'<a class="button secondary" href="{escape(upload)}">Evidence link</a>'
            if upload and item.get("status") != "awaiting_funding"
            else ""
        )
        guarded_note = (
            '<p class="panel-copy">Evidence is locked until the NOTARY escrow is funded.</p>'
            if item.get("status") == "awaiting_funding"
            else ""
        )
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
                <div class="fact"><span>Escrow ref</span><code>{escape(_short(item.get("escrow_payment_reference"), 28))}</code></div>
                <div class="fact"><span>Latest ruling</span><code>{escape(_short(item.get("latest_ruling_id"), 28))}</code></div>
              </div>
              {guarded_note}
              <div class="actions" style="margin-top:12px">{funding_link}{upload_link}</div>
            </article>
            """
        )
    return "".join(cards)


def _agent_role_cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<div class="empty">The witness roles are ready, but no cycle has run yet.</div>'
    cards: list[str] = []
    for item in items:
        cards.append(
            f"""
            <article class="agent-card">
              <div class="kicker">{_label(item.get("status"))}</div>
              <h3>{_text(item.get("name"))}</h3>
              <p>{_text(item.get("role"))}</p>
              <code>{escape(_short(item.get("lastOutput"), 64))}</code>
            </article>
            """
        )
    return "".join(cards)


def _ops_panels(state: dict[str, Any], circle_request_id: str | None = None) -> str:
    notaries = list(reversed(state.get("notaries", [])))
    receipts = list(reversed(state.get("arc_receipts", [])))
    routes = list(reversed(state.get("circle_routes", [])))
    latest = notaries[0] if notaries else {}
    latest_receipts = [
        item for item in receipts
        if _payload_first_arg(item) == latest.get("notary_id")
    ][:4]
    receipt_rows = "".join(
        f"""
        <div class="fact">
          <span>{_text(item.get("payload", {}).get("contract_name"))}</span>
          <code>{escape(_short(item.get("txHash") or item.get("transactionHash") or item.get("status"), 32))}</code>
        </div>
        """
        for item in latest_receipts
    ) or '<div class="empty">No Arc identity receipts yet.</div>'
    route_rows = "".join(
        f"""
        <div class="fact">
          <span>{_text(item.get("amountUSDC"))} USDC</span>
          <code>{escape(_short(item.get("routeId"), 32))}</code>
        </div>
        """
        for item in routes[:3]
    ) or '<div class="empty">No operator Gateway routes prepared yet.</div>'
    notary_panel = (
        f"""
        <div class="facts">
          <div class="fact"><span>Notary ID</span><code>{escape(_short(latest.get("notary_id"), 34))}</code></div>
          <div class="fact"><span>Agent wallet</span><code>{escape(_short(latest.get("agent_wallet"), 34))}</code></div>
          <div class="fact"><span>Agreement hash</span><code>{escape(_short(latest.get("operating_agreement_hash"), 34))}</code></div>
        </div>
        <form class="inline-form compact" method="post" action="/ui/notaries/{escape(str(latest.get("notary_id")) or '')}/register-onchain">
          <label>Arc testnet identity</label>
          <button {'disabled' if not latest else ''}>Register / refresh on Arc</button>
        </form>
        <div class="facts">{receipt_rows}</div>
        """
        if latest
        else """
        <p class="panel-copy">Create a NOTARY first. This mints the local legal identity, Circle agent wallet, operating agreement hash, and Arc registration payload.</p>
        <form class="inline-form" method="post" action="/ui/notaries">
          <label for="notary_label">Label</label>
          <input id="notary_label" name="label" placeholder="NOTARY witness agent" />
          <button>Create NOTARY identity</button>
        </form>
        """
    )
    otp_form = (
        f"""
        <form class="inline-form" method="post" action="/ui/circle/login/complete">
          <input name="request_id" type="hidden" value="{escape(circle_request_id)}" />
          <label for="circle_otp">Circle OTP</label>
          <input id="circle_otp" name="otp" autocomplete="one-time-code" required />
          <button>Complete Circle login</button>
        </form>
        """
        if circle_request_id
        else ""
    )
    return f"""
    <div class="ops-grid">
      <section class="panel">
        <div class="eyebrow">Arc identity</div>
        <h2>On-chain NOTARY</h2>
        <p class="panel-copy">The agent has an Arc identity, operating agreement hash, privacy policy hash, and governance record.</p>
        {notary_panel}
      </section>
      <section class="panel">
        <div class="eyebrow">User funding</div>
        <h2>NOTARY holds escrow, NOTARY witnesses</h2>
        <p class="panel-copy">Users sign in with email, create a case, and fund the NOTARY conditional escrow. Circle CLI stays server-side for the NOTARY agent wallet and executor.</p>
        <div class="facts">
          <div class="fact"><span>User step</span><strong>Email login</strong></div>
          <div class="fact"><span>Payment step</span><strong>Fund NOTARY escrow</strong></div>
          <div class="fact"><span>Agent step</span><strong>Witness then release</strong></div>
        </div>
        <details>
          <summary>Operator Circle session</summary>
          <p class="panel-copy">Only builders/operators need this while running the agent server locally. End users do not install Circle CLI.</p>
        <form class="inline-form" method="post" action="/ui/circle/login/init">
          <label for="circle_email">Operator Circle email</label>
          <input id="circle_email" name="email" type="email" placeholder="operator@example.com" required />
          <button>Start operator Circle login</button>
        </form>
        {otp_form}
        <form class="inline-form" method="post" action="/ui/circle/deposit">
          <label for="wallet_id">NOTARY agent wallet or address</label>
          <input id="wallet_id" name="wallet_id" value="{escape(str(latest.get("agent_wallet") or ""))}" placeholder="0x... or Circle wallet ID" />
          <label for="deposit_amount">Operator deposit amount USDC</label>
          <input id="deposit_amount" name="amount_usdc" type="number" min="0.01" step="0.01" value="10" required />
          <button>Prepare operator Gateway route</button>
        </form>
        </details>
        <div class="facts">{route_rows}</div>
      </section>
    </div>
    """


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
            <div class="eyebrow">AI Witness Layer</div>
            <h1>Programmable USDC payments triggered by real-world proof.</h1>
            <p>NOTARY turns real-world proof — voice notes, files, videos, work logs, and approvals — into signed AI attestations that trigger programmable USDC payments on Arc.</p>
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
    phone: str | None = None,
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
        if auth.get("localSandboxEnabled"):
            config_notice = (
                '<div class="notice">'
                "Live email/SMS auth is not configured, so local sandbox sign-in is available for development."
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
    elif phone:
        form = f"""
        <form method="post" action="/auth/verify-phone-code">
          <input name="phone" type="hidden" value="{escape(phone)}" />
          <div class="notice">SMS Code sent to {escape(phone)}. Check your device messages.</div>
          <label for="token">Verification Code</label>
          <input id="token" name="token" inputmode="numeric" autocomplete="one-time-code" required autofocus />
          <button {disabled}>Verify and enter</button>
        </form>
        <form method="get" action="/login">
          <button class="secondary" type="submit">Use a different phone</button>
        </form>
        """
    else:
        form = f"""
        <div class="login-section">
          <div class="tabs-header login-tabs">
            <button type="button" class="tab-btn active" onclick="switchTab('email-login-tab', event)">Email Code</button>
            <button type="button" class="tab-btn" onclick="switchTab('phone-login-tab', event)">Phone Number</button>
          </div>
          
          <div id="email-login-tab" class="tab-content active">
            <form method="post" action="/auth/send-code">
              <label for="email">Email</label>
              <input id="email" name="email" type="email" autocomplete="email" placeholder="name@domain.com" required autofocus />
              <button class="submit-code" style="width: 100%; margin-top: 12px;" {disabled}>Send sign-in code</button>
            </form>
          </div>
          
          <div id="phone-login-tab" class="tab-content">
            <form method="post" action="/auth/send-phone-code">
              <label for="phone">Phone Number</label>
              <input id="phone" name="phone" type="tel" placeholder="+15550000000" autocomplete="tel" required />
              <button class="submit-code" style="width: 100%; margin-top: 12px;" {disabled}>Send SMS code</button>
            </form>
          </div>
        </div>
        """
    sandbox_form = ""
    if auth.get("localSandboxEnabled"):
        sandbox_form = """
        <div class="sandbox-divider">
          <span>Local Developer Sandbox</span>
        </div>
        <div class="sandbox-section">
          <div class="tabs-header sandbox-tabs">
            <button type="button" class="tab-btn active" onclick="switchSandboxTab('sandbox-email-tab', event)">Sandbox Email</button>
            <button type="button" class="tab-btn" onclick="switchSandboxTab('sandbox-phone-tab', event)">Sandbox Phone</button>
          </div>
          
          <div id="sandbox-email-tab" class="tab-content active">
            <form method="post" action="/auth/dev-login">
              <label for="dev_email">Sandbox email</label>
              <input id="dev_email" name="email" type="email" placeholder="you@example.com" required />
              <button style="width: 100%; margin-top: 12px;">Enter local sandbox</button>
            </form>
          </div>
          
          <div id="sandbox-phone-tab" class="tab-content">
            <form method="post" action="/auth/dev-login">
              <label for="dev_phone">Sandbox phone</label>
              <input id="dev_phone" name="phone" type="tel" placeholder="+1234567890" required />
              <button style="width: 100%; margin-top: 12px;">Enter local sandbox</button>
            </form>
          </div>
        </div>
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
        {sandbox_form}
      </section>
    </main>
    <script>
      function switchTab(tabId, ev) {{
        document.querySelectorAll('.login-section .tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.login-section .tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        ev.currentTarget.classList.add('active');
      }}
      function switchSandboxTab(tabId, ev) {{
        document.querySelectorAll('.sandbox-section .tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.sandbox-section .tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        ev.currentTarget.classList.add('active');
      }}
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


def render_workspace(
    state: dict[str, Any],
    user: dict[str, Any],
    profile: dict[str, Any],
    error: str | None = None,
    message: str | None = None,
    circle_request_id: str | None = None,
) -> str:
    user_label = escape(str(user.get("email") or user.get("id")))
    profile_username = escape(profile.get("username", "unknown"))
    profile_wallet = escape(profile.get("wallet", "0x0000000000000000000000000000000000000000"))
    profile_balance = escape(str(profile.get("balance", "0.00")))
    circle_chain = escape(state.get("circle_wallet_summary", {}).get("chain", "ARC-TESTNET"))

    default_payer = f"@{profile_username}"
    error_html = f'<div class="notice bad">{escape(error)}</div>' if error else ""
    message_html = f'<div class="notice">{escape(message)}</div>' if message else ""
    body = f"""
    <main class="shell">
      <section class="workspace-intro">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
          <div>
            <div class="eyebrow">Interactive Console</div>
            <h2>Autonomous AI Witness Portal</h2>
            <p class="panel-copy">Welcome back, <strong>{user_label}</strong>. NOTARY turns real-world proof into signed AI attestations that trigger programmable USDC payments on Arc.</p>
          </div>
          <div class="sandbox-section" style="margin: 0; min-width: 320px; border: 1px solid var(--line); background: var(--surface-2); border-radius: 8px; padding: 16px; box-shadow: var(--shadow);">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
              <div>
                <span class="eyebrow" style="color: var(--green); margin: 0;">Your Profile</span>
                <h3 style="margin: 4px 0 2px; color: #fff; font-family: 'Outfit';">@{profile_username}</h3>
                <p style="margin: 0; font-size: 11px; color: var(--muted); cursor: pointer;" onclick="navigator.clipboard.writeText('{profile_wallet}'); alert('Copied address!')">
                  Wallet: <code style="color: var(--green); font-size: 11px;">{profile_wallet[:10]}...{profile_wallet[-8:]} 📋</code>
                </p>
              </div>
              <div style="text-align: right;">
                <span class="eyebrow" style="color: var(--green); margin: 0;">Balance</span>
                <h3 style="margin: 4px 0 2px; color: #fff; font-size: 20px; font-family: 'Outfit';">{profile_balance} USDC</h3>
                <p style="margin: 0; font-size: 10px; color: var(--muted);">{circle_chain}</p>
              </div>
            </div>
          </div>
        </div>
        {error_html}
        {message_html}
        <div class="steps">
          <div class="step">
            <strong>1. Define Secured Agreement</strong>
            <span>Write the payment condition in plain English (e.g. who pays, who gets paid, and what deliverables are required).</span>
          </div>
          <div class="step">
            <strong>2. Fund the Escrow Reserve</strong>
            <span>The payer moves funds into a secure conditional vault. Evidence submission unlocks only after funding is confirmed.</span>
          </div>
          <div class="step">
            <strong>3. Submit Proof & Settle</strong>
            <span>Provide a PR merge hash, file link, or payer approval. NOTARY's AI witness runs instant verification and releases the USDC!</span>
          </div>
        </div>
      </section>
      
      <section class="workspace">
        <aside>
          <div class="panel" style="border: 1px solid rgba(16, 185, 129, 0.25);">
            <h2>Send USDC Funds</h2>
            <p class="panel-copy">Transfer USDC instantly from your agent wallet to any recipient handle (e.g. <code>@jennycruzy</code>) or raw EVM address.</p>
            <form method="post" action="/ui/wallet/send">
              <label for="recipient">Recipient (Username or Wallet)</label>
              <input id="recipient" name="recipient" required placeholder="e.g. @jennycruzy or 0x..." />
              
              <label for="amount" style="margin-top: 10px;">Amount in USDC</label>
              <input id="amount" name="amount" type="number" min="0.01" step="0.01" value="10" required placeholder="e.g. 10" />
              
              <button style="margin-top: 14px; width: 100%;">Send USDC Transfer</button>
            </form>
          </div>

          <div class="panel">
            <h2>Create New Secure Escrow</h2>
            <p class="panel-copy">Draft a natural-language contract. The system automatically extracts obligations and generates secure webhook links.</p>
            
            <form method="post" action="/ui/cases">
              <label for="instruction">Agreement Details (Obligation)</label>
              <p class="panel-copy" style="margin-top: -4px; margin-bottom: 8px; font-size: 12px; color: var(--green);">Include the payee username and exact deliverables (e.g., "Pay @jennycruzy $50 when delivery manifest is complete and payer approves").</p>
              <textarea id="instruction" name="instruction" required placeholder="Type your natural language payment agreement here..."></textarea>
              
              <div class="split" style="margin-top: 8px;">
                <div>
                  <label for="payer_identity">Payer Username</label>
                  <input id="payer_identity" name="payer_identity" value="{default_payer}" required placeholder="e.g. @yourhandle" />
                </div>
                <div>
                  <label for="payer_type">Payer Type</label>
                  <select id="payer_type" name="payer_type">
                    <option value="human">Human Participant</option>
                    <option value="agent">Autonomous AI Agent</option>
                  </select>
                </div>
              </div>
              
              <div class="split">
                <div>
                  <label for="payee_identity">Payee Username</label>
                  <input id="payee_identity" name="payee_identity" value="@jennycruzy" required placeholder="e.g. @jennycruzy" />
                </div>
                <div>
                  <label for="payee_type">Payee Type</label>
                  <select id="payee_type" name="payee_type">
                    <option value="human">Human Participant</option>
                    <option value="agent">Autonomous AI Agent</option>
                  </select>
                </div>
              </div>
              
              <label for="amount_usdc">USDC Amount to Lock</label>
              <input id="amount_usdc" name="amount_usdc" type="number" min="0.01" step="0.01" value="50" required placeholder="e.g. 50" />
              
              <button style="margin-top: 18px;">Create Secured Agreement</button>
            </form>
          </div>
          
          <div class="panel">
            <h2>Capture Voice Proof</h2>
            <p class="panel-copy">Speak into your microphone or upload a voice note describing work completion. Speechmatics automatically generates transcription logs for NOTARY to judge.</p>
            <label for="record_privacy_mode">Privacy Shielding</label>
            <select id="record_privacy_mode">
              <option value="protected">Protected (Only counterparties & arbitrators see details)</option>
              <option value="private">Private (Completely encrypted, zero public exposure)</option>
              <option value="public">Public (Fully discoverable on public ledger)</option>
            </select>
            <div class="button-row">
              <button id="start_recording" type="button">🎙️ Start Recording</button>
              <button id="stop_recording" class="danger" type="button" disabled>⏹️ Stop & Transcribe</button>
            </div>
            <p id="recording_status" class="status-line">Microphone is ready.</p>
            
            <form method="post" action="/ui/media" enctype="multipart/form-data" style="border-top: 1px dashed var(--line); margin-top: 16px; padding-top: 16px;">
              <label for="file">Upload Audio/Video Recording</label>
              <input id="file" name="file" type="file" accept="audio/*,video/*" />
              <input name="privacy_mode" type="hidden" value="protected" />
              
              <label for="media_transcript_text">Or, Paste Pre-Recorded Transcript</label>
              <textarea id="media_transcript_text" name="transcript_text" placeholder="Copy/paste transcript text if you already have it..."></textarea>
              
              <button style="margin-top: 12px;">Process Upload & Run Witness</button>
            </form>
          </div>
          
          <div class="panel">
            <h2>Quick Written Proof</h2>
            <p class="panel-copy">Manually submit a text summary, signed authorization, or commit record to trigger instant witness analysis.</p>
            <form method="post" action="/ui/attest">
              <label for="privacy_mode">Privacy Shielding</label>
              <select id="privacy_mode" name="privacy_mode">
                <option value="protected">Protected (Default)</option>
                <option value="private">Private (Encrypted)</option>
                <option value="public">Public (Unrestricted)</option>
              </select>
              <label for="transcript_text">Written Evidence</label>
              <textarea id="transcript_text" name="transcript_text" placeholder="Include clear confirmation markers (e.g. 'I, @yourhandle, approve release of $50 because the pull request #5 is complete and merged')."></textarea>
              <button>Submit Evidence</button>
            </form>
          </div>
        </aside>
        
        <section>
          <div class="section-head">
            <div>
              <h2>My Active Escrow Cases</h2>
              <p>{len(state.get("cases", []))} conditional payment case(s) active on this account.</p>
            </div>
          </div>
          <div class="grid">{_case_cards(state.get("cases", []))}</div>
          
          <div class="section-head" style="margin-top:28px">
            <div>
              <h2>My Witness Rulings</h2>
              <p>{len(state.get("rulings", []))} automated witness ruling(s) committed.</p>
            </div>
          </div>
          <div class="grid">{_record_cards(state.get("rulings", []))}</div>
        </section>
      </section>
      
      <details class="advanced-stack">
        <summary>Advanced Dev Swarm, Arc, & Operator Controls</summary>
        {_ops_panels(state, circle_request_id)}
        <div class="section-head" style="margin-top:18px">
          <div>
            <div class="eyebrow">6-Agent Autonomous Swarm</div>
            <h2>Decision Roles</h2>
            <p>Every case triggers our orchestrated pipeline, split into six specialized consensus agents:</p>
          </div>
        </div>
        <div class="agent-grid">{_agent_role_cards(state.get("swarm_roles", []))}</div>
      </details>
    </main>
    {_workspace_scripts()}
    """
    return _page("Workspace · NOTARY", body, user)


def render_case_evidence(case: dict[str, Any], token: str | None, user: dict[str, Any] | None) -> str:
    hidden_token = f'<input name="token" type="hidden" value="{escape(token)}" />' if token else ""
    is_funded = case.get("status") != "awaiting_funding"
    funding_notice = (
        '<div class="notice bad">🚨 This contract is currently awaiting funding. Submitting proof is locked until the Payer deposits USDC into the secure conditional escrow vault.</div>'
        if not is_funded
        else ""
    )
    disabled = "" if is_funded else "disabled"
    body = f"""
    <main class="signin">
      <section class="panel signin-card" style="width: min(600px, 100%);">
        <div class="eyebrow">Contract Evidence Portal</div>
        <h1>Submit Secured Evidence</h1>
        <p class="panel-copy" style="font-size: 14px; line-height: 1.55;">
          You are submitting verification proof for: <br/>
          <strong>"{_text(case.get("instruction"))}"</strong>
        </p>
        
        <div class="facts" style="margin-bottom: 20px;">
          <div class="fact"><span>Contract Payer</span><strong>{_text(case.get("payer_identity"))}</strong></div>
          <div class="fact"><span>Contract Payee</span><strong>{_text(case.get("payee_identity"))}</strong></div>
          <div class="fact"><span>Secure Escrow Ref</span><code>{escape(_short(case.get("escrow_payment_reference"), 24))}</code></div>
        </div>
        
        {funding_notice}
        
        <form method="post" action="/cases/{escape(case.get("case_id"))}/evidence" style="border-top: 1px dashed var(--line); padding-top: 20px;">
          {hidden_token}
          <label for="submitter_identity">Your Username</label>
          <p class="panel-copy" style="margin-top: -4px; margin-bottom: 8px; font-size: 12px;">Confirm your NOTARY identity (e.g. <i>@jennycruzy</i> or <i>@yourhandle</i>).</p>
          <input id="submitter_identity" name="submitter_identity" value="{escape(str((user or {}).get("email") or case.get("payee_identity") or ""))}" required {disabled} />
          
          <label for="submitter_type" style="margin-top: 14px;">Identity Classification</label>
          <select id="submitter_type" name="submitter_type" {disabled}>
            <option value="human">Human Operator</option>
            <option value="agent">AI Assistant / Autonomous Agent</option>
          </select>
          
          <label for="evidence_text" style="margin-top: 14px;">Evidence / Verifiable Proof</label>
          <p class="panel-copy" style="margin-top: -4px; margin-bottom: 8px; font-size: 12px; color: var(--green);">
            Provide objective proof (e.g. commit hashes, PR merge links, file paths). 
            Include positive action terms like <strong>"completed"</strong>, <strong>"delivered"</strong>, or <strong>"approved"</strong> to guarantee instant payment release!
          </p>
          <textarea id="evidence_text" name="evidence_text" required placeholder="Paste your links, commits, or signed approval statements here..." {disabled}></textarea>
          
          <button style="margin-top: 20px;" {disabled}>🚀 Submit & Verify Proof</button>
        </form>
      </section>
    </main>
    """
    return _page("Submit evidence · NOTARY", body, user)
