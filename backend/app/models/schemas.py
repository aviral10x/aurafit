from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class Gender(str, Enum):
    men = "men"
    women = "women"
    nonbinary = "nonbinary"


class FaceShape(str, Enum):
    oval = "oval"
    round = "round"
    square = "square"
    heart = "heart"
    oblong = "oblong"
    diamond = "diamond"


class ColorSeason(str, Enum):
    spring_light = "spring_light"
    spring_warm = "spring_warm"
    spring_clear = "spring_clear"
    summer_light = "summer_light"
    summer_cool = "summer_cool"
    summer_soft = "summer_soft"
    autumn_soft = "autumn_soft"
    autumn_warm = "autumn_warm"
    autumn_deep = "autumn_deep"
    winter_deep = "winter_deep"
    winter_cool = "winter_cool"
    winter_clear = "winter_clear"


class VisualAnalysisKind(str, Enum):
    color_palette = "color_palette"
    hairstyles = "hairstyles"
    look_audit = "look_audit"


class RecommendationCategory(str, Enum):
    clothing = "clothing"
    jewellery = "jewellery"
    makeup = "makeup"
    footwear = "footwear"
    accessories = "accessories"
    grooming = "grooming"
    hair = "hair"


class RecommendationSubCategory(str, Enum):
    western = "western"
    indian = "indian"
    fusion = "fusion"
    general = "general"


class RecommendationSource(str, Enum):
    rule = "rule"
    ai = "ai"
    hybrid = "hybrid"


class Marketplace(str, Enum):
    amazon = "amazon"
    flipkart = "flipkart"
    myntra = "myntra"
    snitch = "snitch"
    ajio = "ajio"
    other = "other"


# --- Analysis Models ---

class SkinTone(BaseModel):
    fitzpatrick: str
    undertone: str  # warm, cool, neutral, olive
    label: str
    hex_color: str


class BodyType(BaseModel):
    shape: str  # rectangle, inverted-triangle, triangle, hourglass, oval, pear
    build: str  # slim, athletic, average, broad
    height_category: str  # petite, average, tall


class Proportions(BaseModel):
    shoulder_hip_ratio: Optional[str] = None  # balanced, broad-shoulder, wide-hip
    torso_leg_ratio: Optional[str] = None  # long-torso, balanced, long-legs


class ColorRecommendation(BaseModel):
    name: str
    hex: str
    category: str = "best"  # best, good, avoid
    reason: Optional[str] = None


class StyleProfile(BaseModel):
    job_id: str
    gender: Gender
    skin_tone: SkinTone
    body_type: BodyType
    proportions: Optional[Proportions] = None
    face_shape: Optional[FaceShape] = None
    color_season: Optional[ColorSeason] = None
    eye_color: Optional[str] = None
    style_vibes: list[str]
    color_palette: list[ColorRecommendation]
    wardrobe_tips: list[str]
    confidence_score: float = 0.85


