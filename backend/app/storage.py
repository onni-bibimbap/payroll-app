"""Supabase Storage helper — private 'employee-docs' bucket, signed URLs only.

Uses the service-role key from env; never expose it to the browser. If the
key is not configured, uploads are rejected with a clear error and document
rows fall back to storing nothing (source_url-only records still work).
"""

from __future__ import annotations

import os

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET = os.environ.get("SUPABASE_DOCS_BUCKET", "employee-docs")

_HEADERS = {"Authorization": f"Bearer {SERVICE_KEY}", "apikey": SERVICE_KEY}


def configured() -> bool:
    return bool(SUPABASE_URL and SERVICE_KEY)


def ensure_bucket() -> None:
    """Create the private bucket if missing (idempotent)."""
    if not configured():
        return
    r = httpx.post(f"{SUPABASE_URL}/storage/v1/bucket", headers=_HEADERS,
                   json={"id": BUCKET, "name": BUCKET, "public": False})
    if r.status_code not in (200, 201, 400, 409):   # 400/409 = already exists
        r.raise_for_status()


def upload(path: str, content: bytes, content_type: str) -> str:
    """Upload to the private bucket; returns the storage path."""
    if not configured():
        raise RuntimeError("Supabase Storage is not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY).")
    r = httpx.post(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
                   headers={**_HEADERS, "Content-Type": content_type,
                            "x-upsert": "true"},
                   content=content, timeout=60)
    r.raise_for_status()
    return path


def signed_url(path: str, expires_in: int = 600) -> str | None:
    if not (configured() and path):
        return None
    r = httpx.post(f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{path}",
                   headers=_HEADERS, json={"expiresIn": expires_in})
    if r.status_code != 200:
        return None
    return SUPABASE_URL + "/storage/v1" + r.json()["signedURL"]
