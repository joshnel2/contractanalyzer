"""Email reading tool — fetches recent messages from a user's inbox."""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient

logger = logging.getLogger("strapped.tools.email")


class ReadEmailsTool:
    """Fetch recent emails for a user via Microsoft Graph."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "read_emails"

    @property
    def description(self) -> str:
        return (
            "Fetch recent emails from a user's Microsoft 365 inbox. "
            "Returns subject, sender, preview, importance, and read status."
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
                "count": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max emails to fetch",
                },
                "since_hours": {
                    "type": "integer",
                    "default": 24,
                    "description": "Look back this many hours",
                },
            },
            "required": ["user_email"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            emails = await self._graph.get_recent_emails(
                user_email=input["user_email"],
                count=input.get("count", 20),
                since_hours=input.get("since_hours", 24),
            )
            return ToolResult(
                success=True,
                output=json.dumps(emails, default=str),
            )
        except Exception as exc:
            logger.exception("read_emails failed")
            return ToolResult(success=False, error={"message": str(exc)})
