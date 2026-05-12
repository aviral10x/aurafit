from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, or_, select

from app.config import settings
from app.database import async_session, is_db_available
from app.models.db import (
    AnalysisJobModel,
    AnalysisResultModel,
    ColorPaletteModel,
    PhotoModel,
    RecommendationModel,
    SessionModel,
    UserModel,
)
from app.models.schemas import FitProfile, Gender
from app.services.analyzer import analyze_photos
from app.services.cost_ledger import begin_usage_collection, end_usage_collection, persist_usage_events
from app.services.emailer import send_result_email
from app.services.recommender import get_recommendations
from app.services.storage import ensure_local_file

_worker_task: asyncio.Task | None = None
_worker_wake_event: asyncio.Event | None = None


def _result_url(job_id: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/results/{job_id}"


def nudge_analysis_worker() -> None:
    if _worker_wake_event is not None:
        _worker_wake_event.set()


async def start_analysis_worker() -> asyncio.Task | None:
    global _worker_task, _worker_wake_event
    if not settings.analysis_worker_enabled:
        print("[INFO] Analysis worker disabled")
        return None
    if not is_db_available() or async_session is None:
        print("[INFO] Analysis worker unavailable without database session factory")
        return None
    if _worker_task and not _worker_task.done():
        return _worker_task

    _worker_wake_event = asyncio.Event()
    _worker_task = asyncio.create_task(_analysis_worker_loop(), name="analysis-job-worker")
    print("[INFO] Analysis worker started")
    return _worker_task


async def stop_analysis_worker() -> None:
    global _worker_task, _worker_wake_event
    task = _worker_task
    _worker_task = None
    _worker_wake_event = None
    if not task:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _analysis_worker_loop() -> None:
    while True:
        try:
            processed = await process_one_analysis_job()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            processed = False
            print(f"[ERROR] Analysis worker iteration failed: {exc}")

        if processed:
            continue

        event = _worker_wake_event
        if event is None:
            await asyncio.sleep(settings.analysis_worker_poll_interval_seconds)
            continue
        try:
            await asyncio.wait_for(
                event.wait(),
                timeout=settings.analysis_worker_poll_interval_seconds,
            )
        except asyncio.TimeoutError:
            pass
        event.clear()


async def process_one_analysis_job() -> bool:
    """Claim and process one queued/stale analysis job. Useful for tests and dev scripts."""
    if not is_db_available() or async_session is None:
        return False

    job_id = await _claim_next_analysis_job()
    if job_id is None:
        return False

    await _execute_claimed_analysis_job(job_id)
    return True


async def _claim_next_analysis_job() -> str | None:
    if async_session is None:
        return None

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=settings.analysis_job_stale_after_seconds)
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(
                select(AnalysisJobModel)
                .where(
                    AnalysisJobModel.status.in_(["queued", "processing"]),
                    or_(
                        AnalysisJobModel.attempts < AnalysisJobModel.max_attempts,
                        AnalysisJobModel.status == "processing",
                    ),
                    or_(
                        AnalysisJobModel.status == "queued",
                        AnalysisJobModel.locked_at.is_(None),
                        AnalysisJobModel.locked_at <= stale_before,
                    ),
                )
                .order_by(AnalysisJobModel.created_at.asc())
                .with_for_update(skip_locked=True)
            )
            job = result.scalars().first()
            if job is None:
                return None

            result = await db.execute(select(SessionModel).where(SessionModel.id == job.session_id))
            session = result.scalar_one_or_none()
            if session is None:
                job.status = "failed"
                job.error_message = "Session row missing for analysis job"
                job.last_error_at = now
                job.updated_at = now
                job.completed_at = now
                return None

            if (job.attempts or 0) >= (job.max_attempts or settings.analysis_job_max_attempts):
                job.status = "failed"
                job.error_message = "Analysis job lock went stale after max attempts"
                job.last_error_at = now
                job.locked_at = None
                job.updated_at = now
                job.completed_at = now
                session.status = "failed"
                return None

            job.attempts = (job.attempts or 0) + 1
            job.status = "processing"
            job.error_message = None
            job.locked_at = now
            job.started_at = job.started_at or now
            job.updated_at = now
            session.status = "processing"
            return str(job.job_id)


