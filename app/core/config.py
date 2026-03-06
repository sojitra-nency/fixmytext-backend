"""
Application settings loaded from environment variables via pydantic-settings.

Create a '.env' file in /backend (copy from '.env.example') to override defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # ── Project metadata ──────────────────────────────────────────────────────
    PROJECT_NAME: str = "TextUtils API"
    PROJECT_DESCRIPTION: str = (
        "RESTful backend for the TextUtils text-manipulation application."
    )
    VERSION: str = "0.1.0"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list in .env: ALLOWED_ORIGINS=http://localhost:3000,https://myapp.com
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
