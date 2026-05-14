"""Load environment variables for Titan."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _platform_fee_rate() -> float:
    raw = os.getenv("TITAN_PLATFORM_FEE_RATE", "0.05")
    try:
        r = float(raw)
    except (TypeError, ValueError):
        r = 0.05
    return max(0.0, min(1.0, r))


@lru_cache
def get_settings() -> dict:
    """Return settings dict (cached) from environment."""
    return {
        "SQUAD_SECRET_KEY": os.getenv("SQUAD_SECRET_KEY", ""),
        "SQUAD_PUBLIC_KEY": os.getenv("SQUAD_PUBLIC_KEY", ""),
        "SQUAD_BASE_URL": os.getenv("SQUAD_BASE_URL", "https://sandbox-api-d.squadco.com").rstrip("/"),
        "SQUAD_WEBHOOK_LEGACY_SHA256": _truthy("SQUAD_WEBHOOK_LEGACY_SHA256", default=True),
        "SQUAD_VERIFY_ON_INGEST": _truthy("SQUAD_VERIFY_ON_INGEST", default=False),
        "SQUAD_ENABLE_PAYOUT": _truthy("SQUAD_ENABLE_PAYOUT", default=False),
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "APP_SECRET": os.getenv("APP_SECRET", ""),
        # Simulated split on Squad gross (stored kobo); does not call Squad payouts.
        "TITAN_PLATFORM_FEE_RATE": _platform_fee_rate(),
        "TITAN_FEE_RECEIVER_ACCOUNT": os.getenv("TITAN_FEE_RECEIVER_ACCOUNT", "TITAN_OPS_RESERVE").strip()
        or "TITAN_OPS_RESERVE",
    }


settings = get_settings()
