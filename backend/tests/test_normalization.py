"""Unit tests for the deterministic normalization layer.

These are pure-function tests (no LLM, no graph) that lock in the typo/format
robustness the assignment cares about, independent of what any model returns.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.agent import tools
from app.agent.tools import _normalize_patch, _parse_date, get_current_datetime, normalize_hcp_name, normalize_sentiment
from app.schemas import InteractionPreferences


def test_normalize_sentiment_handles_typos_and_synonyms():
    assert normalize_sentiment("Posotive") == "Positive"
    assert normalize_sentiment("positve") == "Positive"
    assert normalize_sentiment("negtive") == "Negative"
    assert normalize_sentiment("Neutral") == "Neutral"
    assert normalize_sentiment("mixed feelings") == "Mixed"
    assert normalize_sentiment("the HCP was very receptive") == "Positive"  # synonym
    assert normalize_sentiment("resistant to switching") == "Negative"      # synonym
    assert normalize_sentiment("") == ""


def test_normalize_sentiment_strict_returns_empty_for_unknown():
    assert normalize_sentiment("PhotonX", strict=True) == ""
    assert normalize_sentiment("patient adherence", strict=True) == ""


def test_normalize_hcp_name_fixes_spacing_and_case():
    assert normalize_hcp_name("dr.amit kumar") == "Dr. Amit Kumar"
    assert normalize_hcp_name("DR AMIT KUMAR") == "Dr. Amit Kumar"
    assert normalize_hcp_name("Dr. Meera Kapoor") == "Dr. Meera Kapoor"
    assert normalize_hcp_name("prof. arjun menon") == "Prof. Arjun Menon"
    # No title present -> do not invent one.
    assert normalize_hcp_name("amit kumar") == "Amit Kumar"


def test_parse_date_accepts_ordinals_and_month_names():
    prefs = InteractionPreferences()
    d = _parse_date("1st jan 2025", prefs)
    assert d is not None and (d.year, d.month, d.day) == (2025, 1, 1)
    d = _parse_date("22nd April 2025", prefs)
    assert d is not None and (d.month, d.day) == (4, 22)
    d = _parse_date("2025-04-19", prefs)
    assert d is not None and (d.month, d.day) == (4, 19)


def test_today_and_now_use_explicit_timezone_regardless_of_field_order(monkeypatch):
    def fixed_now(timezone_name: str) -> datetime:
        return datetime(2026, 7, 14, 18, 5, tzinfo=ZoneInfo(timezone_name))

    monkeypatch.setattr(tools, "_now_in_timezone", fixed_now)
    patch = _normalize_patch(
        {
            "interaction_date": "today",
            "interaction_time": "now",
            "interaction_timezone": "Asia/Dubai",
        },
        InteractionPreferences(),
    )

    assert patch["interaction_timezone"] == "Asia/Dubai"
    assert patch["interaction_date"] == "14/07/2026"
    assert patch["interaction_time"] == "06:05 PM"


def test_live_datetime_uses_default_date_and_time_formats(monkeypatch):
    monkeypatch.setattr(
        tools,
        "_now_in_timezone",
        lambda timezone_name: datetime(2026, 7, 14, 9, 7, tzinfo=ZoneInfo(timezone_name)),
    )

    result = get_current_datetime(preferences=InteractionPreferences().model_dump())

    assert result["date"] == "14/07/2026"
    assert result["time"] == "09:07 AM"
