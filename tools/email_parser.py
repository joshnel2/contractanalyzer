"""Email-parsing Amplifier tool.

Extracts structured scheduling intent from raw inbound email, identifying
participants, proposed times, matter/client references, urgency, and any
embedded Strapped preference commands.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

logger = logging.getLogger("strapped.tools.email_parser")

_PARSE_PROMPT = """\
You are Strapped AI's email-analysis subsystem. Given the raw email below,
extract the following fields as a JSON object. Be precise and conservative —
if you are unsure about a field, leave it as the default.

Required JSON schema:
{{
  "intent": "schedule_meeting | reschedule | cancel | check_availability | update_preferences | general_inquiry | unknown",
  "requesting_attorney_email": "<the person who CC'd or forwarded to Strapped>",
  "external_participants": ["<email or name of people outside the firm>"],
  "proposed_times": ["<any times/dates mentioned, in ISO-8601 or natural language>"],
  "duration_minutes": <int or null>,
  "matter_or_client": "<client name, matter number, or empty string>",
  "urgency": "normal | high | critical",
  "special_instructions": "<any location, call-in, travel, dietary, or other notes>",
  "preference_commands": ["<any 'Strapped: ...' commands found in the body>"],
  "confidence": <0-100 your confidence in the overall parse>,
  "escalation_flags": ["<any of: rate_discussion, travel, multi_party, conflict_of_interest, custom_flag>"],
  "raw_summary": "<one-sentence summary of the request>"
}}

── EMAIL ──
From: {from_address} ({from_name})
To: {to_addresses}
CC: {cc_addresses}
Subject: {subject}
Date: {received_at}
Body:
{body_text}
── END EMAIL ──

Return ONLY the JSON object, no markdown fences.
"""


class EmailParserTool:
    """Amplifier Tool that parses inbound emails into structured intent."""

    @property
    def name(self) -> str:
        return "parse_email"

    @property
    def description(self) -> str:
        return (
            "Parse a raw inbound email and extract structured scheduling intent, "
            "participants, proposed times, matter/client info, urgency, and any "
            "embedded preference commands. Returns JSON."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "from_address": {"type": "string"},
                "from_name": {"type": "string", "default": ""},
                "to_addresses": {"type": "string"},
                "cc_addresses": {"type": "string"},
                "subject": {"type": "string"},
                "body_text": {"type": "string"},
                "received_at": {"type": "string"},
            },
            "required": ["from_address", "subject", "body_text"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        prompt = _PARSE_PROMPT.format(
            from_address=input.get("from_address", ""),
            from_name=input.get("from_name", ""),
            to_addresses=input.get("to_addresses", ""),
            cc_addresses=input.get("cc_addresses", ""),
            subject=input.get("subject", ""),
            body_text=input.get("body_text", "")[:4000],
            received_at=input.get("received_at", ""),
        )
        return ToolResult(
            success=True,
            output=json.dumps({
                "_strapped_internal": "llm_prompt",
                "prompt": prompt,
                "instruction": (
                    "Execute this prompt against the LLM and return the raw JSON. "
                    "Do NOT add commentary — only the JSON object."
                ),
            }),
        )


class IdentifyAttorneyTool:
    """Determine which team member CC'd Strapped and resolve their email."""

    @property
    def name(self) -> str:
        return "identify_attorney"

    @property
    def description(self) -> str:
        return (
            "Given the To and CC lists from an inbound email, identify which "
            "address belongs to the requesting person (i.e. the non-Strapped "
            "internal address)."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "from_address": {"type": "string"},
                "to_addresses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cc_addresses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "vela_mailbox": {"type": "string"},
            },
            "required": ["from_address", "to_addresses", "cc_addresses", "vela_mailbox"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        vela = input["vela_mailbox"].lower()
        from_addr = input["from_address"].lower()

        all_addresses = input.get("to_addresses", []) + input.get("cc_addresses", [])
        internal = [
            addr for addr in all_addresses
            if addr.lower() != vela and addr.lower() != from_addr
        ]

        # The requesting attorney is most likely the sender or on the CC line
        attorney = from_addr
        for addr in all_addresses:
            if addr.lower() != vela and addr.lower().endswith(
                vela.split("@")[-1]
            ):
                attorney = addr.lower()
                break

        return ToolResult(
            success=True,
            output=json.dumps({
                "requesting_attorney": attorney,
                "other_internal": internal,
                "external_sender": from_addr if from_addr != attorney else "",
            }),
        )
