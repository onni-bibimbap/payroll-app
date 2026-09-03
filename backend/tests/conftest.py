"""Shared pytest fixtures: import-path setup and an in-memory SQLite database.

The suite never touches Postgres — the venv has no driver — so everything
runs against SQLite in memory, and money assertions exercise the Decimal
engine directly.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Pin the app to an in-memory database BEFORE any app import builds an engine,
# so no test can accidentally reach a real (Supabase) DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402,F401  (register models on Base)
from app.database import Base  # noqa: E402


@pytest.fixture()
def db() -> Iterator[Session]:
    """Yield a session bound to a fresh in-memory SQLite schema."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db: Session) -> Iterator[object]:
    """FastAPI TestClient whose request sessions are the ``db`` fixture."""
    from fastapi.testclient import TestClient  # noqa: PLC0415 (lazy: httpx)

    from app.database import get_db
    from app.main import app

    def _override() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
