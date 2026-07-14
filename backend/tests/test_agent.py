from app.agent import run_agent
from app.schemas import InteractionPreferences


def test_log_interaction_invokes_required_tool_chain():
    response = run_agent(
        "Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM for a meeting. "
        "Attendees were Ravi and Neha. Discussed Prodo-X efficacy and patient adherence. "
        "Positive sentiment. Shared brochure and safety card."
    )

    assert response.draft.hcp_name == "Dr. Meera Kapoor"
    assert response.draft.interaction_date == "19/04/2025"
    assert response.draft.sentiment == "Positive"
    assert "Prodo-X efficacy" in response.draft.topics_discussed
    assert "brochure" in response.draft.materials_shared

    tool_names = {trace.name for trace in response.tool_trace}
    assert "log_interaction" in tool_names
    assert "lookup_hcp_profile" in tool_names
    assert "compliance_guardrail" in tool_names
    assert "recommend_next_best_action" in tool_names
    assert "validate_interaction" in tool_names
    assert "interaction_summary" in tool_names
    assert response.draft.interaction_datetime_utc is not None
    assert response.draft.suggested_follow_ups == []
    assert response.draft.follow_up_actions == ""
    assert response.draft.follow_up_date == ""
    assert response.draft.completion_status == "Validated"
    assert response.draft.confidence_score == 0
    assert response.draft.ai_confidence == ""
    assert "Dr. Meera Kapoor" in response.draft.interaction_summary
    assert "Recommended next action" not in response.draft.interaction_summary


def test_follow_up_actions_only_fill_when_user_mentions_them():
    response = run_agent(
        "Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM. "
        "Discussed Prodo-X efficacy. Positive sentiment. Shared brochure. "
        "Follow-up actions: send the approved safety data sheet next Friday."
    )

    assert "approved safety data sheet" in response.draft.follow_up_actions.lower()
    assert "Follow-up action" in response.draft.interaction_summary


def test_messy_input_typos_and_formats_are_normalized():
    # The stubbed LLM returns RAW messy values (missing space, ordinal date, misspelled
    # sentiment). The production normalization layer must clean them end-to-end.
    response = run_agent(
        "Met Dr.Amit kumar at 14:00 on 1st jan 2025 and discussed PhotonX, "
        "Posotive sentiment, dshared brochure"
    )

    assert response.draft.hcp_name == "Dr. Amit Kumar"
    assert response.draft.interaction_date == "01/01/2025"
    assert response.draft.interaction_time == "02:00 PM"
    assert response.draft.sentiment == "Positive"
    assert any("brochure" in item.lower() for item in response.draft.materials_shared)
    assert "PhotonX" in response.draft.topics_discussed
    assert "sentiment" not in response.draft.topics_discussed.lower()


def test_edit_interaction_reports_only_named_fields():
    logged = run_agent(
        "Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM. "
        "Discussed Prodo-X efficacy. Positive sentiment. Shared brochure."
    )
    edited = run_agent("Change sentiment to neutral. Keep everything else the same.", logged.draft)

    edit_trace = next(trace for trace in edited.tool_trace if trace.name == "edit_interaction")
    changed = edit_trace.payload.get("changed_fields", [])
    assert changed == ["sentiment"], f"edit should touch only sentiment, got {changed}"


def test_edit_interaction_preserves_unmentioned_fields():
    logged = run_agent(
        "Met Dr. Arjun Menon on 04/19/2025 at 07:36 PM. "
        "Discussed renal dosing. Positive sentiment. Shared safety card."
    )
    edited = run_agent("Change sentiment to neutral and keep everything else the same.", logged.draft)

    assert edited.draft.sentiment == "Neutral"
    assert edited.draft.hcp_name == logged.draft.hcp_name
    assert edited.draft.topics_discussed == logged.draft.topics_discussed
    assert edited.draft.materials_shared == logged.draft.materials_shared
    assert edited.draft.follow_up_date == logged.draft.follow_up_date
    assert edited.draft.next_steps == logged.draft.next_steps
    edit_trace = next(trace for trace in edited.tool_trace if trace.name == "edit_interaction")
    assert edit_trace.payload["changed_fields"] == ["sentiment"]


def test_interaction_respects_date_time_preferences():
    response = run_agent(
        "Met Dr. Priya Shah on April 19, 2025 at 7:36 PM. "
        "Discussed patient affordability. Positive sentiment. Shared affordability card. "
        "Follow-up on April 22, 2025.",
        preferences=InteractionPreferences(
            timezone="Europe/London",
            date_format="DD/MM/YYYY",
            time_format="24h",
        ),
    )

    assert response.draft.interaction_date == "19/04/2025"
    assert response.draft.interaction_time == "19:36"
    assert response.draft.follow_up_date == "22/04/2025"
    assert response.draft.interaction_timezone == "Europe/London"
    assert response.draft.date_format == "DD/MM/YYYY"
    assert response.draft.time_format == "24h"


def test_edit_can_update_time_preferences_without_overwriting_crm_fields():
    logged = run_agent(
        "Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM. "
        "Discussed Prodo-X efficacy. Positive sentiment. Shared brochure."
    )
    edited = run_agent("Use 24-hour format and change timezone to Asia/Dubai.", logged.draft)

    assert edited.draft.hcp_name == logged.draft.hcp_name
    assert edited.draft.topics_discussed == logged.draft.topics_discussed
    assert edited.draft.time_format == "24h"
    assert edited.draft.time_format_preference == "24h"
    assert edited.draft.interaction_timezone == "Asia/Dubai"
    assert edited.draft.interaction_time == "19:36"
    assert edited.draft.interaction_datetime_utc is not None
    edit_trace = next(trace for trace in edited.tool_trace if trace.name == "edit_interaction")
    assert edit_trace.payload["changed_fields"] == ["interaction_timezone", "time_format"]


def test_live_datetime_tool_uses_requested_timezone():
    response = run_agent("What is today's date and current time in Dubai?")

    clock_trace = next(trace for trace in response.tool_trace if trace.name == "get_current_datetime")
    assert clock_trace.payload["timezone"] == "Asia/Dubai"
    assert clock_trace.payload["date"]
    assert clock_trace.payload["time"].endswith(("AM", "PM"))
    assert "Asia/Dubai" in response.assistant_message


def test_explicit_timezone_survives_the_full_automatic_tool_chain():
    response = run_agent(
        "Met Dr. Rao today at the current time in Dubai. Discussed CardioPlus efficacy, "
        "positive sentiment, and shared a brochure."
    )

    assert response.draft.interaction_timezone == "Asia/Dubai"
    assert response.draft.date_format == "DD/MM/YYYY"
    assert response.draft.time_format == "12h"
    assert response.draft.interaction_date
    assert response.draft.interaction_time.endswith(("AM", "PM"))
    assert response.draft.interaction_datetime_utc is not None
