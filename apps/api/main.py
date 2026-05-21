from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.api.dashboard import render_dashboard
from notary.app_service import NotaryAppService
from notary.config import get_settings
from notary.models.schemas import (
    DisclosureLevel,
    Observation,
    PrivacyMode,
    QevorpayPaymentLinkRequest,
)

app = FastAPI(title="NOTARY", version="0.1.0")


@lru_cache
def get_app_service() -> NotaryAppService:
    return NotaryAppService(get_settings())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "notary"}


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(render_dashboard(get_app_service().dashboard_state()))


@app.post("/notaries")
async def create_notary(label: str | None = None) -> dict:
    return await get_app_service().create_notary(label)


@app.get("/notaries")
async def list_notaries() -> list[dict]:
    return get_app_service().list_notaries()


@app.get("/circle/status")
async def circle_status() -> dict:
    return await get_app_service().circle_status()


@app.get("/speechmatics/status")
async def speechmatics_status() -> dict:
    return get_app_service().speechmatics_status()


@app.post("/circle/login/init")
async def circle_login_init(email: str | None = None) -> dict:
    return await get_app_service().circle_login_init(email)


@app.post("/circle/login/complete")
async def circle_login_complete(request_id: str = Form(...), otp: str = Form(...)) -> dict:
    return await get_app_service().circle_login_complete(request_id, otp)


@app.get("/notaries/{notary_id}/operating-agreement")
async def get_operating_agreement(notary_id: str) -> dict:
    agreement = get_app_service().get_operating_agreement(notary_id)
    if not agreement:
        return {"error": "not_found", "notaryId": notary_id}
    return agreement


@app.post("/ui/notaries")
async def ui_create_notary(label: str = Form(default="")) -> RedirectResponse:
    await get_app_service().create_notary(label or None)
    return RedirectResponse("/", status_code=303)


@app.post("/observations/cycle")
async def submit_observation_and_run_cycle(observation: Observation) -> dict:
    return await get_app_service().run_cycle(observation)


@app.get("/attestations")
async def list_attestations() -> list[dict]:
    return get_app_service().list_bucket("attestations")


@app.get("/predictions")
async def list_predictions() -> list[dict]:
    return get_app_service().list_bucket("predictions")


@app.get("/payments")
async def list_payments() -> dict[str, list[dict]]:
    service = get_app_service()
    return {
        "paymentLinks": service.list_bucket("payments"),
        "paymentTriggers": service.list_bucket("payment_triggers"),
    }


@app.get("/pay/{reference}", response_class=HTMLResponse)
async def local_payment_page(reference: str) -> HTMLResponse:
    payments = get_app_service().list_bucket("payments")
    payment = next((item for item in payments if item.get("reference") == reference), None)
    if not payment:
        return HTMLResponse("<h1>Payment not found</h1>", status_code=404)
    request = payment.get("request", {})
    amount = request.get("amount_usdc", request.get("amountUSDC", "n/a"))
    description = request.get("description", "NOTARY payment")
    return HTMLResponse(
        f"""
        <!doctype html>
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Qevorpay Local Payment</title>
            <style>
              body {{
                font-family: Inter, system-ui, sans-serif;
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                background: #f7f3ea;
                color: #151515;
              }}
              main {{
                width: min(520px, calc(100vw - 32px));
                background: #fffaf0;
                border: 1px solid #d8d5cc;
                border-radius: 8px;
                padding: 24px;
              }}
              strong {{ font-size: 42px; display: block; }}
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
        """
    )


@app.get("/karma")
async def list_karma() -> list[dict]:
    return get_app_service().list_bucket("karma")


@app.post("/media/transcribe")
async def transcribe_media(
    file: UploadFile = File(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
    transcript_text: str | None = Form(default=None),
) -> dict:
    upload_dir = Path("media/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    file_path.write_bytes(await file.read())
    return await get_app_service().upload_media(
        file_path=file_path,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        privacy_mode=privacy_mode,
        transcript_text=transcript_text,
    )


@app.post("/ui/media")
async def ui_upload_media(
    file: UploadFile = File(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
    transcript_text: str | None = Form(default=None),
) -> RedirectResponse:
    upload_dir = Path("media/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    file_path.write_bytes(await file.read())
    result = await get_app_service().upload_media(
        file_path=file_path,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        privacy_mode=privacy_mode,
        transcript_text=transcript_text or None,
    )
    if result.get("observation"):
        observation = Observation.model_validate(result["observation"])
        await get_app_service().run_cycle(observation)
    return RedirectResponse("/", status_code=303)


@app.post("/media/attest")
async def attest_transcript(transcript_text: str, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED) -> dict:
    return await get_app_service().ingest_transcript(transcript_text, privacy_mode)


@app.post("/ui/attest")
async def ui_attest_transcript(
    transcript_text: str = Form(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
) -> RedirectResponse:
    await get_app_service().ingest_transcript(transcript_text, privacy_mode)
    return RedirectResponse("/", status_code=303)


@app.post("/qevorpay/payment-link")
async def create_payment_link(request: QevorpayPaymentLinkRequest) -> dict:
    return await get_app_service().create_payment_link(request)


@app.post("/evidence/grants")
async def grant_evidence_access(
    evidence_id: str = Form(...),
    grantee: str = Form(...),
    purpose: str = Form(...),
    disclosure_level: DisclosureLevel = Form(...),
) -> dict:
    return get_app_service().grant_evidence_access(
        evidence_id=evidence_id,
        grantee=grantee,
        purpose=purpose,
        disclosure_level=disclosure_level,
    )


@app.post("/ui/payment-link")
async def ui_create_payment_link(
    amount_usdc: float = Form(...),
    description: str = Form(...),
) -> RedirectResponse:
    await get_app_service().create_payment_link(
        QevorpayPaymentLinkRequest(amount_usdc=amount_usdc, description=description)
    )
    return RedirectResponse("/", status_code=303)


@app.get("/state")
async def state() -> dict:
    return get_app_service().dashboard_state()
