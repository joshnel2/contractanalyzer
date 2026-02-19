"""Tests for the preferences-management Amplifier tools."""

from __future__ import annotations

import json

import pytest

from tools.preferences_tools import ParsePreferenceCommandTool


class TestParsePreferenceCommandTool:
    def test_properties(self) -> None:
        tool = ParsePreferenceCommandTool()
        assert tool.name == "parse_preference_command"
        assert "command" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_returns_llm_prompt(self) -> None:
        tool = ParsePreferenceCommandTool()
        result = await tool.execute({
            "command": "Strapped: set my buffer to 30 min",
            "attorney_email": "test@firm.com",
        })
        assert result.success is True
        data = json.loads(result.output)
        assert data["_strapped_internal"] == "llm_prompt"
        assert "buffer" in data["prompt"].lower()
