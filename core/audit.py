"""Structured audit logger for Strapped AI.

Every email received, decision made, reply sent, and escalation triggered
is recorded to Azure Table Storage with full traceability.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from core.models import AuditEntry

logger = logging.getLogger("strapped.audit")


class AuditLogger:
    """Convenience wrapper that builds ``AuditEntry`` objects and persists them."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def log(
        self,
        attorney_email: str,
        action: str,
        *,
        message_id: str = "",
        details: dict[str, Any] | None = None,
        outcome: str = "",
        confidence: int = 0,
    ) -> None:
        entry = AuditEntry(
            partition_key=attorney_email,
            row_key=_row_key(),
            timestamp=datetime.now(timezone.utc),
            action=action,
            message_id=message_id,
            details=details or {},
            outcome=outcome,
            confidence=confidence,
        )
        try:
            self._storage.log_audit(entry)
        except Exception:
            logger.exception("Failed to persist audit entry for %s", attorney_email)

    # Semantic helpers

    def email_received(self, attorney_email: str, message_id: str, subject: str) -> None:
        self.log(
            attorney_email,
            "email_received",
            message_id=message_id,
            details={"subject": subject},
        )

    def intent_parsed(
        self,
        attorney_email: str,
        message_id: str,
        intent: str,
        confidence: int,
    ) -> None:
        self.log(
            attorney_email,
            "intent_parsed",
            message_id=message_id,
            details={"intent": intent},
            confidence=confidence,
        )

    def reply_sent(
        self,
        attorney_email: str,
        message_id: str,
        to: list[str],
        confidence: int,
    ) -> None:
        self.log(
            attorney_email,
            "reply_sent",
            message_id=message_id,
            details={"to": to},
            outcome="auto_sent",
            confidence=confidence,
        )

    def escalated(
        self,
        attorney_email: str,
        message_id: str,
        reasons: list[str],
    ) -> None:
        self.log(
            attorney_email,
            "escalated",
            message_id=message_id,
            details={"reasons": reasons},
            outcome="escalated",
        )

    def preferences_updated(
        self,
        attorney_email: str,
        changes: dict[str, Any],
    ) -> None:
        self.log(
            attorney_email,
            "preferences_updated",
            details={"changes": changes},
            outcome="prefs_saved",
        )

    def calendar_event_created(
        self,
        attorney_email: str,
        event_id: str,
        subject: str,
    ) -> None:
        self.log(
            attorney_email,
            "calendar_event_created",
            details={"event_id": event_id, "subject": subject},
            outcome="event_created",
        )


def _row_key() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{ts}_{uuid.uuid4().hex[:8]}"
