"""Escalation-handler Amplifier tools.

When Strapped is uncertain, detects sensitive keywords, or encounters complex
multi-party scheduling, it escalates to the requesting attorney with
a clear explanation of what it found and what it needs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient

logger = logging.getLogger("strapped.tools.escalation")


class EvaluateEscalationTool:
    """Decide whether the current request needs human escalation."""

    @property
    def name(self) -> str:
        return "evaluate_escalation"

    @property
    def description(self) -> str:
        return (
            "Evaluate whether a scheduling request should be escalated to the "
            "attorney for manual handling. Checks confidence score, escalation "
            "keywords, complexity flags, and firm policy."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "confidence": {
                    "type": "integer",
                    "description": "Parse confidence 0-100",
                },
                "auto_approve_threshold": {
                    "type": "integer",
                    "description": "Attorney's threshold (default 85)",
                },
                "escalation_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "body_text": {
                    "type": "string",
                    "description": "Email body to scan for sensitive terms",
                },
                "escalation_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Attorney's configured escalation keywords",
                },
                "participant_count": {
                    "type": "integer",
                    "default": 2,
                },
            },
            "required": ["confidence", "auto_approve_threshold"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        confidence = input.get("confidence", 0)
        threshold = input.get("auto_approve_threshold", 85)
        flags = input.get("escalation_flags", [])
        body = input.get("body_text", "").lower()
        keywords = input.get("escalation_keywords", [])
        participants = input.get("participant_count", 2)

        reasons: list[str] = []

        if confidence < threshold:
            reasons.append(
                f"Confidence ({confidence}%) below threshold ({threshold}%)"
            )

        if flags:
            reasons.append(f"Explicit escalation flags: {', '.join(flags)}")

        matched_keywords = [kw for kw in keywords if kw.lower() in body]
        if matched_keywords:
            reasons.append(f"Sensitive keywords detected: {', '.join(matched_keywords)}")

        if participants > 4:
            reasons.append(f"Complex multi-party scheduling ({participants} participants)")

        should_escalate = len(reasons) > 0

        return ToolResult(
            success=True,
            output=json.dumps({
                "should_escalate": should_escalate,
                "reasons": reasons,
                "confidence": confidence,
                "threshold": threshold,
            }),
        )


class SendEscalationTool:
    """Notify the attorney (and optionally the original sender) about escalation."""

    def __init__(self, graph: StrappedGraphClient, vela_mailbox: str) -> None:
        self._graph = graph
        self._vela_mailbox = vela_mailbox

    @property
    def name(self) -> str:
        return "send_escalation"

    @property
    def description(self) -> str:
        return (
            "Send an escalation email to the team member explaining why Strapped "
            "could not auto-handle the request. Includes the original context, "
            "what Strapped understood, and what it needs them to decide."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attorney_email": {"type": "string"},
                "escalation_email": {
                    "type": "string",
                    "description": "Override recipient (defaults to attorney_email)",
                },
                "original_subject": {"type": "string"},
                "original_sender": {"type": "string"},
                "reasons": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "understanding": {
                    "type": "string",
                    "description": "What Strapped understood from the email",
                },
                "suggested_action": {
                    "type": "string",
                    "description": "What Strapped recommends",
                },
                "include_original_sender": {
                    "type": "boolean",
                    "default": False,
                    "description": "CC the original sender on escalation",
                },
            },
            "required": ["attorney_email", "original_subject", "reasons", "understanding"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        to_email = input.get("escalation_email") or input["attorney_email"]
        reasons_html = "".join(f"<li>{r}</li>" for r in input["reasons"])

        body_html = f"""\
<div style="font-family: Calibri, Arial, sans-serif; color: #333;">
  <p>Hello,</p>
  <p>I received a scheduling request that I'd like your guidance on before
  proceeding.</p>

  <h3 style="color: #1a3a5c;">Original Request</h3>
  <p><strong>Subject:</strong> {input.get('original_subject', '')}<br>
  <strong>From:</strong> {input.get('original_sender', 'Unknown')}</p>

  <h3 style="color: #1a3a5c;">What I Understood</h3>
  <p>{input.get('understanding', '')}</p>

  <h3 style="color: #1a3a5c;">Why I'm Escalating</h3>
  <ul>{reasons_html}</ul>

  <h3 style="color: #1a3a5c;">Suggested Next Step</h3>
  <p>{input.get('suggested_action', 'Please reply with instructions and I will handle the rest.')}</p>

  <hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
  <p style="color: #888; font-size: 12px;">
    This message was generated by Strapped AI, your scheduling assistant.<br>
    Reply to this email or forward instructions to continue.
  </p>
</div>
"""
        cc = []
        if input.get("include_original_sender") and input.get("original_sender"):
            cc.append(input["original_sender"])

        try:
            await self._graph.send_mail(
                from_mailbox=self._vela_mailbox,
                to_addresses=[to_email],
                subject=f"[Strapped AI] {input.get('original_subject', '')}",
                body_html=body_html,
                cc_addresses=cc,
            )
            return ToolResult(
                success=True,
                output=json.dumps({
                    "status": "escalation_sent",
                    "to": to_email,
                    "reasons": input["reasons"],
                }),
            )
        except Exception as exc:
            logger.exception("send_escalation failed")
            return ToolResult(success=False, error={"message": str(exc)})
