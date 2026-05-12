from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import is_secret_configured, settings


@dataclass
class StoredFile:
    local_path: Path
    storage_provider: str | None = None
    storage_bucket: str | None = None
    storage_path: str | None = None
    content_type: str | None = None


def supabase_storage_configured() -> bool:
    return (
        settings.supabase_storage_enabled
        and is_secret_configured(settings.supabase_url)
        and is_secret_configured(settings.supabase_service_role_key)
        and bool(settings.supabase_storage_bucket.strip())
    )


def safe_filename(filename: str | None, fallback: str = "upload.jpg") -> str:
    raw = Path(filename or fallback).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-")
    return sanitized or fallback


def storage_object_path(*parts: str) -> str:
    cleaned = [str(part).strip("/ ") for part in parts if str(part).strip("/ ")]
    return "/".join(cleaned)


def _supabase_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def upload_bytes_to_supabase(
    *,
    object_path: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    upsert: bool = True,
) -> tuple[str | None, str | None]:
    if not supabase_storage_configured():
        return None, None

    bucket = settings.supabase_storage_bucket.strip()
    base_url = settings.supabase_url.rstrip("/")
    url = f"{base_url}/storage/v1/object/{bucket}/{object_path}"
    headers = _supabase_headers(content_type)
    if upsert:
        headers["x-upsert"] = "true"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=headers, content=content)
        response.raise_for_status()
    return bucket, object_path


async def download_bytes_from_supabase(object_path: str) -> tuple[bytes, str]:
    if not supabase_storage_configured():
        raise FileNotFoundError("Supabase Storage is not configured")

    bucket = settings.supabase_storage_bucket.strip()
    base_url = settings.supabase_url.rstrip("/")
    url = f"{base_url}/storage/v1/object/{bucket}/{object_path}"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=_supabase_headers())
        response.raise_for_status()
    return response.content, response.headers.get("content-type", "application/octet-stream")


async def save_bytes(
    *,
    local_path: Path,
    content: bytes,
    content_type: str,
    object_path: str | None = None,
) -> StoredFile:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)

    storage_bucket = None
    storage_path = None
    if object_path:
        storage_bucket, storage_path = await upload_bytes_to_supabase(
            object_path=object_path,
            content=content,
            content_type=content_type,
        )

    return StoredFile(
        local_path=local_path,
        storage_provider="supabase" if storage_path else None,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        content_type=content_type,
    )


async def mirror_local_file(
    *,
    local_path: Path,
    content_type: str,
    object_path: str,
) -> StoredFile:
    content = local_path.read_bytes()
    storage_bucket, storage_path = await upload_bytes_to_supabase(
        object_path=object_path,
        content=content,
        content_type=content_type,
    )
    return StoredFile(
        local_path=local_path,
        storage_provider="supabase" if storage_path else None,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        content_type=content_type,
    )


async def ensure_local_file(
    *,
    local_path: Path,
    storage_path: str | None,
) -> Path:
    if local_path.exists():
        return local_path
    if not storage_path:
        raise FileNotFoundError(str(local_path))

    content, _ = await download_bytes_from_supabase(storage_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
    return local_path
