"""Authentication helpers: password hashing and role guards.

Uses stdlib :func:`hashlib.pbkdf2_hmac` so the app has no crypto dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the logged-in user from the session, or ``None``."""
    uid = request.session.get("user_id")
    if not uid:
        return None
    return db.get(User, uid)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required",
                            headers={"Location": "/login"})
    return user


def require_preparer(user: User = Depends(require_user)) -> User:
    if not user.can_prepare:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Preparer or admin role required for this action.")
    return user


def require_approver(user: User = Depends(require_user)) -> User:
    if not user.can_approve:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Approver or admin role required for this action.")
    return user
