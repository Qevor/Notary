from __future__ import annotations

import base64
import hashlib
import hmac
import json
from functools import lru_cache
from pathlib import Path
import time
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.api.dashboard import (
    render_case_evidence,
    render_landing,
    render_public_ledger,
    render_sign_in,
    render_workspace,
)
from notary.app_service import NotaryAppService
from notary.config import get_settings
from notary.models.schemas import (
    DisclosureLevel,
    Observation,
    PrivacyMode,
    QevorpayPaymentLinkRequest,
    WitnessIntakeRequest,
)

app = FastAPI(title="NOTARY", version="0.1.0")
SESSION_COOKIE = "notary_session"


@lru_cache
def get_app_service() -> NotaryAppService:
    return NotaryAppService(get_settings())


def _session_secret() -> str | None:
    return get_settings().notary_session_secret


def _sign_session(payload: dict) -> str:
    secret = _session_secret()
    if not secret:
        raise RuntimeError("NOTARY_SESSION_SECRET is required for UI sign-in")
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode()
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _read_session(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    secret = _session_secret()
    if not token or not secret or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("expiresAt", 0) < int(time.time()):
        return None
    return payload.get("user")


def _require_ui_user(request: Request) -> dict:
    user = _read_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def _user_state(state: dict, user: dict) -> dict:
    identities = {
        str(value).lower()
        for value in (user.get("email"), user.get("id"))
        if value
    }

    def related_ruling(item: dict) -> bool:
        parties = item.get("partyIdentities", {}) or {}
        if any(str(value).lower() in identities for value in parties.values() if value):
            return True
        for evidence in item.get("evidence", []) or []:
            if str(evidence.get("submitter_identity", "")).lower() in identities:
                return True
        return False

    def related_payment(item: dict) -> bool:
        candidates = [
            item.get("payer_identity"),
            item.get("payee_identity"),
            item.get("instruction", {}).get("payer_identity"),
            item.get("instruction", {}).get("payee_identity"),
            item.get("trigger", {}).get("recipient"),
            item.get("trigger", {}).get("metadata", {}).get("payerIdentity"),
        ]
        return any(str(value).lower() in identities for value in candidates if value)

    def related_case(item: dict) -> bool:
        candidates = [
            item.get("created_by_identity"),
            item.get("payer_identity"),
            item.get("payee_identity"),
            item.get("approver_identity"),
        ]
        return any(str(value).lower() in identities for value in candidates if value)

    scoped = dict(state)
    scoped["cases"] = [item for item in state.get("cases", []) if related_case(item)]
    scoped["rulings"] = [item for item in state.get("rulings", []) if related_ruling(item)]
    scoped["payments"] = [item for item in state.get("payments", []) if related_payment(item)]
    scoped["payment_instructions"] = [
        item for item in state.get("payment_instructions", []) if related_payment(item)
    ]
    scoped["disputes"] = []
    scoped["reversals"] = [
        item for item in state.get("reversals", [])
        if any(
            ruling.get("rulingId") in {item.get("original_ruling_id"), item.get("new_ruling_id")}
            for ruling in scoped["rulings"]
        )
    ]
    return scoped


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "notary"}


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    service = get_app_service()
    user = _read_session(request)
    return HTMLResponse(render_landing(service.dashboard_state(), user))


