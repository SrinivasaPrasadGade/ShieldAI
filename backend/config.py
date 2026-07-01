"""
Centralized configuration management for ShieldAI backend.

All environment variables are loaded via pydantic-settings BaseSettings,
providing typed, validated settings with sensible defaults.
"""

from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "ShieldAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered intelligence platform for digital public safety"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ── Database & Storage ───────────────────────────────────────
    SQLITE_DB_PATH: str = "backend/data/shield_ai.db"
    FIREBASE_CREDENTIALS_PATH: str = "backend/firebase-credentials.json"
    FIREBASE_CREDENTIALS_JSON: str = ""
    FIREBASE_CREDENTIALS_B64: str = ""
    FIREBASE_STORAGE_BUCKET: str = "shieldai-hackathon.appspot.com"  # Replace with actual bucket name

    @property
    def sqlite_db_abs_path(self) -> str:
        """Resolve SQLITE_DB_PATH to an absolute path relative to PROJECT_ROOT if it is relative."""
        path = Path(self.SQLITE_DB_PATH)
        if path.is_absolute():
            return str(path)
        return str((PROJECT_ROOT / path).resolve())

    @property
    def firebase_credentials_abs_path(self) -> str:
        """Resolve FIREBASE_CREDENTIALS_PATH to an absolute path relative to PROJECT_ROOT if it is relative."""
        path = Path(self.FIREBASE_CREDENTIALS_PATH)
        if path.is_absolute():
            return str(path)
        return str((PROJECT_ROOT / path).resolve())
    
    # ── AI / ML ──────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT: int = 30  # seconds
    ZERO_SHOT_MODEL: str = "facebook/bart-large-mnli"  # Hugging Face zero-shot classifier (BART-MNLI)
    ENABLE_ZERO_SHOT: bool = False  # Set to True to enable the local HF zero-shot classifier

    # ── HF Model Cache ───────────────────────────────────────────
    HF_HOME: str = ""  # Override Hugging Face model cache directory

    @model_validator(mode="before")
    @classmethod
    def _backward_compat_bert_vars(cls, values):
        """Support legacy ENABLE_BERT / BERT_MODEL env vars for one release cycle."""
        if "ENABLE_ZERO_SHOT" not in values and "ENABLE_BERT" in values:
            values["ENABLE_ZERO_SHOT"] = values.pop("ENABLE_BERT")
        if "ZERO_SHOT_MODEL" not in values and "BERT_MODEL" in values:
            values["ZERO_SHOT_MODEL"] = values.pop("BERT_MODEL")
        return values

    # ── Async Task Store ─────────────────────────────────────────
    TASK_TTL_HOURS: int = 24
    TASK_STALE_TIMEOUT_MINUTES: int = 15
    TASK_CLEANUP_INTERVAL_MINUTES: int = 30

    # ── File Upload Limits ───────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/webp"
    ALLOWED_AUDIO_TYPES: str = "audio/mpeg,audio/wav,audio/ogg,audio/flac,audio/webm"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_image_type_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_IMAGE_TYPES.split(",")]

    @property
    def allowed_audio_type_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_AUDIO_TYPES.split(",")]

    # ── Twilio (WhatsApp Webhook) ────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60  # requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # window duration

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {
        "env_file": (PROJECT_ROOT / ".env", BASE_DIR / ".env", ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Module-level singleton
settings = Settings()
