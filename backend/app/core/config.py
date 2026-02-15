"""
Core Configuration Settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get the project root directory (parent of backend/)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """
    Application configuration settings
    """
    
    # Application
    APP_NAME: str = "Smart Healthcare Appointment Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:root@localhost:5432/shams_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Twilio (SMS)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID", None)
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN", None)
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv("TWILIO_PHONE_NUMBER", None)
    
    # SendGrid (Email)
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY", None)
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "noreply@shams.com")
    
    # Firebase (Real-time notifications)
    FIREBASE_CREDENTIALS_PATH: Optional[str] = os.getenv("FIREBASE_CREDENTIALS_PATH", None)
    
    # AI/ML Models - Using project root structure
    # Models are at: project_root/ml_models/trained_models/
    ML_MODELS_PATH: str = str(PROJECT_ROOT / "ml_models" / "trained_models")
    
    @property
    def NO_SHOW_MODEL_PATH(self) -> str:
        return str(Path(self.ML_MODELS_PATH) / "noshow_model.pkl")
    # We will support BOTH .h5 and .keras.
    # Training script (below) will save .keras by default, but loader accepts .h5 too.
    @property
    def WAIT_TIME_MODEL_PATH(self) -> str:
        keras_path = Path(self.ML_MODELS_PATH) / "waittime_model.keras"
        if keras_path.exists():
            return str(keras_path)
        return str(Path(self.ML_MODELS_PATH) / "waittime_model.h5")
    
    @property
    def PRIORITY_MODEL_PATH(self) -> str:
        return str(Path(self.ML_MODELS_PATH) / "priority_model.pkl")
    
    # Clinic Settings
    DEFAULT_APPOINTMENT_DURATION: int = 30  # minutes
    WORKING_HOURS_START: str = "08:00"
    WORKING_HOURS_END: str = "17:00"
    APPOINTMENT_REMINDER_HOURS: int = 24
    
    # Queue Management
    MAX_QUEUE_SIZE: int = 50
    EMERGENCY_PRIORITY_WEIGHT: float = 3.0
    HIGH_PRIORITY_WEIGHT: float = 2.0
    MEDIUM_PRIORITY_WEIGHT: float = 1.5
    LOW_PRIORITY_WEIGHT: float = 1.0
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v]
        elif isinstance(v, list):
            return v
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create settings instance
settings = Settings()

# Print configuration on import (for debugging)
print(f"📁 Project Root: {PROJECT_ROOT}")
print(f"📁 Backend Dir: {BACKEND_DIR}")
print(f"📁 ML Models Path: {settings.ML_MODELS_PATH}")
