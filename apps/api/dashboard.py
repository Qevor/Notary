from __future__ import annotations

from html import escape
import json
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
      --bg: #090d16;
      --ink: #f3f4f6;
      --muted: #9ca3af;
      --surface: rgba(17, 24, 39, 0.7);
      --surface-2: rgba(31, 41, 55, 0.45);
      --line: rgba(255, 255, 255, 0.07);
      --line-hover: rgba(255, 255, 255, 0.15);
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
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --primary-glow: rgba(99, 102, 241, 0.2);
      --glass: rgba(17, 24, 39, 0.6);
      --shadow: 0 20px 40px rgba(0, 0, 0, 0.55);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      background-image: radial-gradient(circle at top center, rgba(99, 102, 241, 0.12) 0%, rgba(9, 13, 22, 0) 65%), radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.02) 0%, rgba(9, 13, 22, 0) 40%);
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
      background: rgba(9, 13, 22, 0.85);
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
      text-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
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
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
    }
    .nav-link:hover, .mini-form button:hover {
      border-color: var(--line-hover);
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }
    .nav-link.primary {
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
      font-weight: 700;
      box-shadow: 0 4px 12px var(--primary-glow);
    }
    .nav-link.primary:hover {
      background: var(--primary-hover);
      border-color: var(--primary-hover);
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
      color: var(--primary);
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
      border: 1px solid var(--primary);
      background: var(--primary);
      color: white;
      padding: 0 24px;
      font-weight: 700;
      font-size: 14px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      box-shadow: 0 4px 12px var(--primary-glow);
      width: 100%;
    }
    .button:hover {
      background: var(--primary-hover);
      border-color: var(--primary-hover);
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
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
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric:hover {
      border-color: rgba(99, 102, 241, 0.3);
      background: rgba(255, 255, 255, 0.05);
      transform: translateY(-2px);
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
    }
    .metric strong {
      display: block;
      font-size: 28px;
      color: #fff;
      margin-bottom: 4px;
      font-family: 'Outfit', sans-serif;
    }
    .metric span {
      font-size: 12px;
      color: var(--muted);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: 32px;
      box-shadow: var(--shadow);
      margin-bottom: 28px;
      transition: all 0.25s ease;
    }
    .panel:hover {
      border-color: rgba(255, 255, 255, 0.12);
    }
    .panel h2 {
      font-size: 22px;
      color: #fff;
      margin-bottom: 8px;
      letter-spacing: -0.01em;
    }
    .panel-copy {
      color: var(--muted);
      font-size: 13.5px;
      line-height: 1.5;
      margin-bottom: 20px;
    }
    .panel form { margin: 0; }
    label {
      display: block;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 6px;
    }
    input, textarea, select {
      width: 100%;
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, 0.2);
      color: #fff;
      font-family: inherit;
      font-size: 14.5px;
      margin-bottom: 16px;
      transition: all 0.2s ease;
    }
    input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--primary);
      background: rgba(0, 0, 0, 0.3);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }
    textarea { min-height: 90px; resize: vertical; }
    select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 14px center; background-size: 16px; padding-right: 40px; }
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      border-radius: 8px;
      border: 1px solid var(--primary);
      background: var(--primary);
      color: white;
      padding: 0 20px;
      font-weight: 700;
      font-size: 14px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      box-shadow: 0 4px 12px var(--primary-glow);
    }
    button:hover {
      background: var(--primary-hover);
      border-color: var(--primary-hover);
      transform: translateY(-1px);
    }
    button.danger {
      background: rgba(239, 68, 68, 0.1);
      color: var(--red);
      border-color: rgba(239, 68, 68, 0.2);
      box-shadow: none;
    }
    button.danger:hover {
      background: var(--red);
      color: white;
      border-color: var(--red);
      box-shadow: 0 4px 12px var(--red-glow);
    }
    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none !important;
      box-shadow: none !important;
    }
    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .workspace {
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 36px;
      align-items: start;
    }
    .workspace-intro {
      margin-bottom: 36px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--line);
    }
    .workspace-intro h2 {
      font-size: 32px;
      color: #fff;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
    }
    .steps {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-top: 24px;
    }
    .step {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 16px 20px;
    }
    .step strong {
      display: block;
      color: #fff;
      font-size: 14.5px;
      margin-bottom: 6px;
      font-family: 'Outfit', sans-serif;
    }
    .step span {
      font-size: 12.5px;
      color: var(--muted);
      line-height: 1.4;
      display: block;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 20px;
    }
    .section-head h2 { font-size: 24px; color: #fff; margin-bottom: 4px; }
    .section-head p { color: var(--muted); font-size: 13.5px; margin: 0; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface);
      padding: 24px;
      transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .card:hover {
      border-color: rgba(99, 102, 241, 0.35);
      transform: translateY(-2px);
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
    }
    .card-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .card-title {
      font-weight: 700;
      color: #fff;
      font-size: 17px;
      font-family: 'Outfit', sans-serif;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge.active { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge.completed { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge.held { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge.failed { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge.good { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .card p { color: var(--muted); font-size: 13.5px; line-height: 1.5; margin-bottom: 16px; }
    .card-foot {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: auto;
    }
    .fact { display: flex; flex-direction: column; gap: 2px; }
    .fact span { font-size: 10px; text-transform: uppercase; color: var(--muted); letter-spacing: 0.05em; }
    .fact strong { font-size: 14px; color: #fff; font-family: 'Outfit', sans-serif; }
    .notice {
      border: 1px solid rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.05);
      color: #a7f3d0;
      padding: 14px 20px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 24px;
    }
    .notice.bad {
      border-color: rgba(239, 68, 68, 0.3);
      background: rgba(239, 68, 68, 0.05);
      color: #fca5a5;
    }
    .empty {
      padding: 40px;
      text-align: center;
      color: var(--muted);
      font-size: 14.5px;
      border: 1px dashed var(--line);
      border-radius: 12px;
      background: rgba(255,255,255,0.01);
    }
    .advanced-stack {
      margin-top: 48px;
      border-top: 1px solid var(--line);
      padding-top: 24px;
    }
    .advanced-stack summary {
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      cursor: pointer;
      user-select: none;
      transition: color 0.2s ease;
      margin-bottom: 20px;
      display: inline-block;
    }
    .advanced-stack summary:hover { color: #fff; }
    .agent-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-top: 16px;
    }
    .agent-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 20px;
    }
    .agent-card h4 {
      font-size: 15.5px;
      color: #fff;
      margin-bottom: 6px;
      font-family: 'Outfit', sans-serif;
    }
    .agent-card p {
      font-size: 12.5px;
      color: var(--muted);
      line-height: 1.4;
      margin: 0;
    }
    .button-row { display: flex; gap: 8px; margin-bottom: 12px; }
    .button-row button { flex: 1; font-size: 13px; }
    .status-line { font-size: 11px; color: var(--muted); margin: 0; }
    .flow-step {
      display: grid;
      grid-template-columns: 24px 1fr;
      gap: 16px;
      margin-bottom: 16px;
    }
    .flow-step-num {
      width: 24px;
      height: 24px;
      border-radius: 99px;
      border: 1.5px solid var(--primary);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 800;
      font-family: 'Outfit', sans-serif;
    }
    .flow-step-copy {
      font-size: 13.5px;
      color: var(--muted);
      line-height: 1.4;
    }
    .flow-step-copy strong { color: #fff; display: block; margin-bottom: 2px; }
    .tabs-header {
      display: flex;
      border-bottom: 1px solid var(--line);
      margin-bottom: 20px;
    }
    .tab-btn {
      background: transparent !important;
      border: none !important;
      border-bottom: 2px solid transparent !important;
      color: var(--muted) !important;
      font-weight: 600 !important;
      font-size: 14.5px !important;
      padding: 10px 16px !important;
      border-radius: 0 !important;
      box-shadow: none !important;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .tab-btn:hover {
      color: #fff !important;
    }
    .tab-btn.active {
      color: var(--primary) !important;
      border-bottom-color: var(--primary) !important;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .signin-card {
      max-width: 440px;
      margin: 100px auto;
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
    }
    """


def _page(title: str, body: str, user: dict[str, Any] | None = None) -> str:
    if user:
        username = escape(str(user.get("email") or user.get("id"))).split("@")[0].lower()
        auth_link = f"""
        <a class="nav-link" href="/app">Workspace</a>
        <a class="nav-link" href="/profile/{username}">My Profile &amp; Wallet</a>
        <form class="mini-form" method="post" action="/auth/logout" style="display: inline;"><button>Sign out</button></form>
        """
    else:
        auth_link = '<a class="nav-link primary" href="/login">Sign in</a>'

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
            <span>Autonomous AI Witness Layer for USDC Payments on Arc</span>
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
            <div class="flow-step" style="background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px; display: grid; grid-template-columns: auto 1fr auto; padding: 20px; align-items: center; margin-bottom: 12px;">
              <div class="number" style="width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; background: var(--primary-glow); color: var(--primary); font-weight: 800; border: 1px solid var(--primary); margin-right: 16px;">{index}</div>
              <div>
                <strong>{escape(label)}</strong>
                <p style="margin: 4px 0 0; color: var(--muted); font-size: 13.5px;">{escape(str(summary))}</p>
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
        parties = item.get("partyIdentities", {}) or item.get("metadata", {}) or {}
        precedent_list = item.get("precedentRefs", []) or item.get("precedent_refs", []) or []
        precedent = ", ".join(precedent_list) or "none"
        reasoning = escape(str(item.get("reasoningTrace") or item.get("reasoning_trace") or "No reasoning trace recorded."))
        reversal = item.get("reversal") or {}
        reversal_note = ""
        if item.get("reversed") or item.get("supersedes"):
            reversal_note = (
                f'<div class="notice" style="border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.05); color: #fca5a5;">Reversal action: '
                f'{_label(reversal.get("corrective_payment_action", "recorded"))}</div>'
            )
        details = ""
        if not compact:
            details = f"""
            <details style="margin-top: 14px;">
              <summary style="font-size: 13px; color: var(--primary); font-weight: 600; cursor: pointer; user-select: none;">View reasoning and hashes</summary>
              <div class="facts" style="margin-top: 12px; margin-bottom: 12px;">
                <div class="fact"><span>Deliverable</span><strong>{_text(obligation.get("deliverable"))}</strong></div>
                <div class="fact"><span>Acceptance</span><strong>{_text(obligation.get("acceptance_criterion"))}</strong></div>
                <div class="fact"><span>Trace hash</span><code>{escape(_short(item.get("reasoningTraceHash") or item.get("reasoning_trace_hash"), 30))}</code></div>
              </div>
              <pre style="background: rgba(0,0,0,0.25); padding: 16px; border-radius: 8px; border: 1px solid var(--line); font-size: 12.5px; overflow-x: auto; white-space: pre-wrap; font-family: monospace; color: var(--muted);">{reasoning}</pre>
            </details>
            """
        cards.append(
            f"""
            <article class="record" style="border: 1px solid var(--line); border-radius: 16px; padding: 28px; transition: all 0.22s ease; margin-bottom: 20px;">
              <div class="record-head" style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px;">
                <div>
                  <div class="kicker" style="color: var(--primary);">Obligation committed</div>
                  <h3 style="font-size: 20px; color: #fff; margin: 4px 0 6px; font-family: 'Outfit'; font-weight: 800;">{_text(item.get("obligationSummary") or item.get("instruction") or "Untitled obligation")}</h3>
                  <p style="color: var(--muted); font-size: 13px; margin: 0;">payer {_text(parties.get("payer") or item.get("payer_identity"))} · payee {_text(parties.get("payee") or item.get("payee_identity"))}</p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                  {_badge(_label(item.get("verdict") or item.get("status")), _tone(item))}
                  {_badge(f"confidence {item.get('confidence', 'n/a')}", _tone(item))}
                </div>
              </div>
              {reversal_note}
              <div class="facts" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px;">
                <div class="fact"><span>Release</span><strong>{_text(item.get("releasePct") or item.get("release_pct"))}%</strong></div>
                <div class="fact"><span>Gate</span><strong>{_label(item.get("confidenceGate") or item.get("confidence_gate"))}</strong></div>
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
            <article class="record" style="border: 1px solid var(--line); border-radius: 16px; padding: 28px; transition: all 0.22s ease;">
              <div class="record-head" style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px;">
                <div>
                  <div class="kicker" style="color: var(--primary);">Case {escape(_short(item.get("case_id"), 20))}</div>
                  <h3 style="font-size: 20px; color: #fff; margin: 4px 0 6px; font-family: 'Outfit'; font-weight: 800;">{_text(item.get("instruction"))}</h3>
                  <p style="color: var(--muted); font-size: 13px; margin: 0;">payer {_text(item.get("payer_identity"))} · payee {_text(item.get("payee_identity"))}</p>
                </div>
                {_badge(_label(item.get("status")), "good" if item.get("status") == "released" else "hold")}
              </div>
              <div class="facts" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px;">
                <div class="fact"><span>Amount</span><strong>{_text(item.get("amount_usdc"))} USDC</strong></div>
                <div class="fact"><span>Escrow ref</span><code>{escape(_short(item.get("escrow_payment_reference"), 28))}</code></div>
                <div class="fact"><span>Latest ruling</span><code>{escape(_short(item.get("latest_ruling_id"), 28))}</code></div>
              </div>
              {guarded_note}
              <div class="actions" style="margin-top:16px; display: flex; gap: 8px;">{funding_link}{upload_link}</div>
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
            <article class="agent-card" style="border: 1px solid var(--line); border-radius: 12px; background: var(--surface-2); padding: 20px; transition: all 0.2s ease;">
              <div class="kicker" style="color: var(--primary);">{_label(item.get("status"))}</div>
              <h3 style="font-size: 16px; margin: 6px 0; color: #fff; font-family: 'Outfit';">{_text(item.get("name"))}</h3>
              <p style="color: var(--muted); font-size: 13px; line-height: 1.45; margin-bottom: 12px;">{_text(item.get("role"))}</p>
              <code style="display: block; overflow-wrap: anywhere; font-size: 11px; color: var(--green); background: rgba(16, 185, 129, 0.05); padding: 6px 8px; border-radius: 4px;">{escape(_short(item.get("lastOutput"), 64))}</code>
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
        <form class="inline-form compact" method="post" action="/ui/notaries/{escape(str(latest.get("notary_id")) or '')}/register-onchain" style="margin-top: 14px;">
          <button class="button secondary" style="width: 100%;" {'disabled' if not latest else ''}>Register / refresh on Arc</button>
        </form>
        <div class="facts" style="margin-top: 14px;">{receipt_rows}</div>
        """
        if latest
        else """
        <p class="panel-copy">Create a NOTARY first. This mints the local legal identity, Circle agent wallet, operating agreement hash, and Arc registration payload.</p>
        <form class="inline-form" method="post" action="/ui/notaries">
          <label for="notary_label">Label</label>
          <input id="notary_label" name="label" placeholder="NOTARY witness agent" required />
          <button style="width: 100%;">Create NOTARY identity</button>
        </form>
        """
    )
    otp_form = (
        f"""
        <form class="inline-form" method="post" action="/ui/circle/login/complete" style="margin-top: 12px;">
          <input name="request_id" type="hidden" value="{escape(circle_request_id)}" />
          <label for="circle_otp">Circle OTP</label>
          <input id="circle_otp" name="otp" autocomplete="one-time-code" required />
          <button style="width: 100%;">Complete Circle login</button>
        </form>
        """
        if circle_request_id
        else ""
    )
    return f"""
    <div class="ops-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 24px;">
      <section class="panel" style="margin-bottom: 0;">
        <div class="eyebrow" style="color: var(--primary);">Arc identity</div>
        <h2>On-chain NOTARY</h2>
        <p class="panel-copy">The agent has an Arc identity, operating agreement hash, privacy policy hash, and governance record.</p>
        {notary_panel}
      </section>
      <section class="panel" style="margin-bottom: 0;">
        <div class="eyebrow" style="color: var(--primary);">User funding</div>
        <h2>NOTARY holds escrow, NOTARY witnesses</h2>
        <p class="panel-copy">Users sign in with password, create a case, and fund the NOTARY conditional escrow. Circle CLI stays server-side for the NOTARY agent wallet and executor.</p>
        <div class="facts" style="margin-bottom: 14px;">
          <div class="fact"><span>User step</span><strong>Direct Auth</strong></div>
          <div class="fact"><span>Payment step</span><strong>Fund Escrow</strong></div>
          <div class="fact"><span>Agent step</span><strong>Witness &amp; Settle</strong></div>
        </div>
        <details>
          <summary style="font-size: 13px; color: var(--primary); font-weight: 600; cursor: pointer;">Operator Circle session</summary>
          <p class="panel-copy" style="margin-top: 8px;">Only builders/operators need this while running the agent server locally. End users do not install Circle CLI.</p>
          <form class="inline-form" method="post" action="/ui/circle/login/init">
            <label for="circle_email">Operator Circle email</label>
            <input id="circle_email" name="email" type="email" placeholder="operator@example.com" required />
            <button style="width: 100%;">Start operator Circle login</button>
          </form>
          {otp_form}
          <form class="inline-form" method="post" action="/ui/circle/deposit" style="margin-top: 12px; border-top: 1px dashed var(--line); padding-top: 12px;">
            <label for="wallet_id">NOTARY agent wallet or address</label>
            <input id="wallet_id" name="wallet_id" value="{escape(str(latest.get("agent_wallet") or ""))}" placeholder="0x... or Circle wallet ID" required />
            <label for="deposit_amount">Operator deposit amount USDC</label>
            <input id="deposit_amount" name="amount_usdc" type="number" min="0.01" step="0.01" value="10" required />
            <button style="width: 100%;">Prepare operator Gateway route</button>
          </form>
        </details>
        <div class="facts" style="margin-top: 14px;">{route_rows}</div>
      </section>
    </div>
    """

    wallet_card = f"""
    <div class="panel" style="border: 1px solid rgba(99, 102, 241, 0.2); background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px;">
      <div class="eyebrow" style="color: var(--primary);">Secure Wallet</div>
      <h2 style="margin: 6px 0 2px; color: #fff; font-size: 28px; font-family: 'Outfit'; font-weight: 800;">{profile_balance} USDC</h2>
      <p style="margin: 0 0 16px; font-size: 12px; color: var(--muted);">ARC-TESTNET</p>

      <label style="font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 6px;">EVM Address</label>
      <div style="display: grid; gap: 10px; background: var(--surface-2); padding: 12px; border-radius: 8px; border: 1px solid var(--line);">
        <code id="profile-wallet-address" style="color: var(--green); font-size: 12px; font-weight: 700; line-height: 1.5; word-break: break-all; white-space: normal;">{profile_wallet}</code>
        <button type="button" id="copy-wallet-address" class="secondary" style="width: 100%; min-height: 40px; border-radius: 8px;" onclick="copyProfileWalletAddress({profile_wallet_js})">Copy address</button>
        <span id="copy-wallet-status" style="min-height: 16px; color: var(--green); font-size: 12px; font-weight: 700;"></span>
      </div>
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
    <script>
      async function copyProfileWalletAddress(address) {{
        const status = document.getElementById('copy-wallet-status');
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(address);
          }} else {{
            const textArea = document.createElement('textarea');
            textArea.value = address;
            textArea.setAttribute('readonly', '');
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
          }}
          if (status) {{
            status.textContent = 'Address copied';
            setTimeout(() => status.textContent = '', 2200);
          }}
        }} catch (error) {{
          if (status) status.textContent = 'Select the address text and copy manually';
        }}
      }}
    </script>
    <main class="shell">
      <section class="hero" style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 32px; align-items: stretch; margin-bottom: 40px;">
        <div class="hero-copy" style="border: 1px solid var(--line); border-radius: 16px; padding: 48px; background: var(--surface); backdrop-filter: blur(16px); box-shadow: var(--shadow); display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div class="eyebrow" style="color: var(--primary); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em;">AI Witness Layer</div>
            <h1 style="font-size: 46px; line-height: 1.1; letter-spacing: -0.02em; margin: 12px 0 16px; color: #fff; font-family: 'Outfit'; font-weight: 900;">Programmable USDC payments triggered by real-world proof.</h1>
            <p style="color: var(--muted); font-size: 16px; line-height: 1.6; margin-bottom: 28px;">NOTARY turns real-world proof — voice notes, files, videos, work logs, and approvals — into signed AI attestations that trigger programmable USDC payments on Arc.</p>
            <div class="actions" style="display: flex; gap: 12px;">
              <a class="button" href="/app" style="width: auto;">Open workspace</a>
              <a class="button secondary" href="/ledger">View all public records</a>
            </div>
          </div>
          <div class="metrics" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 40px;">
            <div class="metric"><span>Public rulings</span><strong>{len(rulings)}</strong></div>
            <div class="metric"><span>Avg confidence</span><strong>{escape(str(average_confidence))}</strong></div>
            <div class="metric"><span>Disputes</span><strong>{len(state.get("disputes", []))}</strong></div>
            <div class="metric"><span>Reversals</span><strong>{len(state.get("reversals", []))}</strong></div>
          </div>
        </div>
        <div class="flow" style="border: 1px solid var(--line); border-radius: 16px; background: var(--surface); padding: 36px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 16px;">
          <div>
            <div class="eyebrow" style="color: var(--primary);">Settlement flow</div>
            <h2 style="font-size: 24px; color: #fff; font-family: 'Outfit'; font-weight: 800;">Release, hold, or correct on the record</h2>
          </div>
          {_public_flow_items(rulings)}
        </div>
      </section>
      <section class="section" style="margin-top: 48px;">
        <div class="section-head" style="margin-bottom: 24px;">
          <div>
            <h2 style="font-size: 28px; color: #fff; font-family: 'Outfit'; font-weight: 800; margin-bottom: 4px;">Recent public records</h2>
            <p style="color: var(--muted); font-size: 15px;">Summaries and commitments are public. Raw evidence remains private.</p>
          </div>
          <a class="button secondary" href="/ledger">See all</a>
        </div>
        <div class="grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px;">{_record_cards(rulings, limit=3, compact=True)}</div>
      </section>
    </main>
    """
    return _page("NOTARY", body, user)


def render_public_ledger(state: dict[str, Any], user: dict[str, Any] | None = None) -> str:
    body = f"""
    <script>
      async function copyProfileWalletAddress(address) {{
        const status = document.getElementById('copy-wallet-status');
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(address);
          }} else {{
            const textArea = document.createElement('textarea');
            textArea.value = address;
            textArea.setAttribute('readonly', '');
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
          }}
          if (status) {{
            status.textContent = 'Address copied';
            setTimeout(() => status.textContent = '', 2200);
          }}
        }} catch (error) {{
          if (status) status.textContent = 'Select the address text and copy manually';
        }}
      }}
    </script>
    <main class="shell">
      <div class="section-head" style="margin-bottom: 32px; border-bottom: 1px solid var(--line); padding-bottom: 20px;">
        <div>
          <div class="eyebrow" style="color: var(--primary);">Public ledger</div>
          <h2 style="font-size: 34px; color: #fff; font-family: 'Outfit'; font-weight: 800; margin: 4px 0;">Inspectable rulings, reversals, and reasoning</h2>
          <p style="color: var(--muted); font-size: 15px;">Only summaries, verdicts, hashes, and attestation chains are public by default.</p>
        </div>
        <a class="button secondary" href="/">Back home</a>
      </div>
      <div style="max-width: 900px; margin: 0 auto;">{_record_cards(state.get("rulings", []))}</div>
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
    tab: str | None = None,
    prefill: str | None = None,
) -> str:
    notice = ""
    if message:
        notice = f'<div class="notice">{escape(message)}</div>'
    if error:
        notice = f'<div class="notice bad">{escape(error)}</div>'

    show_register = tab == "register"
    login_active = "" if show_register else "active"
    register_active = "active" if show_register else ""

    prefill_val = escape(prefill or "")
    login_prefill = f'value="{prefill_val}"' if prefill_val else ""

    form = f"""
    <div class="login-section">
      <div class="tabs-header login-tabs">
        <button type="button" class="tab-btn {login_active}" onclick="switchTab('login-tab', event)">Sign In</button>
        <button type="button" class="tab-btn {register_active}" onclick="switchTab('register-tab', event)">Register</button>
      </div>

      <div id="login-tab" class="tab-content {login_active}">
        <form method="post" action="/auth/login">
          <label for="username">Email address or @handle</label>
          <input id="username" name="username" type="text" placeholder="mebstel@gmail.com or @yourhandle" {login_prefill} required {'autofocus' if not show_register else ''} />

          <label for="password" style="margin-top: 12px; display: block;">Password</label>
          <input id="password" name="password" type="password" placeholder="••••••••" required />

          <button class="submit-code" style="width: 100%; margin-top: 18px;">Sign In to NOTARY</button>
        </form>
      </div>

      <div id="register-tab" class="tab-content {register_active}">
        <form method="post" action="/auth/register">
          <label for="reg-username">Email address or @handle</label>
          <input id="reg-username" name="username" type="text" placeholder="mebstel@gmail.com or @yourhandle" value="{prefill_val}" required {'autofocus' if show_register else ''} />

          <label for="reg-password" style="margin-top: 12px; display: block;">Password (min 6 characters)</label>
          <input id="reg-password" name="password" type="password" placeholder="••••••••" required />

          <label for="confirm-password" style="margin-top: 12px; display: block;">Confirm Password</label>
          <input id="confirm-password" name="confirm_password" type="password" placeholder="••••••••" required />

          <button class="submit-code" style="width: 100%; margin-top: 18px;">Set Password &amp; Sign In</button>
        </form>
      </div>
    </div>
    """

    body = f"""
    <main class="signin">
      <section class="panel signin-card" style="border-radius: 16px; border: 1px solid var(--line); background: var(--surface); padding: 40px; box-shadow: var(--shadow);">
        <div class="eyebrow" style="color: var(--primary);">Private workspace</div>
        <h1 style="font-size: 30px; font-family: 'Outfit'; font-weight: 800; color: #fff; margin: 6px 0 12px;">Sign in to use NOTARY</h1>
        <p class="panel-copy" style="font-size: 14px; line-height: 1.5;">Each payer, payee, approver, or agent counterparty gets its own workspace. Public records stay on the landing page; your evidence and actions stay here.</p>
        <div class="notice" style="border-color: rgba(99, 102, 241, 0.25); background: rgba(99, 102, 241, 0.05); color: #c7d2fe; font-size: 13px; padding: 12px 16px; margin-bottom: 20px;">
          💡 Secure Auth: Access your workspace with a handle and password. A local agent wallet is automatically mapped to your account.
        </div>
        {notice}
        {form}
      </section>
    </main>
    <script>
      function switchTab(tabId, ev) {{
        document.querySelectorAll('.login-section .tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.login-section .tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        ev.currentTarget.classList.add('active');
      }}
      document.querySelectorAll("form").forEach(form => {{
        form.addEventListener("submit", (e) => {{
          const button = form.querySelector("button[type='submit'], button:not([type])");
          if (button && !button.disabled) {{
            button.dataset.originalText = button.textContent || "";
            button.textContent = "Entering Workspace...";
            setTimeout(() => {{ button.disabled = true; }}, 1);
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
    
    default_payer = f"@{profile_username}"
    error_html = f'<div class="notice bad" style="border-radius: 8px;">{escape(error)}</div>' if error else ""
    message_html = f'<div class="notice" style="border-radius: 8px;">{escape(message)}</div>' if message else ""
    
    body = f"""
    <main class="shell">
      <section class="workspace-intro" style="margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid var(--line);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
          <div>
            <div class="eyebrow" style="color: var(--primary);">Interactive Console</div>
            <h2 style="font-size: 36px; color: #fff; font-family: 'Outfit'; font-weight: 900; letter-spacing: -0.02em; margin: 4px 0 8px;">Autonomous AI Witness Portal</h2>
            <p class="panel-copy" style="margin: 0; font-size: 15px;">Welcome back, <strong>{user_label}</strong>. NOTARY turns real-world proof into signed AI attestations that trigger programmable USDC escrow payments on Arc.</p>
          </div>
        </div>
        {error_html}
        {message_html}
        <div class="steps" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 28px;">
          <div class="step">
            <strong>1. Define Secured Agreement</strong>
            <span>Write the payment condition in plain English (e.g., who pays, who gets paid, and what deliverables are required).</span>
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
      
      <section class="workspace" style="display: grid; grid-template-columns: 380px 1fr; gap: 36px; align-items: start;">
        <aside style="position: sticky; top: 100px;">
          <div class="panel" style="border: 1px solid var(--line); border-radius: 16px; background: var(--surface); padding: 32px; box-shadow: var(--shadow);">
            <h2>Create New Secure Escrow</h2>
            <p class="panel-copy">Draft a natural-language contract. The system automatically extracts obligations and generates secure webhook links.</p>
            
            <form method="post" action="/ui/cases">
              <label for="instruction">Agreement Details (Obligation)</label>
              <p class="panel-copy" style="margin-top: -4px; margin-bottom: 8px; font-size: 12px; color: var(--primary);">Include the payee username and exact deliverables (e.g., "Pay @jennycruzy $50 when delivery manifest is complete and payer approves").</p>
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
              
              <button style="margin-top: 18px; width: 100%;">Create Secured Agreement</button>
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
              
              <button style="margin-top: 12px; width: 100%;">Process Upload & Run Witness</button>
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
              <button style="width: 100%;">Submit Evidence</button>
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
            <div class="eyebrow" style="color: var(--primary);">6-Agent Autonomous Swarm</div>
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
        <div class="eyebrow" style="color: var(--primary);">Contract Evidence Portal</div>
        <h1 style="font-size: 30px; font-family: 'Outfit'; font-weight: 800; color: #fff; margin: 6px 0 12px;">Submit Secured Evidence</h1>
        <p class="panel-copy" style="font-size: 14.5px; line-height: 1.55;">
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
          
          <button style="margin-top: 20px; width: 100%;" {disabled}>🚀 Submit &amp; Verify Proof</button>
        </form>
      </section>
    </main>
    """
    return _page("Submit evidence · NOTARY", body, user)


def render_user_profile(
    profile: dict[str, Any],
    transactions: list[dict[str, Any]],
    viewer: dict[str, Any] | None = None,
    error: str | None = None,
    message: str | None = None,
) -> str:
    from datetime import datetime
    
    profile_username = escape(profile.get("username", "unknown"))
    profile_wallet_raw = str(profile.get("wallet", "0x0000000000000000000000000000000000000000"))
    profile_wallet = escape(profile_wallet_raw)
    profile_wallet_js = escape(json.dumps(profile_wallet_raw))
    profile_balance = escape(str(profile.get("balance", "0.00")))
    
    # Check if the viewer is the owner
    viewer_username = ""
    if viewer and isinstance(viewer, dict) and viewer.get("user"):
        viewer_username = viewer["user"].get("id", "").split("@")[0].lower()
    elif viewer and isinstance(viewer, dict) and viewer.get("id"):
        viewer_username = viewer.get("id", "").split("@")[0].lower()
        
    viewer_is_owner = viewer_username == profile_username
    
    tx_rows = []
    if not transactions:
        tx_rows.append('<div class="empty" style="text-align: center; padding: 40px; background: var(--surface-2); border-radius: 12px; border: 1px solid var(--line); color: var(--muted);">No transaction history recorded yet.</div>')
    else:
        for tx in transactions:
            direction = tx.get("direction")
            is_send = direction == "send"
            color = "#ef4444" if is_send else "#10b981"
            prefix = "-" if is_send else "+"
            arrow = "↗️" if is_send else "↙️"
            amount_display = f'<strong style="color: {color}; font-family: \'Outfit\'; font-size: 16px;">{prefix}{tx.get("amount_usdc")} USDC</strong>'
            
            try:
                date_str = datetime.fromtimestamp(tx.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = "unknown date"
                
            tx_rows.append(
                f"""
                <div class="flow-step" style="background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 12px; display: grid; grid-template-columns: auto 1fr auto; padding: 16px 20px; align-items: center; transition: all 0.2s ease;">
                  <div style="font-size: 24px; line-height: 1; margin-right: 16px;">{arrow}</div>
                  <div>
                    <strong style="font-size: 16px; color: #fff; font-family: 'Outfit';">{escape(tx.get("description", ""))}</strong>
                    <span style="display: block; font-size: 12px; color: var(--muted); margin-top: 4px;">Party: {escape(tx.get("party", ""))} · {date_str}</span>
                  </div>
                  <div style="text-align: right;">
                    {amount_display}
                    <span class="badge good" style="display: inline-block; margin-top: 6px; font-size: 10px; padding: 2px 8px; border-radius: 99px; background: rgba(16,185,129,0.1); color: var(--green); border: 1px solid rgba(16,185,129,0.2);">{escape(tx.get("status", "completed"))}</span>
                  </div>
                </div>
                """
            )
            
    txs_html = "".join(tx_rows)
    
    error_html = f'<div class="notice bad" style="margin-bottom: 20px; border-radius: 8px;">{escape(error)}</div>' if error else ""
    message_html = f'<div class="notice" style="margin-bottom: 20px; border-radius: 8px;">{escape(message)}</div>' if message else ""
    
    # Left Sidebar (aside)
    # 1. Wallet Card
    wallet_card = f"""
    <div class="panel" style="border: 1px solid rgba(99, 102, 241, 0.2); background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px;">
      <div class="eyebrow" style="color: var(--primary);">Secure Wallet</div>
      <h2 style="margin: 6px 0 2px; color: #fff; font-size: 28px; font-family: 'Outfit'; font-weight: 800;">{profile_balance} USDC</h2>
      <p style="margin: 0 0 16px; font-size: 12px; color: var(--muted);">ARC-TESTNET</p>
      
      <label style="font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 6px;">EVM Address</label>
      <div style="display: flex; gap: 8px; align-items: center; background: var(--surface-2); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--line); cursor: pointer;" onclick="navigator.clipboard.writeText('{profile_wallet}'); alert('Copied address!')">
        <code style="color: var(--green); font-size: 12px; font-weight: 700; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{profile_wallet}</code>
        <span style="font-size: 12px;">📋</span>
      </div>
    </div>
    """
    
    wallet_card = f"""
    <div class="panel" style="border: 1px solid rgba(99, 102, 241, 0.2); background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px;">
      <div class="eyebrow" style="color: var(--primary);">Secure Wallet</div>
      <h2 style="margin: 6px 0 2px; color: #fff; font-size: 28px; font-family: 'Outfit'; font-weight: 800;">{profile_balance} USDC</h2>
      <p style="margin: 0 0 16px; font-size: 12px; color: var(--muted);">ARC-TESTNET</p>

      <label style="font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 6px;">EVM Address</label>
      <div style="display: grid; gap: 10px; background: var(--surface-2); padding: 12px; border-radius: 8px; border: 1px solid var(--line);">
        <code id="profile-wallet-address" style="color: var(--green); font-size: 12px; font-weight: 700; line-height: 1.5; word-break: break-all; white-space: normal;">{profile_wallet}</code>
        <button type="button" id="copy-wallet-address" class="secondary" style="width: 100%; min-height: 40px; border-radius: 8px;" onclick="copyProfileWalletAddress({profile_wallet_js})">Copy address</button>
        <span id="copy-wallet-status" style="min-height: 16px; color: var(--green); font-size: 12px; font-weight: 700;"></span>
      </div>
    </div>
    """

    # 2. Change Username form (only if owner and not changed yet)
    change_username_card = ""
    if viewer_is_owner:
        if not profile.get("username_changed"):
            change_username_card = f"""
            <div class="panel" style="margin-bottom: 24px; border-radius: 12px; padding: 24px; background: var(--surface); border: 1px solid var(--line);">
              <h2>✏️ Change Username</h2>
              <p class="panel-copy">You can update your handle exactly once. This will also update your session credentials and profile URL.</p>
              <form method="post" action="/ui/profile/update-username">
                <label for="new_username">New Handle</label>
                <input id="new_username" name="new_username" required placeholder="e.g. newhandle" />
                <button style="margin-top: 14px; width: 100%;">Save Changes</button>
              </form>
            </div>
            """
        else:
            change_username_card = f"""
            <div class="panel" style="margin-bottom: 24px; border-radius: 12px; padding: 20px; background: var(--surface); border: 1px solid var(--line); text-align: center;">
              <span style="font-size: 13px; color: var(--muted);">🔒 Username locked (limit reached)</span>
            </div>
            """
            
    # 3. Send USDC Funds form (only if owner)
    send_funds_card = ""
    if viewer_is_owner:
        send_funds_card = f"""
        <div class="panel" style="border: 1px solid rgba(16, 185, 129, 0.25); background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px;">
          <h2>Send USDC Funds</h2>
          <p class="panel-copy">Transfer USDC instantly from your agent wallet to any recipient handle or raw address.</p>
          <form method="post" action="/ui/wallet/send">
            <input type="hidden" name="redirect_to" value="profile" />
            <label for="recipient">Recipient Handle or EVM Address</label>
            <input id="recipient" name="recipient" required placeholder="e.g. @jennycruzy or 0x..." />
            
            <label for="amount" style="margin-top: 12px;">Amount in USDC</label>
            <input id="amount" name="amount" type="number" min="0.01" step="0.01" value="10" required placeholder="e.g. 10" />
            
            <button style="margin-top: 18px; width: 100%;">Send USDC Transfer</button>
          </form>
        </div>
        """
        
    body = f"""
    <script>
      async function copyProfileWalletAddress(address) {{
        const status = document.getElementById('copy-wallet-status');
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(address);
          }} else {{
            const textArea = document.createElement('textarea');
            textArea.value = address;
            textArea.setAttribute('readonly', '');
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
          }}
          if (status) {{
            status.textContent = 'Address copied';
            setTimeout(() => status.textContent = '', 2200);
          }}
        }} catch (error) {{
          if (status) status.textContent = 'Select the address text and copy manually';
        }}
      }}
    </script>
    <main class="shell">
      <div style="margin-bottom: 32px;">
        <div class="eyebrow" style="color: var(--primary);">{ 'Your Personal Account' if viewer_is_owner else 'Public Agent Profile' }</div>
        <h1 style="margin: 6px 0 0; font-size: 46px; color: #fff; font-family: 'Outfit'; font-weight: 900; letter-spacing: -0.02em;">@{profile_username}</h1>
      </div>
      
      {error_html}
      {message_html}
      
      <section class="workspace" style="display: grid; grid-template-columns: 360px 1fr; gap: 32px; align-items: start;">
        <aside style="position: sticky; top: 100px;">
          {wallet_card}
          {send_funds_card}
          {change_username_card}
        </aside>
        
        <section style="background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 32px; box-shadow: var(--shadow);">
          <div class="section-head" style="margin-bottom: 24px; border-bottom: 1px solid var(--line); padding-bottom: 16px;">
            <div>
              <h2 style="font-size: 24px; color: #fff; margin: 0;">Verified Transaction Ledger</h2>
              <p style="margin: 6px 0 0; font-size: 14px; color: var(--muted);">Direct USDC transfers, case deposits, and escrow releases verified by NOTARY.</p>
            </div>
          </div>
          <div>
            {txs_html}
          </div>
        </section>
      </section>
    </main>
    """
    return _page(f"@{profile_username}'s Profile · NOTARY", body, viewer)
