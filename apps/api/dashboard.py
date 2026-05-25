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
      --bg: linear-gradient(135deg, #FDFFF5 0%, #D4EED7 40%, #152A1A 80%, #000000 100%);
      --ink: #FFFFFF;
      --muted: #A3B3A9;
      --surface: rgba(15, 23, 20, 0.75);
      --surface-2: rgba(30, 41, 35, 0.8);
      --line: rgba(255, 255, 255, 0.1);
      --line-hover: rgba(255, 255, 255, 0.2);
      --green: #10b981;
      --green-glow: rgba(16, 185, 129, 0.2);
      --green-2: #059669;
      --amber: oklch(82% .14 85);
      --amber-glow: oklch(82% .14 85 / .16);
      --red: #ef4444;
      --red-glow: rgba(239, 68, 68, 0.15);
      --blue: #3b82f6;
      --black: #020403;
      --mint: rgba(16, 185, 129, 0.1);
      --primary: #F6C453;
      --primary-hover: #F8D481;
      --primary-foreground: #101814;
      --primary-glow: rgba(246, 196, 83, 0.2);
      --glass: rgba(15, 23, 20, 0.7);
      --shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    }
    :root[data-theme="light"] {
      color-scheme: light;
      --bg: #f8f3e6;
      --ink: #121417;
      --muted: #756b58;
      --surface: rgba(255, 252, 244, 0.84);
      --surface-2: #efe5d1;
      --line: rgba(44, 34, 18, 0.16);
      --line-hover: rgba(44, 34, 18, 0.28);
      --primary: #d99b1c;
      --primary-hover: #f3bd35;
      --primary-foreground: #15100a;
      --primary-glow: rgba(217, 155, 28, 0.3);
      --shadow: 0 22px 50px rgba(82, 58, 18, 0.16);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--bg);
      background-attachment: fixed;
      color: var(--ink);
      font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
      font-size: 16px;
      line-height: 1.55;
      transition: background 0.25s ease, color 0.25s ease;
    }
    a { color: inherit; text-decoration: none; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 16px 36px;
      border-bottom: 1px solid var(--line);
      background: rgba(10, 15, 13, 0.85);
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
      text-shadow: 0 0 10px rgba(246, 196, 83, 0.18);
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
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: #13100a;
      border-color: var(--primary);
      font-weight: 700;
      box-shadow: 0 12px 30px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.38);
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
    
    /* Readability logic: Elements on milk/green background are dark. Panels/Cards stay light. */
    .shell h1, .shell h2, .workspace-intro h2, .section-head h2, .workspace-title h1, .dash-main h1, .dash-main > div > h1, .dash-main h2, main > h1, main > h2, .section-head > div > h2 { color: #000000 !important; }
    .shell p, .workspace-intro p, .section-head p, .workspace-title p, .dash-main > p, .dash-main > div > p, main > p, .section-head > div > p { color: #0A1C12 !important; font-weight: 500; }
    
    /* Strong contrast for text inside explicit panels/cards */
    .panel, .card, .record, .hero-copy, .agent-card, .step, .record-head h3, .metric-card, .feature-card, .status-card { color: #FFFFFF !important; }
    .panel p, .card p, .record p, .hero-copy p, .agent-card p, .step span, .metric-card span, .metric-card p, .feature-card p, .status-card p { color: #E5E7EB !important; }
    .panel h2, .card h2, .card-title, .record h3, .hero h1, .agent-card h3, .step strong, .metric-card strong, .metric-card div, .feature-card h3, .status-card h3 { color: #FFFFFF !important; }
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
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: var(--primary-foreground);
      padding: 0 24px;
      font-weight: 700;
      font-size: 15px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      box-shadow: 0 12px 30px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.38);
      width: 100%;
    }
    .button:hover {
      background: var(--primary-hover);
      border-color: var(--primary-hover);
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(246, 196, 83, 0.28);
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
      border-color: rgba(246, 196, 83, 0.32);
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
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: var(--primary-foreground);
      padding: 0 20px;
      font-weight: 700;
      font-size: 15px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      box-shadow: 0 12px 30px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.38);
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
      border-color: rgba(246, 196, 83, 0.35);
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
    .fact strong { font-size: 15px; color: #fff; font-family: 'Outfit', sans-serif; }
    .notice {
      border: 1px solid rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.05);
      color: #a7f3d0;
      padding: 14px 20px;
      border-radius: 8px;
      font-size: 15px;
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
    .case-step {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.035);
      padding: 14px;
      min-width: 0;
    }
    .case-step strong {
      display: block;
      font-family: 'Outfit', sans-serif;
      font-size: 15px;
      color: #fff;
      margin-bottom: 6px;
    }
    .case-step p {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin: 0 0 12px;
    }
    .case-step.active {
      border-color: rgba(246, 196, 83, 0.34);
      background: rgba(246, 196, 83, 0.07);
    }
    .case-step.complete {
      border-color: rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.06);
    }
    .case-step.locked {
      border-style: dashed;
      opacity: 0.9;
    }
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
      font-size: 15px;
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
    .feature-grid, .profile-metrics, .commerce-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    .dashboard-shell {
      display: grid;
      grid-template-columns: 256px 1fr;
      gap: 0;
      align-items: start;
      max-width: none;
      padding: 0;
      min-height: 100vh;
    }
    .side-rail {
      position: sticky;
      top: 0;
      height: 100vh;
      border-right: 1px solid var(--line);
      background: oklch(13% .02 260);
      padding: 0;
      box-shadow: none;
      display: flex;
      flex-direction: column;
    }
    :root[data-theme="light"] .side-rail { background: #fbf7ec; }
    .side-brand {
      height: 64px;
      display: flex;
      align-items: center;
      padding: 0 24px;
      border-bottom: 1px solid oklch(28% .02 260 / .6);
    }
    .side-brand strong {
      display: block;
      color: #fff;
      font-size: 20px;
      font-family: 'Outfit', sans-serif;
      font-weight: 900;
      letter-spacing: -0.01em;
    }
    .side-brand span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 1px;
    }
    .side-nav {
      display: grid;
      gap: 4px;
      padding: 16px;
    }
    .side-rail a {
      display: flex;
      align-items: center;
      gap: 10px;
      border-radius: 10px;
      padding: 11px 12px;
      color: var(--muted);
      font-weight: 500;
      font-size: 16px;
    }
    .side-rail a:hover, .side-rail a.active {
      color: #fff;
      background: var(--surface-2);
    }
    .side-footer {
      margin-top: auto;
      border-top: 1px solid oklch(28% .02 260 / .6);
      padding: 16px;
      color: var(--muted);
      font-family: 'JetBrains Mono', ui-monospace, monospace;
      font-size: 12px;
    }
    .dash-main { min-width: 0; padding: 40px; animation: pageIn 420ms ease both; }
    @keyframes pageIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .dash-topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 28px;
    }
    .search-pill {
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--surface);
      color: var(--muted);
      padding: 0 16px;
      display: flex;
      align-items: center;
      min-width: min(100%, 460px);
    }
    .avatar-pill {
      width: 38px;
      height: 38px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: var(--primary-foreground);
      font-size: 13px;
      font-weight: 800;
    }
    .theme-toggle {
      width: 42px;
      min-width: 42px;
      height: 38px;
      min-height: 38px;
      border-radius: 10px;
      padding: 0;
      background: var(--surface);
      border-color: var(--line);
      color: var(--ink);
      box-shadow: none;
    }
    .workspace-title h1 {
      font-family: 'Instrument Serif', Georgia, serif;
      color: var(--ink);
      font-size: clamp(48px, 6vw, 72px);
      font-weight: 500;
      letter-spacing: 0;
      margin: 0;
    }
    .workspace-title p {
      color: var(--muted);
      margin: 8px 0 0;
      font-size: 18px;
    }
    .metric-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      padding: 22px;
      box-shadow: 0 12px 28px rgba(0,0,0,0.22);
      animation: cardIn 480ms ease both;
    }
    @keyframes cardIn {
      from { opacity: 0; transform: translateY(8px) scale(0.99); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .metric-trend {
      display: inline-flex;
      color: var(--primary);
      background: oklch(82% .14 85 / .1);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      margin-bottom: 14px;
    }
    .metric-card strong {
      display: block;
      color: #fff;
      font-size: 34px;
      font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
      font-weight: 700;
      margin: 8px 0 2px;
    }
    .metric-card span {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 11px;
      font-weight: 800;
    }
    .section-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      box-shadow: var(--shadow);
      padding: 32px;
      margin-top: 28px;
      animation: pageIn 420ms ease both;
    }
    .section-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }
    .feature-card, .status-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface);
      padding: 24px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.22);
    }
    .feature-card h3, .status-card h3 {
      margin: 6px 0 8px;
      color: #fff;
      font-size: 20px;
    }
    .feature-card p, .status-card p {
      color: var(--muted);
      margin: 0;
      font-size: 15px;
      line-height: 1.5;
    }
    :root[data-theme="light"] .section-head h2,
    :root[data-theme="light"] .feature-card h3,
    :root[data-theme="light"] .status-card h3,
    :root[data-theme="light"] .metric-card strong,
    :root[data-theme="light"] .agent-card h3,
    :root[data-theme="light"] .record h3,
    :root[data-theme="light"] .brand strong,
    :root[data-theme="light"] .side-brand strong {
      color: var(--ink) !important;
    }
    :root[data-theme="light"] input,
    :root[data-theme="light"] textarea,
    :root[data-theme="light"] select {
      background: rgba(255,255,255,0.58);
      color: var(--ink);
    }
    .status-card code, .tx-row code {
      color: var(--green);
      overflow-wrap: anywhere;
      font-size: 12px;
    }
    .tx-row {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 16px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--surface-2);
      padding: 16px;
      margin-bottom: 12px;
    }
    .tx-icon {
      width: 34px;
      height: 34px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.04);
      font-weight: 800;
    }
    @media (max-width: 980px) {
      header { align-items: flex-start; flex-direction: column; padding: 16px 20px; }
      .shell { padding: 24px 16px; }
      .hero, .workspace, .ops-grid, .feature-grid, .profile-metrics, .commerce-grid, .grid, .grid.two, .facts, .dashboard-shell, .section-grid, .case-flow {
        grid-template-columns: 1fr !important;
      }
      aside, .side-rail { position: static !important; }
      .side-rail { display: none; }
      .dash-topbar { align-items: flex-start; flex-direction: column; }
      .hero h1 { font-size: 34px; }
      .section-head { align-items: flex-start; flex-direction: column; }
      .tx-row { grid-template-columns: 1fr; }
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
        <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <script>document.documentElement.dataset.theme = localStorage.getItem("notary-theme") || "dark";</script>
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


def _bare_page(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{escape(title)}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <script>document.documentElement.dataset.theme = localStorage.getItem("notary-theme") || "dark";</script>
        <style>{_css()}</style>
      </head>
      <body>
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
        is_awaiting_funding = item.get("status") == "awaiting_funding"
        funding_link = (
            f'<a class="button secondary" href="{escape(str(funding_url))}">Fund escrow with Arc tx</a>'
            if funding_url and is_awaiting_funding
            else ""
        )
        funding_state = (
            """
            <div class="case-step active">
              <strong>1. Payer funds escrow</strong>
              <p>Open the funding page, send the exact USDC amount on Arc to the reserve wallet, then paste the transaction hash for verification.</p>
            </div>
            """
            if is_awaiting_funding
            else """
            <div class="case-step complete">
              <strong>1. Escrow funded</strong>
              <p>The USDC lock has been verified. The payee can now submit proof for the witness swarm.</p>
            </div>
            """
        )
        evidence_action = (
            f"""
            <div class="case-step active">
              <strong>2. Payee submits evidence</strong>
              <p>The evidence portal is open for the payee or their agent. Submit links, files, commits, or signed completion proof.</p>
              <a class="button secondary" href="{escape(upload)}">Submit evidence</a>
            </div>
            """
            if upload and not is_awaiting_funding
            else """
            <div class="case-step locked">
              <strong>2. Payee submits evidence</strong>
              <p>Locked until funding is verified. Once funded, this card will show the payee's evidence portal.</p>
              <span class="button secondary" aria-disabled="true" style="opacity:.55; pointer-events:none;">Evidence locked</span>
            </div>
            """
        )
        funding_actions = f'<div class="actions" style="margin-top:16px; display: flex; gap: 8px; flex-wrap: wrap;">{funding_link}</div>' if funding_link else ""
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
              <div class="case-flow" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 18px;">
                {funding_state}
                {evidence_action}
              </div>
              {funding_actions}
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


def _commerce_panels(state: dict[str, Any], profile_username: str) -> str:
    predictions = list(reversed(state.get("predictions", [])))
    shares = list(reversed(state.get("micro_shares", [])))
    rulings = list(reversed(state.get("rulings", [])))
    peeks = list(reversed(state.get("reasoning_market", [])))
    x402_payments = list(reversed(state.get("x402_payments", [])))
    yield_payouts = list(reversed(state.get("yield_payouts", [])))
    yield_status = state.get("yield_status", {}) if isinstance(state.get("yield_status"), dict) else {}
    notaries = list(reversed(state.get("notaries", [])))
    latest_notary = notaries[0] if notaries else {}
    default_buyer = f"@{profile_username}"
    latest_prediction_id = str((predictions[0] or {}).get("predictionId") or "") if predictions else ""
    latest_ruling_id = str((rulings[0] or {}).get("ruling_id") or (rulings[0] or {}).get("rulingId") or "") if rulings else ""
    latest_notary_id = str(latest_notary.get("notary_id") or latest_notary.get("notaryId") or "")
    prediction_options = "".join(
        f'<option value="{escape(str(item.get("predictionId")))}">{_text(item.get("question"))}</option>'
        for item in predictions[:8]
    )
    ruling_options = "".join(
        f'<option value="{escape(str(item.get("ruling_id") or item.get("rulingId")))}">{_text(item.get("obligationSummary") or item.get("verdict") or item.get("ruling_id"))}</option>'
        for item in rulings[:8]
    )
    latest_share = shares[0] if shares else {}
    latest_peek = peeks[0] if peeks else {}
    latest_x402 = x402_payments[0] if x402_payments else {}
    latest_yield = yield_payouts[0] if yield_payouts else {}
    reserve = yield_status.get("sponsoredReserve", {}) if isinstance(yield_status.get("sponsoredReserve"), dict) else {}
    usyc = yield_status.get("usyc", {}) if isinstance(yield_status.get("usyc"), dict) else {}
    return f"""
    <section id="predictions" class="section-card app-view">
      <div class="section-head">
        <div>
          <div class="eyebrow">Predictions &amp; Micro-Shares</div>
          <h2>Create a market signal, then let users buy a share</h2>
          <p>Prediction commitments and micro-share purchases are separate actions so users understand the market flow.</p>
        </div>
      </div>
      <div class="section-grid">
        <article class="status-card">
          <span class="badge good">Predictions</span>
          <h3>Create a market signal</h3>
          <p>Publish a probability commitment that users can buy micro-shares in.</p>
          <form method="post" action="/ui/markets/predictions" style="margin-top: 16px;">
            <input name="notary_id" type="hidden" value="{escape(latest_notary_id)}" />
            <label for="prediction_question">Question</label>
            <textarea id="prediction_question" name="question" required placeholder="Will this escrow be released within 24 hours?"></textarea>
            <div class="split">
              <div><label for="probability_bps">Probability bps</label><input id="probability_bps" name="probability_bps" type="number" min="0" max="10000" value="7200" required /></div>
              <div><label for="horizon">Horizon</label><input id="horizon" name="horizon" value="24h" required /></div>
            </div>
            <label for="prediction_rationale">Rationale</label>
            <textarea id="prediction_rationale" name="rationale" required placeholder="Evidence quality, prior behavior, and confidence gates..."></textarea>
            <button style="width: 100%; margin-top: 12px;">Commit prediction on Arc</button>
          </form>
        </article>
        <article class="status-card">
          <span class="badge good">Micro-shares</span>
          <h3>Buy into a prediction</h3>
          <p>Pay verified USDC to buy exposure to a NOTARY prediction output.</p>
          <form method="post" action="/ui/commerce/micro-shares" style="margin-top: 16px;">
            <label for="prediction_id">Prediction ID</label>
            <input id="prediction_id" name="prediction_id" list="prediction_ids" value="{escape(latest_prediction_id)}" required placeholder="Create or paste a prediction ID" />
            <datalist id="prediction_ids">{prediction_options}</datalist>
            <label for="share_buyer">Buyer identity</label>
            <input id="share_buyer" name="buyer_identity" value="{escape(default_buyer)}" required />
            <div class="split">
              <div><label for="share_amount">USDC amount</label><input id="share_amount" name="amount_usdc" type="number" min="0.000001" step="0.000001" value="0.01" required /></div>
              <div><label for="share_tx">Arc tx hash</label><input id="share_tx" name="tx_hash" placeholder="optional if wallet can auto-pay" /></div>
            </div>
            <button style="width: 100%; margin-top: 12px;">Buy micro-share</button>
          </form>
          <p class="status-line" style="margin-top: 10px;">Latest share: {escape(_short(latest_share.get("shareId") or "none yet", 34))}</p>
        </article>
      </div>
    </section>

    <section id="pay-to-peek" class="section-card app-view">
      <div class="section-head">
        <div>
          <div class="eyebrow">Reasoning Marketplace</div>
          <h2>Pay-to-Peek reasoning traces</h2>
          <p>Public verdicts show what NOTARY decided. Pay-to-Peek unlocks why it decided.</p>
        </div>
      </div>
      <div class="section-grid">
        <article class="status-card">
          <span class="badge good">Pay-to-Peek</span>
          <h3>Unlock a trace</h3>
          <form method="post" action="/ui/commerce/pay-to-peek" style="margin-top: 16px;">
            <label for="ruling_id">Ruling ID</label>
            <input id="ruling_id" name="ruling_id" list="ruling_ids" value="{escape(latest_ruling_id)}" required placeholder="Paste a ruling ID" />
            <datalist id="ruling_ids">{ruling_options}</datalist>
            <label for="peek_buyer">Buyer identity</label>
            <input id="peek_buyer" name="buyer_identity" value="{escape(default_buyer)}" required />
            <div class="split">
              <div><label for="peek_amount">USDC amount</label><input id="peek_amount" name="amount_usdc" type="number" min="0.000001" step="0.000001" value="0.005" required /></div>
              <div><label for="peek_tx">Arc tx hash</label><input id="peek_tx" name="tx_hash" placeholder="optional if wallet can auto-pay" /></div>
            </div>
            <button style="width: 100%; margin-top: 12px;">Pay to peek</button>
          </form>
        </article>
        <article class="status-card">
          <span class="badge good">Access record</span>
          <h3>Latest reasoning access</h3>
          <p>Every unlock records buyer, trace hash, amount, and payment proof.</p>
          <div class="facts" style="grid-template-columns: 1fr; margin-top: 14px;">
            <div class="fact"><span>Access ID</span><code>{escape(_short(latest_peek.get("accessId") or "none yet", 34))}</code></div>
            <div class="fact"><span>Trace hash</span><code>{escape(_short(latest_peek.get("reasoningTraceHash") or "awaiting unlock", 34))}</code></div>
            <div class="fact"><span>Payment</span><strong>{escape(str(latest_peek.get("amountUSDC") or 0))} USDC</strong></div>
          </div>
        </article>
      </div>
    </section>

    <section id="data" class="section-card app-view">
      <div class="section-head"><div><div class="eyebrow">Paid Data &amp; Treasury</div><h2>x402 intelligence and yield controls</h2><p>External data purchases and idle capital rewards are displayed as their own operating rails.</p></div></div>
      <div class="section-grid">
        <article class="status-card">
          <span class="badge warn">x402</span><h3>Paid data request</h3><p>Use Circle's paid-service flow for external intelligence sources.</p>
          <form method="post" action="/ui/commerce/x402/data" style="margin-top: 16px;">
            <label for="x402_description">Request description</label><input id="x402_description" name="description" value="Market intelligence request" required />
            <label for="service_url">x402 service URL</label><input id="service_url" name="service_url" placeholder="https://seller.example/x402/feed" required />
            <div class="split"><div><label for="x402_max">Max USDC</label><input id="x402_max" name="max_usdc" type="number" min="0.000001" step="0.000001" value="0.01" required /></div><div><label for="x402_method">Method</label><select id="x402_method" name="method"><option>GET</option><option>POST</option></select></div></div>
            <label for="request_body">Body / headers JSON</label><textarea id="request_body" name="request_body" placeholder='{{"topic":"arbitrage"}}'></textarea>
            <button style="width: 100%; margin-top: 12px;">Pay x402 service</button>
          </form>
          <p class="status-line" style="margin-top: 10px;">Latest request: {escape(_short(latest_x402.get("paymentId") or "none yet", 34))}</p>
        </article>
        <article class="status-card">
          <span class="badge good">Yield</span><h3>Idle balance rewards</h3><p>Sponsored reserve stays live while USYC allocation waits for allowlist/provider execution.</p>
          <div class="facts" style="grid-template-columns: 1fr; margin: 14px 0;"><div class="fact"><span>Reserve</span><code>{escape(_short(reserve.get("wallet"), 34))}</code></div><div class="fact"><span>Target APY</span><strong>{escape(str((reserve.get("targetApyBps") or 0) / 100))}%</strong></div><div class="fact"><span>USYC</span><strong>{escape(str(usyc.get("status", "awaiting_allowlist")))}</strong></div></div>
          <form method="post" action="/ui/treasury/yield/process"><label for="yield_target">Target username / notary ID</label><input id="yield_target" name="target_identity" value="{escape(default_buyer)}" /><label style="display: flex; gap: 8px; align-items: center; margin-top: 10px;"><input name="force" type="checkbox" value="true" /> Force payout check</label><button style="width: 100%; margin-top: 12px;">Process yield</button></form>
          <p class="status-line" style="margin-top: 10px;">Latest payout: {escape(_short(latest_yield.get("arcTxHash") or "none yet", 34))}</p>
        </article>
      </div>
    </section>

    <section id="identity" class="section-card app-view">
      <div class="section-head"><div><div class="eyebrow">Agent Identity &amp; Replication</div><h2>On-chain agent identity and policy DNA</h2><p>Register NOTARY as an ERC-8004-style service agent, then spawn child agents with mutated rules.</p></div></div>
      <div class="section-grid">
        <article class="status-card"><span class="badge good">Identity</span><h3>Register agent identity</h3><form method="post" action="/ui/agents/identity/erc8004" style="margin-top: 16px;"><label for="agent_notary_id">Notary ID</label><input id="agent_notary_id" name="notary_id" value="{escape(latest_notary_id)}" required /><label for="service_endpoint">Service endpoint</label><input id="service_endpoint" name="service_endpoint" value="http://38.49.209.149/agents" required /><button style="width: 100%; margin-top: 12px;">Register agent identity</button></form></article>
        <article class="status-card"><span class="badge good">Replication</span><h3>Spawn child Notary</h3><form method="post" action="/ui/agents/replicate" style="margin-top: 16px;"><input name="parent_notary_id" type="hidden" value="{escape(latest_notary_id)}" /><label for="mutation_prompt">Replication policy DNA</label><textarea id="mutation_prompt" name="mutation_prompt" placeholder="Specialize in invoice disputes and release only after payer approval." required></textarea><button style="width: 100%; margin-top: 12px;">Spawn child Notary</button></form></article>
      </div>
    </section>
    """

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


def render_landing(state: dict[str, Any], user: dict[str, Any] | None = None) -> str:
    rulings = state.get("rulings", [])
    cases = state.get("cases", [])
    predictions = state.get("predictions", [])
    micro_shares = state.get("micro_shares", [])
    reasoning_market = state.get("reasoning_market", [])
    yield_payouts = state.get("yield_payouts", [])
    yield_status = state.get("yield_status", {})
    validations = state.get("validations", [])
    confidence_values = [
        float(item.get("confidence"))
        for item in rulings
        if isinstance(item.get("confidence"), (int, float))
    ]
    average_confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else "n/a"
    latest_yield_tx = (yield_payouts[-1] or {}).get("arcTxHash") if yield_payouts else "awaiting first payout"
    usyc = yield_status.get("usyc", {}) if isinstance(yield_status, dict) else {}
    body = f"""
    <main class="shell">
      <section class="hero">
        <div class="hero-copy">
          <div>
            <div class="eyebrow">Witness-to-Pay on Arc</div>
            <h1>Machine witnesses that turn verified facts into programmable USDC movement.</h1>
            <p>NOTARY combines autonomous AI review, Circle agent wallets, Arc attestations, paid intelligence, prediction micro-shares, and sponsored treasury rewards into one live payment terminal.</p>
            <div class="actions">
              <a class="button" href="/app" style="width: auto;">Open workspace</a>
              <a class="button secondary" href="/ledger">View public ledger</a>
              <a class="button secondary" href="/coverage">Inspect coverage</a>
            </div>
          </div>
          <div class="metrics">
            <div class="metric"><span>Cases</span><strong>{len(cases)}</strong></div>
            <div class="metric"><span>Rulings</span><strong>{len(rulings)}</strong></div>
            <div class="metric"><span>Avg confidence</span><strong>{escape(str(average_confidence))}</strong></div>
            <div class="metric"><span>Arc validations</span><strong>{len(validations)}</strong></div>
          </div>
        </div>
        <div class="flow" style="border: 1px solid var(--line); border-radius: 16px; background: var(--surface); padding: 30px; box-shadow: var(--shadow);">
          <div class="eyebrow">Live rails</div>
          <h2 style="font-size: 24px; color: #fff; margin-bottom: 18px;">What is working now</h2>
          <div class="status-card" style="margin-bottom: 12px;"><span class="badge good">Circle wallet</span><h3>Agent wallets on signup</h3><p>Every profile maps to a Circle developer-controlled wallet for Arc testnet USDC.</p></div>
          <div class="status-card" style="margin-bottom: 12px;"><span class="badge good">Arc verified</span><h3>Payments resolve to tx hashes</h3><p>Micro-shares, Pay-to-Peek, and yield payouts are verified against Arc USDC logs.</p></div>
          <div class="status-card"><span class="badge warn">USYC ready</span><h3>Institutional yield path</h3><p>Teller configured: <code>{escape(_short(usyc.get("providerAddress"), 42))}</code></p></div>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <div><div class="eyebrow">Product map</div><h2>One app, full economic loop</h2><p>Everything below is part of the live NOTARY surface, not pitch-only copy.</p></div>
        </div>
        <div class="feature-grid">
          <div class="feature-card"><span class="badge good">Witness</span><h3>Escrow cases</h3><p>Natural-language obligations become funded cases, evidence links, verdicts, and release/hold/refund actions.</p></div>
          <div class="feature-card"><span class="badge good">Swarm</span><h3>6-agent review</h3><p>Scanner, Sentinel, Risk, Strategy, Validator, and Reflector coordinate evidence review.</p></div>
          <div class="feature-card"><span class="badge good">Arc</span><h3>Onchain memory</h3><p>Identity, validations, attestation hashes, karma, replication, and payment proofs are committed on Arc.</p></div>
          <div class="feature-card"><span class="badge good">Commerce</span><h3>Prediction micro-shares</h3><p>{len(predictions)} prediction(s), {len(micro_shares)} purchase(s), with USDC payment verification.</p></div>
          <div class="feature-card"><span class="badge good">Marketplace</span><h3>Pay-to-Peek traces</h3><p>{len(reasoning_market)} reasoning access purchase(s) recorded with trace hashes and payment proofs.</p></div>
          <div class="feature-card"><span class="badge good">Yield</span><h3>Sponsored reserve</h3><p>{len(yield_payouts)} payout(s). Latest: <code>{escape(_short(latest_yield_tx, 38))}</code></p></div>
          <div class="feature-card"><span class="badge warn">x402</span><h3>Paid data requests</h3><p>GET/POST x402 calls are wired. Arc-compatible sellers or Gateway fallback are the remaining provider choice.</p></div>
          <div class="feature-card"><span class="badge warn">USYC</span><h3>Future institutional yield</h3><p>Current mode: {escape(str(usyc.get("status", "awaiting_allowlist")))}. Sponsored reserve stays live meanwhile.</p></div>
          <div class="feature-card"><span class="badge good">Multimodal</span><h3>Speechmatics evidence</h3><p>Audio/video uploads and transcripts feed the witness pipeline for real-world proof review.</p></div>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <div><div class="eyebrow">Recent activity</div><h2>Public witness ledger</h2><p>Summaries and commitments are public. Raw evidence remains private or protected by default.</p></div>
          <a class="button secondary" href="/ledger">See all</a>
        </div>
        <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));">{_record_cards(rulings, limit=3, compact=True)}</div>
      </section>
    </main>
    """
    return _page("NOTARY", body, user)


def render_feature_coverage(coverage: dict[str, Any], user: dict[str, Any] | None = None) -> str:
    def status_badge(value: Any) -> str:
        if value is True:
            return _badge("Live", "good")
        if value is False or value in {"disabled", "not_configured", None, ""}:
            return _badge("Needs setup", "hold")
        if value in {"configured", "enabled", "implemented", "VALID"}:
            return _badge("Live", "good")
        return _badge(str(value), "neutral")

    def cards(items: list[tuple[str, str, Any]]) -> str:
        html: list[str] = []
        for title, copy, value in items:
            html.append(
                f"""
                <article class="status-card">
                  <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                    <h3>{escape(title)}</h3>
                    {status_badge(value)}
                  </div>
                  <p>{escape(copy)}</p>
                </article>
                """
            )
        return "".join(html)

    arc = coverage.get("arc", {})
    circle = coverage.get("circle", {})
    notary = coverage.get("notary", {})
    registries = arc.get("registries", {}) if isinstance(arc.get("registries"), dict) else {}
    eip712 = arc.get("eip712", {}) if isinstance(arc.get("eip712"), dict) else {}
    agent_wallets = circle.get("agentWallets", {}) if isinstance(circle.get("agentWallets"), dict) else {}
    sponsored_yield = circle.get("sponsoredYield", {}) if isinstance(circle.get("sponsoredYield"), dict) else {}
    usyc = sponsored_yield.get("usycFallback", {}) if isinstance(sponsored_yield.get("usycFallback"), dict) else {}
    body = f"""
    <main class="shell">
      <section class="workspace-intro">
        <div class="eyebrow">Coverage</div>
        <h1 style="font-family:'Instrument Serif', Georgia, serif; font-size:48px; font-weight:500; margin:0 0 8px;">What NOTARY covers now</h1>
        <p class="panel-copy">A readable status page for the Arc, Circle, and witness features. Raw JSON is still available at <a href="/api/coverage" style="color:var(--primary);">/api/coverage</a>.</p>
        <div class="actions">
          <a class="button secondary" href="/">Back home</a>
          <a class="button" href="/app" style="width:auto;">Open workspace</a>
        </div>
      </section>

      <section class="section-card">
        <div class="section-head"><div><h2>Arc economic OS</h2><p>On-chain identity, attestations, finality, and EIP-712 signing.</p></div></div>
        <div class="feature-grid">
          {cards([
            ("Sub-second finality", "Arc RPC is configured for live settlement and verification.", arc.get("finality", {}).get("rpcUrlConfigured")),
            ("USDC fee path", "Paymaster configuration keeps fees denominated in USDC.", arc.get("usdcFeesPaymaster", {}).get("status")),
            ("Attestation registry", "Verdict and trace commitments are routed to the Arc attestation registry.", registries.get("attestation")),
            ("ERC-8004-style identity", "Agent identity receipts are recorded on Arc when users register the NOTARY identity.", registries.get("agentIdentity")),
            ("Karma checkpoints", "Reflector performance updates can be written to the karma registry.", registries.get("karma")),
            ("EIP-712 domain", f"Domain {escape(str(eip712.get('domain', 'NOTARY')))} v{escape(str(eip712.get('version', '1')))} is configured for signatures.", eip712.get("signerConfigured")),
          ])}
        </div>
      </section>

      <section class="section-card">
        <div class="section-head"><div><h2>Circle agentic commerce</h2><p>Wallets, Gateway, x402, Paymaster, and treasury paths.</p></div></div>
        <div class="feature-grid">
          {cards([
            ("Agent wallets", f"Circle token status: {agent_wallets.get('data', {}).get('testnet', {}).get('tokenStatus', agent_wallets.get('status', 'configured'))}.", bool(agent_wallets)),
            ("Gateway", "Unified balance and bridge deposit flow is exposed from the workspace.", circle.get("gateway", {}).get("enabled")),
            ("Bridge Kit and App Kit", "Users can deposit on supported chains and route USDC toward Arc.", bool(circle.get("bridgeAppKit", {}).get("route"))),
            ("Nanopayments / x402", "Paid data requests and Pay-to-Peek are wired through the x402 commerce path.", bool(circle.get("x402", {}).get("route"))),
            ("Sponsored yield reserve", "Idle USDC can earn sponsored reserve yield while USYC remains optional.", sponsored_yield.get("reserveConfigured")),
            ("USYC optional path", f"Provider address: {escape(_short(usyc.get('providerAddress'), 40))}.", bool(usyc.get("providerAddress"))),
          ])}
        </div>
      </section>

      <section class="section-card">
        <div class="section-head"><div><h2>NOTARY intelligence layer</h2><p>Multimodal witness review, predictions, reasoning sales, and programmable escrow.</p></div></div>
        <div class="feature-grid">
          {cards([
            ("Multimodal observation", "Speechmatics audio/video transcription feeds the witness pipeline.", notary.get("multimodalObservation", {}).get("configured")),
            ("Evidence-to-obligation mapping", "Messy human input becomes exact payment obligations.", bool(notary.get("obligationMapping", {}).get("route"))),
            ("Adversarial evidence resistance", "Guardian Sentinel checks source quality, duplicate claims, and manipulation risk.", bool(notary.get("adversarialEvidenceResistance", {}).get("agent"))),
            ("Graded verdicts", "The witness can release partial payment instead of only yes/no outcomes.", notary.get("gradedVerdicts", {}).get("implemented")),
            ("Pay-to-Peek reasoning traces", "Users pay USDC to unlock the full reasoning behind public verdicts.", bool(notary.get("reasoningMarketplace", {}).get("route"))),
            ("Prediction micro-shares", "Users can buy exposure to NOTARY predictions after payment verification.", bool(notary.get("tradeableIntelligence", {}).get("route"))),
            ("Self-improvement", "Reflector checkpoints update karma and policy memory.", bool(notary.get("selfImprovement", {}).get("route"))),
            ("Witness-to-Pay", "Verified facts become escrow release, hold, or refund actions.", bool(notary.get("witnessToPay", {}).get("route"))),
            ("Arbitrage analysis", "Market route analysis is available for treasury-aware opportunities.", bool(notary.get("arbitrage", {}).get("route"))),
          ])}
        </div>
      </section>
    </main>
    """
    return _page("Coverage / NOTARY", body, user)


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
        <p class="panel-copy" style="font-size: 15px; line-height: 1.5;">Each payer, payee, approver, or agent counterparty gets its own workspace. Public records stay on the landing page; your evidence and actions stay here.</p>
        <div class="notice" style="border-color: rgba(246, 196, 83, 0.25); background: rgba(246, 196, 83, 0.07); color: #ffe7a3; font-size: 13px; padding: 12px 16px; margin-bottom: 20px;">
          Secure Auth: Access your workspace with a handle and password. A local agent wallet is automatically mapped to your account.
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
      function applyNotaryTheme(theme) {
        const next = theme === "light" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        localStorage.setItem("notary-theme", next);
        document.querySelectorAll(".theme-toggle").forEach(button => {
          button.textContent = next === "light" ? "Dark" : "Light";
        });
      }
      window.toggleNotaryTheme = function () {
        applyNotaryTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
      };
      applyNotaryTheme(localStorage.getItem("notary-theme") || "dark");
      window.copyWorkspaceWalletAddress = async function (address) {
        const status = document.getElementById("workspace-wallet-copy-status");
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(address);
          } else {
            const textArea = document.createElement("textarea");
            textArea.value = address;
            textArea.setAttribute("readonly", "");
            textArea.style.position = "fixed";
            textArea.style.left = "-9999px";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);
          }
          if (status) {
            status.textContent = "Address copied";
            setTimeout(() => status.textContent = "", 2200);
          }
        } catch (error) {
          if (status) status.textContent = "Select the address text and copy manually";
        }
      };
    </script>
    """


def render_workspace(
    state: dict[str, Any],
    user: dict[str, Any],
    profile: dict[str, Any],
    error: str | None = None,
    message: str | None = None,
    circle_request_id: str | None = None,
    view: str = "overview",
) -> str:
    user_label = escape(str(user.get("email") or user.get("id")))
    profile_username_raw = str(profile.get("username", "unknown"))
    profile_username = escape(profile_username_raw)
    display_name = escape(profile_username_raw.lstrip("@").split("@")[0].replace("_", " ").title() or "Notary")
    initials = "".join(part[:1] for part in profile_username_raw.replace("@", "").replace("_", " ").split()[:2]).upper() or "DN"
    default_payer = f"@{profile_username}"
    cases = state.get("cases", [])
    rulings = state.get("rulings", [])
    active_cases = [item for item in cases if item.get("status") not in {"released", "refunded"}]
    locked_total = sum(float(item.get("amount_usdc") or 0) for item in active_cases)
    yield_total = sum(float(item.get("amountUSDC") or 0) for item in state.get("yield_payouts", []))
    karma_score = sum(int(item.get("delta") or 0) for item in state.get("karma_checkpoints", []))
    profile_balance = escape(str(profile.get("balance", "0.00")))
    error_html = f'<div class="notice bad" style="border-radius: 8px;">{escape(error)}</div>' if error else ""
    message_html = f'<div class="notice" style="border-radius: 8px;">{escape(message)}</div>' if message else ""
    valid_views = {"overview", "wallet", "escrow", "swarm", "evidence", "predictions", "yield", "settings"}
    view_key = view if view in valid_views else "overview"
    active = lambda key: "active" if view_key == key else ""
    wallet_raw = str(profile.get("wallet") or "0x0000000000000000000000000000000000000000")
    wallet = escape(wallet_raw)
    wallet_js = escape(json.dumps(wallet_raw))

    body = f"""
    <style>
      .app-view {{ display: none; }}
      .dashboard-shell[data-view="overview"] #overview,
      .dashboard-shell[data-view="wallet"] #wallet,
      .dashboard-shell[data-view="escrow"] #escrow,
      .dashboard-shell[data-view="swarm"] #agents,
      .dashboard-shell[data-view="evidence"] #evidence,
      .dashboard-shell[data-view="predictions"] #predictions,
      .dashboard-shell[data-view="predictions"] #pay-to-peek,
      .dashboard-shell[data-view="yield"] #data,
      .dashboard-shell[data-view="settings"] #identity,
      .dashboard-shell[data-view="settings"] #settings-advanced {{ display: block; }}
    </style>
    <main class="shell dashboard-shell" data-view="{escape(view_key)}">
      <aside class="side-rail">
        <div class="side-brand">
          <div>
            <strong>NOTARY</strong>
            <span>Witness &middot; Pay &middot; Remember</span>
          </div>
        </div>
        <nav class="side-nav">
          <a class="{active('overview')}" href="/app">Overview</a>
          <a class="{active('wallet')}" href="/app/wallet">Wallet</a>
          <a class="{active('escrow')}" href="/app/escrow">Escrow Cases</a>
          <a class="{active('swarm')}" href="/app/swarm">Witness Swarm</a>
          <a class="{active('evidence')}" href="/app/evidence">Evidence Vault</a>
          <a class="{active('predictions')}" href="/app/predictions">Predictions</a>
          <a class="{active('yield')}" href="/app/yield">Yield &amp; Treasury</a>
          <a href="/ledger">Public Ledger</a>
          <a href="/profile/{profile_username}">Profile</a>
          <a class="{active('settings')}" href="/app/settings">Settings</a>
        </nav>
        <div class="side-footer">Arc testnet &middot; synced</div>
      </aside>

      <div class="dash-main">
        <div class="dash-topbar">
          <div class="search-pill"></div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <a class="button" href="/app/escrow" style="width: auto; min-width: 110px;">New case</a>
            <button type="button" class="theme-toggle" onclick="toggleNotaryTheme()" aria-label="Toggle theme">Light</button>
            <div class="avatar-pill">{escape(initials[:2])}</div>
          </div>
        </div>

        <section id="overview" class="workspace-intro app-view" style="margin-bottom: 28px;">
          <div class="workspace-title">
            <h1>Good morning, {display_name}</h1>
            <p>Here's what your witnesses observed today.</p>
          </div>
          {error_html}
          {message_html}
          <div class="profile-metrics" style="grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 24px;">
            <div class="metric-card"><div class="metric-trend">+2.3%</div><strong>{profile_balance}</strong><span>Wallet balance</span><p class="status-line">USDC · Arc testnet</p></div>
            <div class="metric-card"><strong>${locked_total:,.2f}</strong><span>Locked in escrow</span><p class="status-line">{len(active_cases)} active cases</p></div>
            <div class="metric-card"><div class="metric-trend">+0.4%</div><strong>${yield_total:,.6f}</strong><span>Yield earned</span><p class="status-line">Sponsored reserve</p></div>
            <div class="metric-card"><div class="metric-trend">+12</div><strong>{karma_score}</strong><span>Karma score</span><p class="status-line">Top 4% of agents</p></div>
          </div>
        </section>

        <section id="wallet" class="section-card app-view">
          <div class="section-head">
            <div>
              <h2>Wallet</h2>
              <p>Your NOTARY account wallet, Arc testnet balance, copyable address, and direct USDC transfer controls.</p>
            </div>
          </div>
          <div class="section-grid">
            <article class="status-card">
              <span class="badge good">Wallet</span>
              <h3>{profile_balance} USDC</h3>
              <p>USDC &middot; Arc testnet</p>
              <div class="facts" style="grid-template-columns: 1fr; margin-top: 18px;">
                <div class="fact"><span>EVM address</span><code id="workspace-wallet-address">{wallet}</code></div>
              </div>
              <button type="button" class="button secondary" style="width: 100%; margin-top: 16px;" onclick="copyWorkspaceWalletAddress({wallet_js})">Copy address</button>
              <p id="workspace-wallet-copy-status" class="status-line" style="margin-top: 10px;"></p>
            </article>
            <article class="status-card">
              <span class="badge good">Send</span>
              <h3>Send USDC Funds</h3>
              <p>Transfer USDC from your agent wallet to any recipient handle or raw address.</p>
              <form method="post" action="/ui/wallet/send" style="margin-top: 16px;">
                <label for="wallet_recipient">Recipient handle or EVM address</label>
                <input id="wallet_recipient" name="recipient" required placeholder="e.g. @jennycruzy or 0x..." />
                <label for="wallet_amount">Amount in USDC</label>
                <input id="wallet_amount" name="amount" type="number" min="0.01" step="0.01" value="10" required />
                <button style="width: 100%; margin-top: 12px;">Send USDC Transfer</button>
              </form>
            </article>
          </div>
        </section>

        <section id="escrow" class="section-card app-view">
          <div class="section-head">
            <div>
              <h2>Active escrow cases</h2>
              <p>Define the obligation, lock USDC, invite evidence, and let the witness swarm settle the outcome.</p>
            </div>
            <a class="button secondary" href="#instruction">New case</a>
          </div>
          <div class="section-grid">
            <article class="status-card">
              <span class="badge good">Witness-to-Pay</span>
              <h3>Create a secure escrow</h3>
              <form method="post" action="/ui/cases" style="margin-top: 16px;">
                <label for="instruction">Agreement details</label>
                <textarea id="instruction" name="instruction" required placeholder="Pay @jennycruzy $50 when the delivery manifest is complete and payer approves."></textarea>
                <div class="split" style="margin-top: 8px;">
                  <div><label for="payer_identity">Payer username</label><input id="payer_identity" name="payer_identity" value="{default_payer}" required /></div>
                  <div><label for="payer_type">Payer type</label><select id="payer_type" name="payer_type"><option value="human">Human</option><option value="agent">Agent</option></select></div>
                </div>
                <div class="split">
                  <div><label for="payee_identity">Payee username</label><input id="payee_identity" name="payee_identity" value="@jennycruzy" required /></div>
                  <div><label for="payee_type">Payee type</label><select id="payee_type" name="payee_type"><option value="human">Human</option><option value="agent">Agent</option></select></div>
                </div>
                <label for="amount_usdc">USDC amount to lock</label>
                <input id="amount_usdc" name="amount_usdc" type="number" min="0.01" step="0.01" value="50" required />
                <button style="margin-top: 18px; width: 100%;">Create secure escrow</button>
              </form>
            </article>
            <article class="status-card">
              <span class="badge good">Escrow Cases</span>
              <h3>Escrow case board</h3>
              <p>{len(cases)} case(s), {len(rulings)} witness ruling(s), and {locked_total:,.2f} USDC currently locked or pending.</p>
              <div style="margin-top: 14px; max-height: 520px; overflow: auto;">{_case_cards(cases)}</div>
            </article>
          </div>
        </section>

        <section id="agents" class="section-card app-view">
          <div class="section-head">
            <div>
              <h2>Witness activity</h2>
              <p>Each case runs through the full swarm: scanner, sentinel, risk, strategy, validator, and reflector.</p>
            </div>
            <span class="badge good">Six active agents</span>
          </div>
          <div class="agent-grid">{_agent_role_cards(state.get("swarm_roles", []))}</div>
        </section>

        <section id="evidence" class="section-card app-view">
          <div class="section-head"><div><div class="eyebrow">Evidence Vault</div><h2>Submit proof by voice, media, or text</h2><p>Evidence feeds the same witness pipeline used for escrow, Pay-to-Peek, predictions, and disputes.</p></div></div>
          <div class="section-grid">
            <article class="status-card">
              <span class="badge good">Speechmatics</span><h3>Capture voice proof</h3>
              <p>Record or upload audio/video evidence, then transcribe it for witness analysis.</p>
              <label for="record_privacy_mode">Privacy mode</label><select id="record_privacy_mode"><option value="protected">Protected</option><option value="private">Private</option><option value="public">Public</option></select>
              <div class="button-row"><button id="start_recording" type="button">Start recording</button><button id="stop_recording" class="danger" type="button" disabled>Stop and transcribe</button></div>
              <p id="recording_status" class="status-line">Microphone is ready.</p>
              <form method="post" action="/ui/media" enctype="multipart/form-data" style="border-top: 1px dashed var(--line); margin-top: 16px; padding-top: 16px;"><label for="file">Upload audio/video recording</label><input id="file" name="file" type="file" accept="audio/*,video/*" /><input name="privacy_mode" type="hidden" value="protected" /><label for="media_transcript_text">Or paste transcript</label><textarea id="media_transcript_text" name="transcript_text" placeholder="Copy/paste transcript text if you already have it..."></textarea><button style="margin-top: 12px; width: 100%;">Process upload</button></form>
            </article>
            <article class="status-card">
              <span class="badge good">Written proof</span><h3>Quick evidence submission</h3>
              <p>Submit signed approval, a commit record, a file link, or a work summary.</p>
              <form method="post" action="/ui/attest"><label for="privacy_mode">Privacy mode</label><select id="privacy_mode" name="privacy_mode"><option value="protected">Protected</option><option value="private">Private</option><option value="public">Public</option></select><label for="transcript_text">Written evidence</label><textarea id="transcript_text" name="transcript_text" placeholder="I approve release of $50 because pull request #5 is complete and merged."></textarea><button style="width: 100%;">Submit evidence</button></form>
            </article>
          </div>
        </section>

        {_commerce_panels(state, profile_username)}

        <section id="rulings" class="section-card app-view">
          <div class="section-head"><div><div class="eyebrow">Witness Rulings</div><h2>Recent rulings</h2><p>Rulings are summarized publicly while protected evidence remains private.</p></div></div>
          <div class="grid">{_record_cards(rulings)}</div>
        </section>

        <details id="settings-advanced" class="advanced-stack app-view" open>
          <summary>Advanced Arc, Circle, and operator controls</summary>
          {_ops_panels(state, circle_request_id)}
        </details>
      </div>
    </main>
    {_workspace_scripts()}
    """
    return _bare_page("Workspace / NOTARY", body)

def render_case_evidence(
    case: dict[str, Any],
    token: str | None,
    user: dict[str, Any] | None,
    error: str | None = None,
) -> str:
    hidden_token = f'<input name="token" type="hidden" value="{escape(token)}" />' if token else ""
    is_funded = case.get("status") != "awaiting_funding"
    funding_notice = (
        '<div class="notice bad">This contract is currently awaiting funding. Submitting proof is locked until the payer deposits USDC into the secure conditional escrow vault.</div>'
        if not is_funded
        else ""
    )
    error_notice = (
        f'<div class="notice bad">Evidence submission failed: {escape(error)}</div>'
        if error
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
        {error_notice}
        
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
            Include positive action terms like <strong>"completed"</strong>, <strong>"delivered"</strong>, or <strong>"approved"</strong> to help NOTARY assess whether release is justified.
          </p>
          <textarea id="evidence_text" name="evidence_text" required placeholder="Paste your links, commits, or signed approval statements here..." {disabled}></textarea>
          
          <button style="margin-top: 20px; width: 100%;" {disabled}>Submit &amp; Verify Proof</button>
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
    yield_total = sum(float(tx.get("amount_usdc") or 0) for tx in transactions if tx.get("type") == "sponsored_yield")
    commerce_count = sum(1 for tx in transactions if tx.get("type") in {"micro_share", "pay_to_peek"})
    escrow_count = sum(1 for tx in transactions if str(tx.get("type", "")).startswith("escrow"))
    
    tx_rows = []
    if not transactions:
        tx_rows.append('<div class="empty" style="text-align: center; padding: 40px; background: var(--surface-2); border-radius: 12px; border: 1px solid var(--line); color: var(--muted);">No transaction history recorded yet.</div>')
    else:
        for tx in transactions:
            direction = tx.get("direction")
            is_send = direction == "send"
            color = "#ef4444" if is_send else "#10b981"
            prefix = "-" if is_send else "+"
            arrow = "OUT" if is_send else "IN"
            amount_display = f'<strong style="color: {color}; font-family: \'Outfit\'; font-size: 16px;">{prefix}{tx.get("amount_usdc")} USDC</strong>'
            tx_id_raw = str(tx.get("tx_id") or "")
            tx_id_json = escape(json.dumps(tx_id_raw))
            copy_button = (
                f'<button type="button" class="button secondary" style="min-height: 32px; padding: 0 12px; font-size: 12px; margin-top: 8px;" onclick="copyTxHash({tx_id_json}, this)">Copy tx hash</button>'
                if tx_id_raw
                else ""
            )
            
            try:
                date_str = datetime.fromtimestamp(tx.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = "unknown date"
                
            tx_rows.append(
                f"""
                <div class="tx-row">
                  <div class="tx-icon" style="color: {color};">{arrow}</div>
                  <div>
                    <strong style="font-size: 16px; color: #fff; font-family: 'Outfit';">{escape(tx.get("description", ""))}</strong>
                    <span style="display: block; font-size: 12px; color: var(--muted); margin-top: 4px;">{escape(str(tx.get("type", "transaction")).replace("_", " ").title())} / Party: {escape(tx.get("party", ""))} / {date_str}</span>
                    <code title="{escape(tx_id_raw)}">{escape(_short(tx_id_raw, 48))}</code>
                    {copy_button}
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
    
    wallet_card = f"""
    <div class="panel" style="border: 1px solid rgba(246, 196, 83, 0.2); background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px;">
      <div class="eyebrow" style="color: var(--primary);">Secure Wallet</div>
      <h2 style="margin: 6px 0 2px; color: #fff; font-size: 28px; font-family: 'Outfit'; font-weight: 800;">{profile_balance} USDC</h2>
      <p style="margin: 0 0 16px; font-size: 12px; color: var(--muted);">ARC-TESTNET</p>

      <label style="font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 6px;">EVM Address</label>
      <div style="display: grid; gap: 10px; background: var(--surface-2); padding: 12px; border-radius: 8px; border: 1px solid var(--line);">
        <code id="profile-wallet-address" style="color: var(--green); font-size: 12px; font-weight: 700; line-height: 1.5; word-break: break-all; white-space: normal;">{profile_wallet}</code>
        <button type="button" id="copy-wallet-address" class="button secondary" style="width: 100%; min-height: 40px; border-radius: 8px;" onclick="copyProfileWalletAddress({profile_wallet_js})">Copy address</button>
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
              <h2>Change Username</h2>
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
              <span style="font-size: 13px; color: var(--muted);">Username locked (limit reached)</span>
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
      async function copyTxHash(txHash, button) {{
        const originalText = button ? button.textContent : '';
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(txHash);
          }} else {{
            const textArea = document.createElement('textarea');
            textArea.value = txHash;
            textArea.setAttribute('readonly', '');
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
          }}
          if (button) {{
            button.textContent = 'Copied';
            setTimeout(() => button.textContent = originalText || 'Copy tx hash', 2200);
          }}
        }} catch (error) {{
          if (button) button.textContent = 'Select hash';
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

      <section class="profile-metrics" style="margin-bottom: 28px;">
        <div class="status-card"><span class="badge good">Wallet</span><h3>{profile_balance} USDC</h3><p>Live Arc testnet balance for this account wallet.</p></div>
        <div class="status-card"><span class="badge good">Yield</span><h3>{yield_total:.6f} USDC</h3><p>Sponsored reserve rewards received by this wallet.</p></div>
        <div class="status-card"><span class="badge good">Commerce</span><h3>{commerce_count} action(s)</h3><p>Micro-share and Pay-to-Peek purchases tied to this account.</p></div>
      </section>
      
      <section class="workspace" style="display: grid; grid-template-columns: 360px 1fr; gap: 32px; align-items: start;">
        <aside style="position: sticky; top: 100px;">
          {wallet_card}
          <div class="panel" style="border-radius: 12px; padding: 24px; background: var(--surface); border: 1px solid var(--line); margin-bottom: 24px;">
            <div class="eyebrow">Account rails</div>
            <div class="facts" style="grid-template-columns: 1fr; margin-top: 8px;">
              <div class="fact"><span>Escrow activity</span><strong>{escrow_count} record(s)</strong></div>
              <div class="fact"><span>Prediction commerce</span><strong>{commerce_count} record(s)</strong></div>
              <div class="fact"><span>Yield route</span><strong>Sponsored reserve live</strong></div>
              <div class="fact"><span>USYC</span><strong>Awaiting allowlist</strong></div>
            </div>
          </div>
          {send_funds_card}
          {change_username_card}
        </aside>
        
        <section style="background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 32px; box-shadow: var(--shadow);">
          <div class="section-head" style="margin-bottom: 24px; border-bottom: 1px solid var(--line); padding-bottom: 16px;">
            <div>
              <h2 style="font-size: 24px; color: #fff; margin: 0;">Verified Transaction Ledger</h2>
              <p style="margin: 6px 0 0; font-size: 15px; color: var(--muted);">Direct USDC transfers, case deposits, and escrow releases verified by NOTARY.</p>
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