async def _execute_claimed_analysis_job(job_id: str) -> None:
    if async_session is None:
        return

    session_uuid = uuid.UUID(job_id)
    usage_events = []
    user_id = None

    try:
        async with async_session() as db:
            result = await db.execute(select(AnalysisJobModel).where(AnalysisJobModel.job_id == session_uuid))
            job = result.scalar_one_or_none()
            result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
            db_session = result.scalar_one_or_none()
            if not job or not db_session:
                print(f"[ERROR] Analysis job {job_id} missing database rows")
                return

            user_id = db_session.user_id
            result = await db.execute(
                select(PhotoModel).where(PhotoModel.session_id == session_uuid).order_by(PhotoModel.uploaded_at.asc())
            )
            saved_paths = []
            for photo in result.scalars().all():
                local_path = await ensure_local_file(
                    local_path=Path(photo.file_path),
                    storage_path=photo.storage_path,
                )
                saved_paths.append(str(local_path))
            if not saved_paths:
                raise RuntimeError("No uploaded photos found for analysis job")

            owner = None
            if db_session.user_id:
                result = await db.execute(select(UserModel).where(UserModel.id == db_session.user_id))
                owner = result.scalar_one_or_none()

            fit_profile = FitProfile(
                height_cm=db_session.height_cm,
                weight_kg=db_session.weight_kg,
                shirt_size=db_session.shirt_size,
                bottom_size=db_session.bottom_size,
                shoe_size=db_session.shoe_size,
                preferred_fit=db_session.preferred_fit,
                pincode=db_session.pincode,
            )
            style_preferences = db_session.style_preferences or []
            occasion = db_session.occasion or []
            goals = db_session.goals or []
            gender = Gender(db_session.gender)

            usage_token = begin_usage_collection()
            try:
                profile = await analyze_photos(saved_paths, job_id, gender)
                recs_by_category = await get_recommendations(
                    profile,
                    db_session.budget_min,
                    db_session.budget_max,
                    style_preferences,
                    db_session.wear_type,
                    occasion,
                    goals,
                )
            finally:
                usage_events = end_usage_collection(usage_token)

            await db.execute(delete(RecommendationModel).where(RecommendationModel.session_id == session_uuid))
            await db.execute(delete(ColorPaletteModel).where(ColorPaletteModel.session_id == session_uuid))
            await db.execute(delete(AnalysisResultModel).where(AnalysisResultModel.session_id == session_uuid))

            db.add(AnalysisResultModel(
                session_id=session_uuid,
                body_shape=profile.body_type.shape,
                body_build=profile.body_type.build,
                height_category=profile.body_type.height_category,
                shoulder_hip_ratio=profile.proportions.shoulder_hip_ratio if profile.proportions else None,
                torso_leg_ratio=profile.proportions.torso_leg_ratio if profile.proportions else None,
                skin_fitzpatrick=profile.skin_tone.fitzpatrick,
                skin_undertone=profile.skin_tone.undertone,
                skin_label=profile.skin_tone.label,
                skin_hex=profile.skin_tone.hex_color,
                face_shape=profile.face_shape.value if profile.face_shape else None,
                eye_color=profile.eye_color,
                color_season=profile.color_season.value if profile.color_season else None,
                style_vibes=profile.style_vibes,
                wardrobe_tips=profile.wardrobe_tips,
                confidence_score=profile.confidence_score,
            ))

            for color in profile.color_palette:
                db.add(ColorPaletteModel(
                    session_id=session_uuid,
                    color_name=color.name,
                    hex_value=color.hex,
                    category=color.category,
                    reason=color.reason,
                ))

            for recs in recs_by_category.values():
                for rec in recs:
                    db.add(RecommendationModel(
                        session_id=session_uuid,
                        category=rec.recommendation_category.value,
                        sub_category=rec.sub_category.value if hasattr(rec.sub_category, "value") else rec.sub_category,
                        title=rec.name,
                        description=rec.description,
                        why_it_works=rec.why_it_works,
                        items=[item.model_dump() for item in rec.items],
                        style_tags=rec.style_tags,
                        image_url=rec.image_url,
                        total_price_usd=rec.total_price_usd,
                        source=rec.source.value if hasattr(rec.source, "value") else rec.source,
                        confidence=rec.confidence,
                    ))

            completed_at = datetime.now(timezone.utc)
            db_session.status = "complete"
            job.status = "complete"
            job.error_message = None
            job.locked_at = None
            job.completed_at = completed_at
            job.updated_at = completed_at
            await db.commit()

            await persist_usage_events(
                db,
                usage_events,
                job_id=job_id,
                session_id=session_uuid,
                user_id=user_id,
            )

            if owner and owner.email:
                try:
                    send_result_email(
                        owner.email,
                        db_session.profile_name or owner.display_name or "Your Profile",
                        _result_url(job_id),
                    )
                except Exception as exc:
                    print(f"[WARNING] Result email failed for {owner.email}: {exc}")
    except Exception as exc:
        usage_events = usage_events or []
        print(f"[ERROR] Analysis job {job_id} failed: {exc}")
        async with async_session() as db:
            result = await db.execute(select(AnalysisJobModel).where(AnalysisJobModel.job_id == session_uuid))
            job = result.scalar_one_or_none()
            result = await db.execute(select(SessionModel).where(SessionModel.id == session_uuid))
            db_session = result.scalar_one_or_none()
            failed_at = datetime.now(timezone.utc)
            if job:
                retry = (job.attempts or 0) < (job.max_attempts or settings.analysis_job_max_attempts)
                job.status = "queued" if retry else "failed"
                job.error_message = str(exc)
                job.last_error_at = failed_at
                job.locked_at = None
                job.updated_at = failed_at
                if not retry:
                    job.completed_at = failed_at
            if db_session:
                db_session.status = job.status if job else "failed"
                user_id = db_session.user_id
            await persist_usage_events(
                db,
                usage_events,
                job_id=job_id,
                session_id=session_uuid,
                user_id=user_id,
            )
            await db.commit()
