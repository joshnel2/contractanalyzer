"""PostgreSQL database engine, session factory, and schema bootstrap.

Usage:
    from core.database import get_db, init_db

    # In application startup
    init_db()

    # In request handlers / tools
    with get_db() as db:
        db.execute(...)
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger("strapped.database")

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def _get_engine():
    global _engine
    if _engine is None:
        from core.config import settings
        _engine = create_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a database session with automatic commit/rollback."""
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    import core.db_models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=_get_engine())
    logger.info("Database tables initialised")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
    print("Database tables created successfully.")
