"""Calendar reading tool — fetches upcoming events from a user's calendar."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient

logger = logging.getLogger("strapped.tools.calendar")


class ReadCalendarTool:
    """Fetch upcoming calendar events for a user via Microsoft Graph."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "read_calendar"

    @property
    def description(self) -> str:
        return (
            "Fetch upcoming calendar events for a user. Returns subject, "
            "start/end times, location, attendees, and notes for each event."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "The user's email address",
                },
                "days_ahead": {
                    "type": "integer",
                    "default": 3,
                    "description": "How many days ahead to look",
                },
            },
            "required": ["user_email"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            now = datetime.now(timezone.utc)
            end = now + timedelta(days=input.get("days_ahead", 3))
            events = await self._graph.get_events(
                user_email=input["user_email"],
                start=now,
                end=end,
            )
            return ToolResult(
                success=True,
                output=json.dumps(events, default=str),
            )
        except Exception as exc:
            logger.exception("read_calendar failed")
            return ToolResult(success=False, error={"message": str(exc)})
