from __future__ import annotations

import json
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.tools import tool_catalog_for_prompt
from app.config import get_settings
from app.schemas import InteractionDraft, InteractionPlan, InteractionPreferences, PlannedTool


_GROQ_CALL_TIMESTAMPS: list[float] = []


PLANNER_SYSTEM_PROMPT = """You are the reasoning-and-planning engine behind an AI-first life-sciences CRM
"Log HCP Interaction" screen. A pharmaceutical field representative talks to you in natural language to
log or correct a meeting with a Healthcare Professional (HCP). The form on the left is READ-ONLY for the
human — it changes ONLY through the LangGraph tools you schedule. Read the message, extract clean
structured CRM fields, decide which tools run, and reply with STRICT JSON ONLY — no prose, no markdown,
no code fences, and no <think> reasoning in the output.

WRITE ROBUST, NORMALIZED VALUES. Reps type fast on phones, so expect and silently correct mistakes:
- Spelling: "Posotive"/"positve" -> "Positive"; "dshared"/"shaired" -> "shared"; "recieved" -> "received".
- Names: expand and capitalize. "dr.amit kumar" / "dr amit kumar" -> "Dr. Amit Kumar". Keep the title.
- Dates: output ISO "YYYY-MM-DD". Resolve ordinals/words: "1st jan 2025" -> "2025-01-01",
  "April 19, 2025" -> "2025-04-19". Leave genuinely relative dates as the phrase ("next Friday", "tomorrow").
- Times: output 24-hour "HH:MM" ("2 pm" -> "14:00", "7:36 PM" -> "19:36").

FIELD SEPARATION — never dump everything into one field. Only include a field the message actually
contains; do NOT invent values:
- hcp_name: the doctor's name.
- interaction_type: one of Meeting, Call, Email, Webinar, Conference, Clinic Visit (default Meeting).
- interaction_date / interaction_time: when it happened.
- attendees: other people present (comma-separated names).
- topics_discussed: clinical/scientific discussion points and therapies (e.g. "PhotonX efficacy",
  "renal dosing"). NEVER put sentiment or materials here.
- products_discussed: brand/product names named (e.g. "PhotonX").
- sentiment: EXACTLY one of "Positive", "Neutral", "Negative", "Mixed".
- materials_shared: leave-behind collateral (brochure, safety card, reprint, PDF, monograph).
- samples_distributed: physical drug samples handed over.
- hcp_questions: questions the HCP asked (e.g. "asked about renal dosing").
- objections: concerns/barriers the HCP raised (e.g. affordability, access).
- outcomes: agreements or decisions reached in the meeting.
- follow_up_actions: concrete next steps/tasks after the meeting.
- follow_up_date: an explicit or relative follow-up date ("next Friday").
- organization / specialty: clinic or hospital, and medical specialty, if stated.

DISPLAY-PREFERENCE EDITS. The rep can also change how date/time are saved by talking to you. Map these to
edit_interaction with only these keys:
- "use 24-hour time" / "12-hour" -> time_format: "24h" | "12h".
- "change timezone to Asia/Dubai" / "use IST" -> interaction_timezone: an IANA name or alias.
- "show dates as DD/MM/YYYY" -> date_format: one of MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, DD MMM YYYY.

INTENT & TOOL SELECTION:
- Describing a NEW interaction -> intent "log_interaction" with a single {"tool_name":"log_interaction"}
  call. The system then auto-runs HCP lookup, compliance screening, next-best-action, follow-up
  scheduling, validation, and summary — so you list ONLY log_interaction.
- Correcting/adding to the existing record, or changing a display preference ("change...", "actually...",
  "set...", "use...") -> intent "edit_interaction" with a single {"tool_name":"edit_interaction"} call,
  and put ONLY the explicitly changed fields in extracted_fields. Never resend unchanged fields.
- Asking how to use the screen or a general question that changes nothing -> intent "help", empty
  extracted_fields, empty tool_calls.

Return EXACTLY this JSON shape and nothing else:
{
  "intent": "log_interaction | edit_interaction | help",
  "confidence": "high | medium | low",
  "extracted_fields": { "<field>": "<normalized value>" },
  "tool_calls": [ {"tool_name": "log_interaction", "arguments": {}, "reason": "<why>"} ]
}

EXAMPLE 1 (log, with typos):
User: "Met Dr.amit kumar at 2pm on 1st jan 2025 and discussed PhotonX, Posotive sentiment, dshared brochure"
{"intent":"log_interaction","confidence":"high","extracted_fields":{"hcp_name":"Dr. Amit Kumar","interaction_type":"Meeting","interaction_date":"2025-01-01","interaction_time":"14:00","topics_discussed":"PhotonX","products_discussed":"PhotonX","sentiment":"Positive","materials_shared":"brochure"},"tool_calls":[{"tool_name":"log_interaction","arguments":{},"reason":"New interaction described in natural language."}]}

EXAMPLE 2 (edit only named fields):
User: "Change the HCP to Dr. Arjun Menon and sentiment to neutral. Keep everything else the same."
{"intent":"edit_interaction","confidence":"high","extracted_fields":{"hcp_name":"Dr. Arjun Menon","sentiment":"Neutral"},"tool_calls":[{"tool_name":"edit_interaction","arguments":{},"reason":"User corrected two specific fields."}]}

EXAMPLE 3 (display-preference edit):
User: "Use 24-hour format and change the timezone to Asia/Dubai."
{"intent":"edit_interaction","confidence":"high","extracted_fields":{"time_format":"24h","interaction_timezone":"Asia/Dubai"},"tool_calls":[{"tool_name":"edit_interaction","arguments":{},"reason":"User changed display preferences only."}]}

EXAMPLE 4 (help):
User: "How do I log an interaction here?"
{"intent":"help","confidence":"high","extracted_fields":{},"tool_calls":[]}

Supported CRM field keys: hcp_name, interaction_type, interaction_date, interaction_time, attendees,
topics_discussed, interaction_timezone, date_format, time_format, specialty, organization,
products_discussed, sentiment, materials_shared, samples_distributed, outcomes, follow_up_actions,
hcp_questions, objections, follow_up_date.
"""


