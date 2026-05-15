"""Gemini-powered fraud agent with dashboard tool actions."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.ai.agent.knowledge_base import (
    default_top_k,
    fallback_score_threshold,
    format_for_prompt,
    retrieve,
)
from app.ai.agent.memory_index import build_memory, resolve_query_context
from app.core.config import settings
from app.core.socket_manager import broadcast_agent_action, broadcast_agent_message, broadcast_agent_state

logger = logging.getLogger(__name__)

_sessions: dict[str, list[dict[str, str]]] = {}

SYSTEM_PROMPT = """You are Titan, a fraud operations AI agent for Nigerian payment monitoring (Squad Sentinel).
Use the Knowledge FAQ snippets for greetings, app how-to, setup, and fraud concepts.
Use the Context JSON for live transfers, links, and alerts—always cite transaction_ref when mentioning a transfer.
If the user asks about connections between people (e.g. Bolu and Daniel), explain shared receivers, devices, or graph paths from the links array.
You may request dashboard actions via JSON objects with a "type" field when it helps the analyst.
Be concise (2-5 sentences unless asked for detail)."""


def _actions_from_kb(hit: dict | None) -> list[dict[str, Any]]:
    if not hit:
        return []
    raw = hit.get("actions") or []
    return [a for a in raw if isinstance(a, dict) and a.get("type")]


def _fallback_reply(
    message: str,
    context: dict[str, Any],
    knowledge_hits: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    hits = knowledge_hits if knowledge_hits is not None else retrieve(message, k=default_top_k())
    top = hits[0] if hits else None
    if top and top.get("score", 0) >= fallback_score_threshold():
        return top.get("answer", "").strip(), _actions_from_kb(top)

    txs = context.get("transactions") or []
    links = context.get("links") or []
    actions: list[dict[str, Any]] = []

    msg = message.lower()
    if "bolu" in msg and "daniel" in msg:
        shared = [l for l in links if l.get("type") in ("shared_receiver", "shared_device", "graph_path")]
        if shared:
            reason = shared[0].get("reason", "shared payment pattern")
            refs = shared[0].get("transaction_refs", [])
            reply = (
                f"Bolu and Daniel appear linked: {reason}. "
                f"See transfers {', '.join(refs[:3])}."
            )
        else:
            bolu = [t for t in txs if "bolu" in (t.get("sender_name") or "").lower()]
            daniel = [t for t in txs if "daniel" in (t.get("sender_name") or "").lower()]
            reply = (
                f"I found {len(bolu)} transfer(s) from Bolu and {len(daniel)} from Daniel. "
                "No shared receiver link in current memory — run more OPay-heavy simulation."
            )
            if bolu:
                actions.append({"type": "highlight_transaction", "transaction_ref": bolu[0]["transaction_ref"]})
        return reply, actions

    if txs:
        t0 = txs[0]
        reply = (
            f"Scanned {len(txs)} relevant transfer(s). Latest: {t0.get('sender_name') or 'unknown'} "
            f"→ {t0.get('receiver_bank')} ({t0.get('transaction_ref')}), status {t0.get('status')}."
        )
        if "flag" in msg or "alert" in msg or "held" in msg:
            actions.append({"type": "filter_transactions", "status": "flagged"})
        return reply, actions

    if top:
        return top.get("answer", "").strip(), _actions_from_kb(top)

    return (
        "No matching transactions in memory yet. Start the backend and run simulate.py to ingest demo data.",
        actions,
    )


def _parse_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """Extract JSON tool calls if model returns them inline."""
    actions: list[dict[str, Any]] = []
    for block in re.findall(r"\{[^{}]*\"type\"\s*:\s*\"[^\"]+\"[^{}]*\}", text):
        try:
            obj = json.loads(block)
            if "type" in obj:
                actions.append(obj)
        except json.JSONDecodeError:
            continue
    return actions


async def _gemini_chat(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    knowledge_hits: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    api_key = settings.get("GEMINI_API_KEY") or ""
    if not api_key:
        return _fallback_reply(message, context, knowledge_hits)

    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai not installed")
        return _fallback_reply(message, context, knowledge_hits)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        settings.get("GEMINI_MODEL") or "gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    knowledge_blob = format_for_prompt(knowledge_hits)[:8000]
    context_blob = json.dumps(context, default=str)[:12000]
    hist_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    prompt = (
        f"Knowledge (similar FAQs):\n{knowledge_blob}\n\n"
        f"Context (live data):\n{context_blob}\n\n"
        f"Chat history:\n{hist_text}\n\n"
        f"User: {message}\n\nAssistant:"
    )

    try:
        response = model.generate_content(prompt)
        try:
            text = (response.text or "").strip()
        except ValueError as ve:
            # Blocked or empty candidates — SDK raises instead of returning ""
            logger.warning("Gemini returned no text (safety/block?): %s", ve)
            text = ""
        if not text:
            logger.warning("Gemini empty reply; model=%s", settings.get("GEMINI_MODEL"))
            return _fallback_reply(message, context, knowledge_hits)
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
        return _fallback_reply(message, context, knowledge_hits)

    actions = _parse_tool_calls_from_text(text)
    if not actions and knowledge_hits:
        actions = _actions_from_kb(knowledge_hits[0])
    return text, actions


async def chat(
    db: Session,
    message: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    history = _sessions.setdefault(sid, [])

    memory = build_memory(db)
    context = resolve_query_context(memory, message)
    knowledge_hits = retrieve(message, k=default_top_k())

    await broadcast_agent_state({"state": "thinking", "session_id": sid})

    reply, actions = await _gemini_chat(message, context, history, knowledge_hits)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        _sessions[sid] = history[-20:]

    await broadcast_agent_message({"session_id": sid, "role": "assistant", "content": reply})
    for action in actions:
        await broadcast_agent_action(action)
    await broadcast_agent_state({"state": "idle", "session_id": sid})

    return {
        "session_id": sid,
        "reply": reply,
        "actions": actions,
        "context_size": len(context.get("transactions", [])),
        "knowledge_hits": len(knowledge_hits),
    }


async def narrate_fraud_alert(alert_payload: dict[str, Any]) -> None:
    """Auto-announce high-severity alerts on the agent bubble."""
    name = alert_payload.get("sender_name") or alert_payload.get("sender_account", "Unknown")
    bank = alert_payload.get("receiver_bank", "")
    ref = alert_payload.get("transaction_ref", "")
    summary = (
        f"Alert: {name} → {bank}. Risk {(float(alert_payload.get('risk_score', 0)) * 100):.0f}%. "
        f"Ref {ref}. {alert_payload.get('pattern_type', 'fraud')}."
    )
    await broadcast_agent_state({"state": "alert"})
    await broadcast_agent_message({"role": "assistant", "content": summary, "auto": True})
    alert_id = alert_payload.get("alert_id")
    if alert_id:
        await broadcast_agent_action({"type": "pin_alert", "alert_id": alert_id})
    if ref:
        await broadcast_agent_action({"type": "highlight_transaction", "transaction_ref": ref})
    await broadcast_agent_state({"state": "idle"})
