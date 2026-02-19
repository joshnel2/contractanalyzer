"""Tests for preferences tools."""

from __future__ import annotations

from tools.preferences_tools import GetPreferencesTool, UpdatePreferencesTool


class TestGetPreferencesTool:
    def test_properties(self) -> None:
        tool = GetPreferencesTool.__new__(GetPreferencesTool)
        assert tool.name == "get_preferences"
        assert "user_email" in tool.input_schema["required"]


class TestUpdatePreferencesTool:
    def test_properties(self) -> None:
        tool = UpdatePreferencesTool.__new__(UpdatePreferencesTool)
        assert tool.name == "update_preferences"
        assert "user_email" in tool.input_schema["required"]
        assert "updates" in tool.input_schema["required"]
