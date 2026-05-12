from __future__ import annotations

import uuid
import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.config import is_secret_configured, settings
from app.database import get_db
from app.models.db import (
    UserModel,
    AuthOtpModel,
    AuthSessionModel,
    SessionModel,
    AnalysisJobModel,
    AIUsageLedgerModel,
    PhotoModel,
    AnalysisResultModel,
    RecommendationModel,
    ColorPaletteModel,
)
from app.models.schemas import (
    AuthResponse,
    AIUsageLedgerResponse,
    CatalogImportResponse,
    CatalogStatusResponse,
    CatalogSyncResponse,
    ClaimSessionRequest,
    ClaimSessionResponse,
    CostPolicyResponse,
    FitProfile,
    Gender,
    LoginRequest,
    Marketplace,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    ProductRecommendationResponse,
    SessionCreate,
    SessionResponse,
    AnalysisResponse,
    AnalysisJobResponse,
    RecommendationCategory,
    StyleProfile,
    UserProfile,
    UserSessionsResponse,
    UserSessionSummary,
    VisualAnalysisKind,
    VisualAnalysisResponse,
)
from app.services.catalog_importer import normalize_feed_products, parse_feed_rows
from app.services.analyzer import analyze_photos
from app.services.analysis_jobs import nudge_analysis_worker
from app.services.cost_ledger import (
    begin_usage_collection,
    end_usage_collection,
    persist_usage_events,
    usage_ledger_for_job,
    usage_ledger_for_user,
)
from app.services.emailer import email_delivery_configured, send_otp_email, send_result_email
from app.services.openai_image import generate_visual_analysis
from app.services.marketplace_adapters import (
    FlipkartAffiliateAdapter,
    write_cached_provider_products,
)
from app.services.product_recommender import (
    catalog_counts,
    clear_catalog_cache,
    recommend_products,
)
from app.services.recommender import get_recommendations
from app.services.storage import (
    download_bytes_from_supabase,
    ensure_local_file,
    mirror_local_file,
    safe_filename,
    save_bytes,
    storage_object_path,
    supabase_storage_configured,
)
from app.services.visual_prompts import PROCESS_BY_KIND, PROMPT_VERSION
from app.services.rule_engine import rule_engine
from app.database import is_db_available

router = APIRouter()

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory fallback when DB is unavailable (mock mode)
_memory_store: dict[str, dict] = {}
_memory_jobs: dict[str, dict] = {}
_memory_users: dict[str, dict] = {}
_memory_otps: dict[str, list[dict]] = {}
_memory_auth_sessions: dict[str, dict] = {}


def _username_from_identity(display_name: str, email: str | None = None) -> str:
    source = email.split("@", 1)[0] if email else display_name
    username = re.sub(r"[^a-z0-9]+", "-", source.strip().lower()).strip("-")
    return username or "aurafit-user"


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return normalized


def _hash_secret(value: str) -> str:
    payload = f"{settings.auth_token_secret}:{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _new_otp_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def _new_session_token() -> str:
    return secrets.token_urlsafe(40)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _user_payload(user: UserModel) -> UserProfile:
    return UserProfile(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        created_at=user.created_at,
    )


async def _get_user_by_auth_token(
    token: str | None,
    db: AsyncSession | None,
) -> UserModel | dict | None:
    if not token:
        return None

    now = datetime.now(timezone.utc)
    token_hash = _hash_secret(token)

    if db is None or not is_db_available():
        session_data = _memory_auth_sessions.get(token_hash)
        if not session_data:
            return None
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if expires_at <= now or session_data.get("revoked_at"):
            return None
        return _memory_users.get(session_data["user_id"])

    result = await db.execute(
        select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
    )
    auth_session = result.scalar_one_or_none()
    if not auth_session or auth_session.revoked_at or auth_session.expires_at <= now:
        return None

    auth_session.last_seen_at = now
    result = await db.execute(select(UserModel).where(UserModel.id == auth_session.user_id))
    return result.scalar_one_or_none()


async def _create_auth_session(
    user: UserModel | dict,
    db: AsyncSession | None,
) -> tuple[str, datetime]:
    token = _new_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.auth_session_ttl_days)
    token_hash = _hash_secret(token)

    if db is None or not is_db_available():
        user_id = user["id"] if isinstance(user, dict) else str(user.id)
        _memory_auth_sessions[token_hash] = {
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
            "revoked_at": None,
        }
        return token, expires_at

    db.add(AuthSessionModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    ))
    await db.flush()
    return token, expires_at


async def _find_or_create_user_by_email(
    email: str,
    display_name: str | None,
    db: AsyncSession | None,
) -> UserModel | dict:
    now = datetime.now(timezone.utc)
    name = (display_name or "").strip() or email.split("@", 1)[0].replace(".", " ").title()
    username = _username_from_identity(name, email)

    if db is None or not is_db_available():
        existing = next(
            (user for user in _memory_users.values() if user.get("email") == email),
            None,
        )
        if existing is None:
            user_id = str(uuid.uuid4())
            existing = {
                "id": user_id,
                "username": username,
                "display_name": name,
                "email": email,
                "created_at": now.isoformat(),
            }
            _memory_users[user_id] = existing
        else:
            existing["display_name"] = name or existing["display_name"]
            existing["email"] = email
        return existing

    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

    if user is None:
        user = UserModel(
            username=username,
            display_name=name,
            email=email,
            email_verified_at=now,
            last_seen_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        user.display_name = name or user.display_name
        user.email = email
        user.email_verified_at = user.email_verified_at or now
        user.last_seen_at = now

    return user


async def _enforce_analysis_quota(
    user: UserModel | dict,
    db: AsyncSession | None,
):
    limit = settings.analysis_limit_per_user_per_day
    if limit <= 0:
        return

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    user_id = user["id"] if isinstance(user, dict) else str(user.id)

    if db is None or not is_db_available():
        used = sum(
            1
            for item in _memory_store.values()
            if (item.get("user") or {}).get("id") == user_id
            and datetime.fromisoformat(item.get("created_at", now.isoformat())) >= day_start
        )
    else:
        result = await db.execute(
            select(func.count())
            .select_from(SessionModel)
            .where(
                SessionModel.user_id == uuid.UUID(user_id),
                SessionModel.created_at >= day_start,
            )
        )
        used = result.scalar_one()

    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily analysis limit reached ({limit}/day). Try again tomorrow.",
        )


