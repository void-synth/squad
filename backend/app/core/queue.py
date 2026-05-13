"""Redis-backed transaction queue."""

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "transaction_queue"
_redis: redis.Redis | None = None


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings["REDIS_URL"], decode_responses=True)
    return _redis


async def push_transaction(data: dict[str, Any]) -> None:
    """Serialize transaction dict as JSON and LPUSH to the queue."""
    try:
        r = _client()
        await r.lpush(QUEUE_KEY, json.dumps(data))
    except Exception as e:
        logger.exception("Redis push_transaction failed: %s", e)


async def pop_transaction() -> dict[str, Any] | None:
    """Blocking pop from the right of the list (FIFO with LPUSH). Timeout 1s."""
    try:
        r = _client()
        result = await r.brpop(QUEUE_KEY, timeout=1)
        if result is None:
            return None
        _, payload = result
        return json.loads(payload)
    except Exception as e:
        logger.exception("Redis pop_transaction failed: %s", e)
        return None


async def get_queue_length() -> int:
    try:
        r = _client()
        return int(await r.llen(QUEUE_KEY))
    except Exception as e:
        logger.exception("Redis get_queue_length failed: %s", e)
        return -1
