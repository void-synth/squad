"""Load environment variables for Titan."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings() -> dict:
    """Return settings dict (cached) from environment."""
    return {
        "SQUAD_SECRET_KEY": os.getenv("SQUAD_SECRET_KEY", ""),
        "SQUAD_PUBLIC_KEY": os.getenv("SQUAD_PUBLIC_KEY", ""),
        "SQUAD_BASE_URL": os.getenv("SQUAD_BASE_URL", "https://sandbox-api-d.squadco.com").rstrip("/"),
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "APP_SECRET": os.getenv("APP_SECRET", ""),
    }


settings = get_settings()
