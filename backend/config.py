"""
Centralized configuration management for ShieldAI backend.

All environment variables are loaded via pydantic-settings BaseSettings,
providing typed, validated settings with sensible defaults.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


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
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ── Database ─────────────────────────────────────────────────
    SQLITE_DB_PATH: str = "backend/shield_ai.db"
    FIREBASE_CREDENTIALS_PATH: str = "backend/firebase-credentials.json"

    # ── AI / ML ──────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT: int = 30  # seconds
    BERT_MODEL: str = "facebook/bart-large-mnli"
    ENABLE_BERT: bool = True  # Set to False to skip BERT loading on low-memory systems

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Module-level singleton
settings = Settings()
