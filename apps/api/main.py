from __future__ import annotations

import base64
import hashlib
import hmac
import json
from functools import lru_cache
from pathlib import Path
import time
from urllib.parse import quote
from html import escape

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.api.dashboard import (
    render_case_evidence,
    render_landing,
    render_public_ledger,
    render_sign_in,
    render_workspace,
    render_user_profile,
)
from notary.app_service import NotaryAppService
from notary.config import get_settings
from notary.models.schemas import (
    DisclosureLevel,
    Observation,
    PrivacyMode,
    EscrowPaymentLinkRequest,
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


def _ui_error(exc: Exception) -> str:
    text = str(exc)
    if "NOTARY_EXISTS" in text:
        return "This NOTARY is already registered on Arc. You can keep using this workspace."
    if "ARC RPC error" in text:
        return "Arc testnet rejected that transaction. Check the configured identity and try again."
    if "Circle CLI" in text:
        return "Circle operator session is not ready on this machine. Users can still create NOTARY escrow cases."
    if len(text) > 180:
        return f"{text[:177]}..."
    return text


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
    phone: str | None = None,
    message: str | None = None,
    error: str | None = None,
    tab: str | None = None,
    prefill: str | None = None,
) -> HTMLResponse:
    service = get_app_service()
    return HTMLResponse(
        render_sign_in(
            auth=service.auth_status(),
            email=email,
            phone=phone,
            message=message,
            error=error,
            tab=tab,
            prefill=prefill,
        )
    )


@app.get("/ledger", response_class=HTMLResponse)
async def public_ledger_page(request: Request) -> HTMLResponse:
    service = get_app_service()
    return HTMLResponse(render_public_ledger(service.dashboard_state(), _read_session(request)))


@app.get("/p/{username}", response_class=HTMLResponse)
@app.get("/profile/{username}", response_class=HTMLResponse)
async def user_profile_page(
    request: Request,
    username: str,
    error: str | None = None,
    message: str | None = None,
) -> HTMLResponse:
    normalized = username.strip().lower()
    if normalized.startswith("@"):
        normalized = normalized[1:]
        
    service = get_app_service()
    profile_data = service.store.get("profiles", normalized)
    if not profile_data:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    profile = await service.get_or_create_user_profile(normalized)
    transactions = service.get_user_transactions(normalized)
    
    return HTMLResponse(
        render_user_profile(
            profile,
            transactions,
            _read_session(request),
            error=error,
            message=message,
        )
    )


@app.get("/profile", response_class=HTMLResponse)
async def own_profile_redirect(request: Request) -> RedirectResponse:
    user = _get_user_from_session(request)
    if not user:
        return RedirectResponse("/login?error=Please%20sign%20in%20to%20view%20your%20profile.", status_code=303)
    service = get_app_service()
    profile = await service.get_or_create_user_profile(user.get("email") or user.get("id") or "")
    username = profile.get("username", "unknown")
    return RedirectResponse(f"/profile/{username}", status_code=303)



