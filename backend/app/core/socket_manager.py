"""Socket.IO server for real-time dashboard updates."""

import logging
from typing import Any

import socketio

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

connected_sids: list[str] = []


@sio.event
async def connect(sid, _environ, _auth):
    connected_sids.append(sid)
    logger.info("Socket.IO client connected: %s (total=%s)", sid, len(connected_sids))


@sio.event
async def disconnect(sid):
    if sid in connected_sids:
        connected_sids.remove(sid)
    logger.info("Socket.IO client disconnected: %s", sid)


async def broadcast_transaction(data: dict[str, Any]) -> None:
    await sio.emit("new_transaction", data)


async def broadcast_alert(data: dict[str, Any]) -> None:
    await sio.emit("fraud_alert", data)


async def broadcast_stats(data: dict[str, Any]) -> None:
    await sio.emit("stats_update", data)


async def broadcast_agent_message(data: dict[str, Any]) -> None:
    await sio.emit("agent_message", data)


async def broadcast_agent_action(data: dict[str, Any]) -> None:
    await sio.emit("agent_action", data)


async def broadcast_agent_state(data: dict[str, Any]) -> None:
    await sio.emit("agent_state", data)
