import os
from pydantic_settings import BaseSettings

DEFAULT_UPLOAD_DIR = "/tmp/aurafit-uploads" if os.getenv("VERCEL") else "uploads"


class Settings(BaseSettings):
    mock_mode: bool = True
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-2"
    openai_image_size: str = "1536x1024"
    openai_image_quality: str = "high"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "AuraFit"
    frontend_base_url: str = "http://localhost:3000"
    openrouter_text_model: str = "google/gemini-2.5-flash"
    openrouter_vision_model: str = "google/gemini-2.5-flash"
    openrouter_image_model: str = "openai/gpt-5.4-image-2"
    openrouter_image_aspect_ratio: str = "3:2"
    openrouter_image_size: str = "2K"
    openrouter_image_input_max_dimension: int = 1536
    llm_max_images: int = 5
    llm_image_max_dimension: int = 1280
    llm_image_quality: int = 85
    flipkart_affiliate_id: str = ""
    flipkart_affiliate_token: str = ""
    amazon_associate_tag: str = ""
    myntra_affiliate_url_template: str = ""
    snitch_affiliate_url_template: str = ""
    ajio_affiliate_url_template: str = ""
    catalog_cache_file: str = ""
    auth_token_secret: str = "change-me-dev-secret"
    auth_otp_ttl_minutes: int = 10
    auth_otp_max_attempts: int = 5
    auth_otp_request_limit: int = 5
    auth_session_ttl_days: int = 30
    auth_cookie_secure: bool = False
    auth_dev_return_otp: bool = True
    auth_require_email_delivery: bool = False
    auth_require_token_for_claim: bool = False
    analysis_requires_auth: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "AuraFit <no-reply@aurafit.local>"
    smtp_use_tls: bool = True
    analysis_limit_per_user_per_day: int = 3
    free_guest_analysis_limit_per_day: int = 3
    visual_generation_requires_auth: bool = True
    standalone_visual_generation_enabled: bool = False
    max_visual_generations_per_user_per_day: int = 1
    max_daily_ai_cost_per_user_usd: float = 1.0
    analysis_worker_enabled: bool = not bool(os.getenv("VERCEL"))
    analysis_worker_poll_interval_seconds: float = 5.0
    analysis_job_max_attempts: int = 3
    analysis_job_stale_after_seconds: int = 900
    cost_tracking_enabled: bool = True
    openrouter_text_input_cost_per_million: float = 0.0
    openrouter_text_output_cost_per_million: float = 0.0
    openrouter_vision_input_cost_per_million: float = 0.0
    openrouter_vision_output_cost_per_million: float = 0.0
    openrouter_image_input_cost_per_million: float = 0.0
    openrouter_image_output_cost_per_million: float = 0.0
    openrouter_image_cost_per_image: float = 0.0
    openai_image_cost_per_image: float = 0.0
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_enabled: bool = False
    supabase_storage_bucket: str = "aurafit"
    supabase_storage_uploads_prefix: str = "uploads"
    supabase_storage_signed_url_ttl_seconds: int = 3600
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://aurafit:aurafit@localhost:5432/aurafit"
    upload_dir: str = DEFAULT_UPLOAD_DIR

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def is_secret_configured(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in {"your_key_here", "your-key-here", "changeme"}
