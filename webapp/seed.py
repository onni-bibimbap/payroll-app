"""Initialise the database: create tables, seed users, import employees.

Usage:
    python seed.py [path/to/employee-registration-form.xlsx]

Safe to re-run: users are upserted by username; employees are only imported
when the table is empty (pass --reimport to force a fresh employee import).
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import delete, func, select

from app import config, store
from app.database import SessionLocal, init_db
from app.importer import import_employees
from app.models import Employee, User
from app.security import hash_password

DEFAULT_FORM = Path(__file__).resolve().parent.parent / "employee-registration-form (1).xlsx"


# Only these staff are active for the current period; everyone else is resigned.
ACTIVE_ROSTER = [
    "cheong fong cheng", "tan kui thean", "mohd aminludin bin yahya",
    "mohd hafizal bin azahar", "liew chen hao", "tai jun xi", "nay lin zaw",
    "ong peir ann", "thulasi raj murugan", "shannen gomes", "soh jia man",
    "chee wei hong",
]
# Only these staff have KWSP/EPF; all others default to no EPF.
EPF_ROSTER = ["cheong fong cheng", "tan kui thean"]


def _norm(name: str) -> str:
    return " ".join((name or "").lower().split())


def configure_roster(db) -> None:
    """Apply the active-staff roster and KWSP eligibility."""
    from app.models import Settings
    active, epf = set(ACTIVE_ROSTER), set(EPF_ROSTER)
    n_active = n_epf = 0
    for emp in db.scalars(select(Employee)).all():
        key = _norm(emp.name)
        emp.active = key in active
        emp.inactive_reason = None if emp.active else "resigned"
        emp.epf_enabled = key in epf
        n_active += emp.active
        n_epf += emp.epf_enabled
    s = db.get(Settings, 1)
    if s:
        s.ft_default_epf = False
        s.pt_default_epf = False
    db.commit()
    print(f"Roster: {n_active} active (rest resigned), {n_epf} with KWSP/EPF.")


def seed_users(db) -> None:
    for spec in config.SEED_USERS:
        user = db.scalar(select(User).where(User.username == spec["username"]))
        if user:
            user.password_hash = hash_password(spec["password"])
            user.role = spec["role"]
            user.full_name = spec["full_name"]
        else:
            db.add(User(username=spec["username"], full_name=spec["full_name"],
                        role=spec["role"], password_hash=hash_password(spec["password"])))
    db.commit()
    print(f"Seeded {len(config.SEED_USERS)} users: "
          + ", ".join(f"{u['username']}/{u['role']}" for u in config.SEED_USERS))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reimport = "--reimport" in sys.argv
    form_path = Path(args[0]) if args else DEFAULT_FORM

    init_db()
    db = SessionLocal()
    try:
        store.get_settings(db)     # create the Settings singleton with defaults
        seed_users(db)
        count = db.scalar(select(func.count()).select_from(Employee)) or 0
        if reimport:
            db.execute(delete(Employee))
            db.commit()
            count = 0
        if count == 0:
            if not form_path.exists():
                print(f"!! Registration form not found: {form_path}")
            else:
                result = import_employees(db, str(form_path))
                print(f"Imported {result['imported']} employees "
                      f"({result['flagged']} flagged for review) from {form_path.name}")
                configure_roster(db)
        else:
            print(f"Employees already present ({count}); pass --reimport to replace.")
            configure_roster(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
