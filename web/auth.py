"""Authentication module — JWT sessions with users stored in PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from core.database import get_db
from core.db_models import DemoRequest, User

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
    """User CRUD backed by PostgreSQL."""

    def create_user(
        self,
        email: str,
        password: str,
        name: str = "",
        company: str = "",
    ) -> bool:
        if self.get_user(email):
            return False
        with get_db() as db:
            db.add(User(
                email=email.lower(),
                name=name,
                company=company,
                password_hash=hash_password(password),
                is_active=True,
            ))
        return True

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.execute(
                select(User).where(User.email == email.lower())
            ).scalar_one_or_none()
            if not user:
                return None
            if not verify_password(password, user.password_hash):
                return None
            return {
                "email": user.email,
                "name": user.name,
                "company": user.company,
            }

    def get_user(self, email: str) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.execute(
                select(User).where(User.email == email.lower())
            ).scalar_one_or_none()
            if not user:
                return None
            return {
                "email": user.email,
                "name": user.name,
                "company": user.company,
                "is_active": user.is_active,
            }

    def save_demo_request(
        self,
        name: str,
        email: str,
        company: str,
        message: str = "",
    ) -> None:
        with get_db() as db:
            db.add(DemoRequest(
                name=name,
                email=email,
                company=company,
                message=message,
                status="pending",
            ))