def _user_id_string(user: UserModel | dict) -> str:
    return user["id"] if isinstance(user, dict) else str(user.id)


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def _daily_ai_cost_for_user(
    user_id: str,
    db: AsyncSession | None,
) -> float:
    if db is None or not is_db_available():
        return 0.0

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(
                        AIUsageLedgerModel.actual_cost_usd,
                        AIUsageLedgerModel.estimated_cost_usd,
                    )
                ),
                0,
            )
        )
        .select_from(AIUsageLedgerModel)
        .where(
            AIUsageLedgerModel.user_id == uuid.UUID(user_id),
            AIUsageLedgerModel.created_at >= _today_start(),
        )
    )
    return float(result.scalar_one() or 0)


async def _enforce_daily_ai_cost_budget(
    user: UserModel | dict,
    db: AsyncSession | None,
):
    limit = settings.max_daily_ai_cost_per_user_usd
    if limit <= 0:
        return

    used = await _daily_ai_cost_for_user(_user_id_string(user), db)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI credit limit reached (${limit:.2f}/day). Try again tomorrow.",
        )


async def _enforce_visual_generation_quota(
    user: UserModel | dict,
    db: AsyncSession | None,
):
    limit = settings.max_visual_generations_per_user_per_day
    if limit <= 0:
        return

    user_id = _user_id_string(user)
    if db is None or not is_db_available():
        return

    result = await db.execute(
        select(func.count())
        .select_from(AIUsageLedgerModel)
        .where(
            AIUsageLedgerModel.user_id == uuid.UUID(user_id),
            AIUsageLedgerModel.created_at >= _today_start(),
            AIUsageLedgerModel.operation.in_(["visual_analysis", "session_visual_analysis"]),
        )
    )
    used = result.scalar_one() or 0
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily visual board limit reached ({limit}/day). Try again tomorrow.",
        )


def _optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _build_fit_profile(
    height_cm: str | None = None,
    weight_kg: str | None = None,
    shirt_size: str | None = None,
    bottom_size: str | None = None,
    shoe_size: str | None = None,
    preferred_fit: str | None = None,
    pincode: str | None = None,
) -> FitProfile:
    return FitProfile(
        height_cm=_optional_float(height_cm),
        weight_kg=_optional_float(weight_kg),
        shirt_size=shirt_size or None,
        bottom_size=bottom_size or None,
        shoe_size=shoe_size or None,
        preferred_fit=preferred_fit or None,
        pincode=pincode or None,
    )


@router.post("/auth/otp/request", response_model=OtpRequestResponse)
async def request_login_otp(payload: OtpRequest, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    display_name = (payload.display_name or "").strip() or None
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_otp_ttl_minutes)
    window_start = now - timedelta(minutes=settings.auth_otp_ttl_minutes)
    code = _new_otp_code()
    otp_record: AuthOtpModel | None = None

    if db is None or not is_db_available():
        recent = [
            item for item in _memory_otps.get(email, [])
            if datetime.fromisoformat(item["created_at"]) >= window_start
        ]
        if len(recent) >= settings.auth_otp_request_limit:
            raise HTTPException(status_code=429, detail="Too many OTP requests. Try again shortly.")

        _memory_otps.setdefault(email, []).append({
            "code_hash": _hash_secret(code),
            "display_name": display_name,
            "attempts": 0,
            "expires_at": expires_at.isoformat(),
            "consumed_at": None,
            "created_at": now.isoformat(),
        })
    else:
        result = await db.execute(
            select(AuthOtpModel).where(
                AuthOtpModel.email == email,
                AuthOtpModel.created_at >= window_start,
            )
        )
        recent = result.scalars().all()
        if len(recent) >= settings.auth_otp_request_limit:
            raise HTTPException(status_code=429, detail="Too many OTP requests. Try again shortly.")

        otp_record = AuthOtpModel(
            email=email,
            display_name=display_name,
            code_hash=_hash_secret(code),
            expires_at=expires_at,
        )
        db.add(otp_record)
        await db.commit()

    try:
        delivery = send_otp_email(email, code)
    except Exception as exc:
        if db is None or not is_db_available():
            if _memory_otps.get(email):
                _memory_otps[email].pop()
        elif otp_record is not None:
            await db.delete(otp_record)
            await db.commit()
        raise HTTPException(
            status_code=503,
            detail=f"OTP email delivery is not configured: {exc}",
        ) from exc
    return OtpRequestResponse(
        status="sent",
        email=email,
        expires_in_seconds=settings.auth_otp_ttl_minutes * 60,
        delivery=delivery,
        dev_otp=code if delivery == "dev_console" and settings.auth_dev_return_otp else None,
    )


