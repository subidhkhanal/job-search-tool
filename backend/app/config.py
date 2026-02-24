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

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
