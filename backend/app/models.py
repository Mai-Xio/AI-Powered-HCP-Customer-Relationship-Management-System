from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HCPProfile(Base):
    __tablename__ = "hcp_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    specialty: Mapped[str] = mapped_column(String(120), default="")
    segment: Mapped[str] = mapped_column(String(80), default="")
    territory: Mapped[str] = mapped_column(String(120), default="")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    last_interaction_summary: Mapped[str] = mapped_column(Text, default="")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hcp_name: Mapped[str] = mapped_column(String(160), default="")
    specialty: Mapped[str] = mapped_column(String(120), default="")
    organization: Mapped[str] = mapped_column(String(180), default="")
    interaction_type: Mapped[str] = mapped_column(String(80), default="Meeting")
    interaction_date: Mapped[str] = mapped_column(String(32), default="")
    interaction_time: Mapped[str] = mapped_column(String(32), default="")
    interaction_datetime_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interaction_timezone: Mapped[str] = mapped_column(String(80), default="Asia/Kolkata")
    original_timezone: Mapped[str] = mapped_column(String(80), default="Asia/Kolkata")
    date_format: Mapped[str] = mapped_column(String(24), default="MM/DD/YYYY")
    time_format: Mapped[str] = mapped_column(String(8), default="12h")
    time_format_preference: Mapped[str] = mapped_column(String(8), default="12h")
    attendees: Mapped[list[str]] = mapped_column(JSON, default=list)
    topics_discussed: Mapped[str] = mapped_column(Text, default="")
    products_discussed: Mapped[list[str]] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(40), default="")
    materials_shared: Mapped[list[str]] = mapped_column(JSON, default=list)
    samples_distributed: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcomes: Mapped[str] = mapped_column(Text, default="")
    follow_up_actions: Mapped[str] = mapped_column(Text, default="")
    suggested_follow_ups: Mapped[list[str]] = mapped_column(JSON, default=list)
    hcp_questions: Mapped[str] = mapped_column(Text, default="")
    objections: Mapped[str] = mapped_column(Text, default="")
    commitments: Mapped[str] = mapped_column(Text, default="")
    next_steps: Mapped[str] = mapped_column(Text, default="")
    follow_up_date: Mapped[str] = mapped_column(String(32), default="")
    interaction_summary: Mapped[str] = mapped_column(Text, default="")
    completion_status: Mapped[str] = mapped_column(String(40), default="Needs Review")
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    compliance_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    ai_confidence: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
