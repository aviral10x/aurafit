from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.config import settings
from app.models.db import Base

_db_available = False

_is_supabase_pooler = "pooler.supabase.com" in settings.database_url

try:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool if _is_supabase_pooler else None,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        } if _is_supabase_pooler else {},
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception:
    engine = None
    async_session = None


async def init_db():
    global _db_available
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id UUID"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS profile_name VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS height_cm FLOAT"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS weight_kg FLOAT"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS shirt_size VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS bottom_size VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS shoe_size VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS preferred_fit VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pincode VARCHAR(12)"))
        await conn.execute(text("ALTER TABLE photos ADD COLUMN IF NOT EXISTS storage_provider VARCHAR(40)"))
        await conn.execute(text("ALTER TABLE photos ADD COLUMN IF NOT EXISTS storage_bucket VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE photos ADD COLUMN IF NOT EXISTS storage_path VARCHAR(700)"))
        await conn.execute(text("ALTER TABLE photos ADD COLUMN IF NOT EXISTS content_type VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS error_message TEXT"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE"))
    _db_available = True


def is_db_available() -> bool:
    return _db_available


async def get_db() -> AsyncSession:
    if not _db_available or async_session is None:
        yield None
        return
    async with async_session() as session:
        yield session
