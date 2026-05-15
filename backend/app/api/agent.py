"""Live fraud agent: chat + memory graph."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.agent.memory_index import build_memory
from app.ai.agent.service import chat
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


@router.post("/chat")
async def agent_chat(body: ChatBody, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return await chat(db, body.message, body.session_id)


@router.get("/memory")
def agent_memory(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return build_memory(db)
