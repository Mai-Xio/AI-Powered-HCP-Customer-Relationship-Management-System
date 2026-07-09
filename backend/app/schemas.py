from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class InteractionPreferences(BaseModel):
    timezone: str = "Asia/Kolkata"
    date_format: Literal["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "DD MMM YYYY"] = "MM/DD/YYYY"
    time_format: Literal["12h", "24h"] = "12h"


class InteractionDraft(BaseModel):
    hcp_name: str = ""
    specialty: str = ""
    organization: str = ""
    interaction_type: str = "Meeting"
    interaction_date: str = ""
    interaction_time: str = ""
    interaction_datetime_utc: datetime | None = None
    interaction_timezone: str = "Asia/Kolkata"
    original_timezone: str = "Asia/Kolkata"
    date_format: str = "MM/DD/YYYY"
    time_format: str = "12h"
    time_format_preference: str = "12h"
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    products_discussed: list[str] = Field(default_factory=list)
    sentiment: str = ""
    materials_shared: list[str] = Field(default_factory=list)
    samples_distributed: list[str] = Field(default_factory=list)
    outcomes: str = ""
    follow_up_actions: str = ""
    suggested_follow_ups: list[str] = Field(default_factory=list)
    hcp_questions: str = ""
    objections: str = ""
    commitments: str = ""
    next_steps: str = ""
    follow_up_date: str = ""
    interaction_summary: str = ""
    completion_status: str = "Needs Review"
    confidence_score: int = 0
    compliance_flags: list[str] = Field(default_factory=list)
    ai_confidence: str = ""


class HCPProfileOut(BaseModel):
    id: int
    name: str
    specialty: str
    segment: str
    territory: str
    preferences: dict[str, Any]
    last_interaction_summary: str

    model_config = ConfigDict(from_attributes=True)


class InteractionOut(InteractionDraft):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    current_draft: InteractionDraft = Field(default_factory=InteractionDraft)
    preferences: InteractionPreferences = Field(default_factory=InteractionPreferences)
    planner_model: str | None = Field(
        default=None, description="Optional Groq model id override selected in the Developer panel."
    )


class ToolTrace(BaseModel):
    name: str
    label: str
    status: Literal["completed", "skipped", "needs_review"] = "completed"
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    assistant_message: str
    draft: InteractionDraft
    tool_trace: list[ToolTrace]
    planner_mode: Literal["llm", "error"] = "llm"
    planner_model: str = ""


class PlannedTool(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class InteractionPlan(BaseModel):
    intent: Literal[
        "log_interaction",
        "edit_interaction",
        "lookup_hcp",
        "recommend_next_action",
        "schedule_follow_up",
        "compliance_review",
        "validate_interaction",
        "summarize_interaction",
        "help",
    ] = "log_interaction"
    tool_calls: list[PlannedTool] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: Literal["high", "medium", "low"] = "medium"
    planner_mode: Literal["llm", "error"] = "llm"
    planner_model: str = ""
