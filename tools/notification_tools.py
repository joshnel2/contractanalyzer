"""Notification tool — sends digest summaries to users via email."""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient

logger = logging.getLogger("strapped.tools.notification")


class SendDigestTool:
    """Send a summary digest email to a user."""

    def __init__(self, graph: StrappedGraphClient, from_mailbox: str) -> None:
        self._graph = graph
        self._from = from_mailbox

    @property
    def name(self) -> str:
        return "send_digest"

    @property
    def description(self) -> str:
        return (
            "Send a digest summary email to the user. Provide the HTML body "
            "with the email and calendar summary you generated."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "description": "Recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body_html": {
                    "type": "string",
                    "description": "HTML body with the digest content",
                },
            },
            "required": ["to_email", "subject", "body_html"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            await self._graph.send_mail(
                from_mailbox=self._from,
                to_addresses=[input["to_email"]],
                subject=input["subject"],
                body_html=input["body_html"],
            )
            return ToolResult(
                success=True,
                output=json.dumps({"status": "sent", "to": input["to_email"]}),
            )
        except Exception as exc:
            logger.exception("send_digest failed")
            return ToolResult(success=False, error={"message": str(exc)})
