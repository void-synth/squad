"""ASGI entry: FastAPI + Socket.IO."""

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import integration, transactions, webhook
from app.core.database import init_db
from app.core.socket_manager import sio


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    from app.services.processor import start_worker_background, stop_worker_background

    start_worker_background()
    try:
        yield
    finally:
        await stop_worker_background()


fastapi_app = FastAPI(title="Titan", lifespan=lifespan)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/")
def root():
    return {"status": "Titan is running"}


fastapi_app.include_router(webhook.router)
fastapi_app.include_router(transactions.router)
fastapi_app.include_router(integration.router)


# Combined ASGI app for uvicorn (HTTP + Socket.IO)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
