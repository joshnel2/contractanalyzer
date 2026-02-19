"""Tests for the notification/digest tool."""

from __future__ import annotations

from tools.notification_tools import SendDigestTool


class TestSendDigestTool:
    def test_properties(self) -> None:
        tool = SendDigestTool.__new__(SendDigestTool)
        assert tool.name == "send_digest"
        assert "digest" in tool.description.lower()
        schema = tool.input_schema
        assert "to_email" in schema["required"]
        assert "subject" in schema["required"]
        assert "body_html" in schema["required"]
