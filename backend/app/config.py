import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    GROQ_API_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production"
    APP_USERNAME: str = "subidh"
    APP_PASSWORD: str = "subidh"
    JOOBLE_API_KEY: str = ""
    WELLFOUND_SESSION: str = ""
    WELLFOUND_CF: str = ""
    WELLFOUND_DATADOME: str = ""
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CLAIM_EMAIL: str = ""
    FRONTEND_URL: str = ""
    CORS_ORIGINS: str = ""  # Comma-separated list of allowed origins

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_cors_origins(self) -> list[str]:
        """Build the list of allowed CORS origins from config."""
        origins = ["http://localhost:3000", "http://localhost:3001"]
        if self.FRONTEND_URL:
            origins.append(self.FRONTEND_URL.rstrip("/"))
        if self.CORS_ORIGINS:
            for origin in self.CORS_ORIGINS.split(","):
                stripped = origin.strip().rstrip("/")
                if stripped and stripped not in origins:
                    origins.append(stripped)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
