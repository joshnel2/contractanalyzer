"""Tests for calendar reading tool."""

from __future__ import annotations

from tools.calendar_tools import ReadCalendarTool


class TestReadCalendarTool:
    def test_properties(self) -> None:
        tool = ReadCalendarTool.__new__(ReadCalendarTool)
        assert tool.name == "read_calendar"
        assert "calendar" in tool.description.lower()
        assert "user_email" in tool.input_schema["properties"]
        assert "user_email" in tool.input_schema["required"]

    def test_schema_defaults(self) -> None:
        tool = ReadCalendarTool.__new__(ReadCalendarTool)
        schema = tool.input_schema
        assert schema["properties"]["days_ahead"]["default"] == 3
