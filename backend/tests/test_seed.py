"""Tests for the gated demo seed script (INFRA-01, SEC-03, SEC-10, INFRA-08).

Covers the boot-safety guarantees: seeding never runs without the explicit
``SEED_DEMO_DATA=true`` gate, never overwrites an existing user's password,
never re-touches an existing employee roster, and only ever inserts clearly
synthetic demo data.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import seed
from app.models import Employee, User
from app.security import verify_password


@pytest.mark.unit
def test_seed_users_creates_missing(db: Session) -> None:
    # Arrange: empty users table.
    assert db.scalar(select(func.count()).select_from(User)) == 0

    # Act
    created = seed.seed_users(db)

    # Assert: the three demo roles exist with working passwords.
    assert created == 3
    roles = {u.username: u.role for u in db.scalars(select(User)).all()}
    assert set(roles.values()) == {"preparer", "approver", "admin"}


@pytest.mark.unit
def test_seed_users_never_overwrites_existing_password(db: Session) -> None:
    # Arrange: an admin whose password was changed through the app.
    sentinel_hash = "sentinel-hash-must-survive"
    db.add(User(username="admin", full_name="Real Admin", role="admin",
                password_hash=sentinel_hash))
    db.commit()

    # Act: re-running the seed must not reset the credential (SEC-03/SEC-10).
    seed.seed_users(db)

    # Assert
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assert admin.password_hash == sentinel_hash
    assert admin.full_name == "Real Admin"


@pytest.mark.unit
def test_seed_users_created_password_verifies(db: Session) -> None:
    # Arrange / Act
    seed.seed_users(db)

    # Assert: each created user's stored hash verifies against the configured
    # password and is never the plaintext itself.
    for spec in seed.config.SEED_USERS:
        user = db.scalar(select(User).where(User.username == spec["username"]))
        assert user is not None
        assert user.password_hash != spec["password"]
        assert verify_password(spec["password"], user.password_hash)


@pytest.mark.unit
def test_main_refuses_without_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: gate unset — main() must exit before touching the database.
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)
    monkeypatch.setattr(seed, "wait_for_db",
                        lambda *a, **k: pytest.fail("touched the database"))

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        seed.main()
    assert exc.value.code == 1


@pytest.mark.unit
def test_main_refuses_supabase_url_without_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: gate set, but DATABASE_URL looks like production Supabase.
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    monkeypatch.delenv("SEED_ALLOW_REMOTE", raising=False)
    monkeypatch.setattr(
        seed.config, "DATABASE_URL",
        "postgresql+psycopg2://postgres:x@db.ref.supabase.co:5432/postgres",
    )
    monkeypatch.setattr(seed, "wait_for_db",
                        lambda *a, **k: pytest.fail("touched the database"))

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        seed.main()
    assert exc.value.code == 1


@pytest.mark.unit
def test_demo_roster_is_synthetic() -> None:
    # The hardcoded real-name rosters must stay gone (SEC-09/INFRA-08).
    assert not hasattr(seed, "ACTIVE_ROSTER")
    assert not hasattr(seed, "EPF_ROSTER")
    assert not hasattr(seed, "configure_roster")
    for spec in seed.DEMO_EMPLOYEES:
        assert spec["bank_account"].startswith("00000000")
        assert any(tag in spec["name"] for tag in ("Demo", "Contoh", "Ujian"))


@pytest.mark.unit
def test_seed_demo_employees_only_when_empty(db: Session) -> None:
    # Act: first run populates, second run must be a no-op.
    first = seed.seed_demo_employees(db)
    second = seed.seed_demo_employees(db)

    # Assert
    assert first == len(seed.DEMO_EMPLOYEES)
    assert second == 0
    assert (db.scalar(select(func.count()).select_from(Employee))
            == len(seed.DEMO_EMPLOYEES))


@pytest.mark.unit
def test_seed_demo_employees_skips_populated_table(db: Session) -> None:
    # Arrange: a real employee already exists (e.g. via HR flows).
    db.add(Employee(emp_code="ON99999", name="Existing Person", active=True))
    db.commit()

    # Act
    inserted = seed.seed_demo_employees(db)

    # Assert: nothing was added or modified.
    assert inserted == 0
    assert db.scalar(select(func.count()).select_from(Employee)) == 1
