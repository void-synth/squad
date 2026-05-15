"""Load environment variables for Titan."""

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _normalize_database_url(raw: str) -> str:
    """Strip placeholders/quotes; map Render postgres:// → postgresql:// for SQLAlchemy."""
    url = (raw or "").strip().strip('"').strip("'")
    if not url:
        return ""
    upper = url.upper()
    if upper.startswith("YOUR_") or "REPLACE_WITH" in upper or url == "postgresql://USER:PASSWORD@HOST:5432/railway":
        logger.warning("DATABASE_URL looks like a placeholder; ignoring")
        return ""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    try:
        from sqlalchemy.engine.url import make_url

        make_url(url)
    except Exception:
        logger.warning("DATABASE_URL is not a valid SQLAlchemy URL; ignoring")
        return ""
    return url


def _database_url() -> str:
    raw = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_INTERNAL") or ""
    return _normalize_database_url(raw)


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
        "DATABASE_URL": _database_url(),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "APP_SECRET": os.getenv("APP_SECRET", ""),
        # Simulated split on Squad gross (stored kobo); does not call Squad payouts.
        "TITAN_PLATFORM_FEE_RATE": _platform_fee_rate(),
        "TITAN_FEE_RECEIVER_ACCOUNT": os.getenv("TITAN_FEE_RECEIVER_ACCOUNT", "TITAN_OPS_RESERVE").strip()
        or "TITAN_OPS_RESERVE",
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash",
        "AGENT_KB_PATH": os.getenv("AGENT_KB_PATH", "").strip(),
        "AGENT_KB_TOP_K": os.getenv("AGENT_KB_TOP_K", "5").strip() or "5",
    }


settings = get_settings()
