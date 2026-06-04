from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./soc_phishing.db"

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # Gmail Watch
    GMAIL_ACCOUNT: str = ""
    PUBSUB_TOPIC: str = ""
    WEBHOOK_TOKEN: str = "changeme"

    # JWT Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_MINUTES: int = 10080  # 7 days

    # Dashboard URL (for post-OAuth redirect). FRONTEND_URL is used by the
    # React SPA; STREAMLIT_URL is kept for the legacy dashboard.
    FRONTEND_URL: str = "http://localhost:5173"
    STREAMLIT_URL: str = "http://localhost:8501"

    # AI Model paths
    NLP_MODEL_PATH: str = "../models/nlp_model.pkl"
    URL_MODEL_PATH: str = "../models/url_model.pkl"

    # Risk thresholds
    SUSPICIOUS_THRESHOLD: float = 0.40
    DANGEROUS_THRESHOLD: float = 0.70

    # Ensemble weights
    EMAIL_WEIGHT: float = 0.45
    URL_WEIGHT: float = 0.45
    RULE_WEIGHT: float = 0.10


@lru_cache
def get_settings() -> Settings:
    return Settings()
