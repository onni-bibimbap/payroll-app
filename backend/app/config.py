"""Application configuration (environment-overridable)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Prefer an explicit DATABASE_URL (e.g. postgresql+psycopg2://...); fall back to
# a local SQLite file for development outside docker.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'payroll.db'}"
)

SECRET_KEY = os.environ.get("PAYROLL_SECRET", "onni-payroll-dev-secret-change-me")
COMPANY_NAME = os.environ.get("PAYROLL_COMPANY", "Onni")

# Seed accounts (change the passwords in production via env vars).
SEED_USERS = [
    {"username": os.environ.get("PREPARER_USER", "preparer"),
     "password": os.environ.get("PREPARER_PASS", "preparer123"),
     "full_name": "Payroll Preparer", "role": "preparer"},
    {"username": os.environ.get("APPROVER_USER", "approver"),
     "password": os.environ.get("APPROVER_PASS", "approver123"),
     "full_name": "Payroll Approver", "role": "approver"},
    {"username": os.environ.get("ADMIN_USER", "admin"),
     "password": os.environ.get("ADMIN_PASS", "admin123"),
     "full_name": "Administrator", "role": "admin"},
]
