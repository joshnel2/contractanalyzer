"""SQLAlchemy ORM models for Strapped AI.

Tables:
    users            — web app authentication
    preferences      — per-team-member scheduling preferences
    firm_defaults    — firm-wide default preference values
    audit_log        — every action Strapped takes
    threads          — conversation thread state
    demo_requests    — inbound demo booking requests
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")

    working_hours_start: Mapped[str] = mapped_column(String(10), default="08:00")
    working_hours_end: Mapped[str] = mapped_column(String(10), default="18:00")
    timezone: Mapped[str] = mapped_column(String(100), default="America/New_York")

    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=15)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=10)
    preferred_duration_internal: Mapped[int] = mapped_column(Integer, default=30)
    preferred_duration_client: Mapped[int] = mapped_column(Integer, default=60)

    priority_order: Mapped[dict] = mapped_column(JSONB, default=list)
    response_tone: Mapped[str] = mapped_column(String(20), default="formal")
    auto_approve_threshold: Mapped[int] = mapped_column(Integer, default=85)

    blackout_dates: Mapped[dict] = mapped_column(JSONB, default=list)
    blocked_times: Mapped[dict] = mapped_column(JSONB, default=list)
    favorite_locations: Mapped[dict] = mapped_column(JSONB, default=list)
    default_virtual_platform: Mapped[str] = mapped_column(String(255), default="Microsoft Teams")

    escalation_email: Mapped[str] = mapped_column(String(255), default="")
    escalation_keywords: Mapped[dict] = mapped_column(JSONB, default=list)
    custom_signature: Mapped[str] = mapped_column(Text, default="")
    court_block_calendars: Mapped[dict] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FirmDefault(Base):
    __tablename__ = "firm_defaults"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attorney_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    message_id: Mapped[str] = mapped_column(String(500), default="")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    outcome: Mapped[str] = mapped_column(String(100), default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
