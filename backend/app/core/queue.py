"""Transaction queue: Redis when available, in-memory fallback for local demo."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "transaction_queue"
_redis: redis.Redis | None = None
_redis_ok: bool | None = None
_memory: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


async def queue_backend() -> str:
    """``redis`` or ``memory`` — used by health checks."""
    return "redis" if await _use_redis() else "memory"


async def _use_redis() -> bool:
    global _redis, _redis_ok
    if _redis_ok is not None:
        return _redis_ok
    try:
        if _redis is None:
            _redis = redis.from_url(settings["REDIS_URL"], decode_responses=True)
        await _redis.ping()
        _redis_ok = True
        logger.info("Transaction queue using Redis (%s)", settings["REDIS_URL"])
    except Exception as exc:
        _redis_ok = False
        logger.warning(
            "Redis unavailable (%s); using in-memory queue (fine for local demo, not for production).",
            exc,
        )
    return _redis_ok


async def push_transaction(data: dict[str, Any]) -> None:
    if await _use_redis():
        try:
            await _redis.lpush(QUEUE_KEY, json.dumps(data))  # type: ignore[union-attr]
            return
        except Exception:
            logger.exception("Redis push_transaction failed; using in-memory queue")
    await _memory.put(data)


async def pop_transaction() -> dict[str, Any] | None:
    if await _use_redis():
        try:
            result = await _redis.brpop(QUEUE_KEY, timeout=1)  # type: ignore[union-attr]
            if result is None:
                return None
            _, payload = result
            return json.loads(payload)
        except Exception:
            logger.exception("Redis pop_transaction failed")
            return None
    try:
        return await asyncio.wait_for(_memory.get(), timeout=1.0)
    except asyncio.TimeoutError:
        return None


async def get_queue_length() -> int:
    if await _use_redis():
        try:
            return int(await _redis.llen(QUEUE_KEY))  # type: ignore[union-attr]
        except Exception:
            logger.exception("Redis get_queue_length failed")
    return _memory.qsize()