def _allow_groq_call() -> bool:
    settings = get_settings()
    now = time.monotonic()
    window_start = now - 60
    active = [ts for ts in _GROQ_CALL_TIMESTAMPS if ts >= window_start]
    _GROQ_CALL_TIMESTAMPS[:] = active
    if len(_GROQ_CALL_TIMESTAMPS) >= settings.aivoa_groq_calls_per_minute:
        return False
    _GROQ_CALL_TIMESTAMPS.append(now)
    return True


def _invoke_with_budget(model, messages):
    if not _allow_groq_call():
        raise RuntimeError("Local Groq call budget reached for this minute.")
    return model.invoke(messages)


class PlannerUnavailable(RuntimeError):
    """Raised when the LangGraph planner cannot reach a working LLM.

    The app is AI-only by design (the assignment forbids hard-coded logic), so we
    never silently fall back to deterministic extraction — we surface this instead.
    """


def _groq_model_configs(model_override: str | None = None) -> list[tuple[str, str]]:
    settings = get_settings()
    if not settings.aivoa_use_live_llm:
        return []
    try:
        import langchain_groq  # noqa: F401
    except ImportError:
        return []

    api_key = settings.groq_api_key

    pairs: list[tuple[str, str | None]] = []
    if model_override:
        pairs.append((model_override, api_key))
    pairs.append((settings.groq_model, api_key))
    pairs.append((settings.groq_fallback_model, api_key))

    seen: set[str] = set()
    configs: list[tuple[str, str]] = []
    for model_name, api_key in pairs:
        if model_name and api_key and model_name not in seen:
            seen.add(model_name)
            configs.append((model_name, api_key))
    return configs


