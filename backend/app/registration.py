"""Public registration endpoint — replaces the Google Form.

Anonymous, insert-only: creates an application_submissions row (verbatim
payload), an employees row in ``pending_review`` (via ``applicant``), the
satellite rows, and the same auto-flags the legacy import raises. Documents
upload into a quarantined ``applicants/<ref>/`` path of the private bucket.

PDPA: identity numbers, bank accounts and phones are TEXT end-to-end and are
never echoed back or logged; errors reference field names only.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import storage
from .database import get_db
from .models import Employee

router = APIRouter(prefix="/api/register", tags=["registration"])

BANKS = ["Maybank", "CIMB", "Public Bank", "RHB", "Hong Leong", "AmBank",
         "Bank Islam", "Bank Muamalat", "Alliance", "BSN", "GXBank",
         "Bank of China", "Merchantrade", "Touch 'n Go", "Other"]

DOC_TYPES = {"nric_front", "nric_back", "passport", "work_permit",
             "food_handler_cert", "typhoid_proof", "education_transcript",
             "profile_photo"}

MAX_UPLOAD = 10 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def _clean(v, limit=500) -> str:
    return str(v or "").strip()[:limit]


def _valid_nric(digits: str) -> bool:
    if not re.fullmatch(r"\d{12}", digits):
        return False
    yy, mm, dd = int(digits[:2]), int(digits[2:4]), int(digits[4:6])
    try:
        dt.date(2000 + yy if yy < 30 else 1900 + yy, mm, dd)
        return True
    except ValueError:
        return False


@router.get("/meta")
def meta():
    """Static form metadata (banks, doc types) for the PWA."""
    return {"banks": BANKS, "doc_types": sorted(DOC_TYPES)}


@router.post("")
def submit(body: dict = Body(...), db: Session = Depends(get_db)):
    name = _clean(body.get("full_name"), 128)
    email = _clean(body.get("email"), 128).lower() or None
    phone = re.sub(r"[^\d+]", "", _clean(body.get("phone"), 32))
    identity_type = _clean(body.get("identity_type"), 16) or "nric"
    identity_no = re.sub(r"[\s-]", "", _clean(body.get("identity_no"), 32))

    if not name:
        raise HTTPException(422, "Name is required.")
    if identity_type not in ("nric", "passport", "unhcr", "other"):
        raise HTTPException(422, "Invalid identity type.")
    if identity_type == "nric" and not _valid_nric(identity_no):
        raise HTTPException(422, "NRIC must be 12 digits with a valid date prefix.")
    if phone and not re.fullmatch(r"\+?\d{9,13}", phone):
        raise HTTPException(422, "Phone number looks invalid.")
    if phone and not phone.startswith("+"):
        phone = "+60" + phone.lstrip("0")

    bank_name = _clean(body.get("bank_name"), 64)
    account_no = re.sub(r"\s", "", _clean(body.get("account_no"), 34))
    if account_no and not re.fullmatch(r"\d{6,20}", account_no):
        raise HTTPException(422, "Bank account must be 6–20 digits.")

    dob = None
    if body.get("date_of_birth"):
        try:
            dob = dt.date.fromisoformat(str(body["date_of_birth"]))
        except ValueError:
            raise HTTPException(422, "Invalid date of birth.")

    ref = "PWA-" + dt.date.today().strftime("%y%m") + "-" + secrets.token_hex(3).upper()

    flags: list[tuple[str, str, str]] = []
    if identity_type in ("passport", "unhcr", "other"):
        flags.append(("work_authorization_review", "blocker",
                      "non-NRIC identity — verify work authorization before activation"))
    if dob:
        age = (dt.date.today() - dob).days / 365.25
        if age < 15 or age > 70:
            flags.append(("suspicious_dob", "warning", f"implausible age {age:.0f}"))
    if account_no:
        flags.append(("unverified_bank_account", "blocker",
                      "self-submitted bank account — HR must verify before payroll"))

    # duplicate detection against existing records
    dup = db.execute(text("""
        select id from employees
        where (nric = :idno and :idno <> '') or (lower(email) = :em and :em <> '')
           or (phone = :ph and :ph <> '') limit 1
    """), {"idno": identity_no, "em": email or "", "ph": phone or ""}).first()
    if dup:
        flags.append(("duplicate_suspect", "blocker",
                      f"matches existing employee id {dup[0]}"))

    code = db.scalar(text(
        "select 'ONNI' || lpad((coalesce(max(substring(emp_code from '\\d+')::int),0)+1)::text, 4, '0') from employees"))
    emp = Employee(
        emp_code=code, name=name, email=email, phone=phone or None,
        nric=identity_no or None, identity_type=identity_type,
        residential_address=_clean(body.get("residential_address"), 500) or None,
        nationality="MY" if identity_type == "nric" else _clean(body.get("nationality"), 8) or "non-MY",
        dob=dob, bank_name=bank_name or None, bank_account=account_no or None,
        position=_clean(body.get("position"), 64) or None,
        employment_type="part_time" if body.get("employment_type") == "part_time" else "full_time",
        is_foreign=identity_type != "nric", active=False, needs_review=True,
        epf_enabled=False, socso_enabled=False,
    )
    db.add(emp)
    db.flush()

    payload = {k: v for k, v in body.items() if isinstance(v, (str, int, float, bool, type(None)))}
    db.execute(text("""
        insert into application_submissions (source, reference_no, payload, employee_id, processed_at)
        values ('pwa', :ref, :p, :eid, now())
    """), {"ref": ref, "p": json.dumps(payload, ensure_ascii=False), "eid": emp.id})

    for status in ("applicant", "pending_review"):
        db.execute(text("""
            insert into employee_status_history (employee_id, status, effective_date, reason, changed_by)
            values (:eid, :st, current_date, 'PWA registration', 'pwa')
        """), {"eid": emp.id, "st": status})

    if account_no:
        db.execute(text("""
            insert into bank_accounts (employee_id, bank_name, account_no, account_holder_name, verified)
            values (:eid, :b, :a, :n, false)
        """), {"eid": emp.id, "b": bank_name or "Other", "a": account_no, "n": name})

    ec_name = _clean(body.get("emergency_contact_name"), 128)
    ec_phone = _clean(body.get("emergency_contact_phone"), 32)
    if ec_name or ec_phone:
        db.execute(text("""
            insert into emergency_contacts (employee_id, name, phone, relationship)
            values (:eid, :n, :p, :r)
        """), {"eid": emp.id, "n": ec_name or "(unknown)", "p": ec_phone,
               "r": _clean(body.get("emergency_contact_relationship"), 64) or None})

    for ftype, sev, note in flags:
        db.execute(text("""
            insert into hr_review_flags (employee_id, flag_type, severity, details, raised_by)
            values (:eid, :t, :s, :d, 'system')
        """), {"eid": emp.id, "t": ftype, "s": sev,
               "d": json.dumps({"note": note, "ref": ref})})

    db.commit()
    return {"reference_no": ref, "submission_ok": True}


@router.post("/{ref}/documents/{doc_type}")
async def upload_document(ref: str, doc_type: str, file: UploadFile,
                          expiry_date: str | None = None,
                          db: Session = Depends(get_db)):
    if doc_type not in DOC_TYPES:
        raise HTTPException(422, "Unknown document type.")
    sub = db.execute(text(
        "select employee_id from application_submissions where reference_no = :r"),
        {"r": ref}).first()
    if not sub or sub[0] is None:
        raise HTTPException(404, "Unknown reference number.")
    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "File too large (max 10 MB).")
    if (file.content_type or "") not in ALLOWED_MIME:
        raise HTTPException(422, "Only JPEG/PNG/WebP images or PDF are accepted.")

    expiry = None
    if expiry_date:
        try:
            expiry = dt.date.fromisoformat(expiry_date)
        except ValueError:
            raise HTTPException(422, "Invalid expiry date.")

    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
           "application/pdf": "pdf"}[file.content_type]
    path = f"applicants/{ref}/{doc_type}.{ext}"
    stored = None
    if storage.configured():
        stored = storage.upload(path, content, file.content_type)

    db.execute(text("""
        insert into employee_documents (employee_id, doc_type, storage_path, expiry_date, verified)
        values (:eid, :t, :p, :x, false)
    """), {"eid": sub[0], "t": doc_type, "p": stored, "x": expiry})
    if not stored:
        db.execute(text("""
            insert into hr_review_flags (employee_id, flag_type, severity, details, raised_by)
            values (:eid, 'missing_document', 'warning', :d, 'system')
        """), {"eid": sub[0],
               "d": json.dumps({"note": f"{doc_type} upload received but storage not configured", "ref": ref})})
    db.commit()
    return {"ok": True, "doc_type": doc_type, "stored": bool(stored)}
