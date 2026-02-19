"""PostgreSQL-backed storage for preferences, audit logs, and thread state.

Replaces the original Azure Table Storage implementation.
All public method signatures are preserved so callers are unaffected.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import get_db
from core.db_models import AuditLog, FirmDefault, Preference, Thread
from core.models import AttorneyPreferences, AuditEntry

logger = logging.getLogger("strapped.storage")

_PREF_FIELDS = [
    "display_name", "working_hours_start", "working_hours_end", "timezone",
    "buffer_before_minutes", "buffer_after_minutes",
    "preferred_duration_internal", "preferred_duration_client",
    "priority_order", "response_tone", "auto_approve_threshold",
    "blackout_dates", "blocked_times", "favorite_locations",
    "default_virtual_platform", "escalation_email", "escalation_keywords",
    "custom_signature", "court_block_calendars",
]


class StrappedTableStorage:
    """Thin facade over PostgreSQL for backward-compatible storage ops."""

    # ── Preferences ──────────────────────────────────────────────────────

    def get_preferences(self, attorney_email: str) -> AttorneyPreferences:
        """Return merged firm-default + per-user overrides."""
        defaults = self._get_firm_defaults()
        overrides = self._get_user_prefs(attorney_email)
        merged = {**defaults, **overrides, "attorney_email": attorney_email}
        return AttorneyPreferences(**merged)

    def upsert_preferences(self, prefs: AttorneyPreferences) -> None:
        data = {k: v for k, v in prefs.model_dump().items() if k in _PREF_FIELDS}
        data["email"] = prefs.attorney_email
        # Convert enum to string for storage
        if hasattr(data.get("response_tone"), "value"):
            data["response_tone"] = data["response_tone"].value
        # Convert Priority enums in priority_order
        if "priority_order" in data and data["priority_order"]:
            data["priority_order"] = [
                p.value if hasattr(p, "value") else p for p in data["priority_order"]
            ]

        with get_db() as db:
            stmt = pg_insert(Preference).values(**data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["email"],
                set_={k: v for k, v in data.items() if k != "email"},
            )
            db.execute(stmt)
        logger.info("Preferences saved for %s", prefs.attorney_email)

    def upsert_firm_defaults(self, prefs: dict[str, Any]) -> None:
        with get_db() as db:
            for key, value in prefs.items():
                stmt = pg_insert(FirmDefault).values(key=key, value=value)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["key"],
                    set_={"value": value, "updated_at": datetime.now(timezone.utc)},
                )
                db.execute(stmt)

    def list_attorneys(self) -> list[str]:
        with get_db() as db:
            rows = db.execute(select(Preference.email).order_by(Preference.email)).scalars().all()
            return list(rows)

    def _get_firm_defaults(self) -> dict[str, Any]:
        with get_db() as db:
            rows = db.execute(select(FirmDefault)).scalars().all()
            return {row.key: row.value for row in rows}

    def _get_user_prefs(self, email: str) -> dict[str, Any]:
        with get_db() as db:
            row = db.execute(
                select(Preference).where(Preference.email == email)
            ).scalar_one_or_none()
            if not row:
                return {}
            result: dict[str, Any] = {}
            for field in _PREF_FIELDS:
                val = getattr(row, field, None)
                if val is not None:
                    result[field] = val
            return result

    # ── Audit Log ────────────────────────────────────────────────────────

    def log_audit(self, entry: AuditEntry) -> None:
        with get_db() as db:
            row = AuditLog(
                attorney_email=entry.partition_key,
                action=entry.action,
                message_id=entry.message_id,
                details=entry.details,
                outcome=entry.outcome,
                confidence=entry.confidence,
            )
            db.add(row)
        logger.debug("Audit logged: %s / %s", entry.action, entry.partition_key)

    def get_audit_trail(
        self, attorney_email: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        with get_db() as db:
            rows = db.execute(
                select(AuditLog)
                .where(AuditLog.attorney_email == attorney_email)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [
                {
                    "action": r.action,
                    "message_id": r.message_id,
                    "details": r.details,
                    "outcome": r.outcome,
                    "confidence": r.confidence,
                    "timestamp": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]

    # ── Thread State ─────────────────────────────────────────────────────

    def save_thread(self, conversation_id: str, data: dict[str, Any]) -> None:
        with get_db() as db:
            stmt = pg_insert(Thread).values(conversation_id=conversation_id, data=data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["conversation_id"],
                set_={"data": data, "updated_at": datetime.now(timezone.utc)},
            )
            db.execute(stmt)

    def get_thread(self, conversation_id: str) -> dict[str, Any] | None:
        with get_db() as db:
            row = db.execute(
                select(Thread).where(Thread.conversation_id == conversation_id)
            ).scalar_one_or_none()
            return row.data if row else None
