"""Shared fixtures for Strapped AI tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "test-deployment")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")


@pytest.fixture
def sample_email_payload() -> dict:
    return {
        "Id": "AAMkAGI2TG93AAA=",
        "ConversationId": "conv-123",
        "From": "jsmith@externalclient.com",
        "FromName": "John Smith",
        "To": "j.nakamura@yourcompany.com;strapped@yourcompany.com",
        "Cc": "",
        "Subject": "Meeting Request: Q1 Strategy Review",
        "Body": (
            "Hi Jun,\n\n"
            "Could we schedule a 60-minute meeting sometime next week to "
            "review the Q1 litigation strategy? Tuesday or Wednesday "
            "afternoon would work best for me.\n\n"
            "Thanks,\nJohn Smith\nGeneral Counsel, Acme Corp"
        ),
        "BodyPreview": "Hi Jun, Could we schedule a 60-minute meeting...",
        "DateTimeReceived": "2026-02-19T14:30:00Z",
        "HasAttachments": False,
        "Importance": "normal",
    }


@pytest.fixture
def sample_prefs_command_payload() -> dict:
    return {
        "Id": "AAMkAGI2TG94BBB=",
        "ConversationId": "conv-456",
        "From": "j.nakamura@yourcompany.com",
        "To": "strapped@yourcompany.com",
        "Subject": "Preference update",
        "Body": (
            "Strapped: set my buffer to 30 min\n"
            "Strapped: prefer 45-min internal calls\n"
            "Thanks!"
        ),
        "DateTimeReceived": "2026-02-19T15:00:00Z",
        "HasAttachments": False,
        "Importance": "normal",
    }


@pytest.fixture
def sample_preferences() -> dict:
    return {
        "attorney_email": "j.nakamura@yourcompany.com",
        "display_name": "Jun Nakamura",
        "working_hours_start": "07:30",
        "working_hours_end": "17:30",
        "timezone": "America/New_York",
        "buffer_before_minutes": 20,
        "buffer_after_minutes": 15,
        "preferred_duration_internal": 30,
        "preferred_duration_client": 60,
        "response_tone": "formal",
        "auto_approve_threshold": 90,
        "blackout_dates": ["2026-12-24", "2026-12-25"],
        "blocked_times": ["MWF 12:00-13:00"],
        "favorite_locations": ["Conference Room A"],
        "default_virtual_platform": "Microsoft Teams",
        "escalation_keywords": ["rate", "fee", "conflict", "deposition"],
        "custom_signature": "Best regards,\nJun Nakamura",
    }
