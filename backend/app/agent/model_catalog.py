"""Groq model catalog and live status checks for the Developer settings panel.

The assignment specified `gemma2-9b-it` and `llama-3.3-70b-versatile`. Both are on
Groq's deprecation path (gemma2 is already decommissioned; the llama models
deprecate 2026-08-16), so this module exposes a switchable catalog that includes the
specified models plus Groq's recommended, still-supported replacements, and can ping
each model live to report whether it actually works from the current account.
"""

from __future__ import annotations

import time
from typing import Any

from app.config import get_settings

# Ordered best-first. `tier`: recommended | deprecating | decommissioned.
# `role` documents how each maps to the assignment's named models.
GROQ_MODEL_CATALOG: list[dict[str, str]] = [
    {
        "id": "openai/gpt-oss-120b",
        "label": "GPT-OSS 120B",
        "tier": "recommended",
        "role": "Default primary planner. Groq-recommended replacement for llama-3.3-70b-versatile.",
    },
    {
        "id": "openai/gpt-oss-20b",
        "label": "GPT-OSS 20B",
        "tier": "recommended",
        "role": "Default fallback. Fast, Groq-recommended replacement for llama-3.1-8b-instant.",
    },
    {
        "id": "qwen/qwen3-32b",
        "label": "Qwen3 32B",
        "tier": "recommended",
        "role": "Alternative recommended model (emits reasoning tokens; handled by the JSON parser).",
    },
    {
        "id": "llama-3.3-70b-versatile",
        "label": "Llama 3.3 70B Versatile",
        "tier": "deprecating",
        "role": "Assignment-specified 'for context' model. Groq deprecation: 2026-08-16.",
    },
    {
        "id": "llama-3.1-8b-instant",
        "label": "Llama 3.1 8B Instant",
        "tier": "deprecating",
        "role": "Fast small model. Groq deprecation: 2026-08-16.",
    },
    {
        "id": "gemma2-9b-it",
        "label": "Gemma2 9B IT",
        "tier": "decommissioned",
        "role": "Assignment-specified primary model. Decommissioned on Groq (kept for transparency).",
    },
]

CATALOG_IDS = {m["id"] for m in GROQ_MODEL_CATALOG}


def _api_key() -> str | None:
    settings = get_settings()
    return settings.groq_api_key


def key_configured() -> bool:
    return bool(_api_key())


def check_model(model_id: str) -> dict[str, Any]:
    """Ping a model with a minimal completion to confirm it is reachable and working.

    Returns a status dict: status in {online, decommissioned, error, unconfigured}.
    """
    key = _api_key()
    if not key:
        return {"id": model_id, "status": "unconfigured", "detail": "No Groq API key configured."}
    try:
        from langchain_core.messages import HumanMessage
        from langchain_groq import ChatGroq
    except ImportError:
        return {"id": model_id, "status": "error", "detail": "langchain-groq is not installed."}

    started = time.monotonic()
    try:
        model = ChatGroq(api_key=key, model=model_id, temperature=0, max_tokens=4)
        model.invoke([HumanMessage(content="ping")])
        return {"id": model_id, "status": "online", "latency_ms": round((time.monotonic() - started) * 1000)}
    except Exception as exc:  # noqa: BLE001 - surface any provider error to the dev panel
        message = str(exc)
        lowered = message.lower()
        if "decommission" in lowered or "has been deprecated" in lowered:
            status = "decommissioned"
        elif "does not exist" in lowered or "404" in lowered:
            status = "not_found"
        else:
            status = "error"
        return {"id": model_id, "status": status, "detail": message[:280]}


def catalog_with_context() -> dict[str, Any]:
    settings = get_settings()
    return {
        "models": GROQ_MODEL_CATALOG,
        "active_model": settings.groq_model,
        "fallback_model": settings.groq_fallback_model,
        "live_llm_enabled": settings.aivoa_use_live_llm,
        "key_configured": key_configured(),
    }
