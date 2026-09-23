"""Application settings loaded from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jev_mode: str = os.getenv("JEV_MODE", "mock").lower()
    jev_api_url: str = os.getenv("JEV_API_URL", "")
    jev_api_key: str = os.getenv("JEV_API_KEY", "")


settings = Settings()
