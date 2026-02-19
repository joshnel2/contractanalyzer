"""Preferences tools — read and update user notification preferences."""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.models import AttorneyPreferences
from core.table_storage import StrappedTableStorage

logger = logging.getLogger("strapped.tools.preferences")


class GetPreferencesTool:
    """Load preferences for a user."""

    def __init__(self, storage: StrappedTableStorage) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "get_preferences"

    @property
    def description(self) -> str:
        return "Retrieve a user's notification and summary preferences."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "The user's email address",
                },
            },
            "required": ["user_email"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            prefs = self._storage.get_preferences(input["user_email"])
            return ToolResult(
                success=True,
                output=json.dumps(prefs.model_dump(), default=str),
            )
        except Exception as exc:
            logger.exception("get_preferences failed")
            return ToolResult(success=False, error={"message": str(exc)})


class UpdatePreferencesTool:
    """Update preferences for a user."""

    def __init__(self, storage: StrappedTableStorage) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "update_preferences"

    @property
    def description(self) -> str:
        return (
            "Update a user's preferences. Accepts a partial dict of fields "
            "to change — unchanged fields are kept."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_email": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": "Partial dict of preference fields to update",
                },
            },
            "required": ["user_email", "updates"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            email = input["user_email"]
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
                    "user": email,
                    "changed_fields": list(updates.keys()),
                }),
            )
        except Exception as exc:
            logger.exception("update_preferences failed")
            return ToolResult(success=False, error={"message": str(exc)})
