"""
Core Configuration Settings
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()

# Directory helpers
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application configuration settings — all values can be overridden via .env"""

    # ── Application ─────────────────────────────────────────────────────────────
    APP_NAME: str = "Smart Healthcare Appointment Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ── Security ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Internal Service-to-Service Auth ─────────────────────────────────────────
    # IMPORTANT: This MUST match ML_SERVICE_API_KEY in your NestJS .env
    INTERNAL_API_KEY: str = "my-shared-internal-key-12345"

    # ── Database ─────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:root@localhost:5432/shams_db"

    # ── Redis ────────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── CORS ─────────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ── External Services ────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@shams.com"

    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # ── AI / ML ──────────────────────────────────────────────────────────────────
    ML_MODELS_PATH: str = str(PROJECT_ROOT / "ml_models" / "trained_models")

    @property
    def NO_SHOW_MODEL_PATH(self) -> str:
        return str(Path(self.ML_MODELS_PATH) / "noshow_model.pkl")

    @property
    def WAIT_TIME_MODEL_PATH(self) -> str:
        keras_path = Path(self.ML_MODELS_PATH) / "waittime_model.keras"
        if keras_path.exists():
            return str(keras_path)
        return str(Path(self.ML_MODELS_PATH) / "waittime_model.h5")

    @property
    def PRIORITY_MODEL_PATH(self) -> str:
        return str(Path(self.ML_MODELS_PATH) / "priority_model.pkl")

    # ── Clinic Settings ──────────────────────────────────────────────────────────
    DEFAULT_APPOINTMENT_DURATION: int = 30
    WORKING_HOURS_START: str = "08:00"
    WORKING_HOURS_END: str = "17:00"
    APPOINTMENT_REMINDER_HOURS: int = 24

    # ── Queue Management ─────────────────────────────────────────────────────────
    MAX_QUEUE_SIZE: int = 50
    EMERGENCY_PRIORITY_WEIGHT: float = 3.0
    HIGH_PRIORITY_WEIGHT: float = 2.0
    MEDIUM_PRIORITY_WEIGHT: float = 1.5
    LOW_PRIORITY_WEIGHT: float = 1.0

    # ── Rate Limiting / Pagination ───────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── Validators ───────────────────────────────────────────────────────────────
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v]
        return v if isinstance(v, list) else v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Singleton
settings = Settings()

# Debug output on import
print(f"📁 Project Root   : {PROJECT_ROOT}")
print(f"📁 Backend Dir    : {BACKEND_DIR}")
print(f"📁 ML Models Path : {settings.ML_MODELS_PATH}")
print(f"🔑 Internal Key   : {'SET ✅' if settings.INTERNAL_API_KEY != 'my-shared-internal-key-12345' else 'DEFAULT ⚠️  (change in production)'}")
