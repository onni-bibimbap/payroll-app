"""Seed demo users and clearly synthetic demo employees (explicit one-shot).

This script is NEVER run on container boot (the image CMD starts uvicorn
only). Run it deliberately against the local dev database:

    make seed
    # equivalent to:
    docker compose --profile dev run --rm -e SEED_DEMO_DATA=true \
        backend python seed.py

Safety gates:
    * Refuses to run unless ``SEED_DEMO_DATA=true`` is set in the
      environment (INFRA-01).
    * Refuses to run against a Supabase/remote-looking DATABASE_URL unless
      ``SEED_ALLOW_REMOTE=true`` is also set.
    * Never overwrites an existing user's password hash or role (SEC-03/
      SEC-10) — users are created only when missing.
    * Employees are seeded only when the employees table is empty, and every
      seeded row is synthetic (Ali Demo, Siti Contoh, ... with all-zero bank
      account numbers). No real roster, no spreadsheet import (SEC-09/
      INFRA-08); real-data imports are a separate, documented operator task.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import config, store
from app.database import SessionLocal, engine, init_db
from app.models import Employee, User
from app.security import hash_password

logger = logging.getLogger(__name__)

# Clearly synthetic demo roster (Malay "contoh"/"ujian" = example/test).
# All identity and bank values are obviously fake placeholders.
DEMO_EMPLOYEES: list[dict[str, Any]] = [
    {
        "emp_code": "DEMO001",
        "name": "Ali Demo",
        "employment_type": "full_time",
        "basic_salary": Decimal("2600"),
        "epf_enabled": True,
        "socso_enabled": True,
        "bank_name": "Demo Bank",
        "bank_account": "000000000001",
        "nric": "000000000001",
    },
    {
        "emp_code": "DEMO002",
        "name": "Siti Contoh",
        "employment_type": "full_time",
        "basic_salary": Decimal("3100"),
        "epf_enabled": True,
        "socso_enabled": True,
        "bank_name": "Demo Bank",
        "bank_account": "000000000002",
        "nric": "000000000002",
    },
    {
        "emp_code": "DEMO003",
        "name": "Kumar Ujian",
        "employment_type": "part_time",
        "hourly_rate": Decimal("8"),
        "epf_enabled": False,
        "socso_enabled": False,
        "bank_name": "Demo Bank",
        "bank_account": "000000000003",
        "nric": "000000000003",
    },
    {
        "emp_code": "DEMO004",
        "name": "Mei Contoh",
        "employment_type": "part_time",
        "hourly_rate": Decimal("8"),
        "epf_enabled": False,
        "socso_enabled": False,
        "bank_name": "Demo Bank",
        "bank_account": "000000000004",
        "nric": "000000000004",
    },
    {
        "emp_code": "DEMO005",
        "name": "Aung Demo",
        "employment_type": "full_time",
        "basic_salary": Decimal("2300"),
        "epf_enabled": False,
        "socso_enabled": True,
        "is_foreign": True,
        "bank_name": "Demo Bank",
        "bank_account": "000000000005",
        "nric": "000000000005",
    },
]


def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    """Block until the database accepts connections (docker startup order).

    Args:
        retries: Maximum connection attempts before giving up.
        delay: Seconds to sleep between attempts.

    Raises:
        OperationalError: When the database is still unreachable after the
            final attempt.
    """
    for attempt in range(retries):
        try:
            with engine.connect():
                return
        except OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def seed_users(db: Session) -> int:
    """Create the configured demo users when missing; never touch existing.

    An existing user's password hash, role and name are left untouched so a
    re-run can never reset credentials that were changed through the app
    (SEC-03/SEC-10).

    Args:
        db: Open SQLAlchemy session.

    Returns:
        The number of users created.
    """
    created = 0
    for spec in config.SEED_USERS:
        user = db.scalar(select(User).where(User.username == spec["username"]))
        if user is not None:
            logger.info("User %r exists — left untouched.", spec["username"])
            continue
        db.add(User(username=spec["username"], full_name=spec["full_name"],
                    role=spec["role"],
                    password_hash=hash_password(spec["password"])))
        created += 1
        logger.info("Created user %r (%s).", spec["username"], spec["role"])
    db.commit()
    return created


def seed_demo_employees(db: Session) -> int:
    """Insert the synthetic demo employees when the table is empty.

    Args:
        db: Open SQLAlchemy session.

    Returns:
        The number of employees inserted (0 when the table already has rows).
    """
    count = db.scalar(select(func.count()).select_from(Employee)) or 0
    if count:
        logger.info("Employees already present (%d); demo roster skipped.",
                    count)
        return 0
    hire = dt.date.today().replace(day=1)
    for spec in DEMO_EMPLOYEES:
        db.add(Employee(active=True, status="active", hire_date=hire,
                        outlet="Setapak", **spec))
    db.commit()
    logger.info("Inserted %d synthetic demo employees.", len(DEMO_EMPLOYEES))
    return len(DEMO_EMPLOYEES)


def _refuse(reason: str) -> None:
    """Log a refusal and exit non-zero without touching the database."""
    logger.error("Refusing to seed: %s", reason)
    sys.exit(1)


def main() -> None:
    """Run the gated demo seed against the configured database."""
    if os.environ.get("SEED_DEMO_DATA", "").lower() != "true":
        _refuse("SEED_DEMO_DATA=true is not set. Seeding is an explicit "
                "one-shot (`make seed`), never part of normal startup.")
    db_url = config.DATABASE_URL.lower()
    remote_ok = os.environ.get("SEED_ALLOW_REMOTE", "").lower() == "true"
    if "supabase" in db_url and not remote_ok:
        _refuse("DATABASE_URL looks like Supabase/production. Set "
                "SEED_ALLOW_REMOTE=true only if you are certain.")

    wait_for_db()
    init_db()
    db = SessionLocal()
    try:
        store.get_settings(db)  # create the Settings singleton with defaults
        users = seed_users(db)
        emps = seed_demo_employees(db)
        logger.info("Seed complete: %d users created, %d demo employees.",
                    users, emps)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(levelname)s %(name)s: %(message)s")
    main()
