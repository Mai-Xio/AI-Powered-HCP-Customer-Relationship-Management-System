from __future__ import annotations

import difflib
import re
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.crud import SEED_HCPS
from app.schemas import InteractionDraft, InteractionPreferences


LIST_FIELDS = {
    "attendees",
    "materials_shared",
    "samples_distributed",
    "compliance_flags",
    "products_discussed",
    "suggested_follow_ups",
}
VALID_FIELDS = set(InteractionDraft.model_fields.keys())
SYSTEM_TOOL_FIELDS = {
    "ai_confidence",
    "completion_status",
    "compliance_flags",
    "confidence_score",
    "interaction_datetime_utc",
    "interaction_summary",
    "next_steps",
    "suggested_follow_ups",
}
DATE_FORMATS = {
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD MMM YYYY": "%d %b %Y",
}


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        separators = [";", "\n", ",", " and "]
        items = [value]
        for separator in separators:
            if separator in value:
                items = value.split(separator)
                break
        return [item.strip(" .") for item in items if item.strip(" .")]
    return [str(value).strip()]


_SENTIMENT_CANON = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
    "mixed": "Mixed",
}
_SENTIMENT_SYNONYMS = {
    "good": "positive",
    "great": "positive",
    "happy": "positive",
    "receptive": "positive",
    "favourable": "positive",
    "favorable": "positive",
    "enthusiastic": "positive",
    "interested": "positive",
    "supportive": "positive",
    "bad": "negative",
    "poor": "negative",
    "unhappy": "negative",
    "resistant": "negative",
    "hostile": "negative",
    "skeptical": "negative",
    "sceptical": "negative",
    "dismissive": "negative",
    "ok": "neutral",
    "okay": "neutral",
    "indifferent": "neutral",
    "noncommittal": "neutral",
    "reserved": "neutral",
}

_NAME_TITLES = {
    "dr": "Dr.",
    "doctor": "Dr.",
    "prof": "Prof.",
    "professor": "Prof.",
    "mr": "Mr.",
    "mrs": "Mrs.",
    "ms": "Ms.",
    "miss": "Miss",
}


def normalize_sentiment(value: Any, strict: bool = False) -> str:
    """Map free-text/typo'd sentiment to one of Positive/Neutral/Negative/Mixed.

    Tolerant of misspellings ("Posotive" -> Positive) via synonym and fuzzy
    matching. With ``strict=True`` an unrecognised value returns "" so callers
    can decide (used when scanning ambiguous text); otherwise the original text
    is preserved title-cased so no signal is silently dropped.
    """
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    words = re.findall(r"[a-z]+", raw)
    for word in words:
        if word in _SENTIMENT_CANON:
            return _SENTIMENT_CANON[word]
        if word in _SENTIMENT_SYNONYMS:
            return _SENTIMENT_CANON[_SENTIMENT_SYNONYMS[word]]
    for word in words:
        match = difflib.get_close_matches(word, list(_SENTIMENT_CANON.keys()), n=1, cutoff=0.72)
        if match:
            return _SENTIMENT_CANON[match[0]]
    return "" if strict else str(value).strip().title()


