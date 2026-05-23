from __future__ import annotations

import argparse
import asyncio
import cgi
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apps.api.dashboard import render_landing
from notary.app_service import NotaryAppService
from notary.config import get_settings
from notary.models.schemas import PrivacyMode, QevorpayPaymentLinkRequest


SERVICE = NotaryAppService(get_settings())


def run_async(coro):
    return asyncio.run(coro)


class NotaryHandler(BaseHTTPRequestHandler):
    server_version = "NOTARY/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._html(HTTPStatus.OK, render_landing(SERVICE.dashboard_state()))
            return
        if parsed.path == "/state":
            self._json(HTTPStatus.OK, SERVICE.dashboard_state())
            return
        if parsed.path == "/speechmatics/status":
            self._json(HTTPStatus.OK, SERVICE.speechmatics_status())
            return
        if parsed.path == "/circle/status":
            try:
                self._json(HTTPStatus.OK, run_async(SERVICE.circle_status()))
            except Exception as exc:
                self._json(
                    HTTPStatus.OK,
                    {
                        "provider": "circle",
                        "configured": False,
                        "status": "unavailable",
                        "message": str(exc),
                    },
                )
            return
        if parsed.path.startswith("/pay/"):
            self._render_payment(parsed.path.removeprefix("/pay/"))
            return
        self._html(HTTPStatus.NOT_FOUND, "<h1>Not found</h1>")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/ui/notaries":
            form = self._read_form()
            run_async(SERVICE.create_notary(form.get("label") or None))
            self._redirect("/")
            return
        if parsed.path == "/ui/attest":
            form = self._read_form()
            transcript = form.get("transcript_text", "")
            privacy = PrivacyMode(form.get("privacy_mode", PrivacyMode.PROTECTED.value))
            if transcript.strip():
                run_async(SERVICE.ingest_transcript(transcript, privacy))
            self._redirect("/")
            return
        if parsed.path == "/ui/payment-link":
            form = self._read_form()
            amount = float(form.get("amount_usdc", "1"))
            description = form.get("description", "Verified NOTARY payment")
            run_async(
                SERVICE.create_payment_link(
                    QevorpayPaymentLinkRequest(amount_usdc=amount, description=description)
                )
            )
            self._redirect("/")
            return
        if parsed.path == "/ui/media":
            self._handle_media_upload()
            return
        self._html(HTTPStatus.NOT_FOUND, "<h1>Not found</h1>")

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return {key: values[-1] for key, values in parse_qs(body).items()}

    def _handle_media_upload(self) -> None:
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            self._html(HTTPStatus.BAD_REQUEST, "<h1>Expected multipart form data</h1>")
            return
        pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
        pdict["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", "0"))
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
            keep_blank_values=True,
        )
        privacy = PrivacyMode(_field_value(form, "privacy_mode") or PrivacyMode.PROTECTED.value)
        transcript = _field_value(form, "transcript_text") or None
        upload = form["file"] if "file" in form else None
        if upload is None or not getattr(upload, "filename", ""):
            self._html(HTTPStatus.BAD_REQUEST, "<h1>No file uploaded</h1>")
            return

        upload_dir = Path("media/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(upload.filename).name
        file_path = upload_dir / filename
        with file_path.open("wb") as handle:
            handle.write(upload.file.read())

        result = run_async(
            SERVICE.upload_media(
                file_path=file_path,
                filename=filename,
                content_type=getattr(upload, "type", None) or "application/octet-stream",
                privacy_mode=privacy,
                transcript_text=transcript,
            )
        )
        observation = result.get("observation")
        if observation:
            from notary.models.schemas import Observation

            run_async(SERVICE.run_cycle(Observation.model_validate(observation)))
        self._redirect("/")

    def _render_payment(self, reference: str) -> None:
        reference = unquote(reference)
        payments = SERVICE.list_bucket("payments")
        payment = next((item for item in payments if item.get("reference") == reference), None)
        if not payment:
            self._html(HTTPStatus.NOT_FOUND, "<h1>Payment not found</h1>")
            return
        request = payment.get("request", {})
        amount = request.get("amount_usdc", request.get("amountUSDC", "n/a"))
        description = request.get("description", "NOTARY payment")
        self._html(
            HTTPStatus.OK,
            f"""
            <!doctype html>
            <html lang="en">
              <head>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>Qevorpay Payment</title>
                <style>
                  body {{
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    background: #f7f3ea;
                    color: #151515;
                    font-family: Inter, system-ui, sans-serif;
                  }}
                  main {{
                    width: min(520px, calc(100vw - 32px));
                    background: #fffaf0;
                    border: 1px solid #d8d5cc;
                    border-radius: 8px;
                    padding: 24px;
                  }}
                  strong {{ display: block; font-size: 44px; }}
                  a {{ color: #116149; font-weight: 800; }}
                </style>
              </head>
              <body>
                <main>
                  <h1>Qevorpay Payment</h1>
                  <p>{description}</p>
                  <strong>{amount} USDC</strong>
                  <p>Status: {payment.get("status", "created")}</p>
                  <p><a href="/">Back to NOTARY</a></p>
                </main>
              </body>
            </html>
            """,
        )

    def _redirect(self, path: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", path)
        self.end_headers()

    def _json(self, status: HTTPStatus, data: object) -> None:
        payload = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _html(self, status: HTTPStatus, html: str) -> None:
        payload = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _field_value(form: cgi.FieldStorage, key: str) -> str | None:
    if key not in form:
        return None
    value = form[key]
    if isinstance(value, list):
        value = value[-1]
    raw = value.value
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NOTARY live app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NotaryHandler)
    print(f"NOTARY live app running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
