"""Reply-drafting Amplifier tools.

Generates professional, tone-appropriate scheduling replies and sends
them through the Graph API from the Strapped shared mailbox.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient

logger = logging.getLogger("strapped.tools.reply")


class DraftReplyTool:
    """Compose a scheduling reply based on available slots and preferences."""

    @property
    def name(self) -> str:
        return "draft_reply"

    @property
    def description(self) -> str:
        return (
            "Draft a professional scheduling reply email. Provide the available "
            "slots, attorney preferences (tone, signature), and original request "
            "context. Returns the formatted email body."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "original_subject": {"type": "string"},
                "original_sender": {"type": "string"},
                "attorney_name": {"type": "string"},
                "available_slots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                    },
                },
                "duration_minutes": {"type": "integer"},
                "meeting_type": {
                    "type": "string",
                    "description": "client, internal, or admin",
                },
                "tone": {
                    "type": "string",
                    "enum": ["formal", "friendly", "concise"],
                    "default": "formal",
                },
                "custom_signature": {"type": "string", "default": ""},
                "location_or_platform": {"type": "string", "default": "Microsoft Teams"},
                "special_instructions": {"type": "string", "default": ""},
            },
            "required": ["original_subject", "original_sender", "attorney_name", "available_slots"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        tone = input.get("tone", "formal")
        slots = input.get("available_slots", [])
        attorney = input.get("attorney_name", "the attorney")
        sig = input.get("custom_signature", "")

        tone_instruction = {
            "formal": "Use polished, professional legal language. Address the recipient respectfully.",
            "friendly": "Be warm and approachable while remaining professional.",
            "concise": "Be brief and direct. Minimal pleasantries.",
        }.get(tone, "Use professional legal language.")

        prompt = f"""\
Draft a scheduling reply email on behalf of {attorney}.

{tone_instruction}

Original subject: {input.get('original_subject', '')}
Recipient: {input.get('original_sender', '')}
Meeting type: {input.get('meeting_type', 'client')}
Duration: {input.get('duration_minutes', 60)} minutes
Platform/Location: {input.get('location_or_platform', 'Microsoft Teams')}
Special instructions: {input.get('special_instructions', 'None')}

Propose these time slots (present 2-3 as options with brief reasoning):
{json.dumps(slots[:3], indent=2, default=str)}

End with: {sig if sig else f'Best regards,\\nOffice of {attorney}'}

Return the reply as HTML suitable for email. Include a plain-text fallback
after a separator "---PLAIN---".
"""
        return ToolResult(
            success=True,
            output=json.dumps({
                "_strapped_internal": "llm_prompt",
                "prompt": prompt,
                "instruction": "Generate the HTML email body followed by ---PLAIN--- and plain-text version.",
            }),
        )


class SendReplyTool:
    """Send an already-drafted reply via the Strapped shared mailbox."""

    def __init__(self, graph: StrappedGraphClient, vela_mailbox: str) -> None:
        self._graph = graph
        self._vela_mailbox = vela_mailbox

    @property
    def name(self) -> str:
        return "send_reply"

    @property
    def description(self) -> str:
        return (
            "Send a reply email from the Strapped shared mailbox. Use this ONLY "
            "when the confidence threshold is met or after explicit attorney "
            "approval. Provide to, cc, subject, and HTML body."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to_addresses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cc_addresses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "subject": {"type": "string"},
                "body_html": {"type": "string"},
            },
            "required": ["to_addresses", "subject", "body_html"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            await self._graph.send_mail(
                from_mailbox=self._vela_mailbox,
                to_addresses=input["to_addresses"],
                subject=input["subject"],
                body_html=input["body_html"],
                cc_addresses=input.get("cc_addresses"),
            )
            return ToolResult(
                success=True,
                output=json.dumps({
                    "status": "sent",
                    "to": input["to_addresses"],
                    "subject": input["subject"],
                }),
            )
        except Exception as exc:
            logger.exception("send_reply failed")
            return ToolResult(success=False, error={"message": str(exc)})
