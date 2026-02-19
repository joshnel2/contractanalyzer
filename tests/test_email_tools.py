"""Tests for the email reading tool."""

from __future__ import annotations

from tools.email_tools import ReadEmailsTool


class TestReadEmailsTool:
    def test_properties(self) -> None:
        tool = ReadEmailsTool.__new__(ReadEmailsTool)
        assert tool.name == "read_emails"
        assert "inbox" in tool.description.lower()
        assert "user_email" in tool.input_schema["properties"]
        assert "user_email" in tool.input_schema["required"]

    def test_schema_defaults(self) -> None:
        tool = ReadEmailsTool.__new__(ReadEmailsTool)
        schema = tool.input_schema
        assert schema["properties"]["count"]["default"] == 20
        assert schema["properties"]["since_hours"]["default"] == 24
