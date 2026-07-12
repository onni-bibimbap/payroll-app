"""Application configuration (environment-overridable)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("PAYROLL_DB", str(BASE_DIR / "payroll.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

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
