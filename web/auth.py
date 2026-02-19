"""Authentication module — JWT sessions with passwords stored in Table Storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger("strapped.auth")

_SECRET_KEY = "strapped-ai-change-me-in-production"
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 72

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        return None


class UserStore:
    """Thin CRUD layer for users in Azure Table Storage."""

    _TABLE = "StrappedUsers"

    def __init__(self, storage_conn: str) -> None:
        from azure.data.tables import TableServiceClient
        svc = TableServiceClient.from_connection_string(storage_conn)
        try:
            svc.create_table_if_not_exists(self._TABLE)
        except Exception:
            pass
        self._table = svc.get_table_client(self._TABLE)

    def create_user(
        self,
        email: str,
        password: str,
        name: str = "",
        company: str = "",
    ) -> bool:
        if self.get_user(email):
            return False
        entity = {
            "PartitionKey": "user",
            "RowKey": email.lower(),
            "name": name,
            "company": company,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        self._table.upsert_entity(entity)
        return True

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        user = self.get_user(email)
        if not user:
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        return user

    def get_user(self, email: str) -> dict[str, Any] | None:
        try:
            entity = self._table.get_entity("user", email.lower())
            return {
                "email": entity["RowKey"],
                "name": entity.get("name", ""),
                "company": entity.get("company", ""),
                "created_at": entity.get("created_at", ""),
                "is_active": entity.get("is_active", True),
            }
        except Exception:
            return None

    def save_demo_request(
        self,
        name: str,
        email: str,
        company: str,
        message: str = "",
    ) -> None:
        entity = {
            "PartitionKey": "demo_request",
            "RowKey": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{email}",
            "name": name,
            "email": email,
            "company": company,
            "message": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        self._table.upsert_entity(entity)
