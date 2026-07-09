"""Test configuration.

The app is AI-only: `build_plan` always calls the Groq LLM through the single seam
`app.agent.llm._call_planner`. There is no offline/regex planner in production. To keep
the suite hermetic (no network, no quota, deterministic), we patch that one seam with a
fake planner that returns canned tool-plan JSON for the known test prompts — exactly as a
real LLM would. The rest of the pipeline (LangGraph graph, tools, and the deterministic
normalization layer) runs for real, so these are genuine integration tests of everything
except the model call.
"""

import json
import os

import pytest

os.environ["AIVOA_USE_LIVE_LLM"] = "false"
os.environ.setdefault("DATABASE_URL", "mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm")

from app.agent import llm as llm_module  # noqa: E402
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


def _wrap(intent: str, fields: dict, tool: str) -> dict:
    return {
        "intent": intent,
        "confidence": "high",
        "extracted_fields": fields,
        "tool_calls": [{"tool_name": tool, "arguments": {}, "reason": "fake planner"}],
    }


def _user_message(messages) -> str:
    """Pull just the user's message out of the planner prompt (ignore the draft JSON)."""
    content = messages[-1].content if messages else ""
    marker = "User message:"
    idx = content.rfind(marker)
    return (content[idx + len(marker):] if idx >= 0 else content).strip()


def _plan_for(text: str) -> dict:
    low = text.lower()
    # --- display-preference edit ---
    if "24-hour" in low or "24 hour" in low:
        return _wrap("edit_interaction", {"time_format": "24h", "interaction_timezone": "Asia/Dubai"}, "edit_interaction")
    # --- content edit ---
    if "change sentiment to neutral" in low or ("sentiment" in low and "neutral" in low and "change" in low):
        return _wrap("edit_interaction", {"sentiment": "Neutral"}, "edit_interaction")
    # --- messy log: fake returns RAW messy values so the production normalization
    #     layer is exercised end-to-end (name/date/sentiment cleanup happen downstream) ---
    if "amit kumar" in low:
        return _wrap(
            "log_interaction",
            {
                "hcp_name": "dr.amit kumar",
                "interaction_date": "1st jan 2025",
                "interaction_time": "14:00",
                "topics_discussed": "PhotonX",
                "sentiment": "Posotive",
                "materials_shared": "brochure",
            },
            "log_interaction",
        )
    if "meera kapoor" in low:
        fields = {
            "hcp_name": "Dr. Meera Kapoor",
            "interaction_type": "Meeting",
            "interaction_date": "2025-04-19",
            "interaction_time": "19:36",
            "attendees": "Ravi, Neha",
            "topics_discussed": "Prodo-X efficacy and patient adherence",
            "products_discussed": "Prodo-X",
            "sentiment": "Positive",
            "materials_shared": "brochure, safety card",
        }
        if "follow-up actions" in low:
            fields["follow_up_actions"] = "send the approved safety data sheet next Friday"
        return _wrap(
            "log_interaction",
            fields,
            "log_interaction",
        )
    if "arjun menon" in low:
        return _wrap(
            "log_interaction",
            {
                "hcp_name": "Dr. Arjun Menon",
                "interaction_date": "2025-04-19",
                "interaction_time": "19:36",
                "topics_discussed": "renal dosing",
                "sentiment": "Positive",
                "materials_shared": "safety card",
            },
            "log_interaction",
        )
    if "priya shah" in low:
        fields = {
            "hcp_name": "Dr. Priya Shah",
            "interaction_date": "2025-04-19",
            "interaction_time": "19:36",
            "topics_discussed": "patient affordability",
            "sentiment": "Positive",
            "materials_shared": "affordability card",
        }
        if "follow-up" in low or "follow up" in low:
            fields["follow_up_date"] = "2025-04-22"
        return _wrap(
            "log_interaction",
            fields,
            "log_interaction",
        )
    return {"intent": "help", "confidence": "high", "extracted_fields": {}, "tool_calls": []}


def _fake_call_planner(messages, model_override=None):
    return json.dumps(_plan_for(_user_message(messages))), (model_override or "fake-model")


@pytest.fixture(autouse=True)
def _mock_llm_planner(monkeypatch):
    """Replace the single LLM seam so no live Groq call is made during tests."""
    monkeypatch.setattr(llm_module, "_call_planner", _fake_call_planner)
