"""Tests for Vela-Law Pydantic domain models."""

from __future__ import annotations

from datetime import datetime, timezone

from core.models import (
    AttorneyPreferences,
    AuditEntry,
    CalendarEvent,
    DraftReply,
    EmailIntent,
    EscalationReason,
    InboundEmail,
    ParsedEmailIntent,
    Priority,
    TimeSlot,
    Tone,
)


class TestAttorneyPreferences:
    def test_defaults(self) -> None:
        prefs = AttorneyPreferences(attorney_email="test@firm.com")
        assert prefs.working_hours_start == "08:00"
        assert prefs.working_hours_end == "18:00"
        assert prefs.buffer_before_minutes == 15
        assert prefs.response_tone == Tone.FORMAL
        assert prefs.auto_approve_threshold == 85

    def test_custom_values(self, sample_preferences: dict) -> None:
        prefs = AttorneyPreferences(**sample_preferences)
        assert prefs.display_name == "Jun Nakamura"
        assert prefs.buffer_before_minutes == 20
        assert prefs.auto_approve_threshold == 90
        assert "rate" in prefs.escalation_keywords

    def test_priority_order(self) -> None:
        prefs = AttorneyPreferences(attorney_email="test@firm.com")
        assert prefs.priority_order == [Priority.CLIENT, Priority.INTERNAL, Priority.ADMIN]


class TestInboundEmail:
    def test_from_payload(self, sample_email_payload: dict) -> None:
        email = InboundEmail(
            message_id=sample_email_payload["Id"],
            from_address=sample_email_payload["From"],
            subject=sample_email_payload["Subject"],
            body_text=sample_email_payload["Body"],
            received_at=datetime.fromisoformat(sample_email_payload["DateTimeReceived"]),
        )
        assert email.message_id == "AAMkAGI2TG93AAA="
        assert "Q1 Strategy Review" in email.subject
        assert email.from_address == "jsmith@externalclient.com"


class TestParsedEmailIntent:
    def test_schedule_intent(self) -> None:
        parsed = ParsedEmailIntent(
            intent=EmailIntent.SCHEDULE_MEETING,
            requesting_attorney_email="j.nakamura@firm.com",
            duration_minutes=60,
            confidence=92,
        )
        assert parsed.intent == EmailIntent.SCHEDULE_MEETING
        assert parsed.confidence == 92
        assert parsed.escalation_flags == []

    def test_with_escalation_flags(self) -> None:
        parsed = ParsedEmailIntent(
            intent=EmailIntent.SCHEDULE_MEETING,
            confidence=40,
            escalation_flags=[EscalationReason.RATE_DISCUSSION],
        )
        assert len(parsed.escalation_flags) == 1
        assert parsed.escalation_flags[0] == EscalationReason.RATE_DISCUSSION


class TestTimeSlot:
    def test_slot_with_score(self) -> None:
        slot = TimeSlot(
            start=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
            score=0.95,
            reason="Prime morning focus time",
        )
        assert slot.score == 0.95
        assert "morning" in slot.reason.lower()


class TestAuditEntry:
    def test_audit_creation(self) -> None:
        entry = AuditEntry(
            partition_key="test@firm.com",
            row_key="20260219T143000_abc123",
            action="email_received",
            message_id="msg-001",
            outcome="processed",
            confidence=88,
        )
        assert entry.action == "email_received"
        assert entry.confidence == 88


class TestDraftReply:
    def test_auto_approve_eligible(self) -> None:
        reply = DraftReply(
            to_addresses=["jsmith@client.com"],
            subject="Re: Meeting Request",
            body_html="<p>Available slots...</p>",
            confidence=92,
            requires_escalation=False,
        )
        assert reply.confidence >= 85
        assert not reply.requires_escalation
