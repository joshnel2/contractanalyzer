"""Tests for escalation evaluation logic."""

from __future__ import annotations

import json

import pytest

from tools.escalation_tools import EvaluateEscalationTool


class TestEvaluateEscalationTool:
    def test_properties(self) -> None:
        tool = EvaluateEscalationTool()
        assert tool.name == "evaluate_escalation"

    @pytest.mark.asyncio
    async def test_no_escalation_high_confidence(self) -> None:
        tool = EvaluateEscalationTool()
        result = await tool.execute({
            "confidence": 95,
            "auto_approve_threshold": 85,
            "escalation_flags": [],
            "body_text": "Let's schedule a quick call next week.",
            "escalation_keywords": ["rate", "fee", "conflict"],
            "participant_count": 2,
        })
        data = json.loads(result.output)
        assert data["should_escalate"] is False
        assert data["reasons"] == []

    @pytest.mark.asyncio
    async def test_escalation_low_confidence(self) -> None:
        tool = EvaluateEscalationTool()
        result = await tool.execute({
            "confidence": 40,
            "auto_approve_threshold": 85,
            "escalation_flags": [],
            "body_text": "Can we meet?",
            "escalation_keywords": [],
            "participant_count": 2,
        })
        data = json.loads(result.output)
        assert data["should_escalate"] is True
        assert any("Confidence" in r for r in data["reasons"])

    @pytest.mark.asyncio
    async def test_escalation_keyword_match(self) -> None:
        tool = EvaluateEscalationTool()
        result = await tool.execute({
            "confidence": 92,
            "auto_approve_threshold": 85,
            "escalation_flags": [],
            "body_text": "We should discuss the hourly rate before proceeding.",
            "escalation_keywords": ["rate", "fee", "conflict"],
            "participant_count": 2,
        })
        data = json.loads(result.output)
        assert data["should_escalate"] is True
        assert any("rate" in r.lower() for r in data["reasons"])

    @pytest.mark.asyncio
    async def test_escalation_explicit_flags(self) -> None:
        tool = EvaluateEscalationTool()
        result = await tool.execute({
            "confidence": 90,
            "auto_approve_threshold": 85,
            "escalation_flags": ["conflict_of_interest"],
            "body_text": "Regular meeting.",
            "escalation_keywords": [],
            "participant_count": 2,
        })
        data = json.loads(result.output)
        assert data["should_escalate"] is True

    @pytest.mark.asyncio
    async def test_escalation_multi_party(self) -> None:
        tool = EvaluateEscalationTool()
        result = await tool.execute({
            "confidence": 90,
            "auto_approve_threshold": 85,
            "escalation_flags": [],
            "body_text": "Group meeting.",
            "escalation_keywords": [],
            "participant_count": 7,
        })
        data = json.loads(result.output)
        assert data["should_escalate"] is True
        assert any("multi-party" in r.lower() for r in data["reasons"])
