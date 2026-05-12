from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import AIUsageLedgerModel


@dataclass
class AIUsageEvent:
    operation: str
    provider: str
    model: str
    status: str = "recorded"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    image_count: int = 0
    estimated_cost_usd: float = 0
    actual_cost_usd: float | None = None
    currency: str = "USD"
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_usage_collector: ContextVar[list[AIUsageEvent] | None] = ContextVar("ai_usage_collector", default=None)


def begin_usage_collection() -> object:
    return _usage_collector.set([])


def end_usage_collection(token: object) -> list[AIUsageEvent]:
    events = _usage_collector.get() or []
    _usage_collector.reset(token)
    return events


def record_usage_event(event: AIUsageEvent) -> AIUsageEvent:
    if not settings.cost_tracking_enabled:
        return event
    collector = _usage_collector.get()
    if collector is not None:
        collector.append(event)
    return event


def _field(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _usage_payload(response: Any) -> dict[str, Any]:
    usage = _field(response, "usage")
    if usage is None and hasattr(response, "model_dump"):
        usage = response.model_dump().get("usage")
    return usage if isinstance(usage, dict) else {
        "prompt_tokens": _field(usage, "prompt_tokens", 0),
        "completion_tokens": _field(usage, "completion_tokens", 0),
        "input_tokens": _field(usage, "input_tokens", 0),
        "output_tokens": _field(usage, "output_tokens", 0),
        "total_tokens": _field(usage, "total_tokens", 0),
        "cost": _field(usage, "cost"),
    }


def _configured_token_cost(operation: str, prompt_tokens: int, completion_tokens: int) -> float:
    if operation.startswith("visual."):
        input_rate = settings.openrouter_image_input_cost_per_million
        output_rate = settings.openrouter_image_output_cost_per_million
    elif operation.startswith("analysis.vision"):
        input_rate = settings.openrouter_vision_input_cost_per_million
        output_rate = settings.openrouter_vision_output_cost_per_million
    else:
        input_rate = settings.openrouter_text_input_cost_per_million
        output_rate = settings.openrouter_text_output_cost_per_million
    return ((prompt_tokens / 1_000_000) * input_rate) + ((completion_tokens / 1_000_000) * output_rate)


def capture_response_usage(
    response: Any,
    *,
    operation: str,
    provider: str,
    model: str,
    image_count: int = 0,
    details: dict[str, Any] | None = None,
) -> AIUsageEvent:
    usage = _usage_payload(response)
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
    actual_cost = usage.get("cost") or usage.get("total_cost") or usage.get("estimated_cost")
    actual_cost_float = float(actual_cost) if actual_cost is not None else None
    estimated_cost = actual_cost_float
    if estimated_cost is None:
        estimated_cost = _configured_token_cost(operation, prompt_tokens, completion_tokens)
        if provider == "openrouter" and image_count:
            estimated_cost += image_count * settings.openrouter_image_cost_per_image
        elif provider == "openai" and image_count:
            estimated_cost += image_count * settings.openai_image_cost_per_image

    event = AIUsageEvent(
        operation=operation,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        image_count=image_count,
        actual_cost_usd=actual_cost_float,
        estimated_cost_usd=round(float(estimated_cost or 0), 8),
        details={
            **(details or {}),
            "usage_source": "provider_response" if usage else "not_returned",
        },
    )
    return record_usage_event(event)


def capture_image_usage(
    *,
    operation: str,
    provider: str,
    model: str,
    image_count: int = 1,
    actual_cost_usd: float | None = None,
    details: dict[str, Any] | None = None,
) -> AIUsageEvent:
    if actual_cost_usd is not None:
        estimated_cost = actual_cost_usd
    elif provider == "openrouter":
        estimated_cost = image_count * settings.openrouter_image_cost_per_image
    elif provider == "openai":
        estimated_cost = image_count * settings.openai_image_cost_per_image
    else:
        estimated_cost = 0
    event = AIUsageEvent(
        operation=operation,
        provider=provider,
        model=model,
        image_count=image_count,
        actual_cost_usd=actual_cost_usd,
        estimated_cost_usd=round(float(estimated_cost or 0), 8),
        details=details or {},
    )
    return record_usage_event(event)


def _uuid_or_none(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def persist_usage_events(
    db: AsyncSession | None,
    events: list[AIUsageEvent],
    *,
    job_id: str | uuid.UUID | None,
    session_id: str | uuid.UUID | None,
    user_id: str | uuid.UUID | None,
) -> None:
    if not db or not events or not settings.cost_tracking_enabled:
        return
    job_uuid = _uuid_or_none(job_id)
    session_uuid = _uuid_or_none(session_id)
    user_uuid = _uuid_or_none(user_id)
    for event in events:
        db.add(AIUsageLedgerModel(
            job_id=job_uuid,
            session_id=session_uuid,
            user_id=user_uuid,
            operation=event.operation,
            provider=event.provider,
            model=event.model,
            status=event.status,
            prompt_tokens=event.prompt_tokens,
            completion_tokens=event.completion_tokens,
            total_tokens=event.total_tokens,
            image_count=event.image_count,
            estimated_cost_usd=event.estimated_cost_usd,
            actual_cost_usd=event.actual_cost_usd,
            currency=event.currency,
            details=event.details,
            created_at=event.created_at,
        ))
    await db.commit()


def usage_row_payload(row: AIUsageLedgerModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "job_id": str(row.job_id) if row.job_id else None,
        "session_id": str(row.session_id) if row.session_id else None,
        "user_id": str(row.user_id) if row.user_id else None,
        "operation": row.operation,
        "provider": row.provider,
        "model": row.model,
        "status": row.status,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "image_count": row.image_count,
        "estimated_cost_usd": row.estimated_cost_usd,
        "actual_cost_usd": row.actual_cost_usd,
        "currency": row.currency,
        "details": row.details or {},
        "created_at": row.created_at,
    }


async def usage_ledger_for_job(db: AsyncSession, job_id: str) -> dict[str, Any]:
    job_uuid = uuid.UUID(job_id)
    result = await db.execute(
        select(AIUsageLedgerModel)
        .where(AIUsageLedgerModel.job_id == job_uuid)
        .order_by(AIUsageLedgerModel.created_at.asc())
    )
    rows = result.scalars().all()
    entries = [usage_row_payload(row) for row in rows]
    actual_costs = [row.actual_cost_usd for row in rows if row.actual_cost_usd is not None]
    return {
        "job_id": job_id,
        "total_estimated_cost_usd": round(sum(row.estimated_cost_usd or 0 for row in rows), 8),
        "total_actual_cost_usd": round(sum(actual_costs), 8) if actual_costs else None,
        "total_tokens": sum(row.total_tokens or 0 for row in rows),
        "entries": entries,
    }


async def usage_ledger_for_user(db: AsyncSession, user_id: str) -> dict[str, Any]:
    user_uuid = uuid.UUID(user_id)
    result = await db.execute(
        select(AIUsageLedgerModel)
        .where(AIUsageLedgerModel.user_id == user_uuid)
        .order_by(AIUsageLedgerModel.created_at.desc())
    )
    rows = result.scalars().all()
    entries = [usage_row_payload(row) for row in rows]
    actual_costs = [row.actual_cost_usd for row in rows if row.actual_cost_usd is not None]
    return {
        "user_id": user_id,
        "total_estimated_cost_usd": round(sum(row.estimated_cost_usd or 0 for row in rows), 8),
        "total_actual_cost_usd": round(sum(actual_costs), 8) if actual_costs else None,
        "total_tokens": sum(row.total_tokens or 0 for row in rows),
        "entries": entries,
    }
