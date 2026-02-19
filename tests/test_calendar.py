"""Tests for calendar tool schemas and basic validation."""

from __future__ import annotations

import pytest

from tools.calendar_tools import (
    CheckCalendarTool,
    CheckMultiPartyAvailabilityTool,
    CreateCalendarEventTool,
    FindAvailableSlotsTool,
)


class TestCalendarToolSchemas:
    """Verify tool contracts (name, description, input_schema) are correct."""

    def test_check_calendar_schema(self) -> None:
        # Graph client is only called on execute, not on property access
        tool = CheckCalendarTool.__new__(CheckCalendarTool)
        assert tool.name == "check_calendar"
        assert "attorney_email" in tool.input_schema["properties"]
        assert "start_date" in tool.input_schema["required"]

    def test_find_available_slots_schema(self) -> None:
        tool = FindAvailableSlotsTool.__new__(FindAvailableSlotsTool)
        assert tool.name == "find_available_slots"
        schema = tool.input_schema
        assert "duration_minutes" in schema["properties"]
        assert schema["properties"]["duration_minutes"].get("default") == 60

    def test_create_event_schema(self) -> None:
        tool = CreateCalendarEventTool.__new__(CreateCalendarEventTool)
        assert tool.name == "create_calendar_event"
        assert "attendees" in tool.input_schema["required"]

    def test_multi_party_schema(self) -> None:
        tool = CheckMultiPartyAvailabilityTool.__new__(CheckMultiPartyAvailabilityTool)
        assert tool.name == "check_multi_party_availability"
        assert "attendee_emails" in tool.input_schema["properties"]