@router.post("/auth/otp/verify", response_model=AuthResponse)
async def verify_login_otp(
    payload: OtpVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = _normalize_email(payload.email)
    code = re.sub(r"\D", "", payload.otp_code or "")
    if len(code) != 6:
        raise HTTPException(status_code=400, detail="Enter the 6-digit OTP")

    now = datetime.now(timezone.utc)
    display_name = (payload.display_name or "").strip() or None

    if db is None or not is_db_available():
        candidates = [
            item for item in _memory_otps.get(email, [])
            if not item.get("consumed_at")
        ]
        otp = candidates[-1] if candidates else None
        if not otp:
            raise HTTPException(status_code=400, detail="Request a fresh OTP first")
        if datetime.fromisoformat(otp["expires_at"]) <= now:
            raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
        if otp["attempts"] >= settings.auth_otp_max_attempts:
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new code.")
        if otp["code_hash"] != _hash_secret(code):
            otp["attempts"] += 1
            raise HTTPException(status_code=400, detail="Incorrect OTP")

        otp["consumed_at"] = now.isoformat()
        user = await _find_or_create_user_by_email(email, display_name or otp.get("display_name"), db)
        session_token, expires_at = await _create_auth_session(user, db)
        user_profile = UserProfile(**user)
    else:
        result = await db.execute(
            select(AuthOtpModel)
            .where(AuthOtpModel.email == email, AuthOtpModel.consumed_at.is_(None))
            .order_by(AuthOtpModel.created_at.desc())
        )
        otp = result.scalars().first()
        if not otp:
            raise HTTPException(status_code=400, detail="Request a fresh OTP first")
        if otp.expires_at <= now:
            raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
        if otp.attempts >= settings.auth_otp_max_attempts:
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new code.")
        if otp.code_hash != _hash_secret(code):
            otp.attempts += 1
            await db.commit()
            raise HTTPException(status_code=400, detail="Incorrect OTP")

        otp.consumed_at = now
        user = await _find_or_create_user_by_email(email, display_name or otp.display_name, db)
        session_token, expires_at = await _create_auth_session(user, db)
        await db.commit()
        await db.refresh(user)
        user_profile = _user_payload(user)

    response.set_cookie(
        key="aurafit_session",
        value=session_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_days * 24 * 60 * 60,
    )
    return AuthResponse(
        status="complete",
        user=user_profile,
        session_token=session_token,
        expires_at=expires_at,
    )


@router.get("/auth/me", response_model=AuthResponse)
async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    token = _extract_bearer_token(authorization)
    user = await _get_user_by_auth_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")

    if isinstance(user, dict):
        return AuthResponse(status="complete", user=UserProfile(**user))
    return AuthResponse(status="complete", user=_user_payload(user))


@router.post("/auth/logout")
async def logout_user(
    response: Response,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    token = _extract_bearer_token(authorization)
    if token:
        token_hash = _hash_secret(token)
        if db is None or not is_db_available():
            if token_hash in _memory_auth_sessions:
                _memory_auth_sessions[token_hash]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        else:
            result = await db.execute(
                select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
            )
            auth_session = result.scalar_one_or_none()
            if auth_session:
                auth_session.revoked_at = datetime.now(timezone.utc)
                await db.commit()

    response.delete_cookie("aurafit_session")
    return {"status": "complete"}


@router.post("/auth/login", response_model=AuthResponse)
async def login_user(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    display_name = payload.display_name.strip()
    email = payload.email.strip().lower() if payload.email else None
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    username = _username_from_identity(display_name, email)

    if db is None or not is_db_available():
        existing = next(
            (
                user
                for user in _memory_users.values()
                if user["username"] == username or (email and user.get("email") == email)
            ),
            None,
        )
        if existing is None:
            user_id = str(uuid.uuid4())
            existing = {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "email": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _memory_users[user_id] = existing
        else:
            existing["display_name"] = display_name
            existing["email"] = email or existing.get("email")

        return AuthResponse(status="complete", user=UserProfile(**existing))

    result = await db.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    if user is None and email:
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = UserModel(username=username, display_name=display_name, email=email)
        db.add(user)
        await db.flush()
    else:
        user.display_name = display_name
        if email:
            user.email = email
        user.last_seen_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)
    return AuthResponse(status="complete", user=_user_payload(user))


@router.post("/sessions/{job_id}/claim", response_model=ClaimSessionResponse)
async def claim_session(
    job_id: str,
    payload: ClaimSessionRequest,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    profile_name = (payload.profile_name or "").strip()

    try:
        session_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    token = payload.session_token or _extract_bearer_token(authorization)
    token_user = await _get_user_by_auth_token(token, db)

    user_uuid: uuid.UUID | None = None
    if payload.user_id:
        try:
            user_uuid = uuid.UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
    elif token_user:
        user_uuid = uuid.UUID(token_user["id"] if isinstance(token_user, dict) else str(token_user.id))
    else:
        raise HTTPException(status_code=401, detail="Sign in before saving this profile")

    if settings.auth_require_token_for_claim and not token_user:
        raise HTTPException(status_code=401, detail="A verified session token is required")

    if token_user:
        token_user_id = token_user["id"] if isinstance(token_user, dict) else str(token_user.id)
        if str(user_uuid) != token_user_id:
            raise HTTPException(status_code=403, detail="Session token does not match this user")

    if db is None or not is_db_available():
        session_data = _memory_store.get(job_id)
        user_data = _memory_users.get(str(user_uuid))
        if not session_data or not user_data:
            raise HTTPException(status_code=404, detail="User or session not found")
        session_data["user"] = user_data
        session_data["profile_name"] = profile_name or user_data["display_name"]
        return ClaimSessionResponse(
            status="complete",
            job_id=job_id,
            profile_name=session_data["profile_name"],
            user=UserProfile(**user_data),
        )

    result = await db.execute(select(UserModel).where(UserModel.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.user_id = user.id
    session.profile_name = profile_name or user.display_name
    user.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return ClaimSessionResponse(
        status="complete",
        job_id=job_id,
        profile_name=session.profile_name or user.display_name,
        user=_user_payload(user),
    )


@router.get("/users/{user_id}/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if db is None or not is_db_available():
        user_data = _memory_users.get(str(user_uuid))
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        sessions = [
            UserSessionSummary(
                job_id=job_id,
                status=data.get("status", "complete"),
                profile_name=data.get("profile_name"),
                gender=(data.get("profile") or {}).get("gender", "men"),
                skin_label=((data.get("profile") or {}).get("skin_tone") or {}).get("label"),
                color_season=(data.get("profile") or {}).get("color_season"),
                style_vibes=(data.get("profile") or {}).get("style_vibes") or [],
            )
            for job_id, data in _memory_store.items()
            if (data.get("user") or {}).get("id") == str(user_uuid)
        ]
        return UserSessionsResponse(user=UserProfile(**user_data), sessions=sessions)

    result = await db.execute(select(UserModel).where(UserModel.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user_uuid)
        .order_by(SessionModel.created_at.desc())
    )
    sessions = result.scalars().all()
    summaries: list[UserSessionSummary] = []
    for session in sessions:
        result = await db.execute(
            select(AnalysisResultModel).where(AnalysisResultModel.session_id == session.id)
        )
        analysis = result.scalar_one_or_none()
        summaries.append(
            UserSessionSummary(
                job_id=str(session.id),
                status=session.status,
                profile_name=session.profile_name,
                created_at=session.created_at,
                gender=session.gender,
                skin_label=analysis.skin_label if analysis else None,
                color_season=analysis.color_season if analysis else None,
                style_vibes=analysis.style_vibes if analysis and analysis.style_vibes else [],
            )
        )

    return UserSessionsResponse(user=_user_payload(user), sessions=summaries)


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "mock_mode": settings.mock_mode,
        "cost_tracking_enabled": settings.cost_tracking_enabled,
        "ai_providers": {
            "openrouter": is_secret_configured(settings.openrouter_api_key),
            "openrouter_images": is_secret_configured(settings.openrouter_api_key),
            "anthropic": is_secret_configured(settings.anthropic_api_key),
            "openai_images": is_secret_configured(settings.openai_api_key),
        },
        "storage": {
            "provider": "supabase" if supabase_storage_configured() else "local",
            "supabase_configured": supabase_storage_configured(),
            "bucket": settings.supabase_storage_bucket if supabase_storage_configured() else None,
        },
        "email": {
            "configured": email_delivery_configured(),
            "dev_otp_enabled": settings.auth_dev_return_otp,
            "requires_delivery": settings.auth_require_email_delivery,
        },
        "credit_guardrails": {
            "analysis_limit_per_user_per_day": settings.analysis_limit_per_user_per_day,
            "max_visual_generations_per_user_per_day": settings.max_visual_generations_per_user_per_day,
            "max_daily_ai_cost_per_user_usd": settings.max_daily_ai_cost_per_user_usd,
        },
        "rule_categories": rule_engine.get_all_categories(),
    }


@router.get("/cost-policy", response_model=CostPolicyResponse)
async def get_cost_policy():
    return CostPolicyResponse(
        analysis_limit_per_user_per_day=settings.analysis_limit_per_user_per_day,
        guest_analysis_limit_per_day=settings.free_guest_analysis_limit_per_day,
        visual_generation_requires_auth=settings.visual_generation_requires_auth,
        visual_generation_trigger="after_otp_save",
        standalone_visual_generation_enabled=settings.standalone_visual_generation_enabled,
        max_visual_generations_per_user_per_day=settings.max_visual_generations_per_user_per_day,
        max_daily_ai_cost_per_user_usd=settings.max_daily_ai_cost_per_user_usd,
        cost_tracking_enabled=settings.cost_tracking_enabled,
        dev_otp_enabled=settings.auth_dev_return_otp,
        email_delivery_configured=email_delivery_configured(),
        pricing={
            "openrouter_text_input_cost_per_million": settings.openrouter_text_input_cost_per_million,
            "openrouter_text_output_cost_per_million": settings.openrouter_text_output_cost_per_million,
            "openrouter_vision_input_cost_per_million": settings.openrouter_vision_input_cost_per_million,
            "openrouter_vision_output_cost_per_million": settings.openrouter_vision_output_cost_per_million,
            "openrouter_image_input_cost_per_million": settings.openrouter_image_input_cost_per_million,
            "openrouter_image_output_cost_per_million": settings.openrouter_image_output_cost_per_million,
            "openrouter_image_cost_per_image": settings.openrouter_image_cost_per_image,
        },
        guardrails=[
            "Upload/preferences can be completed before login, but analysis requires verified email OTP.",
            f"Verified users are limited to {settings.analysis_limit_per_user_per_day} analyses per day.",
            f"Verified users are capped at ${settings.max_daily_ai_cost_per_user_usd:.2f} of recorded AI usage per day.",
            f"Structured analysis is capped at {settings.llm_max_images} images per AI call.",
            f"Generated editorial image boards are limited to {settings.max_visual_generations_per_user_per_day} per verified user per day.",
            "Standalone image generation is disabled unless explicitly enabled by ops.",
            "Completed result links are emailed to verified users for recovery.",
            "Marketplace matching is deterministic and catalog-based, so it does not spend LLM credits.",
            "AI usage is recorded per job so failed runs, retries, and visual generations can be audited.",
            "Cache completed results by job ID and user ID instead of re-running analysis on refresh.",
        ],
    )


@router.get("/catalog/status", response_model=CatalogStatusResponse)
async def get_catalog_status():
    seed_count, cached_count, cache_path = catalog_counts()
    flipkart = FlipkartAffiliateAdapter()
    return CatalogStatusResponse(
        seed_products=seed_count,
        cached_products=cached_count,
        cache_path=cache_path,
        providers={
            Marketplace.flipkart.value: flipkart.configured,
            Marketplace.amazon.value: bool(settings.amazon_associate_tag),
            Marketplace.myntra.value: bool(settings.myntra_affiliate_url_template),
            Marketplace.snitch.value: bool(settings.snitch_affiliate_url_template),
            Marketplace.ajio.value: bool(settings.ajio_affiliate_url_template),
        },
    )


@router.post("/catalog/sync/flipkart", response_model=CatalogSyncResponse)
async def sync_flipkart_catalog(
    categories: str = "",
    max_products_per_category: int = 100,
):
    adapter = FlipkartAffiliateAdapter()
    if not adapter.configured:
        return CatalogSyncResponse(
            status="skipped",
            provider=Marketplace.flipkart,
            configured=False,
            message="Set FLIPKART_AFFILIATE_ID and FLIPKART_AFFILIATE_TOKEN to sync Flipkart feeds.",
        )

    category_list = [item.strip() for item in categories.split(",") if item.strip()]
    try:
        products = adapter.sync(
            categories=category_list or None,
            max_products_per_category=max_products_per_category,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Flipkart catalog sync failed: {exc}") from exc

    cache_path = write_cached_provider_products(products, replace_marketplaces={Marketplace.flipkart})
    clear_catalog_cache()
    return CatalogSyncResponse(
        status="complete",
        provider=Marketplace.flipkart,
        configured=True,
        products_synced=len(products),
        cache_path=str(cache_path),
    )


@router.post("/catalog/import-feed", response_model=CatalogImportResponse)
async def import_catalog_feed(
    file: UploadFile = File(...),
    marketplace: str = Form(...),
    replace_marketplace: bool = Form(False),
    sub_id: str = Form(""),
):
    try:
        marketplace_enum = Marketplace(marketplace.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Unsupported marketplace")

    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".json")):
        raise HTTPException(status_code=400, detail="Upload a CSV or JSON product feed")

    content = await file.read()
    try:
        rows = parse_feed_rows(content, filename)
        products = normalize_feed_products(rows, marketplace_enum, sub_id=sub_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse product feed: {exc}") from exc

    cache_path = write_cached_provider_products(
        products,
        replace_marketplaces={marketplace_enum} if replace_marketplace else None,
    )
    clear_catalog_cache()
    return CatalogImportResponse(
        status="complete",
        provider=marketplace_enum,
        products_imported=len(products),
        cache_path=str(cache_path),
        message="No valid products found" if not products else None,
    )


def _result_url(job_id: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/results/{job_id}"


def _job_payload(
    job_id: str,
    status: str,
    session_id: str | None = None,
    error_message: str | None = None,
    attempts: int = 0,
    max_attempts: int = 0,
    created_at: datetime | str | None = None,
    updated_at: datetime | str | None = None,
    locked_at: datetime | str | None = None,
    started_at: datetime | str | None = None,
    last_error_at: datetime | str | None = None,
    completed_at: datetime | str | None = None,
) -> dict:
    return {
        "job_id": job_id,
        "session_id": session_id or job_id,
        "status": status,
        "result_url": _result_url(job_id) if status == "complete" else None,
        "error_message": error_message,
        "attempts": attempts,
        "max_attempts": max_attempts,
        "created_at": created_at,
        "updated_at": updated_at,
        "locked_at": locked_at,
        "started_at": started_at,
        "last_error_at": last_error_at,
        "completed_at": completed_at,
    }


async def _run_memory_analysis_job(
    job_id: str,
    saved_paths: list[str],
    gender: Gender,
    budget_min: float,
    budget_max: float,
    style_preferences: list[str],
    wear_type: str,
    occasion: list[str],
    goals: list[str],
    fit_profile: FitProfile,
    owner_profile_name: str | None,
    serialized_owner: dict | None,
):
    now = datetime.now(timezone.utc)
    job_data = _memory_jobs.get(job_id)
    if job_data:
        job_data["status"] = "processing"
        job_data["updated_at"] = now.isoformat()

    try:
        profile = await analyze_photos(saved_paths, job_id, gender)
        recs_by_category = await get_recommendations(
            profile,
            budget_min,
            budget_max,
            style_preferences,
            wear_type,
            occasion,
            goals,
        )
        serialized_profile = profile.model_dump(mode="json")
        serialized_recs = {
            cat_key: [r.model_dump(mode="json") for r in recs]
            for cat_key, recs in recs_by_category.items()
        }
        complete_at = datetime.now(timezone.utc)
        _memory_store[job_id] = {
            "status": "complete",
            "profile": serialized_profile,
            "recommendations": serialized_recs,
            "fit_profile": fit_profile.model_dump(mode="json"),
            "user": serialized_owner,
            "profile_name": owner_profile_name,
            "photo_paths": saved_paths,
            "created_at": (job_data or {}).get("created_at", complete_at.isoformat()),
        }
        _memory_jobs[job_id] = _job_payload(
            job_id,
            "complete",
            attempts=1,
            max_attempts=1,
            completed_at=complete_at.isoformat(),
            created_at=(job_data or {}).get("created_at"),
            updated_at=complete_at.isoformat(),
        )
        result_email = (serialized_owner or {}).get("email")
        if result_email:
            try:
                send_result_email(
                    result_email,
                    owner_profile_name or (serialized_owner or {}).get("display_name") or "Your Profile",
                    _result_url(job_id),
                )
            except Exception as exc:
                print(f"[WARNING] Result email failed for {result_email}: {exc}")
    except Exception as exc:
        failed_at = datetime.now(timezone.utc)
        _memory_jobs[job_id] = _job_payload(
            job_id,
            "failed",
            error_message=str(exc),
            attempts=1,
            max_attempts=1,
            created_at=(job_data or {}).get("created_at"),
            updated_at=failed_at.isoformat(),
            last_error_at=failed_at.isoformat(),
            completed_at=failed_at.isoformat(),
        )
        if job_id in _memory_store:
            _memory_store[job_id]["status"] = "failed"
        print(f"[ERROR] Analysis job {job_id} failed: {exc}")


@router.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    photos: list[UploadFile] = File(...),
    gender: str = Form("men"),
    budget_min: float = Form(50),
    budget_max: float = Form(300),
    style_preferences: str = Form(""),
    wear_type: str = Form("all"),
    occasion: str = Form(""),
    goals: str = Form(""),
    age_range: str = Form(""),
    height_cm: str = Form(""),
    weight_kg: str = Form(""),
    shirt_size: str = Form(""),
    bottom_size: str = Form(""),
    shoe_size: str = Form(""),
    preferred_fit: str = Form(""),
    pincode: str = Form(""),
    user_id: str = Form(""),
    profile_name: str = Form(""),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    if len(photos) < 1:
        raise HTTPException(status_code=400, detail="Upload at least 1 photo")
    if len(photos) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 photos allowed")

    # Parse form data
    try:
        gender_enum = Gender(gender.lower())
    except ValueError:
        gender_enum = Gender.men

    prefs = [s.strip() for s in style_preferences.split(",") if s.strip()]
    occasion_list = [s.strip() for s in occasion.split(",") if s.strip()] if occasion else []
    goals_list = [s.strip() for s in goals.split(",") if s.strip()] if goals else []
    fit_profile = _build_fit_profile(
        height_cm=height_cm,
        weight_kg=weight_kg,
        shirt_size=shirt_size,
        bottom_size=bottom_size,
        shoe_size=shoe_size,
        preferred_fit=preferred_fit,
        pincode=pincode,
    )

    token_user = await _get_user_by_auth_token(_extract_bearer_token(authorization), db)
    if settings.analysis_requires_auth and not token_user:
        raise HTTPException(status_code=401, detail="Verify email OTP before running analysis")
    if token_user:
        await _enforce_analysis_quota(token_user, db)
        await _enforce_daily_ai_cost_budget(token_user, db)

    session_id = uuid.uuid4()
    serialized_owner = None
    owner_profile_name = profile_name.strip() or None
    if token_user:
        if isinstance(token_user, dict):
            user_id = token_user["id"]
            owner_profile_name = owner_profile_name or token_user["display_name"]
            serialized_owner = UserProfile(**token_user).model_dump(mode="json")
        else:
            user_id = str(token_user.id)
            owner_profile_name = owner_profile_name or token_user.display_name
            serialized_owner = _user_payload(token_user).model_dump(mode="json")

    # Save uploaded files
    saved_paths: list[str] = []
    stored_uploads = []
    job_dir = UPLOAD_DIR / str(session_id)
    job_dir.mkdir(exist_ok=True)

    for photo in photos:
        filename = safe_filename(photo.filename, fallback="photo.jpg")
        file_path = job_dir / filename
        content = await photo.read()
        content_type = photo.content_type or "application/octet-stream"
        stored = await save_bytes(
            local_path=file_path,
            content=content,
            content_type=content_type,
            object_path=storage_object_path(
                settings.supabase_storage_uploads_prefix,
                str(session_id),
                filename,
            ),
        )
        stored_uploads.append(stored)
        saved_paths.append(str(stored.local_path))

    if db is not None and is_db_available():
        owner_id = None
        owner_name = owner_profile_name
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user ID format")
            result = await db.execute(select(UserModel).where(UserModel.id == user_uuid))
            owner = result.scalar_one_or_none()
            if not owner:
                raise HTTPException(status_code=404, detail="User not found")
            owner_id = owner.id
            owner_name = owner_name or owner.display_name
            serialized_owner = _user_payload(owner).model_dump(mode="json")
        owner_profile_name = owner_name

        db_session = SessionModel(
            id=session_id, user_id=owner_id, profile_name=owner_name,
            gender=gender_enum.value, age_range=age_range or None,
            occasion=occasion_list or None, goals=goals_list or None,
            budget_min=budget_min, budget_max=budget_max,
            style_preferences=prefs or None, wear_type=wear_type,
            height_cm=fit_profile.height_cm, weight_kg=fit_profile.weight_kg,
            shirt_size=fit_profile.shirt_size, bottom_size=fit_profile.bottom_size,
            shoe_size=fit_profile.shoe_size, preferred_fit=fit_profile.preferred_fit,
            pincode=fit_profile.pincode, status="queued",
        )
        db.add(db_session)

        for stored in stored_uploads:
            db.add(PhotoModel(
                session_id=session_id,
                file_path=str(stored.local_path),
                storage_provider=stored.storage_provider,
                storage_bucket=stored.storage_bucket,
                storage_path=stored.storage_path,
                content_type=stored.content_type,
            ))

        db.add(AnalysisJobModel(
            job_id=session_id,
            session_id=session_id,
            user_id=owner_id,
            status="queued",
            max_attempts=settings.analysis_job_max_attempts,
        ))
        await db.commit()
        nudge_analysis_worker()
        return _job_payload(
            str(session_id),
            "queued",
            attempts=0,
            max_attempts=settings.analysis_job_max_attempts,
        )
    else:
        created_at = datetime.now(timezone.utc).isoformat()
        _memory_store[str(session_id)] = {
            "status": "processing",
            "profile": None,
            "recommendations": None,
            "fit_profile": fit_profile.model_dump(mode="json"),
            "user": serialized_owner,
            "profile_name": owner_profile_name,
            "photo_paths": saved_paths,
            "created_at": created_at,
        }
        _memory_jobs[str(session_id)] = _job_payload(
            str(session_id),
            "queued",
            attempts=0,
            max_attempts=1,
            created_at=created_at,
            updated_at=created_at,
        )

        background_tasks.add_task(
            _run_memory_analysis_job,
            str(session_id),
            saved_paths,
            gender_enum,
            budget_min,
            budget_max,
            prefs,
            wear_type,
            occasion_list,
            goals_list,
            fit_profile,
            owner_profile_name,
            serialized_owner,
        )

        return _job_payload(str(session_id), "queued", attempts=0, max_attempts=1)


@router.post("/visual-analysis", response_model=VisualAnalysisResponse)
async def create_visual_analysis(
    photo: UploadFile = File(...),
    kind: str = Form(VisualAnalysisKind.color_palette.value),
    db: AsyncSession = Depends(get_db),
):
    if not settings.standalone_visual_generation_enabled:
        raise HTTPException(
            status_code=403,
            detail="Standalone visual generation is disabled. Generate boards from a saved profile.",
        )

    try:
        visual_kind = VisualAnalysisKind(kind)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid visual analysis kind")

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload a valid image file")

    visual_job_id = uuid.uuid4()
    job_dir = UPLOAD_DIR / str(visual_job_id)
    job_dir.mkdir(exist_ok=True)

    suffix = Path(safe_filename(photo.filename, "portrait.jpg")).suffix.lower() or ".jpg"
    input_path = job_dir / f"portrait{suffix}"
    output_path = job_dir / "visual-analysis.png"

    content = await photo.read()
    await save_bytes(
        local_path=input_path,
        content=content,
        content_type=photo.content_type or "application/octet-stream",
        object_path=storage_object_path("visual-analysis", str(visual_job_id), f"portrait{suffix}"),
    )

    try:
        usage_token = begin_usage_collection()
        try:
            await generate_visual_analysis(input_path, output_path, visual_kind)
        finally:
            usage_events = end_usage_collection(usage_token)
        try:
            await mirror_local_file(
                local_path=output_path,
                content_type="image/png",
                object_path=storage_object_path("visual-analysis", str(visual_job_id), "visual-analysis.png"),
            )
        except Exception as storage_exc:
            print(f"[WARNING] Could not mirror visual analysis to Supabase Storage: {storage_exc}")
        await persist_usage_events(
            db,
            usage_events,
            job_id=visual_job_id,
            session_id=None,
            user_id=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Visual analysis generation failed: {exc}") from exc

    return VisualAnalysisResponse(
        job_id=str(visual_job_id),
        status="complete",
        kind=visual_kind,
        image_url=f"/visual-analysis/{visual_job_id}/image",
        prompt_version=PROMPT_VERSION,
        process=PROCESS_BY_KIND[visual_kind],
    )


@router.post("/sessions/{job_id}/visual-analysis", response_model=VisualAnalysisResponse)
async def create_saved_session_visual_analysis(
    job_id: str,
    kind: str = Form(VisualAnalysisKind.color_palette.value),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        session_uuid = uuid.UUID(job_id)
        visual_kind = VisualAnalysisKind(kind)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID or visual analysis kind")

    token_user = None
    if settings.visual_generation_requires_auth:
        token_user = await _get_user_by_auth_token(_extract_bearer_token(authorization), db)
        if not token_user:
            raise HTTPException(status_code=401, detail="Save this profile with OTP before generating visual boards")

    output_path = UPLOAD_DIR / job_id / f"visual-analysis-{visual_kind.value}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if db is None or not is_db_available():
        session_data = _memory_store.get(job_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        if settings.visual_generation_requires_auth:
            session_user = session_data.get("user") or {}
            token_user_id = token_user["id"] if isinstance(token_user, dict) else str(token_user.id)
            if session_user.get("id") != token_user_id:
                raise HTTPException(status_code=403, detail="Save this profile to your account first")
        photo_paths = session_data.get("photo_paths") or []
        if not photo_paths:
            raise HTTPException(status_code=404, detail="No source photo found for this session")
        input_path = Path(photo_paths[0])
    else:
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if settings.visual_generation_requires_auth:
            token_user_id = token_user["id"] if isinstance(token_user, dict) else str(token_user.id)
            if str(session.user_id) != token_user_id:
                raise HTTPException(status_code=403, detail="Save this profile to your account first")
        result = await db.execute(select(PhotoModel).where(PhotoModel.session_id == session_uuid))
        photo = result.scalars().first()
        if not photo:
            raise HTTPException(status_code=404, detail="No source photo found for this session")
        input_path = Path(photo.file_path)

    if not input_path.exists():
        try:
            if db is not None and is_db_available():
                await ensure_local_file(local_path=input_path, storage_path=photo.storage_path)
            else:
                raise FileNotFoundError(str(input_path))
        except Exception:
            raise HTTPException(status_code=404, detail="Source photo file is missing")

    if not output_path.exists():
        if token_user:
            await _enforce_visual_generation_quota(token_user, db)
            await _enforce_daily_ai_cost_budget(token_user, db)
        try:
            usage_token = begin_usage_collection()
            try:
                await generate_visual_analysis(input_path, output_path, visual_kind)
            finally:
                usage_events = end_usage_collection(usage_token)
            try:
                await mirror_local_file(
                    local_path=output_path,
                    content_type="image/png",
                    object_path=storage_object_path("sessions", job_id, f"visual-analysis-{visual_kind.value}.png"),
                )
            except Exception as storage_exc:
                print(f"[WARNING] Could not mirror saved visual analysis to Supabase Storage: {storage_exc}")
            await persist_usage_events(
                db,
                usage_events,
                job_id=job_id,
                session_id=session_uuid,
                user_id=session.user_id if db is not None and is_db_available() else None,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Visual analysis generation failed: {exc}") from exc

    return VisualAnalysisResponse(
        job_id=job_id,
        status="complete",
        kind=visual_kind,
        image_url=f"/sessions/{job_id}/visual-analysis/{visual_kind.value}/image",
        prompt_version=PROMPT_VERSION,
        process=PROCESS_BY_KIND[visual_kind],
    )


@router.get("/visual-analysis/{job_id}/image")
async def get_visual_analysis_image(job_id: str):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    image_path = UPLOAD_DIR / job_id / "visual-analysis.png"
    if not image_path.exists():
        try:
            content, media_type = await download_bytes_from_supabase(
                storage_object_path("visual-analysis", job_id, "visual-analysis.png")
            )
            return Response(content=content, media_type=media_type)
        except Exception:
            raise HTTPException(status_code=404, detail="Visual analysis image not found")

    return FileResponse(image_path, media_type="image/png")


@router.get("/sessions/{job_id}/visual-analysis/{kind}/image")
async def get_saved_session_visual_analysis_image(job_id: str, kind: str):
    try:
        uuid.UUID(job_id)
        visual_kind = VisualAnalysisKind(kind)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID or visual analysis kind")

    image_path = UPLOAD_DIR / job_id / f"visual-analysis-{visual_kind.value}.png"
    if not image_path.exists():
        try:
            content, media_type = await download_bytes_from_supabase(
                storage_object_path("sessions", job_id, f"visual-analysis-{visual_kind.value}.png")
            )
            return Response(content=content, media_type=media_type)
        except Exception:
            raise HTTPException(status_code=404, detail="Visual analysis image not found")

    return FileResponse(image_path, media_type="image/png")


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(job_id: str, db: AsyncSession = Depends(get_db)):
    if job_id in _memory_jobs:
        return _memory_jobs[job_id]
    if job_id in _memory_store:
        data = _memory_store[job_id]
        return _job_payload(
            job_id,
            data.get("status", "processing"),
            created_at=data.get("created_at"),
            updated_at=data.get("created_at"),
        )

    if db is None or not is_db_available():
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(select(AnalysisJobModel).where(AnalysisJobModel.job_id == job_uuid))
    job = result.scalar_one_or_none()
    if not job:
        result = await db.execute(select(SessionModel).where(SessionModel.id == job_uuid))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_payload(
            str(session.id),
            session.status if session.status in {"queued", "processing", "complete", "failed"} else "processing",
            session_id=str(session.id),
            created_at=session.created_at,
            updated_at=session.created_at,
            completed_at=session.created_at if session.status == "complete" else None,
        )

    return _job_payload(
        str(job.job_id),
        job.status,
        session_id=str(job.session_id),
        error_message=job.error_message,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        started_at=job.started_at,
        last_error_at=job.last_error_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/usage", response_model=AIUsageLedgerResponse)
async def get_analysis_job_usage(
    job_id: str,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    if db is None or not is_db_available():
        raise HTTPException(status_code=404, detail="Usage ledger unavailable")

    result = await db.execute(select(SessionModel).where(SessionModel.id == job_uuid))
    session = result.scalar_one_or_none()
    if session and session.user_id:
        token_user = await _get_user_by_auth_token(_extract_bearer_token(authorization), db)
        token_user_id = token_user["id"] if isinstance(token_user, dict) else str(token_user.id) if token_user else None
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Sign in to view usage for this job")
        if str(session.user_id) != token_user_id:
            raise HTTPException(status_code=403, detail="Usage ledger belongs to another user")

    return await usage_ledger_for_job(db, job_id)


@router.get("/users/{user_id}/usage", response_model=AIUsageLedgerResponse)
async def get_user_usage(
    user_id: str,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if db is None or not is_db_available():
        raise HTTPException(status_code=404, detail="Usage ledger unavailable")

    token_user = await _get_user_by_auth_token(_extract_bearer_token(authorization), db)
    token_user_id = token_user["id"] if isinstance(token_user, dict) else str(token_user.id) if token_user else None
    if not token_user_id:
        raise HTTPException(status_code=401, detail="Sign in to view usage")
    if str(user_uuid) != token_user_id:
        raise HTTPException(status_code=403, detail="Usage ledger belongs to another user")

    return await usage_ledger_for_user(db, user_id)


@router.get("/profile/{job_id}")
async def get_profile(job_id: str, db: AsyncSession = Depends(get_db)):
    # Check in-memory store first (no-DB fallback)
    if job_id in _memory_store:
        return _memory_store[job_id]

    if db is None or not is_db_available():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Fetch session
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "failed":
        return {"status": "failed"}
    if session.status != "complete":
        return {"status": "processing"}

    # Fetch analysis
    result = await db.execute(
        select(AnalysisResultModel).where(AnalysisResultModel.session_id == session_uuid)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        return {"status": "processing"}

    # Fetch colors
    result = await db.execute(
        select(ColorPaletteModel).where(ColorPaletteModel.session_id == session_uuid)
    )
    colors = result.scalars().all()

    # Build profile response
    from app.models.schemas import (
        StyleProfile, SkinTone, BodyType, Proportions,
        ColorRecommendation, FaceShape, ColorSeason,
    )

    face_shape = None
    if analysis.face_shape:
        try:
            face_shape = FaceShape(analysis.face_shape)
        except ValueError:
            pass

    color_season = None
    if analysis.color_season:
        try:
            color_season = ColorSeason(analysis.color_season)
        except ValueError:
            pass

    profile = StyleProfile(
        job_id=job_id,
        gender=Gender(session.gender),
        skin_tone=SkinTone(
            fitzpatrick=analysis.skin_fitzpatrick,
            undertone=analysis.skin_undertone,
            label=analysis.skin_label,
            hex_color=analysis.skin_hex,
        ),
        body_type=BodyType(
            shape=analysis.body_shape,
            build=analysis.body_build,
            height_category=analysis.height_category,
        ),
        proportions=Proportions(
            shoulder_hip_ratio=analysis.shoulder_hip_ratio,
            torso_leg_ratio=analysis.torso_leg_ratio,
        ),
        face_shape=face_shape,
        color_season=color_season,
        eye_color=analysis.eye_color,
        style_vibes=analysis.style_vibes or [],
        color_palette=[
            ColorRecommendation(
                name=c.color_name,
                hex=c.hex_value,
                category=c.category,
                reason=c.reason,
            )
            for c in colors
        ],
        wardrobe_tips=analysis.wardrobe_tips or [],
        confidence_score=analysis.confidence_score,
    )
    fit_profile = FitProfile(
        height_cm=session.height_cm,
        weight_kg=session.weight_kg,
        shirt_size=session.shirt_size,
        bottom_size=session.bottom_size,
        shoe_size=session.shoe_size,
        preferred_fit=session.preferred_fit,
        pincode=session.pincode,
    )
    owner_payload = None
    if session.user_id:
        result = await db.execute(select(UserModel).where(UserModel.id == session.user_id))
        owner = result.scalar_one_or_none()
        if owner:
            owner_payload = _user_payload(owner).model_dump(mode="json")

    # Fetch recommendations
    result = await db.execute(
        select(RecommendationModel).where(RecommendationModel.session_id == session_uuid)
    )
    recs = result.scalars().all()

    from app.models.schemas import OutfitRecommendation, OutfitItem

    recommendations: dict[str, list] = {}
    for rec in recs:
        items = []
        if rec.items:
            for item_data in rec.items:
                items.append(OutfitItem(**item_data))

        outfit_rec = OutfitRecommendation(
            id=str(rec.id),
            name=rec.title,
            description=rec.description,
            why_it_works=rec.why_it_works,
            items=items,
            total_price_usd=rec.total_price_usd or 0,
            style_tags=rec.style_tags or [],
            image_url=rec.image_url or "",
            recommendation_category=rec.category,
            sub_category=rec.sub_category,
            source=rec.source,
            confidence=rec.confidence,
        )

        if rec.sub_category not in recommendations:
            recommendations[rec.sub_category] = []
        recommendations[rec.sub_category].append(outfit_rec.model_dump())

    return {
        "status": "complete",
        "profile": profile.model_dump(),
        "recommendations": recommendations,
        "fit_profile": fit_profile.model_dump(),
        "user": owner_payload,
        "profile_name": session.profile_name,
    }


@router.get("/products/recommendations/{job_id}", response_model=ProductRecommendationResponse)
async def get_product_recommendations(
    job_id: str,
    budget_max_inr: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    data = await get_profile(job_id, db)
    if data.get("status") != "complete" or not data.get("profile"):
        raise HTTPException(status_code=400, detail="Analysis not yet complete")

    profile = StyleProfile(**data["profile"])
    fit_profile = FitProfile(**(data.get("fit_profile") or {}))
    products = recommend_products(
        profile=profile,
        fit_profile=fit_profile,
        budget_max_inr=budget_max_inr,
    )

    return ProductRecommendationResponse(
        job_id=job_id,
        status="complete",
        fit_profile=fit_profile,
        products=products,
    )


@router.get("/report/{job_id}")
async def get_report(job_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and return a PDF style report for a completed session."""
    try:
        session_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Fetch session
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "complete":
        raise HTTPException(status_code=400, detail="Analysis not yet complete")

    # Fetch analysis
    result = await db.execute(
        select(AnalysisResultModel).where(AnalysisResultModel.session_id == session_uuid)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=400, detail="Analysis not yet complete")

    # Fetch colors
    result = await db.execute(
        select(ColorPaletteModel).where(ColorPaletteModel.session_id == session_uuid)
    )
    db_colors = result.scalars().all()

    # Build profile
    from app.models.schemas import (
        StyleProfile, SkinTone, BodyType, Proportions,
        ColorRecommendation, FaceShape, ColorSeason,
        OutfitRecommendation, OutfitItem,
    )

    face_shape = None
    if analysis.face_shape:
        try:
            face_shape = FaceShape(analysis.face_shape)
        except ValueError:
            pass

    color_season = None
    if analysis.color_season:
        try:
            color_season = ColorSeason(analysis.color_season)
        except ValueError:
            pass

    profile = StyleProfile(
        job_id=job_id,
        gender=Gender(session.gender),
        skin_tone=SkinTone(
            fitzpatrick=analysis.skin_fitzpatrick,
            undertone=analysis.skin_undertone,
            label=analysis.skin_label,
            hex_color=analysis.skin_hex,
        ),
        body_type=BodyType(
            shape=analysis.body_shape,
            build=analysis.body_build,
            height_category=analysis.height_category,
        ),
        proportions=Proportions(
            shoulder_hip_ratio=analysis.shoulder_hip_ratio,
            torso_leg_ratio=analysis.torso_leg_ratio,
        ),
        face_shape=face_shape,
        color_season=color_season,
        eye_color=analysis.eye_color,
        style_vibes=analysis.style_vibes or [],
        color_palette=[
            ColorRecommendation(
                name=c.color_name,
                hex=c.hex_value,
                category=c.category,
                reason=c.reason,
            )
            for c in db_colors
        ],
        wardrobe_tips=analysis.wardrobe_tips or [],
        confidence_score=analysis.confidence_score,
    )

    # Fetch recommendations
    result = await db.execute(
        select(RecommendationModel).where(RecommendationModel.session_id == session_uuid)
    )
    recs = result.scalars().all()

    recommendations: dict[str, list[OutfitRecommendation]] = {}
    for rec in recs:
        items = []
        if rec.items:
            for item_data in rec.items:
                items.append(OutfitItem(**item_data))

        outfit_rec = OutfitRecommendation(
            id=str(rec.id),
            name=rec.title,
            description=rec.description,
            why_it_works=rec.why_it_works,
            items=items,
            total_price_usd=rec.total_price_usd or 0,
            style_tags=rec.style_tags or [],
            image_url=rec.image_url or "",
            recommendation_category=rec.category,
            sub_category=rec.sub_category,
            source=rec.source,
            confidence=rec.confidence,
        )

        if rec.sub_category not in recommendations:
            recommendations[rec.sub_category] = []
        recommendations[rec.sub_category].append(outfit_rec)

    # Generate PDF
    from app.services.report_generator import generate_report
    pdf_bytes = generate_report(profile, recommendations)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=aurafit-style-report-{job_id[:8]}.pdf"},
    )


@router.get("/rules/categories")
async def get_rule_categories():
    return {"categories": rule_engine.get_all_categories()}