def _build_groq(model_name: str, api_key: str, json_mode: bool):
    from langchain_groq import ChatGroq

    kwargs: dict[str, Any] = {"api_key": api_key, "model": model_name, "temperature": 0}
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    return ChatGroq(**kwargs)


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    # Drop <think>...</think> reasoning some models (e.g. Qwen3) emit before the JSON.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip markdown code fences the model may wrap around JSON.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _call_planner(messages, model_override: str | None = None) -> tuple[str, str]:
    """Invoke the Groq planner. Returns (raw_content, model_id_used).

    This is the single seam between LangGraph and the LLM. It is patched in tests so
    the suite never makes a live call. Raises ``PlannerUnavailable`` if no model is
    configured or every configured model fails.
    """
    configs = _groq_model_configs(model_override)
    if not configs:
        raise PlannerUnavailable(
            "Live LLM planning is disabled or no Groq API key is configured. "
            "Set AIVOA_USE_LIVE_LLM=true and provide GROQ_API_KEY."
        )
    last_error: Exception | None = None
    for model_name, api_key in configs:
        # Try native JSON mode first; retry the SAME model without it if unsupported,
        # so a model choice is never silently downgraded to the next one on JSON quirks.
        for json_mode in (True, False):
            try:
                model = _build_groq(model_name, api_key, json_mode)
                response = _invoke_with_budget(model, messages)
                return str(response.content), model_name
            except Exception as exc:  # noqa: BLE001 - collect and continue to next option
                last_error = exc
                continue
    raise PlannerUnavailable(f"All configured Groq models failed. Last error: {last_error}")


def build_plan(
    message: str,
    draft: InteractionDraft,
    preferences: InteractionPreferences | None = None,
    model_override: str | None = None,
) -> InteractionPlan:
    preferences = preferences or InteractionPreferences()
    prompt = f"""Tool catalog:
{tool_catalog_for_prompt()}

Current draft JSON:
{draft.model_dump_json()}

Active date/time preferences:
{preferences.model_dump_json()}

User message:
{message}
"""
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    content, model_used = _call_planner(messages, model_override)
    data = _extract_json(content)
    plan = _normalize_llm_plan(InteractionPlan.model_validate(data), draft)
    return plan.model_copy(update={"planner_mode": "llm", "planner_model": model_used})


def compose_response(
    message: str,
    draft: InteractionDraft,
    plan: InteractionPlan,
    tool_trace: list[dict[str, Any]],
) -> str:
    changed = [trace.get("label", trace.get("name", "")) for trace in tool_trace]
    if plan.intent == "help" and not tool_trace:
        return (
            "Describe an HCP interaction in plain language and I'll fill the form for you — for example: "
            '"Met Dr. Meera Kapoor on 04/19/2025 at 7:36 PM, discussed Prodo-X efficacy, positive sentiment, '
            'shared brochure." To correct something, just say what to change ("set sentiment to neutral"). '
            "You can also change display preferences by chat, e.g. \"use 24-hour time\" or "
            '"change timezone to Asia/Dubai". The form is AI-controlled, so everything happens through me.'
        )
    if not get_settings().aivoa_compose_with_llm:
        if plan.intent == "edit_interaction":
            return f"Updated the requested fields and left the rest unchanged. Tools used: {', '.join(changed)}."
        return f"I captured the interaction details and refreshed the AI recommendations. Tools used: {', '.join(changed)}."

    configs = _groq_model_configs()
    if not configs:
        return f"I updated the interaction draft. Tools used: {', '.join(changed)}."

    for model_name, api_key in configs:
        try:
            model = _build_groq(model_name, api_key, json_mode=False)
            response = _invoke_with_budget(
                model,
                [
                    SystemMessage(
                        content=(
                            "You are a concise CRM assistant. Confirm what was updated, mention any compliance flags, "
                            "and do not invent facts outside the draft."
                        )
                    ),
                    HumanMessage(
                        content=json.dumps(
                            {
                                "user_message": message,
                                "draft": draft.model_dump(),
                                "tool_trace": tool_trace,
                            },
                            indent=2,
                        )
                    ),
                ],
            )
            return str(response.content)
        except Exception:
            continue
    return f"I updated the interaction draft. Tools used: {', '.join(changed)}."