class FitProfile(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    shirt_size: Optional[str] = None
    bottom_size: Optional[str] = None
    shoe_size: Optional[str] = None
    preferred_fit: Optional[str] = None  # slim, regular, relaxed, oversized
    pincode: Optional[str] = None


# --- Outfit Models ---

class OutfitItem(BaseModel):
    name: str
    price_usd: float
    buy_url: str
    image_url: str
    brand: str
    category: str


class OutfitRecommendation(BaseModel):
    id: str
    name: str
    description: str
    why_it_works: str
    items: list[OutfitItem]
    total_price_usd: float
    style_tags: list[str]
    image_url: str
    recommendation_category: RecommendationCategory = RecommendationCategory.clothing
    sub_category: RecommendationSubCategory = RecommendationSubCategory.western
    source: RecommendationSource = RecommendationSource.ai
    confidence: float = 0.85


class ProductColor(BaseModel):
    name: str
    hex: Optional[str] = None
    undertone_tags: list[str] = []
    season_tags: list[str] = []


class CatalogProduct(BaseModel):
    id: str
    title: str
    brand: str
    marketplace: Marketplace
    category: str
    sub_category: str
    gender: str
    image_url: str
    product_url: str
    affiliate_url: Optional[str] = None
    price_inr: float
    original_price_inr: Optional[float] = None
    currency: str = "INR"
    colors: list[ProductColor]
    sizes: list[str] = []
    available_sizes: list[str] = []
    fit: Optional[str] = None
    fabric: Optional[str] = None
    pattern: Optional[str] = None
    tags: list[str] = []
    rating: Optional[float] = None
    returnable: bool = True

    @field_validator("sizes", "available_sizes", mode="before")
    @classmethod
    def normalize_sizes(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class ProductMatch(BaseModel):
    product: CatalogProduct
    score: float
    reasons: list[str]
    warnings: list[str] = []


class ProductRecommendationResponse(BaseModel):
    job_id: str
    status: str
    fit_profile: FitProfile
    products: list[ProductMatch]


class CatalogSyncResponse(BaseModel):
    status: str
    provider: Marketplace
    configured: bool
    products_synced: int = 0
    cache_path: Optional[str] = None
    message: Optional[str] = None


class CatalogImportResponse(BaseModel):
    status: str
    provider: Marketplace
    products_imported: int = 0
    cache_path: str
    message: Optional[str] = None


class CatalogStatusResponse(BaseModel):
    seed_products: int
    cached_products: int
    cache_path: str
    providers: dict[str, bool]


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    display_name: str
    email: Optional[str] = None


class AuthResponse(BaseModel):
    status: str
    user: UserProfile
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class OtpRequest(BaseModel):
    email: str
    display_name: Optional[str] = None


class OtpRequestResponse(BaseModel):
    status: str
    email: str
    expires_in_seconds: int
    delivery: str
    dev_otp: Optional[str] = None


class OtpVerifyRequest(BaseModel):
    email: str
    otp_code: str
    display_name: Optional[str] = None


class ClaimSessionRequest(BaseModel):
    user_id: Optional[str] = None
    profile_name: Optional[str] = None
    session_token: Optional[str] = None


class ClaimSessionResponse(BaseModel):
    status: str
    job_id: str
    profile_name: str
    user: UserProfile


class UserSessionSummary(BaseModel):
    job_id: str
    status: str
    profile_name: Optional[str] = None
    created_at: Optional[datetime] = None
    gender: str
    skin_label: Optional[str] = None
    color_season: Optional[str] = None
    style_vibes: list[str] = []


class UserSessionsResponse(BaseModel):
    user: UserProfile
    sessions: list[UserSessionSummary]


class CostPolicyResponse(BaseModel):
    analysis_limit_per_user_per_day: int
    guest_analysis_limit_per_day: int
    visual_generation_requires_auth: bool
    visual_generation_trigger: str
    standalone_visual_generation_enabled: bool = False
    max_visual_generations_per_user_per_day: int = 1
    max_daily_ai_cost_per_user_usd: float = 0
    cost_tracking_enabled: bool = True
    dev_otp_enabled: bool = False
    email_delivery_configured: bool = False
    pricing: dict[str, float] = Field(default_factory=dict)
    guardrails: list[str]


class AIUsageLedgerEntry(BaseModel):
    id: str
    job_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: str
    provider: str
    model: str
    status: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    image_count: int = 0
    estimated_cost_usd: float = 0
    actual_cost_usd: Optional[float] = None
    currency: str = "USD"
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class AIUsageLedgerResponse(BaseModel):
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    total_estimated_cost_usd: float = 0
    total_actual_cost_usd: Optional[float] = None
    total_tokens: int = 0
    entries: list[AIUsageLedgerEntry] = Field(default_factory=list)


# --- Request/Response Models ---

class SessionCreate(BaseModel):
    gender: Gender = Gender.men
    age_range: Optional[str] = None  # 18-25, 26-35, 36-45, 46-55, 55+
    occasion: Optional[list[str]] = None
    goals: Optional[list[str]] = None
    budget_min: float = 50
    budget_max: float = 300
    style_preferences: list[str] = []
    wear_type: str = "all"  # western, indian, fusion, all
    fit_profile: Optional[FitProfile] = None


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: Optional[datetime] = None


class AnalysisResponse(BaseModel):
    status: str
    profile: Optional[StyleProfile] = None
    recommendations: Optional[dict[str, list[OutfitRecommendation]]] = None


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: str
    session_id: Optional[str] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class VisualAnalysisResponse(BaseModel):
    job_id: str
    status: str
    kind: VisualAnalysisKind
    image_url: str
    prompt_version: str
    process: list[str]


class RecommendationRequest(BaseModel):
    profile: StyleProfile
    budget_min: float = 50
    budget_max: float = 300
    style_preferences: list[str] = []
    wear_type: str = "all"
    occasion: Optional[list[str]] = None
    goals: Optional[list[str]] = None


class AnalyzeRequest(BaseModel):
    gender: Gender
    budget_min: float = 50
    budget_max: float = 300
    style_preferences: list[str] = []