@app.get("/login", response_class=HTMLResponse)
async def login(
    email: str | None = None,
    message: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    service = get_app_service()
    return HTMLResponse(
        render_sign_in(
            auth=service.auth_status(),
            email=email,
            message=message,
            error=error,
        )
    )


@app.get("/ledger", response_class=HTMLResponse)
async def public_ledger_page(request: Request) -> HTMLResponse:
    service = get_app_service()
    return HTMLResponse(render_public_ledger(service.dashboard_state(), _read_session(request)))


@app.get("/app", response_class=HTMLResponse)
async def workspace(
    request: Request,
    error: str | None = None,
    circle_request_id: str | None = None,
) -> HTMLResponse:
    user = _read_session(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    state = _user_state(get_app_service().dashboard_state(), user)
    return HTMLResponse(render_workspace(state, user, error=error, circle_request_id=circle_request_id))


@app.post("/ui/cases")
async def ui_create_case(
    request: Request,
    instruction: str = Form(...),
    payer_identity: str = Form(...),
    payee_identity: str = Form(...),
    amount_usdc: float = Form(...),
    payer_type: str = Form(default="human"),
    payee_type: str = Form(default="human"),
) -> RedirectResponse:
    user = _require_ui_user(request)
    identity = str(user.get("email") or user.get("id"))
    try:
        await get_app_service().create_conditional_case(
            created_by_identity=identity,
            created_by_type="human",
            payer_identity=payer_identity,
            payee_identity=payee_identity,
            approver_identity=payer_identity,
            payer_type=payer_type,
            payee_type=payee_type,
            approver_type=payer_type,
            instruction=instruction,
            amount_usdc=amount_usdc,
        )
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/app", status_code=303)


@app.get("/cases/{case_id}/evidence", response_class=HTMLResponse)
async def case_evidence_page(
    request: Request,
    case_id: str,
    token: str | None = None,
) -> HTMLResponse:
    case = get_app_service().store.get("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return HTMLResponse(render_case_evidence(case, token, _read_session(request)))


@app.post("/cases/{case_id}/evidence")
async def submit_case_evidence_ui(
    case_id: str,
    token: str | None = Form(default=None),
    submitter_identity: str = Form(...),
    submitter_type: str = Form(default="human"),
    evidence_text: str = Form(...),
) -> RedirectResponse:
    try:
        result = await get_app_service().submit_case_evidence(
            case_id=case_id,
            token=token,
            evidence_text=evidence_text,
            submitter_identity=submitter_identity,
            submitter_type=submitter_type,
        )
    except Exception as exc:
        return RedirectResponse(
            f"/cases/{case_id}/evidence?token={quote(token or '')}&error={quote(str(exc))}",
            status_code=303,
        )
    if result.get("error"):
        return RedirectResponse(
            f"/cases/{case_id}/evidence?token={quote(token or '')}&error={quote(str(result['error']))}",
            status_code=303,
        )
    return RedirectResponse("/ledger", status_code=303)


@app.post("/api/cases")
async def api_create_case(request: WitnessIntakeRequest) -> dict:
    if not request.payer_identity or not request.payee_identity or not request.amount_usdc:
        raise HTTPException(status_code=400, detail="payer_identity, payee_identity, and amount_usdc are required")
    try:
        return await get_app_service().create_conditional_case(
            created_by_identity=request.payer_identity,
            created_by_type=request.payer_type.value,
            payer_identity=request.payer_identity,
            payee_identity=request.payee_identity,
            approver_identity=request.approver_identity or request.payer_identity,
            payer_type=request.payer_type.value,
            payee_type=request.payee_type.value,
            approver_type=request.approver_type.value,
            instruction=request.instruction,
            amount_usdc=request.amount_usdc,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/cases/{case_id}/evidence")
async def api_submit_case_evidence(case_id: str, request: WitnessIntakeRequest) -> dict:
    try:
        result = await get_app_service().submit_case_evidence(
            case_id=case_id,
            token=str(request.metadata.get("inviteToken") or "") or None,
            evidence_text=request.evidence_text or request.instruction,
            evidence_ref=request.evidence_ref,
            submitter_identity=request.submitter_identity,
            submitter_type=request.submitter_type.value,
            privacy_mode=request.privacy_mode,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/auth/send-code")
async def auth_send_code(email: str = Form(...)) -> RedirectResponse:
    try:
        await get_app_service().send_login_otp(email)
    except Exception as exc:
        return RedirectResponse(f"/login?error={quote(str(exc))}", status_code=303)
    return RedirectResponse(
        f"/login?email={quote(email)}&message=Check%20your%20email%20for%20the%20sign-in%20code.",
        status_code=303,
    )


@app.post("/auth/verify-code")
async def auth_verify_code(email: str = Form(...), token: str = Form(...)) -> RedirectResponse:
    try:
        session = await get_app_service().verify_login_otp(email, token)
        cookie = _sign_session(
            {
                "user": session["user"],
                "accessToken": session.get("accessToken"),
                "expiresAt": int(time.time()) + int(session.get("expiresIn") or 3600),
            }
        )
    except Exception as exc:
        return RedirectResponse(f"/login?error={quote(str(exc))}", status_code=303)
    response = RedirectResponse("/app", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        cookie,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=int(session.get("expiresIn") or 3600),
    )
    return response


@app.post("/auth/dev-login")
async def auth_dev_login(email: str = Form(default="founder@notary.local")) -> RedirectResponse:
    settings = get_settings()
    if settings.notary_env == "production":
        raise HTTPException(status_code=404, detail="local sandbox login is disabled")
    cookie = _sign_session(
        {
            "user": {
                "id": email,
                "email": email,
                "role": "local_sandbox",
            },
            "expiresAt": int(time.time()) + 24 * 3600,
        }
    )
    response = RedirectResponse("/app", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        cookie,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=24 * 3600,
    )
    return response


@app.post("/auth/logout")
async def auth_logout() -> RedirectResponse:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.post("/notaries")
async def create_notary(label: str | None = None) -> dict:
    return await get_app_service().create_notary(label)


@app.get("/notaries")
async def list_notaries() -> list[dict]:
    return get_app_service().list_notaries()


@app.get("/circle/status")
async def circle_status() -> dict:
    return await get_app_service().circle_status()


@app.get("/circle/wallet")
async def circle_wallet_summary() -> dict:
    return await get_app_service().circle_wallet_summary()


@app.get("/speechmatics/status")
async def speechmatics_status() -> dict:
    return get_app_service().speechmatics_status()


@app.post("/circle/login/init")
async def circle_login_init(email: str | None = None) -> dict:
    return await get_app_service().circle_login_init(email)


@app.post("/circle/login/complete")
async def circle_login_complete(request_id: str = Form(...), otp: str = Form(...)) -> dict:
    return await get_app_service().circle_login_complete(request_id, otp)


@app.post("/circle/gateway/deposit")
async def circle_gateway_deposit(
    amount_usdc: float = Form(...),
    wallet_id: str | None = Form(default=None),
) -> dict:
    return await get_app_service().prepare_circle_gateway_deposit(
        amount_usdc=amount_usdc,
        wallet_id=wallet_id or None,
    )


@app.get("/agents")
async def list_agents() -> list[dict]:
    return get_app_service().swarm_roles()


@app.get("/notaries/{notary_id}/operating-agreement")
async def get_operating_agreement(notary_id: str) -> dict:
    agreement = get_app_service().get_operating_agreement(notary_id)
    if not agreement:
        return {"error": "not_found", "notaryId": notary_id}
    return agreement


@app.post("/ui/notaries")
async def ui_create_notary(request: Request, label: str = Form(default="")) -> RedirectResponse:
    _require_ui_user(request)
    await get_app_service().create_notary(label or None)
    return RedirectResponse("/app", status_code=303)


@app.post("/notaries/{notary_id}/register-onchain")
async def register_notary_onchain(notary_id: str) -> dict:
    return await get_app_service().register_notary_onchain(notary_id)


@app.post("/ui/notaries/{notary_id}/register-onchain")
async def ui_register_notary_onchain(request: Request, notary_id: str) -> RedirectResponse:
    _require_ui_user(request)
    try:
        await get_app_service().register_notary_onchain(notary_id)
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/app", status_code=303)


@app.post("/ui/circle/login/init")
async def ui_circle_login_init(request: Request, email: str = Form(...)) -> RedirectResponse:
    _require_ui_user(request)
    try:
        result = await get_app_service().circle_login_init(email)
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(str(exc))}", status_code=303)
    request_id = quote(str(result.get("requestId") or result.get("request_id") or ""))
    return RedirectResponse(f"/app?circle_request_id={request_id}", status_code=303)


@app.post("/ui/circle/login/complete")
async def ui_circle_login_complete(
    request: Request,
    request_id: str = Form(...),
    otp: str = Form(...),
) -> RedirectResponse:
    _require_ui_user(request)
    try:
        await get_app_service().circle_login_complete(request_id, otp)
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/app", status_code=303)


@app.post("/ui/circle/deposit")
async def ui_circle_gateway_deposit(
    request: Request,
    amount_usdc: float = Form(...),
    wallet_id: str | None = Form(default=None),
) -> RedirectResponse:
    _require_ui_user(request)
    try:
        await get_app_service().prepare_circle_gateway_deposit(
            amount_usdc=amount_usdc,
            wallet_id=wallet_id or None,
        )
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/app", status_code=303)


@app.post("/observations/cycle")
async def submit_observation_and_run_cycle(observation: Observation) -> dict:
    return await get_app_service().run_cycle(observation)


@app.post("/witness/obligations")
async def submit_witness_obligation(request: WitnessIntakeRequest) -> dict:
    try:
        return await get_app_service().submit_witness_obligation(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/witness/rulings/{ruling_id}/dispute")
async def dispute_witness_ruling(
    ruling_id: str,
    counter_evidence_text: str = Form(...),
    submitter_identity: str = Form(...),
    submitter_type: str = Form(default="human"),
    evidence_ref: str | None = Form(default=None),
) -> dict:
    try:
        return await get_app_service().dispute_ruling(
            ruling_id,
            counter_evidence_text=counter_evidence_text,
            submitter_identity=submitter_identity,
            submitter_type=submitter_type,
            evidence_ref=evidence_ref,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/witness/rulings/{ruling_id}/reverse")
async def reverse_witness_ruling(
    ruling_id: str,
    new_evidence_text: str = Form(...),
    submitter_identity: str = Form(...),
    submitter_type: str = Form(default="human"),
    evidence_ref: str | None = Form(default=None),
) -> dict:
    try:
        return await get_app_service().reverse_ruling_with_new_evidence(
            ruling_id,
            new_evidence_text=new_evidence_text,
            submitter_identity=submitter_identity,
            submitter_type=submitter_type,
            evidence_ref=evidence_ref,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/witness/rulings/{ruling_id}/confirm")
async def confirm_witness_ruling(
    ruling_id: str,
    party_identity: str = Form(...),
    party_type: str = Form(default="human"),
    outcome: str = Form(...),
    notes: str | None = Form(default=None),
) -> dict:
    return get_app_service().confirm_ruling_outcome(
        ruling_id=ruling_id,
        party_identity=party_identity,
        party_type=party_type,
        outcome=outcome,
        notes=notes,
    )


@app.get("/witness/ledger")
async def witness_public_ledger() -> list[dict]:
    return get_app_service().public_ledger()


@app.get("/witness/parties/{party_identity}/history")
async def witness_party_history(party_identity: str) -> dict:
    return get_app_service().party_operating_history(party_identity)


@app.get("/attestations")
async def list_attestations() -> list[dict]:
    return get_app_service().list_bucket("witness_attestations")


@app.get("/payments")
async def list_payments() -> dict[str, list[dict]]:
    service = get_app_service()
    return {
        "paymentLinks": service.list_bucket("payments"),
        "paymentInstructions": service.list_bucket("payment_instructions"),
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


@app.post("/media/transcribe")
async def transcribe_media(
    request: Request,
    file: UploadFile = File(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
    transcript_text: str | None = Form(default=None),
) -> dict:
    user = _require_ui_user(request)
    upload_dir = Path("media/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    file_path.write_bytes(await file.read())
    result = await get_app_service().upload_media(
        file_path=file_path,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        privacy_mode=privacy_mode,
        transcript_text=transcript_text,
    )
    if result.get("observation"):
        result["observation"]["source"]["submitted_by"] = str(user.get("email") or user.get("id"))
        result["observation"].setdefault("metadata", {})
        result["observation"]["metadata"]["submitter_identity"] = str(user.get("email") or user.get("id"))
        result["observation"]["metadata"]["payer_identity"] = str(user.get("email") or user.get("id"))
    return result


@app.post("/ui/media")
async def ui_upload_media(
    request: Request,
    file: UploadFile = File(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
    transcript_text: str | None = Form(default=None),
) -> RedirectResponse:
    user = _require_ui_user(request)
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
        observation.source.submitted_by = str(user.get("email") or user.get("id"))
        observation.metadata["submitter_identity"] = str(user.get("email") or user.get("id"))
        observation.metadata["payer_identity"] = str(user.get("email") or user.get("id"))
        await get_app_service().run_cycle(observation)
    return RedirectResponse("/app", status_code=303)


@app.post("/media/attest")
async def attest_transcript(transcript_text: str, privacy_mode: PrivacyMode = PrivacyMode.PROTECTED) -> dict:
    return await get_app_service().ingest_transcript(transcript_text, privacy_mode)


@app.post("/ui/attest")
async def ui_attest_transcript(
    request: Request,
    transcript_text: str = Form(...),
    privacy_mode: PrivacyMode = Form(default=PrivacyMode.PROTECTED),
) -> RedirectResponse:
    user = _require_ui_user(request)
    await get_app_service().ingest_transcript(
        transcript_text,
        privacy_mode,
        source_kind="signed_in_transcript",
        notary_id=None,
        submitter_identity=str(user.get("email") or user.get("id")),
    )
    return RedirectResponse("/app", status_code=303)


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
    request: Request,
    amount_usdc: float = Form(...),
    description: str = Form(...),
) -> RedirectResponse:
    _require_ui_user(request)
    await get_app_service().create_payment_link(
        QevorpayPaymentLinkRequest(amount_usdc=amount_usdc, description=description)
    )
    return RedirectResponse("/app", status_code=303)


@app.post("/webhooks/qevorpay/settlement")
async def qevorpay_settlement_webhook(request: Request) -> dict:
    """Receives signed settlement notifications from Qevor's batch executor.

    Qevor posts here once it has independently verified NOTARY's EIP-712
    attestation, looked up the on-chain AttestationRegistry record, and either
    executed or rejected the batch. We HMAC-verify the body against
    QEVORPAY_WEBHOOK_SECRET (matching Qevor's outbound signer), then persist
    the event so the ledger reflects real settlement state instead of the
    optimistic 'queued' we wrote when we kicked off the batch.
    """
    service = get_app_service()
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not service.qevorpay.verify_webhook(headers=headers, body=body):
        raise HTTPException(status_code=401, detail="invalid_webhook_signature")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid_json")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload_must_be_object")

    settlement_id = (
        payload.get("batch_payment_id")
        or payload.get("batchPaymentId")
        or payload.get("batch_request_id")
        or payload.get("batchRequestId")
        or payload.get("reference")
        or f"qevor_settlement_{int(time.time() * 1000)}"
    )
    record = {
        "id": settlement_id,
        "receivedAt": int(time.time()),
        "event": payload,
    }
    service.store.put("qevor_settlements", str(settlement_id), record)

    # Reconcile the local payment record. Qevor's executor identifies the batch
    # via batch_request_id which we stored as the payment reference when
    # _create_supabase_batch returned. If we find a matching payment row,
    # update its status so the dashboard shows the final outcome.
    payment_ref = (
        payload.get("batch_request_id")
        or payload.get("batchRequestId")
        or payload.get("reference")
    )
    if payment_ref:
        existing = service.store.get("payments", str(payment_ref))
        if existing:
            existing["status"] = payload.get("status") or payload.get("state") or existing.get("status")
            existing["settlement"] = payload
            service.store.put("payments", str(payment_ref), existing)
        service.mark_case_funded_from_qevor(str(payment_ref), payload)
    return {"ok": True, "settlementId": settlement_id}


@app.get("/state")
async def state(request: Request) -> dict:
    _require_ui_user(request)
    return get_app_service().dashboard_state()
