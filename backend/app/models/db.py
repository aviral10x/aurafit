import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sessions: Mapped[List["SessionModel"]] = relationship(back_populates="user")
    auth_sessions: Mapped[List["AuthSessionModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthOtpModel(Base):
    __tablename__ = "auth_otps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), default="login")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="auth_sessions")


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    profile_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    age_range: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    occasion: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    goals: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    budget_min: Mapped[float] = mapped_column(Float, default=50)
    budget_max: Mapped[float] = mapped_column(Float, default=300)
    style_preferences: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    wear_type: Mapped[str] = mapped_column(String(20), default="all")
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shirt_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bottom_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    shoe_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    preferred_fit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped[Optional["UserModel"]] = relationship(back_populates="sessions")
    photos: Mapped[List["PhotoModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analysis: Mapped[Optional["AnalysisResultModel"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[List["RecommendationModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    color_palettes: Mapped[List["ColorPaletteModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analysis_job: Mapped[Optional["AnalysisJobModel"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")


class AnalysisJobModel(Base):
    __tablename__ = "analysis_jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["SessionModel"] = relationship(back_populates="analysis_job")
    user: Mapped[Optional["UserModel"]] = relationship()


class AIUsageLedgerModel(Base):
    __tablename__ = "ai_usage_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    operation: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(20), default="recorded", index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0)
    actual_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[Optional["SessionModel"]] = relationship()
    user: Mapped[Optional["UserModel"]] = relationship()


class PhotoModel(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(500))
    storage_provider: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(700), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped["SessionModel"] = relationship(back_populates="photos")


class AnalysisResultModel(Base):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), unique=True)

    # Body analysis
    body_shape: Mapped[str] = mapped_column(String(30))
    body_build: Mapped[str] = mapped_column(String(20))
    height_category: Mapped[str] = mapped_column(String(20))
    shoulder_hip_ratio: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    torso_leg_ratio: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Skin analysis
    skin_fitzpatrick: Mapped[str] = mapped_column(String(5))
    skin_undertone: Mapped[str] = mapped_column(String(20))
    skin_label: Mapped[str] = mapped_column(String(100))
    skin_hex: Mapped[str] = mapped_column(String(10))

    # Face analysis
    face_shape: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    eye_color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Color analysis
    color_season: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Style
    style_vibes: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    wardrobe_tips: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)

    # Meta
    raw_ai_response: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped["SessionModel"] = relationship(back_populates="analysis")


class RecommendationModel(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(30))
    sub_category: Mapped[str] = mapped_column(String(20), default="western")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    why_it_works: Mapped[str] = mapped_column(Text)
    items: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    style_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="rule")
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped["SessionModel"] = relationship(back_populates="recommendations")


class ColorPaletteModel(Base):
    __tablename__ = "color_palettes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    color_name: Mapped[str] = mapped_column(String(50))
    hex_value: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(10), default="best")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["SessionModel"] = relationship(back_populates="color_palettes")
