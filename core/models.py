"""Pydantic domain models shared across Vela-Law.

Every data structure that crosses module boundaries is defined here so that
tools, the function app, and the dashboard share a single source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────


class Priority(str, Enum):
    CLIENT = "client"
    INTERNAL = "internal"
    ADMIN = "admin"
    PERSONAL = "personal"


class Tone(str, Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    CONCISE = "concise"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    RATE_DISCUSSION = "rate_discussion"
    TRAVEL = "travel"
    MULTI_PARTY = "multi_party"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    CUSTOM_FLAG = "custom_flag"
    PREFERENCE_COMMAND = "preference_command"
    UNKNOWN_INTENT = "unknown_intent"


class EmailIntent(str, Enum):
    SCHEDULE_MEETING = "schedule_meeting"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    CHECK_AVAILABILITY = "check_availability"
    UPDATE_PREFERENCES = "update_preferences"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"


# ── Attorney Preferences ─────────────────────────────────────────────────────


class AttorneyPreferences(BaseModel):
    """Per-attorney configuration — the heart of Vela's personalisation."""

    attorney_email: str = Field(..., description="Primary email / partition key")
    display_name: str = Field(default="")

    # Working hours
    working_hours_start: str = Field(default="08:00")
    working_hours_end: str = Field(default="18:00")
    timezone: str = Field(default="America/New_York")

    # Buffer & duration
    buffer_before_minutes: int = Field(default=15)
    buffer_after_minutes: int = Field(default=10)
    preferred_duration_internal: int = Field(default=30, description="Minutes")
    preferred_duration_client: int = Field(default=60, description="Minutes")

    # Priority
    priority_order: list[Priority] = Field(
        default_factory=lambda: [Priority.CLIENT, Priority.INTERNAL, Priority.ADMIN]
    )

    # Tone
    response_tone: Tone = Field(default=Tone.FORMAL)

    # Auto-approve
    auto_approve_threshold: int = Field(
        default=85, ge=0, le=100,
        description="Confidence pct above which Vela sends without asking",
    )

    # Blackout / blocked
    blackout_dates: list[str] = Field(default_factory=list, description="ISO dates")
    blocked_times: list[str] = Field(
        default_factory=list,
        description="Recurring blocks, e.g. 'MWF 12:00-13:00'",
    )

    # Locations
    favorite_locations: list[str] = Field(default_factory=list)
    default_virtual_platform: str = Field(default="Microsoft Teams")

    # Escalation
    escalation_email: str = Field(
        default="",
        description="Override; falls back to attorney_email",
    )
    escalation_keywords: list[str] = Field(
        default_factory=lambda: ["rate", "fee", "conflict", "travel", "deposition"]
    )

    # Signature
    custom_signature: str = Field(default="")

    # Firm-wide court blocks (inherited, can override)
    court_block_calendars: list[str] = Field(default_factory=list)


# ── Email Models ─────────────────────────────────────────────────────────────


class InboundEmail(BaseModel):
    """Normalised representation of an email received by the Logic App."""

    message_id: str
    conversation_id: str = ""
    from_address: str
    from_name: str = ""
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str
    body_text: str
    body_html: str = ""
    received_at: datetime
    has_attachments: bool = False
    importance: str = "normal"
    internet_message_id: str = ""


class ParsedEmailIntent(BaseModel):
    """Structured output from the email-parsing tool."""

    intent: EmailIntent
    requesting_attorney_email: str = ""
    external_participants: list[str] = Field(default_factory=list)
    proposed_times: list[str] = Field(default_factory=list)
    duration_minutes: int | None = None
    matter_or_client: str = ""
    urgency: str = "normal"
    special_instructions: str = ""
    preference_commands: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    escalation_flags: list[EscalationReason] = Field(default_factory=list)
    raw_summary: str = ""


# ── Calendar Models ──────────────────────────────────────────────────────────


class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    score: float = Field(default=0.0, description="Higher = better fit")
    reason: str = ""


class CalendarEvent(BaseModel):
    event_id: str = ""
    subject: str
    start: datetime
    end: datetime
    location: str = ""
    attendees: list[str] = Field(default_factory=list)
    is_all_day: bool = False
    show_as: str = "busy"


# ── Reply / Action Models ───────────────────────────────────────────────────


class DraftReply(BaseModel):
    to_addresses: list[str]
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str
    body_html: str
    body_text: str = ""
    confidence: int = Field(default=50, ge=0, le=100)
    requires_escalation: bool = False
    escalation_reasons: list[EscalationReason] = Field(default_factory=list)


# ── Audit ────────────────────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    partition_key: str = Field(description="attorney_email")
    row_key: str = Field(description="Timestamp-based unique key")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str
    message_id: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    outcome: str = ""
    confidence: int = 0
