"""Azure Table Storage client for preferences, audit logs, and thread state.

Tables
------
* ``VelaPreferences``  — one row per attorney (PartitionKey = firm, RowKey = email)
* ``VelaAuditLog``     — append-only log (PartitionKey = attorney email, RowKey = timestamp)
* ``VelaThreads``      — conversation thread tracking (PartitionKey = conversation_id)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from azure.data.tables import TableClient, TableServiceClient, UpdateMode

from core.models import AttorneyPreferences, AuditEntry

logger = logging.getLogger("vela.storage")

_PREFS_TABLE = "VelaPreferences"
_AUDIT_TABLE = "VelaAuditLog"
_THREADS_TABLE = "VelaThreads"

_FIRM_PARTITION = "firm_default"


class VelaTableStorage:
    """Thin wrapper around Azure Table Storage for the three Vela tables."""

    def __init__(self, connection_string: str) -> None:
        self._svc = TableServiceClient.from_connection_string(connection_string)
        self._ensure_tables()

    # ── Bootstrap ────────────────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        for name in (_PREFS_TABLE, _AUDIT_TABLE, _THREADS_TABLE):
            try:
                self._svc.create_table_if_not_exists(name)
                logger.info("Table ready: %s", name)
            except Exception:
                logger.debug("Table %s already exists or creation deferred", name)

    def _table(self, name: str) -> TableClient:
        return self._svc.get_table_client(name)

    # ── Preferences ──────────────────────────────────────────────────────────

    def get_preferences(self, attorney_email: str) -> AttorneyPreferences:
        """Return merged firm-default + per-attorney overrides."""
        defaults = self._get_raw_prefs(_FIRM_PARTITION, "defaults")
        overrides = self._get_raw_prefs("attorney", attorney_email)

        merged = {**defaults, **overrides}
        merged["attorney_email"] = attorney_email
        return AttorneyPreferences(**merged)

    def upsert_preferences(self, prefs: AttorneyPreferences) -> None:
        entity = self._prefs_to_entity(prefs)
        self._table(_PREFS_TABLE).upsert_entity(entity, mode=UpdateMode.MERGE)
        logger.info("Preferences saved for %s", prefs.attorney_email)

    def upsert_firm_defaults(self, prefs: dict[str, Any]) -> None:
        entity: dict[str, Any] = {
            "PartitionKey": _FIRM_PARTITION,
            "RowKey": "defaults",
        }
        for k, v in prefs.items():
            entity[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        self._table(_PREFS_TABLE).upsert_entity(entity, mode=UpdateMode.MERGE)

    def list_attorneys(self) -> list[str]:
        """Return emails of all attorneys with stored preferences."""
        rows = self._table(_PREFS_TABLE).query_entities(
            "PartitionKey eq 'attorney'", select=["RowKey"]
        )
        return [r["RowKey"] for r in rows]

    def _get_raw_prefs(self, pk: str, rk: str) -> dict[str, Any]:
        try:
            entity = self._table(_PREFS_TABLE).get_entity(pk, rk)
            return self._entity_to_dict(entity)
        except Exception:
            return {}

    @staticmethod
    def _prefs_to_entity(prefs: AttorneyPreferences) -> dict[str, Any]:
        data = prefs.model_dump()
        entity: dict[str, Any] = {
            "PartitionKey": "attorney",
            "RowKey": prefs.attorney_email,
        }
        for k, v in data.items():
            entity[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        return entity

    @staticmethod
    def _entity_to_dict(entity: dict[str, Any]) -> dict[str, Any]:
        skip = {"PartitionKey", "RowKey", "Timestamp", "etag", "odata.etag", "odata.metadata"}
        result: dict[str, Any] = {}
        for k, v in entity.items():
            if k in skip:
                continue
            if isinstance(v, str):
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            else:
                result[k] = v
        return result

    # ── Audit Log ────────────────────────────────────────────────────────────

    def log_audit(self, entry: AuditEntry) -> None:
        entity: dict[str, Any] = {
            "PartitionKey": entry.partition_key,
            "RowKey": entry.row_key or _audit_row_key(),
            "timestamp": entry.timestamp.isoformat(),
            "action": entry.action,
            "message_id": entry.message_id,
            "details": json.dumps(entry.details),
            "outcome": entry.outcome,
            "confidence": entry.confidence,
        }
        self._table(_AUDIT_TABLE).upsert_entity(entity, mode=UpdateMode.REPLACE)
        logger.debug("Audit logged: %s / %s", entry.action, entry.partition_key)

    def get_audit_trail(
        self, attorney_email: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        query = f"PartitionKey eq '{attorney_email}'"
        rows = self._table(_AUDIT_TABLE).query_entities(query)
        results = sorted(rows, key=lambda r: r.get("timestamp", ""), reverse=True)
        return [self._entity_to_dict(r) for r in results[:limit]]

    # ── Thread State ─────────────────────────────────────────────────────────

    def save_thread(self, conversation_id: str, data: dict[str, Any]) -> None:
        entity: dict[str, Any] = {
            "PartitionKey": "thread",
            "RowKey": conversation_id,
            "data": json.dumps(data),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._table(_THREADS_TABLE).upsert_entity(entity, mode=UpdateMode.REPLACE)

    def get_thread(self, conversation_id: str) -> dict[str, Any] | None:
        try:
            entity = self._table(_THREADS_TABLE).get_entity("thread", conversation_id)
            raw = entity.get("data", "{}")
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return None


def _audit_row_key() -> str:
    """Reverse-chronological key so newest entries sort first."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{ts}_{uuid.uuid4().hex[:8]}"
