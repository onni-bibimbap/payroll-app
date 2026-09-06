"""Application configuration (environment-overridable).

Module validates critical environment variables and raises RuntimeError
if the app is misconfigured for its deployment environment.
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment and deployment mode ---
APP_ENV = os.environ.get("APP_ENV", "development")
"""deployment environment: 'development' or 'production'."""

# --- Database URL (INFRA-04, INFRA-11) ---
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    # In production or explicit Postgres mode, require DATABASE_URL.
    if APP_ENV != "development":
        raise RuntimeError(
            f"DATABASE_URL is required in APP_ENV={APP_ENV}. "
            "Set DATABASE_URL env var to a PostgreSQL connection string."
        )
    # Development fallback to local SQLite.
    DATABASE_URL = f"sqlite:///{BASE_DIR / 'payroll.db'}"

if APP_ENV == "production" and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "SQLite databases are not allowed in production. "
        "Set DATABASE_URL to a PostgreSQL connection string."
    )

# --- Secret key (SEC-01) ---
SECRET_KEY = os.environ.get("PAYROLL_SECRET", "")

if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError(
            "PAYROLL_SECRET is required in production and must not be a known default. "
            "Set it to a cryptographically random string (at least 32 bytes)."
        )
    # Development: generate a random per-boot secret with a warning.
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "PAYROLL_SECRET unset in development; generated random per-boot secret. "
        "Sessions will be invalidated on restart. "
        "Set PAYROLL_SECRET in .env for persistence."
    )
else:
    # Known defaults are forbidden everywhere.
    known_bad_secrets = {
        "onni-payroll-dev-secret-change-me",
        "change-me-in-production",
    }
    if SECRET_KEY in known_bad_secrets:
        raise RuntimeError(
            f"PAYROLL_SECRET is set to a known default ({SECRET_KEY!r}). "
            "Generate a new cryptographically random secret (at least 32 bytes) "
            "and set it in the environment."
        )

COMPANY_NAME = os.environ.get("PAYROLL_COMPANY", "Onni")

# --- Seed accounts (only dev/testing) ---
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

#: Version of the API (for /api/health endpoint).
VERSION = "2.0.0"
