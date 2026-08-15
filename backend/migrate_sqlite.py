"""One-shot migration: copy all data from the legacy SQLite file into the
database pointed at by DATABASE_URL (local docker Postgres or Supabase).

Usage (inside the backend container, sqlite file copied alongside):
    python migrate_sqlite.py /srv/payroll.db

REPLACES existing rows in the target: payslips, payroll_runs, employees,
users and settings are wiped first, then copied over with their original ids.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import Session

from app.database import engine as target_engine, init_db
from app.models import Employee, Payslip, PayrollRun, Settings, User

MODELS = [Settings, User, Employee, PayrollRun, Payslip]   # FK-safe insert order


def main(sqlite_path: str) -> None:
    src_engine = create_engine(f"sqlite:///{sqlite_path}")
    init_db()

    with Session(src_engine) as src, Session(target_engine) as dst:
        # wipe target in reverse-FK order
        for model in reversed(MODELS):
            dst.execute(delete(model))

        for model in MODELS:
            rows = src.scalars(select(model)).all()
            cols = [c.key for c in model.__table__.columns]
            for row in rows:
                dst.merge(model(**{c: getattr(row, c) for c in cols}))
            print(f"{model.__tablename__}: {len(rows)} rows")

        dst.commit()

        # realign Postgres identity sequences with the copied ids
        if target_engine.dialect.name == "postgresql":
            for model in MODELS:
                table = model.__tablename__
                max_id = dst.scalar(select(func.max(model.id))) or 1
                dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), :m)"
                ), {"m": max_id})
            dst.commit()
            print("Sequences realigned.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python migrate_sqlite.py path/to/payroll.db")
    main(sys.argv[1])