def normalize_hcp_name(value: Any) -> str:
    """Clean an HCP name: fix a missing space after the title and capitalize.

    "dr.amit kumar" -> "Dr. Amit Kumar". Does not invent a title when none is
    present, and preserves intentional internal capitalization (e.g. "McKenzie").
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    title = ""
    match = re.match(r"^(dr|doctor|prof|professor|mr|mrs|ms|miss)\.?\s*", raw, re.I)
    if match:
        title = _NAME_TITLES[match.group(1).lower()]
        raw = raw[match.end():].strip()

    def _cap(word: str) -> str:
        if word.isupper() or word.islower():
            return word[:1].upper() + word[1:].lower()
        return word

    body = " ".join(_cap(word) for word in raw.split())
    return f"{title} {body}".strip()


def _safe_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _now_in_timezone(timezone_name: str) -> datetime:
    return datetime.now(_safe_timezone(timezone_name))


def _preferences(preferences: dict[str, Any] | InteractionPreferences | None = None) -> InteractionPreferences:
    if isinstance(preferences, InteractionPreferences):
        return preferences
    return InteractionPreferences(**(preferences or {}))


def _display_date(value: datetime, preferences: InteractionPreferences) -> str:
    return value.strftime(DATE_FORMATS.get(preferences.date_format, "%m/%d/%Y"))


def _display_time(value: time, preferences: InteractionPreferences) -> str:
    if preferences.time_format == "24h":
        return value.strftime("%H:%M")
    return value.strftime("%I:%M %p")


def _parse_date(value: str, preferences: InteractionPreferences | None = None) -> datetime | None:
    if not value:
        return None
    prefs = preferences or InteractionPreferences()
    raw = value.strip()
    lower = raw.lower()
    today = _now_in_timezone(prefs.timezone).replace(hour=0, minute=0, second=0, microsecond=0)
    if lower in {"today", "now"}:
        return today
    if lower == "tomorrow":
        return today + timedelta(days=1)
    if lower == "yesterday":
        return today - timedelta(days=1)

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    weekday_match = lower.replace("-", " ").strip()
    if weekday_match.startswith("next "):
        weekday_name = weekday_match.removeprefix("next ").strip()
        if weekday_name in weekdays:
            days_ahead = (weekdays[weekday_name] - today.weekday()) % 7
            return today + timedelta(days=days_ahead or 7)

    normalized = re_sub_date_noise(raw)
    preferred_formats = [DATE_FORMATS.get(prefs.date_format, "%m/%d/%Y")]
    fallback_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %y",
        "%d %B %y",
    ]
    for fmt in preferred_formats + [fmt for fmt in fallback_formats if fmt not in preferred_formats]:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def re_sub_date_noise(value: str) -> str:
    # Drop ordinal suffixes ("1st", "22nd") so "1st jan 2025" parses as a date.
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", value, flags=re.I)
    cleaned = cleaned.replace(",", " ").replace(".", " ").strip()
    return " ".join(cleaned.split())


def _parse_time(value: str, preferences: InteractionPreferences | None = None) -> time | None:
    if not value:
        return None
    raw = value.strip().upper().replace(".", "")
    prefs = preferences or InteractionPreferences()
    if raw in {"NOW", "CURRENT TIME", "CURRENT"}:
        return _now_in_timezone(prefs.timezone).time().replace(second=0, microsecond=0)
    if raw in {"NOON", "12 NOON"}:
        return time(hour=12)
    if raw in {"MIDNIGHT", "12 MIDNIGHT"}:
        return time(hour=0)
    compact = " ".join(raw.split())
    formats = ["%I:%M %p", "%I %p", "%H:%M", "%H%M"]
    for fmt in formats:
        try:
            return datetime.strptime(compact, fmt).time()
        except ValueError:
            continue
    return None


def _normalize_patch(
    payload: dict[str, Any],
    preferences: dict[str, Any] | InteractionPreferences | None = None,
    inject_preferences: bool = True,
) -> dict[str, Any]:
    prefs = _preferences(preferences)
    patch: dict[str, Any] = {}
    aliases = {
        "hcp": "hcp_name",
        "doctor": "hcp_name",
        "clinic": "organization",
        "hospital": "organization",
        "org": "organization",
        "date": "interaction_date",
        "time": "interaction_time",
        "timezone": "interaction_timezone",
        "time_zone": "interaction_timezone",
        "original_timezone": "interaction_timezone",
        "type": "interaction_type",
        "topics": "topics_discussed",
        "products": "products_discussed",
        "product": "products_discussed",
        "materials": "materials_shared",
        "items_shared": "materials_shared",
        "samples": "samples_distributed",
        "outcome": "outcomes",
        "agreements": "outcomes",
        "agreement": "outcomes",
        "follow_up_action": "follow_up_actions",
        "followup_action": "follow_up_actions",
        "follow_up_actions": "follow_up_actions",
        "next_action": "follow_up_actions",
        "questions": "hcp_questions",
        "follow_up": "follow_up_date",
        "followup": "follow_up_date",
        "summary": "interaction_summary",
        "status": "completion_status",
        "preferred_time_format": "time_format",
        "time_format_preference": "time_format",
    }

    # Preferences must be resolved before relative dates and times. LLM JSON
    # field order should never decide which timezone "today" or "now" uses.
    aliased_payload = {aliases.get(key, key): value for key, value in payload.items()}
    timezone_value = aliased_payload.get("interaction_timezone")
    if timezone_value is not None:
        normalized_timezone = _normalize_timezone(str(timezone_value), prefs.timezone)
        patch["interaction_timezone"] = normalized_timezone
        prefs = prefs.model_copy(update={"timezone": normalized_timezone})
    date_format_value = aliased_payload.get("date_format")
    if date_format_value is not None:
        normalized_date_format = _normalize_date_format(str(date_format_value), prefs.date_format)
        patch["date_format"] = normalized_date_format
        prefs = prefs.model_copy(update={"date_format": normalized_date_format})
    time_format_value = aliased_payload.get("time_format")
    if time_format_value is not None:
        normalized_time_format = _normalize_time_format(str(time_format_value), prefs.time_format)
        patch["time_format"] = normalized_time_format
        prefs = prefs.model_copy(update={"time_format": normalized_time_format})

    for raw_key, raw_value in payload.items():
        key = aliases.get(raw_key, raw_key)
        if key not in VALID_FIELDS or key in SYSTEM_TOOL_FIELDS or raw_value is None:
            continue
        if key in {"interaction_timezone", "date_format", "time_format"}:
            continue
        if key in LIST_FIELDS:
            patch[key] = _as_list(raw_value)
        elif key in {"interaction_date", "follow_up_date"}:
            parsed = _parse_date(str(raw_value), prefs)
            patch[key] = _display_date(parsed, prefs) if parsed else str(raw_value).strip()
        elif key == "interaction_time":
            parsed_time = _parse_time(str(raw_value), prefs)
            patch[key] = _display_time(parsed_time, prefs) if parsed_time else str(raw_value).strip()
        elif key == "sentiment":
            patch[key] = normalize_sentiment(raw_value)
        elif key == "hcp_name":
            patch[key] = normalize_hcp_name(raw_value)
        elif isinstance(raw_value, str):
            cleaned = raw_value.strip()
            if cleaned:
                patch[key] = cleaned
        elif raw_value != "":
            patch[key] = raw_value
    if not inject_preferences:
        return patch
    patch["interaction_timezone"] = patch.get("interaction_timezone", prefs.timezone)
    patch["original_timezone"] = patch["interaction_timezone"]
    patch["date_format"] = prefs.date_format
    patch["time_format"] = prefs.time_format
    patch["time_format_preference"] = prefs.time_format
    return patch


def _apply_patch(current_draft: dict[str, Any], patch: dict[str, Any]) -> InteractionDraft:
    draft = InteractionDraft(**current_draft)
    data = draft.model_dump()
    old_preferences = InteractionPreferences(
        timezone=data.get("interaction_timezone") or "Asia/Kolkata",
        date_format=data.get("date_format") or "DD/MM/YYYY",
        time_format=data.get("time_format") or "12h",
    )
    for key, value in patch.items():
        if key in LIST_FIELDS:
            data[key] = _as_list(value)
        elif key in VALID_FIELDS:
            data[key] = value

    new_preferences = InteractionPreferences(
        timezone=data.get("interaction_timezone") or old_preferences.timezone,
        date_format=data.get("date_format") or old_preferences.date_format,
        time_format=data.get("time_format") or old_preferences.time_format,
    )
    if "date_format" in patch and "interaction_date" not in patch:
        parsed_date = _parse_date(str(draft.interaction_date or ""), old_preferences)
        if parsed_date:
            data["interaction_date"] = _display_date(parsed_date, new_preferences)
    if "date_format" in patch and "follow_up_date" not in patch:
        parsed_follow_up = _parse_date(str(draft.follow_up_date or ""), old_preferences)
        if parsed_follow_up:
            data["follow_up_date"] = _display_date(parsed_follow_up, new_preferences)
    if "time_format" in patch and "interaction_time" not in patch:
        parsed_time = _parse_time(str(draft.interaction_time or ""), old_preferences)
        if parsed_time:
            data["interaction_time"] = _display_time(parsed_time, new_preferences)

    data["time_format_preference"] = data.get("time_format") or data.get("time_format_preference") or "12h"
    data["original_timezone"] = data.get("interaction_timezone") or data.get("original_timezone") or "Asia/Kolkata"
    data["interaction_datetime_utc"] = _build_utc_datetime(data)
    return InteractionDraft(**data)


def _normalize_timezone(value: str, fallback: str) -> str:
    raw = value.strip()
    aliases = {
        "IST": "Asia/Kolkata",
        "INDIA": "Asia/Kolkata",
        "KOLKATA": "Asia/Kolkata",
        "DUBAI": "Asia/Dubai",
        "UAE": "Asia/Dubai",
        "UTC": "UTC",
        "GMT": "UTC",
        "LONDON": "Europe/London",
        "NEW YORK": "America/New_York",
    }
    candidate = aliases.get(raw.upper(), raw)
    try:
        ZoneInfo(candidate)
        return candidate
    except ZoneInfoNotFoundError:
        return fallback


def _normalize_date_format(value: str, fallback: str) -> str:
    raw = value.strip().upper().replace("-", "/")
    if raw in DATE_FORMATS:
        return raw
    if "DD" in raw and "MM" in raw and raw.index("DD") < raw.index("MM"):
        return "DD/MM/YYYY"
    if raw.startswith("YYYY"):
        return "YYYY-MM-DD"
    if "MMM" in raw:
        return "DD MMM YYYY"
    return fallback


def _normalize_time_format(value: str, fallback: str) -> str:
    raw = value.strip().lower()
    if raw in {"24", "24h", "24-hour", "24 hour", "military"}:
        return "24h"
    if raw in {"12", "12h", "12-hour", "12 hour", "am/pm"}:
        return "12h"
    return fallback


def _build_utc_datetime(data: dict[str, Any]) -> datetime | None:
    prefs = InteractionPreferences(
        timezone=data.get("interaction_timezone") or "Asia/Kolkata",
        date_format=data.get("date_format") or "DD/MM/YYYY",
        time_format=data.get("time_format") or "12h",
    )
    date_value = _parse_date(str(data.get("interaction_date") or ""), prefs)
    time_value = _parse_time(str(data.get("interaction_time") or ""), prefs)
    if not date_value or not time_value:
        return None
    local_zone = _safe_timezone(prefs.timezone)
    local_dt = datetime.combine(date_value.date(), time_value, local_zone)
    return local_dt.astimezone(datetime_timezone.utc)


class LogInteractionArgs(BaseModel):
    extracted: dict[str, Any] = Field(description="Fields extracted by the LLM from the user's prompt.")
    current_draft: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


def log_interaction(
    extracted: dict[str, Any],
    current_draft: dict[str, Any],
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Populate the interaction draft from natural language."""
    patch = _normalize_patch(extracted, preferences)
    updated = _apply_patch(current_draft, patch)
    return {
        "draft": updated.model_dump(),
        "changed_fields": sorted(patch.keys()),
        "summary": f"Logged {len(patch)} extracted field(s) into the HCP interaction draft.",
    }


