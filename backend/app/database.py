"""Database engine, session factory and declarative base."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args,
                       pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if using SQLite; fail fast if Postgres without migrations.

    INFRA-04: For Postgres, the schema source of truth is supabase/migrations,
    applied by the migrate service (or external management). create_all should
    only run on local SQLite (dev fallback).

    For fresh Postgres without migrations applied, models with enum types
    (Employee.status, identity_type) will raise an error referencing non-existent
    types, which is correct — it signals that migrations must be run first.
    """
    from . import models  # noqa: F401  (register models on Base)
    from .config import DATABASE_URL

    # Create tables only for SQLite dev/test; Postgres schema is managed by migrations.
    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