@app.get("/app", response_class=HTMLResponse)
async def workspace(
    request: Request,
    error: str | None = None,
    message: str | None = None,
    circle_request_id: str | None = None,
) -> HTMLResponse:
    user = _read_session(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    service = get_app_service()
    try:
        profile = await service.get_or_create_user_profile(user.get("email") or user.get("id") or "")
    except Exception:
        profile = {
            "username": "unknown",
            "wallet": "0x0000000000000000000000000000000000000000",
            "balance": "0.00"
        }
    state = _user_state(service.dashboard_state(), user)
    display_error = _ui_error(RuntimeError(error)) if error else None
    return HTMLResponse(
        render_workspace(
            state,
            user,
            profile,
            error=display_error,
            message=message,
            circle_request_id=circle_request_id,
        )
    )


@app.post("/ui/wallet/send")
async def ui_wallet_send(
    request: Request,
    recipient: str = Form(...),
    amount: float = Form(...),
    redirect_to: str | None = Form(None),
) -> RedirectResponse:
    user = _require_ui_user(request)
    service = get_app_service()
    
    username = (user.get("email") or user.get("id") or "").split("@")[0].lower()
    success_redirect = "/app?message=USDC%20transfer%20successful!"
    error_redirect = "/app?error="
    
    if redirect_to == "profile":
        success_redirect = f"/profile/{username}?message=USDC%20transfer%20successful!"
        error_redirect = f"/profile/{username}?error="

    try:
        await service.send_user_funds(
            sender_email_or_id=user.get("email") or user.get("id") or "",
            to_identity=recipient,
            amount_usdc=amount,
        )
    except Exception as exc:
        return RedirectResponse(f"{error_redirect}{quote(_ui_error(exc))}", status_code=303)
    return RedirectResponse(success_redirect, status_code=303)


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
        return RedirectResponse(f"/app?error={quote(_ui_error(exc))}", status_code=303)
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
            f"/cases/{case_id}/evidence?token={quote(token or '')}&error={quote(_ui_error(exc))}",
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


@app.post("/auth/login")
async def auth_login(
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    service = get_app_service()
    try:
        user = await service.authenticate_user(username, password)
        user_payload = {
            "id": user["username"],
            "email": f"{user['username']}@notary.local",
            "role": "user",
        }
        cookie = _sign_session(
            {
                "user": user_payload,
                "expiresAt": int(time.time()) + 24 * 3600,
            }
        )
    except Exception as exc:
        error_text = str(exc)
        # If the profile exists but has no password, redirect to register tab
        # so they can set a password without confusion
        if "has no password" in error_text or "register first" in error_text.lower():
            return RedirectResponse(
                f"/login?tab=register&prefill={quote(username)}"
                f"&error={quote('Your account was created without a password. Please set one using the Register tab below.')}",
                status_code=303,
            )
        return RedirectResponse(f"/login?error={quote(_ui_error(exc))}", status_code=303)
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


@app.post("/auth/register")
async def auth_register(
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
) -> RedirectResponse:
    if password != confirm_password:
        return RedirectResponse("/login?error=Passwords%20do%20not%20match.", status_code=303)
    service = get_app_service()
    try:
        user = await service.register_user(username, password)
        user_payload = {
            "id": user["username"],
            "email": f"{user['username']}@notary.local",
            "role": "user",
        }
        cookie = _sign_session(
            {
                "user": user_payload,
                "expiresAt": int(time.time()) + 24 * 3600,
            }
        )
    except Exception as exc:
        return RedirectResponse(f"/login?error={quote(_ui_error(exc))}", status_code=303)
    response = RedirectResponse("/app?message=Account%20created%20successfully!", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        cookie,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=24 * 3600,
    )
    return response



@app.post("/auth/dev-login")
async def auth_dev_login(
    email: str | None = Form(None),
    phone: str | None = Form(None),
) -> RedirectResponse:
    settings = get_settings()
    if settings.notary_env == "production":
        raise HTTPException(status_code=404, detail="local sandbox login is disabled")
    
    identity = email or phone
    if not identity:
        return RedirectResponse("/login?error=Email%20or%20phone%20number%20is%20required.", status_code=303)
        
    user_payload = {
        "id": identity,
        "email": identity,
        "role": "local_sandbox",
    }
    if phone:
        user_payload["phone"] = phone
        
    cookie = _sign_session(
        {
            "user": user_payload,
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


@app.post("/ui/profile/update-username")
async def ui_update_username(
    request: Request,
    new_username: str = Form(...),
) -> RedirectResponse:
    user = _require_ui_user(request)
    current_username = user.get("id") or ""
    service = get_app_service()
    try:
        updated_profile = await service.change_username(current_username, new_username)
        user_payload = {
            "id": updated_profile["username"],
            "email": f"{updated_profile['username']}@notary.local",
            "role": "user",
        }
        cookie = _sign_session(
            {
                "user": user_payload,
                "expiresAt": int(time.time()) + 24 * 3600,
            }
        )
    except Exception as exc:
        return RedirectResponse(f"/profile/{current_username}?error={quote(_ui_error(exc))}", status_code=303)
        
    response = RedirectResponse(f"/profile/{new_username}?message=Username%20changed%20successfully!", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        cookie,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=24 * 3600,
    )
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


@app.get("/coverage")
async def feature_coverage() -> dict:
    return await get_app_service().feature_coverage()


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


@app.post("/commerce/x402/data")
async def x402_paid_data(
    description: str = Form(...),
    service_url: str = Form(...),
    max_usdc: float = Form(default=0.01),
    wallet_id: str | None = Form(default=None),
) -> dict:
    return await get_app_service().paid_data_service_request(
        description=description,
        service_url=service_url,
        max_usdc=max_usdc,
        wallet_id=wallet_id or None,
    )


@app.post("/commerce/reasoning/pay-to-peek")
async def reasoning_pay_to_peek(
    ruling_id: str = Form(...),
    buyer_identity: str = Form(...),
    amount_usdc: float = Form(...),
    tx_hash: str | None = Form(default=None),
) -> dict:
    return await get_app_service().create_reasoning_pay_to_peek(
        ruling_id=ruling_id,
        buyer_identity=buyer_identity,
        amount_usdc=amount_usdc,
        tx_hash=tx_hash or None,
    )


@app.post("/markets/predictions")
async def create_prediction(
    question: str = Form(...),
    probability_bps: int = Form(...),
    horizon: str = Form(...),
    rationale: str = Form(...),
    notary_id: str | None = Form(default=None),
) -> dict:
    return await get_app_service().create_prediction(
        question=question,
        probability_bps=probability_bps,
        horizon=horizon,
        rationale=rationale,
        notary_id=notary_id or None,
    )


@app.post("/commerce/micro-shares")
async def buy_micro_share(
    prediction_id: str = Form(...),
    buyer_identity: str = Form(...),
    amount_usdc: float = Form(...),
    tx_hash: str | None = Form(default=None),
) -> dict:
    return await get_app_service().buy_micro_share(
        prediction_id=prediction_id,
        buyer_identity=buyer_identity,
        amount_usdc=amount_usdc,
        tx_hash=tx_hash or None,
    )


@app.post("/agents/karma/checkpoint")
async def karma_checkpoint(
    notary_id: str = Form(...),
    delta: int = Form(...),
    reason: str = Form(...),
    evidence_ref: str | None = Form(default=None),
) -> dict:
    return await get_app_service().record_karma_checkpoint(
        notary_id=notary_id,
        delta=delta,
        reason=reason,
        evidence_ref=evidence_ref or None,
    )


@app.post("/agents/identity/erc8004")
async def erc8004_identity(
    notary_id: str = Form(...),
    service_endpoint: str = Form(...),
    metadata_uri: str | None = Form(default=None),
) -> dict:
    return await get_app_service().register_agent_identity_erc8004(
        notary_id=notary_id,
        service_endpoint=service_endpoint,
        metadata_uri=metadata_uri or None,
    )


@app.post("/agents/replicate")
async def replicate_notary(
    parent_notary_id: str = Form(...),
    mutation_prompt: str = Form(...),
    min_karma: int = Form(default=0),
) -> dict:
    return await get_app_service().replicate_notary(
        parent_notary_id=parent_notary_id,
        mutation_prompt=mutation_prompt,
        min_karma=min_karma,
    )


@app.post("/treasury/usyc/intents")
async def usyc_intent(
    notary_id: str = Form(...),
    amount_usdc: float = Form(...),
    tx_hash: str | None = Form(default=None),
) -> dict:
    return await get_app_service().create_usyc_intent(
        notary_id=notary_id,
        amount_usdc=amount_usdc,
        tx_hash=tx_hash or None,
    )


@app.post("/markets/arbitrage/analyze")
async def arbitrage_analyze(payload: dict = Body(...)) -> dict:
    return await get_app_service().analyze_arbitrage(
        base_asset=str(payload.get("base_asset") or payload.get("baseAsset") or "USDC"),
        quote_asset=str(payload.get("quote_asset") or payload.get("quoteAsset") or "USD"),
        amount_usdc=float(payload.get("amount_usdc") or payload.get("amountUSDC") or 0),
        venues=list(payload.get("venues") or []),
        max_slippage_bps=int(payload.get("max_slippage_bps") or payload.get("maxSlippageBps") or 50),
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
        return RedirectResponse(f"/app?error={quote(_ui_error(exc))}", status_code=303)
    return RedirectResponse("/app", status_code=303)


@app.post("/ui/circle/login/init")
async def ui_circle_login_init(request: Request, email: str = Form(...)) -> RedirectResponse:
    _require_ui_user(request)
    try:
        result = await get_app_service().circle_login_init(email)
    except Exception as exc:
        return RedirectResponse(f"/app?error={quote(_ui_error(exc))}", status_code=303)
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
        return RedirectResponse(f"/app?error={quote(_ui_error(exc))}", status_code=303)
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
        return RedirectResponse(f"/app?error={quote(_ui_error(exc))}", status_code=303)
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
@app.get("/request/{reference}", response_class=HTMLResponse)
async def local_payment_page(reference: str, error: str | None = None) -> HTMLResponse:
    service = get_app_service()
    case = next((item for item in service.store.list("cases") if item.get("escrow_payment_reference") == reference), None)
    
    amount = "n/a"
    description = "NOTARY Escrow Deposit"
    payer = "@me"
    payee = "@someone"
    status = "awaiting_funding"
    payer_wallet = ""
    reserve_wallet = ""
    
    if case:
        amount = f"{case.get('amount_usdc')} USDC"
        description = case.get("instruction")
        payer = case.get("payer_identity")
        payee = case.get("payee_identity")
        status = case.get("status")
        metadata = case.get("metadata", {}) or {}
        payer_wallet = str(metadata.get("payerWallet") or "")
        reserve_wallet = str(metadata.get("executorEscrowAddress") or "")
    else:
        payments = service.list_bucket("payments")
        payment = next((item for item in payments if item.get("reference") == reference), None)
        if payment:
            request = payment.get("request", {})
            amount = f"{request.get('amount_usdc', request.get('amountUSDC', 'n/a'))} USDC"
            description = request.get("description", "NOTARY payment")
            status = payment.get("status", "created")
            payer = request.get("payer_identity") or payer
            payee = request.get("payee_identity") or payee
    error_html = (
        f'<div style="margin:0 0 16px;padding:12px;border-left:4px solid #ef4444;background:rgba(239,68,68,0.12);color:#fecaca;text-align:left;border-radius:10px;">{escape(error)}</div>'
        if error
        else ""
    )

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Authorize Escrow · NOTARY</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;800&display=swap" rel="stylesheet" />
            <style>
              :root {{
                --bg: #0B0F19;
                --surface: rgba(17, 24, 39, 0.7);
                --primary: #6366f1;
                --primary-glow: rgba(99, 102, 241, 0.15);
                --green: #10b981;
                --green-glow: rgba(16, 185, 129, 0.2);
                --text: #f3f4f6;
                --muted: #9ca3af;
                --line: rgba(255, 255, 255, 0.08);
              }}
              body {{
                font-family: 'Inter', system-ui, sans-serif;
                margin: 0;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                background-color: var(--bg);
                background-image: 
                  radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                  radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
                color: var(--text);
                padding: 16px;
              }}
              main {{
                width: min(540px, 100%);
                background: var(--surface);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid var(--line);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-align: center;
              }}
              .badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: var(--primary-glow);
                border: 1px solid rgba(99, 102, 241, 0.3);
                color: #818cf8;
                padding: 6px 14px;
                border-radius: 9999px;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 24px;
              }}
              h1 {{
                font-family: 'Outfit', sans-serif;
                font-size: 32px;
                font-weight: 800;
                margin: 0 0 8px;
                color: #fff;
                letter-spacing: -0.5px;
              }}
              .amount-display {{
                font-family: 'Outfit', sans-serif;
                font-size: 48px;
                font-weight: 800;
                color: var(--green);
                text-shadow: 0 0 20px var(--green-glow);
                margin: 18px 0;
              }}
              .contract-details {{
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--line);
                border-radius: 16px;
                padding: 20px;
                text-align: left;
                margin-bottom: 28px;
              }}
              .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                font-size: 14px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
              }}
              .detail-row:last-child {{
                border-bottom: none;
              }}
              .detail-label {{
                color: var(--muted);
              }}
              .detail-value {{
                color: #fff;
                font-weight: 600;
              }}
              .instruction-box {{
                margin-top: 12px;
                padding: 12px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                font-size: 14px;
                color: var(--text);
                line-height: 1.5;
                border-left: 3px solid var(--primary);
              }}
              button {{
                display: block;
                width: 100%;
                background: var(--green);
                color: #0b0f19;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 12px var(--green-glow);
              }}
              button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
                background: #34d399;
              }}
              button:active {{
                transform: translateY(0);
              }}
              .cancel-link {{
                display: inline-block;
                margin-top: 20px;
                color: var(--muted);
                text-decoration: none;
                font-size: 14px;
                font-weight: 500;
                transition: color 0.15s ease;
              }}
              .cancel-link:hover {{
                color: #fff;
              }}
            </style>
          </head>
          <body>
            <main>
              <div class="badge">
                <span>🔒 SECURE ESCROW AGENT</span>
              </div>
              <h1>Fund on Arc</h1>
              <p style="color: var(--muted); margin: 0 0 24px; font-size: 15px;">Send the exact USDC amount on Arc, then paste the transaction hash. NOTARY unlocks evidence only after RPC verification.</p>
              {error_html}
              
              <div class="amount-display">{amount}</div>
              
              <div class="contract-details">
                <div class="detail-row">
                  <span class="detail-label">Payer Account</span>
                  <span class="detail-value">{escape(payer)}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Payee Account</span>
                  <span class="detail-value">{escape(payee)}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Escrow Reference</span>
                  <span class="detail-value" style="font-family: monospace; font-size: 12px;">{escape(reference[:18])}...</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">From Wallet</span>
                  <span class="detail-value" style="font-family: monospace; font-size: 12px;">{escape(payer_wallet or 'payer wallet unavailable')}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Reserve Wallet</span>
                  <span class="detail-value" style="font-family: monospace; font-size: 12px;">{escape(reserve_wallet or 'reserve wallet unavailable')}</span>
                </div>
                <div style="margin-top: 14px; font-size: 13px; color: var(--muted); font-weight: 500;">OBLIGATION STATEMENT:</div>
                <div class="instruction-box">
                  "{escape(description)}"
                </div>
              </div>
              
              <form method="post">
                <input name="tx_hash" required placeholder="Arc transaction hash: 0x..." style="box-sizing:border-box;width:100%;margin-bottom:12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,0.04);color:var(--text);padding:14px;font-family:monospace;" />
                <button type="submit">Verify Arc Funding</button>
              </form>
              
              <a href="/app" class="cancel-link">Return to Console</a>
            </main>
          </body>
        </html>
        """
    )


@app.post("/pay/{reference}")
@app.post("/request/{reference}")
async def local_payment_submit(
    reference: str,
    tx_hash: str = Form(...),
):
    service = get_app_service()
    try:
        await service.verify_arc_funding_and_mark_case(reference, tx_hash.strip())
    except Exception as exc:
        return RedirectResponse(
            f"/request/{quote(reference)}?error={quote(_ui_error(exc))}",
            status_code=303,
        )
    return RedirectResponse("/app?message=Arc%20funding%20verified%20successfully!", status_code=303)


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


@app.post("/escrow/payment-link")
async def create_payment_link(request: EscrowPaymentLinkRequest) -> dict:
    try:
        return await get_app_service().create_payment_link(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        EscrowPaymentLinkRequest(amount_usdc=amount_usdc, description=description)
    )
    return RedirectResponse("/app", status_code=303)


@app.post("/webhooks/escrow/settlement")
async def escrow_settlement_webhook(request: Request) -> dict:
    """Receives signed settlement notifications from NOTARY's batch executor.

    The executor posts here once it has independently verified NOTARY's EIP-712
    attestation, looked up the on-chain AttestationRegistry record, and either
    executed or rejected the batch. We HMAC-verify the body against
    NOTARY_ESCROW_WEBHOOK_SECRET, then persist the event so the ledger reflects
    real settlement state instead of the optimistic 'queued' we wrote when we
    kicked off the batch.
    """
    service = get_app_service()
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not service.escrow.verify_webhook(headers=headers, body=body):
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
        or f"notary_settlement_{int(time.time() * 1000)}"
    )
    record = {
        "id": settlement_id,
        "receivedAt": int(time.time()),
        "event": payload,
    }
    service.store.put("notary_settlements", str(settlement_id), record)

    # Reconcile the local payment record. The executor identifies the batch
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
        funding_tx = (
            payload.get("arcTxHash")
            or payload.get("txHash")
            or payload.get("transactionHash")
            or payload.get("tx_hash")
        )
        if funding_tx:
            await service.verify_arc_funding_and_mark_case(str(payment_ref), str(funding_tx))
    return {"ok": True, "settlementId": settlement_id}


@app.get("/state")
async def state(request: Request) -> dict:
    _require_ui_user(request)
    return get_app_service().dashboard_state()
