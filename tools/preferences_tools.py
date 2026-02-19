"""Preferences-management Amplifier tools.

Allows Vela (and the LLM agent) to read, update, and interpret attorney
preferences stored in Azure Table Storage.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.models import AttorneyPreferences
from core.table_storage import VelaTableStorage

logger = logging.getLogger("vela.tools.preferences")


class GetPreferencesTool:
    """Load the merged (firm-default + override) preferences for an attorney."""

    def __init__(self, storage: VelaTableStorage) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "get_preferences"

    @property
    def description(self) -> str:
        return (
            "Retrieve the full preferences profile for an attorney, including "
            "working hours, buffer times, preferred durations, tone, escalation "
            "rules, blackout dates, and more."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attorney_email": {
                    "type": "string",
                    "description": "Attorney's email address",
                },
            },
            "required": ["attorney_email"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            prefs = self._storage.get_preferences(input["attorney_email"])
            return ToolResult(
                success=True,
                output=json.dumps(prefs.model_dump(), default=str),
            )
        except Exception as exc:
            logger.exception("get_preferences failed")
            return ToolResult(success=False, error={"message": str(exc)})


class UpdatePreferencesTool:
    """Apply one or more preference changes for an attorney."""

    def __init__(self, storage: VelaTableStorage) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "update_preferences"

    @property
    def description(self) -> str:
        return (
            "Update specific preferences for an attorney. Accepts a partial "
            "dict of preference fields to change — unchanged fields are kept. "
            "Examples: buffer_before_minutes, working_hours_start, response_tone, "
            "preferred_duration_internal, blackout_dates, etc."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attorney_email": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": (
                        "Partial dict of preference fields to update, e.g. "
                        '{"buffer_before_minutes": 30, "response_tone": "friendly"}'
                    ),
                },
            },
            "required": ["attorney_email", "updates"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            email = input["attorney_email"]
            updates = input.get("updates", {})

            current = self._storage.get_preferences(email)
            merged = current.model_dump()
            merged.update(updates)
            merged["attorney_email"] = email

            new_prefs = AttorneyPreferences(**merged)
            self._storage.upsert_preferences(new_prefs)

            return ToolResult(
                success=True,
                output=json.dumps({
                    "status": "updated",
                    "attorney": email,
                    "changed_fields": list(updates.keys()),
                }),
            )
        except Exception as exc:
            logger.exception("update_preferences failed")
            return ToolResult(success=False, error={"message": str(exc)})


class ParsePreferenceCommandTool:
    """Interpret natural-language preference commands from email bodies.

    Attorneys can embed commands like:
        "Vela: set my buffer to 30 min"
        "Vela: prefer 45-min internal calls"
        "Vela: block Fridays after 3pm"
    """

    @property
    def name(self) -> str:
        return "parse_preference_command"

    @property
    def description(self) -> str:
        return (
            "Parse a natural-language 'Vela: ...' preference command and return "
            "the structured preference update. Use this when the email contains "
            "preference-update instructions."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The raw 'Vela: ...' command text",
                },
                "attorney_email": {"type": "string"},
            },
            "required": ["command", "attorney_email"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        command = input.get("command", "").strip()
        prompt = f"""\
Parse this Vela preference command into a JSON object mapping preference
field names to their new values.

Valid fields: working_hours_start, working_hours_end, buffer_before_minutes,
buffer_after_minutes, preferred_duration_internal, preferred_duration_client,
response_tone (formal/friendly/concise), auto_approve_threshold (0-100),
blackout_dates (list of ISO dates), blocked_times (list like "MWF 12:00-13:00"),
favorite_locations (list), default_virtual_platform, timezone.

Command: "{command}"

Return ONLY a JSON object like: {{"field_name": "new_value"}}
If the command is unclear, return: {{"_error": "Could not parse command"}}
"""
        return ToolResult(
            success=True,
            output=json.dumps({
                "_vela_internal": "llm_prompt",
                "prompt": prompt,
                "instruction": "Execute this prompt and return the JSON.",
            }),
        )


class ListAttorneysTool:
    """List all attorneys with stored preferences."""

    def __init__(self, storage: VelaTableStorage) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "list_attorneys"

    @property
    def description(self) -> str:
        return "List all attorney email addresses that have preferences stored in Vela."

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            attorneys = self._storage.list_attorneys()
            return ToolResult(
                success=True,
                output=json.dumps({"attorneys": attorneys, "count": len(attorneys)}),
            )
        except Exception as exc:
            return ToolResult(success=False, error={"message": str(exc)})