class EditInteractionArgs(BaseModel):
    patch: dict[str, Any] = Field(description="Only the fields the user explicitly asked to change.")
    current_draft: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


def edit_interaction(
    patch: dict[str, Any],
    current_draft: dict[str, Any],
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Modify only requested fields while preserving the rest of the draft."""
    clean_patch = _normalize_patch(patch, preferences, inject_preferences=False)
    updated = _apply_patch(current_draft, clean_patch)
    return {
        "draft": updated.model_dump(),
        "changed_fields": sorted(clean_patch.keys()),
        "summary": f"Edited {len(clean_patch)} field(s) and preserved all other interaction details.",
    }


class LookupHCPArgs(BaseModel):
    hcp_name: str = ""
    current_draft: dict[str, Any] = Field(default_factory=dict)


def lookup_hcp_profile(hcp_name: str = "", current_draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retrieve profile context for the HCP to personalize recommendations."""
    draft_name = (current_draft or {}).get("hcp_name", "")
    target = (hcp_name or draft_name).lower().strip()
    profile = None
    for item in SEED_HCPS:
        name = item["name"].lower()
        if target and (target in name or name in target):
            profile = item
            break
    if profile is None:
        profile = {
            "name": hcp_name or draft_name or "Unknown HCP",
            "specialty": "Unmatched",
            "segment": "Unknown",
            "territory": "Unassigned",
            "preferences": {},
            "last_interaction_summary": "No prior CRM context found.",
        }
    return {"profile": profile, "summary": f"Loaded HCP context for {profile['name']}."}


class ComplianceArgs(BaseModel):
    message: str = ""
    current_draft: dict[str, Any] = Field(default_factory=dict)


def compliance_guardrail(message: str = "", current_draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check the draft for common life-sciences sales compliance risks."""
    draft = InteractionDraft(**(current_draft or {}))
    text = " ".join(
        [
            message,
            draft.topics_discussed,
            draft.hcp_questions,
            draft.objections,
            " ".join(draft.materials_shared),
        ]
    ).lower()
    flags: list[str] = []
    if any(term in text for term in ["off-label", "unapproved", "outside label"]):
        flags.append("Review off-label discussion before saving.")
    if any(term in text for term in ["adverse event", "side effect", "serious reaction"]):
        flags.append("Potential adverse event: route to pharmacovigilance workflow.")
    if "voice note" in text and "consent" not in text:
        flags.append("Voice note mentioned without consent confirmation.")
    if not flags:
        flags.append("No immediate compliance risk detected.")
    updated = _apply_patch(draft.model_dump(), {"compliance_flags": flags})
    return {
        "draft": updated.model_dump(),
        "flags": flags,
        "summary": "Completed promotional compliance and safety screening.",
    }


class NextActionArgs(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    current_draft: dict[str, Any] = Field(default_factory=dict)


def recommend_next_best_action(
    profile: dict[str, Any] | None = None,
    current_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recommend the next sales action from HCP context and interaction content."""
    draft = InteractionDraft(**(current_draft or {}))
    profile = profile or {}
    specialty = profile.get("specialty") or "the HCP's specialty"
    preferred_content = (profile.get("preferences") or {}).get("content", "clinical evidence")
    if draft.sentiment.lower() == "negative":
        action = f"Send a concise objection-handling follow-up with approved {preferred_content} and offer a short clarification call."
    elif "sample" in " ".join(draft.samples_distributed).lower():
        action = f"Confirm sample receipt and pair it with approved {specialty} patient-selection guidance."
    elif draft.hcp_questions:
        action = f"Answer the HCP question with approved {preferred_content} and document any medical-information request."
    else:
        action = f"Share approved {preferred_content} and schedule a value-focused follow-up."
    updated = _apply_patch(
        draft.model_dump(),
        {
            "next_steps": action,
            "suggested_follow_ups": [],
        },
    )
    return {
        "draft": updated.model_dump(),
        "recommendation": action,
        "summary": "Generated an internal next-best-action recommendation.",
    }


class ValidationArgs(BaseModel):
    current_draft: dict[str, Any] = Field(default_factory=dict)


def validate_interaction(current_draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check whether the CRM record is complete and ready to save."""
    draft = InteractionDraft(**(current_draft or {}))
    missing: list[str] = []
    checks = {
        "HCP name": draft.hcp_name,
        "interaction date": draft.interaction_date,
        "interaction time": draft.interaction_time,
        "topics discussed": draft.topics_discussed,
        "sentiment": draft.sentiment,
    }
    for label, value in checks.items():
        if not value:
            missing.append(label)

    if not draft.hcp_name or not draft.interaction_date:
        status = "Missing Fields"
    elif missing:
        status = "Needs Review"
    else:
        status = "Validated"

    updated = _apply_patch(
        draft.model_dump(),
        {
            "completion_status": status,
            "confidence_score": 0,
            "ai_confidence": "",
        },
    )
    return {
        "draft": updated.model_dump(),
        "missing_fields": missing,
        "summary": f"Validation completed: {status}.",
    }


class SummaryArgs(BaseModel):
    current_draft: dict[str, Any] = Field(default_factory=dict)


def interaction_summary(current_draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate a concise CRM-ready summary from the structured interaction."""
    draft = InteractionDraft(**(current_draft or {}))
    hcp = draft.hcp_name or "The HCP"
    sentiment = draft.sentiment.lower() if draft.sentiment else "unspecified"
    products = ", ".join(draft.products_discussed) if draft.products_discussed else "the discussed product(s)"
    materials = ", ".join(draft.materials_shared) if draft.materials_shared else "no materials"
    notes = draft.topics_discussed or "No discussion notes captured"
    outcomes = draft.outcomes or "Outcomes pending"
    summary_parts = [
        f"{hcp} had a {sentiment} interaction about {products}.",
        f"Key notes: {notes}.",
        f"Outcomes: {outcomes}.",
        f"Materials shared: {materials}.",
    ]
    if draft.follow_up_actions:
        summary_parts.append(f"Follow-up action: {draft.follow_up_actions}.")
    summary = " ".join(summary_parts)
    updated = _apply_patch(draft.model_dump(), {"interaction_summary": summary})
    return {"draft": updated.model_dump(), "summary": "Generated CRM-ready interaction summary."}


class FollowUpArgs(BaseModel):
    requested_date: str = ""
    current_draft: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


def schedule_follow_up(
    requested_date: str = "",
    current_draft: dict[str, Any] | None = None,
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a follow-up date only when the user or planner explicitly provides one."""
    prefs = _preferences(preferences)
    draft = InteractionDraft(**(current_draft or {}))
    effective_preferences = InteractionPreferences(
        timezone=draft.interaction_timezone or prefs.timezone,
        date_format=draft.date_format or prefs.date_format,
        time_format=draft.time_format or prefs.time_format,
    )
    if requested_date:
        parsed = _parse_date(requested_date, effective_preferences)
        follow_up = _display_date(parsed, effective_preferences) if parsed else requested_date
        updated = _apply_patch(
            draft.model_dump(),
            {
                "follow_up_date": follow_up,
            },
        )
        return {
            "draft": updated.model_dump(),
            "summary": f"Stored explicit follow-up date: {follow_up}.",
        }

    if draft.follow_up_date:
        return {
            "draft": draft.model_dump(),
            "summary": f"Kept existing follow-up date: {draft.follow_up_date}.",
        }
    return {
        "draft": draft.model_dump(),
        "summary": "No explicit follow-up date was provided.",
    }


class CurrentDateTimeArgs(BaseModel):
    timezone: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)


def get_current_datetime(
    timezone: str = "",
    preferences: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Fetch the live date and time in the requested or active timezone."""
    prefs = _preferences(preferences)
    selected_timezone = _normalize_timezone(timezone, prefs.timezone) if timezone else prefs.timezone
    active_preferences = prefs.model_copy(update={"timezone": selected_timezone})
    current = _now_in_timezone(selected_timezone)
    current_date = _display_date(current, active_preferences)
    current_time = _display_time(current.time(), active_preferences)
    return {
        "timezone": selected_timezone,
        "date": current_date,
        "time": current_time,
        "utc": current.astimezone(datetime_timezone.utc).isoformat(),
        "summary": f"Current date and time in {selected_timezone}: {current_date} at {current_time}.",
    }


TOOL_REGISTRY: dict[str, StructuredTool] = {
    "log_interaction": StructuredTool.from_function(
        func=log_interaction,
        name="log_interaction",
        description="Mandatory tool: extract natural-language HCP interaction details and populate the CRM form.",
        args_schema=LogInteractionArgs,
    ),
    "edit_interaction": StructuredTool.from_function(
        func=edit_interaction,
        name="edit_interaction",
        description="Mandatory tool: update only explicitly requested fields and preserve every other field.",
        args_schema=EditInteractionArgs,
    ),
    "lookup_hcp_profile": StructuredTool.from_function(
        func=lookup_hcp_profile,
        name="lookup_hcp_profile",
        description="Custom tool: retrieve HCP specialty, segment, territory, and engagement preferences.",
        args_schema=LookupHCPArgs,
    ),
    "compliance_guardrail": StructuredTool.from_function(
        func=compliance_guardrail,
        name="compliance_guardrail",
        description="Custom tool: screen for adverse event, off-label, and consent risks.",
        args_schema=ComplianceArgs,
    ),
    "recommend_next_best_action": StructuredTool.from_function(
        func=recommend_next_best_action,
        name="recommend_next_best_action",
        description="Custom tool: suggest the best next action from CRM and HCP context.",
        args_schema=NextActionArgs,
    ),
    "schedule_follow_up": StructuredTool.from_function(
        func=schedule_follow_up,
        name="schedule_follow_up",
        description="Custom tool: store an explicit follow-up date when one is provided.",
        args_schema=FollowUpArgs,
    ),
    "validate_interaction": StructuredTool.from_function(
        func=validate_interaction,
        name="validate_interaction",
        description="Custom tool: check core CRM completeness and completion status.",
        args_schema=ValidationArgs,
    ),
    "interaction_summary": StructuredTool.from_function(
        func=interaction_summary,
        name="interaction_summary",
        description="Custom tool: generate a clean CRM-ready summary from the structured interaction.",
        args_schema=SummaryArgs,
    ),
    "get_current_datetime": StructuredTool.from_function(
        func=get_current_datetime,
        name="get_current_datetime",
        description="Custom tool: fetch the live date and time in the requested or active timezone.",
        args_schema=CurrentDateTimeArgs,
    ),
}


TOOL_LABELS = {
    "log_interaction": "Log Interaction",
    "edit_interaction": "Edit Interaction",
    "lookup_hcp_profile": "HCP Profile Lookup",
    "compliance_guardrail": "Compliance Guardrail",
    "recommend_next_best_action": "Next Best Action",
    "schedule_follow_up": "Follow-up Scheduler",
    "validate_interaction": "Validate Record",
    "interaction_summary": "CRM Summary",
    "get_current_datetime": "Live Date & Time",
}


def tool_catalog_for_prompt() -> str:
    return "\n".join(
        f"- {name}: {tool.description}" for name, tool in TOOL_REGISTRY.items()
    )
