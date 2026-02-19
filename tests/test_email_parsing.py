"""Tests for the email-parsing Amplifier tools."""

from __future__ import annotations

import json

import pytest

from tools.email_parser import EmailParserTool, IdentifyAttorneyTool


class TestEmailParserTool:
    def test_properties(self) -> None:
        tool = EmailParserTool()
        assert tool.name == "parse_email"
        assert "scheduling intent" in tool.description.lower()
        assert "from_address" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_returns_prompt(self, sample_email_payload: dict) -> None:
        tool = EmailParserTool()
        result = await tool.execute({
            "from_address": sample_email_payload["From"],
            "subject": sample_email_payload["Subject"],
            "body_text": sample_email_payload["Body"],
            "received_at": sample_email_payload["DateTimeReceived"],
        })
        assert result.success is True
        data = json.loads(result.output)
        assert data["_vela_internal"] == "llm_prompt"
        assert "Q1 Strategy Review" in data["prompt"]

    @pytest.mark.asyncio
    async def test_execute_truncates_long_body(self) -> None:
        tool = EmailParserTool()
        long_body = "x" * 10000
        result = await tool.execute({
            "from_address": "test@test.com",
            "subject": "Test",
            "body_text": long_body,
        })
        data = json.loads(result.output)
        assert len(data["prompt"]) < len(long_body)


class TestIdentifyAttorneyTool:
    def test_properties(self) -> None:
        tool = IdentifyAttorneyTool()
        assert tool.name == "identify_attorney"

    @pytest.mark.asyncio
    async def test_identifies_internal_attorney(self) -> None:
        tool = IdentifyAttorneyTool()
        result = await tool.execute({
            "from_address": "jsmith@externalclient.com",
            "to_addresses": ["j.nakamura@ourfirm.onmicrosoft.com", "vela@ourfirm.onmicrosoft.com"],
            "cc_addresses": [],
            "vela_mailbox": "vela@ourfirm.onmicrosoft.com",
        })
        assert result.success is True
        data = json.loads(result.output)
        assert data["requesting_attorney"] == "j.nakamura@ourfirm.onmicrosoft.com"

    @pytest.mark.asyncio
    async def test_excludes_vela_mailbox(self) -> None:
        tool = IdentifyAttorneyTool()
        result = await tool.execute({
            "from_address": "attorney@ourfirm.onmicrosoft.com",
            "to_addresses": ["vela@ourfirm.onmicrosoft.com"],
            "cc_addresses": ["colleague@ourfirm.onmicrosoft.com"],
            "vela_mailbox": "vela@ourfirm.onmicrosoft.com",
        })
        data = json.loads(result.output)
        assert data["requesting_attorney"] != "vela@ourfirm.onmicrosoft.com"