def _normalize_llm_plan(plan: InteractionPlan, draft: InteractionDraft) -> InteractionPlan:
    normalized: list[PlannedTool] = []
    for call in plan.tool_calls:
        args = dict(call.arguments)
        if call.tool_name == "log_interaction":
            args.setdefault("extracted", plan.extracted_fields)
        if call.tool_name == "edit_interaction":
            args.setdefault("patch", plan.extracted_fields)
        normalized.append(PlannedTool(tool_name=call.tool_name, arguments=args, reason=call.reason))

    if not normalized and plan.extracted_fields:
        tool_name = "edit_interaction" if plan.intent == "edit_interaction" else "log_interaction"
        key = "patch" if tool_name == "edit_interaction" else "extracted"
        normalized.append(
            PlannedTool(
                tool_name=tool_name,
                arguments={key: plan.extracted_fields},
                reason="Fallback tool call from extracted fields.",
            )
        )

    is_edit_only = any(call.tool_name == "edit_interaction" for call in normalized) and not any(
        call.tool_name == "log_interaction" for call in normalized
    )
    if is_edit_only:
        normalized = [
            call for call in normalized if call.tool_name in {"edit_interaction", "lookup_hcp_profile"}
        ]
        current_hcp = plan.extracted_fields.get("hcp_name") or draft.hcp_name
        if current_hcp and not any(call.tool_name == "lookup_hcp_profile" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="lookup_hcp_profile",
                    arguments={"hcp_name": current_hcp},
                    reason="Load HCP profile context without modifying unmentioned fields.",
                )
            )
        if not any(call.tool_name == "validate_interaction" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="validate_interaction",
                    arguments={},
                    reason="Refresh completion status after the explicit edit.",
                )
            )
        return InteractionPlan(
            intent=plan.intent,
            confidence=plan.confidence,
            extracted_fields=plan.extracted_fields,
            tool_calls=normalized,
        )

    if any(call.tool_name == "log_interaction" for call in normalized):
        current_hcp = plan.extracted_fields.get("hcp_name") or draft.hcp_name
        if current_hcp and not any(call.tool_name == "lookup_hcp_profile" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="lookup_hcp_profile",
                    arguments={"hcp_name": current_hcp},
                    reason="Load HCP profile context for CRM personalization.",
                )
            )
        if not any(call.tool_name == "compliance_guardrail" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="compliance_guardrail",
                    arguments={"message": ""},
                    reason="Check life-sciences compliance risks.",
                )
            )
        if not any(call.tool_name == "recommend_next_best_action" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="recommend_next_best_action",
                    arguments={},
                    reason="Generate the field rep's next best action.",
                )
            )
        if not any(call.tool_name == "schedule_follow_up" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="schedule_follow_up",
                    arguments={},
                    reason="Store an explicit follow-up date if the interaction includes one.",
                )
            )
        if not any(call.tool_name == "validate_interaction" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="validate_interaction",
                    arguments={},
                    reason="Validate core CRM completeness.",
                )
            )
        if not any(call.tool_name == "interaction_summary" for call in normalized):
            normalized.append(
                PlannedTool(
                    tool_name="interaction_summary",
                    arguments={},
                    reason="Generate CRM-ready interaction summary.",
                )
            )

    return InteractionPlan(
        intent=plan.intent,
        confidence=plan.confidence,
        extracted_fields=plan.extracted_fields,
        tool_calls=normalized,
    )
