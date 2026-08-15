"""HR review dashboard API — admin/approver ('hr_admin') only.

Queue, detail, flag resolution, audited edits, the Phase-2 approval routine,
rejection, resignation workflow, and the compliance board.
"""

from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import storage
from .database import get_db
from .models import Employee, User
from .security import require_user

router = APIRouter(prefix="/api/hr", tags=["hr"])

EDITABLE = ("name", "email", "phone", "nric", "identity_type", "position",
            "residential_address", "nationality", "outlet", "bank_name",
            "bank_account", "employment_type")


def require_hr(user: User = Depends(require_user)) -> User:
    if user.role not in ("admin", "approver"):
        raise HTTPException(403, "HR admin role required.")
    return user


def _audit(db: Session, actor: str, action: str, entity: str, entity_id,
           fields: list[str] | None = None) -> None:
    db.execute(text("""
        insert into audit_log (actor, action, entity, entity_id, changed_fields)
        values (:a, :ac, :e, :id, :f)
    """), {"a": actor, "ac": action, "e": entity, "id": str(entity_id), "f": fields})


def _emp(db: Session, emp_id: int) -> Employee:
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


def _mask(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return value
    return "•" * max(len(value) - keep, 0) + value[-keep:]


@router.get("/queue")
def queue(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select e.id, e.emp_code, e.name, e.status::text, e.position, e.identity_type::text,
               e.created_at::date::text,
               count(f.id) filter (where f.status='open') as open_flags,
               count(f.id) filter (where f.status='open' and f.severity='blocker') as blockers
        from employees e
        left join hr_review_flags f on f.employee_id = e.id
        where e.status in ('applicant','pending_review')
        group by e.id order by blockers desc, e.created_at
    """)).mappings().all()
    return {"queue": [dict(r) for r in rows]}


@router.get("/employees/{emp_id}")
def detail(emp_id: int, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    emp = _emp(db, emp_id)
    flags = db.execute(text("""
        select id, flag_type, severity, details, status::text, raised_by,
               created_at::text, resolved_by, resolved_at::text
        from hr_review_flags where employee_id = :e order by status, severity desc, id
    """), {"e": emp_id}).mappings().all()
    docs = db.execute(text("""
        select id, doc_type::text, storage_path, source_url, expiry_date::text, verified
        from employee_documents where employee_id = :e order by doc_type
    """), {"e": emp_id}).mappings().all()
    banks = db.execute(text("""
        select id, bank_name, account_no, account_holder_name, verified
        from bank_accounts where employee_id = :e order by id desc
    """), {"e": emp_id}).mappings().all()
    contacts = db.execute(text("""
        select name, phone, relationship from emergency_contacts where employee_id = :e
    """), {"e": emp_id}).mappings().all()
    history = db.execute(text("""
        select status::text, effective_date::text, reason, changed_by, created_at::text
        from employee_status_history where employee_id = :e order by id
    """), {"e": emp_id}).mappings().all()
    subs = db.execute(text("""
        select reference_no, source, payload, created_at::text
        from application_submissions where employee_id = :e order by id
    """), {"e": emp_id}).mappings().all()

    return {
        "employee": {
            "id": emp.id, "emp_code": emp.emp_code, "name": emp.name,
            "email": emp.email, "phone": emp.phone, "nric": emp.nric,
            "identity_type": emp.identity_type, "status": emp.status,
            "position": emp.position, "employment_type": emp.employment_type,
            "residential_address": emp.residential_address,
            "nationality": emp.nationality, "outlet": emp.outlet,
            "dob": emp.dob.isoformat() if emp.dob else None,
            "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
            "last_working_day": emp.last_working_day.isoformat() if emp.last_working_day else None,
            "basic_salary": float(emp.basic_salary or 0),
            "hourly_rate": float(emp.hourly_rate or 0),
            "bank_name": emp.bank_name, "bank_account": emp.bank_account,
        },
        "flags": [dict(f) for f in flags],
        "documents": [{**dict(d), "signed_url": storage.signed_url(d["storage_path"])}
                      for d in docs],
        "bank_accounts": [dict(b) for b in banks],
        "emergency_contacts": [dict(c) for c in contacts],
        "status_history": [dict(h) for h in history],
        "submissions": [dict(s) for s in subs],
    }


@router.put("/employees/{emp_id}")
def edit(emp_id: int, body: dict = Body(...), user: User = Depends(require_hr),
         db: Session = Depends(get_db)):
    emp = _emp(db, emp_id)
    changed = []
    for f in EDITABLE:
        if f in body and str(getattr(emp, f) or "") != str(body[f] or ""):
            setattr(emp, f, str(body[f] or "").strip() or None)
            changed.append(f)
    for f in ("dob", "hire_date", "probation_end_date"):
        if f in body:
            setattr(emp, f, dt.date.fromisoformat(body[f]) if body[f] else None)
            changed.append(f)
    if changed:
        _audit(db, user.username, "edit", "employee", emp_id, changed)
    db.commit()
    return {"ok": True, "changed": changed}


@router.post("/flags/{flag_id}/{action}")
def flag_action(flag_id: int, action: str, user: User = Depends(require_hr),
                db: Session = Depends(get_db)):
    if action not in ("resolve", "dismiss"):
        raise HTTPException(422, "action must be resolve or dismiss")
    n = db.execute(text("""
        update hr_review_flags
        set status = :st, resolved_by = :u, resolved_at = now()
        where id = :id and status = 'open'
    """), {"st": "resolved" if action == "resolve" else "dismissed",
           "u": user.username, "id": flag_id}).rowcount
    if not n:
        raise HTTPException(404, "Flag not found or not open.")
    _audit(db, user.username, f"flag_{action}", "hr_review_flags", flag_id)
    db.commit()
    return {"ok": True}


@router.post("/bank/{bank_id}/verify")
def verify_bank(bank_id: int, user: User = Depends(require_hr),
                db: Session = Depends(get_db)):
    row = db.execute(text(
        "update bank_accounts set verified = true where id = :id returning employee_id"),
        {"id": bank_id}).first()
    if not row:
        raise HTTPException(404, "Bank account not found.")
    db.execute(text("""
        update hr_review_flags set status='resolved', resolved_by=:u, resolved_at=now()
        where employee_id=:e and status='open'
          and flag_type in ('unverified_bank_account','corrupted_bank_account')
    """), {"u": user.username, "e": row[0]})
    _audit(db, user.username, "bank_verify", "bank_accounts", bank_id)
    db.commit()
    return {"ok": True}


@router.post("/employees/{emp_id}/approve")
def approve(emp_id: int, body: dict = Body(default={}),
            user: User = Depends(require_hr), db: Session = Depends(get_db)):
    """Phase-2 activation routine — all gates enforced here, atomically."""
    emp = _emp(db, emp_id)
    if emp.status not in ("applicant", "pending_review"):
        raise HTTPException(409, f"Cannot approve an employee in status {emp.status}.")

    blockers = db.execute(text("""
        select flag_type from hr_review_flags
        where employee_id=:e and status='open' and severity='blocker'
    """), {"e": emp_id}).scalars().all()
    if blockers:
        raise HTTPException(409, "Open blocker flags: " + ", ".join(sorted(set(blockers))))

    bank_ok = db.scalar(text(
        "select count(*) from bank_accounts where employee_id=:e and verified"), {"e": emp_id})
    if not bank_ok:
        raise HTTPException(409, "A verified bank account is required for activation.")

    position = str(body.get("position") or emp.position or "").strip()
    if not position:
        raise HTTPException(409, "A position is required for activation.")
    employment_type = body.get("employment_type") or emp.employment_type
    pay_type = body.get("pay_type") or ("hourly" if employment_type == "part_time" else "monthly")
    basic = body.get("basic_salary")
    hourly = body.get("hourly_rate")
    if pay_type == "monthly" and not (basic or emp.basic_salary):
        raise HTTPException(409, "Monthly pay requires basic_salary.")
    if pay_type == "hourly" and not (hourly or emp.hourly_rate):
        raise HTTPException(409, "Hourly pay requires hourly_rate.")
    hire = dt.date.fromisoformat(body["hire_date"]) if body.get("hire_date") else dt.date.today()

    emp.position = position
    emp.employment_type = employment_type
    if basic is not None:
        emp.basic_salary = basic
    if hourly is not None:
        emp.hourly_rate = hourly
    emp.hire_date = hire

    db.execute(text("""
        insert into employee_positions (employee_id, position, employment_type, effective_from)
        values (:e, :p, :t, :d)
    """), {"e": emp_id, "p": position,
           "t": employment_type if employment_type in ("full_time", "part_time", "casual") else "full_time",
           "d": hire})
    db.execute(text("""
        insert into pay_profiles (employee_id, pay_type, basic_salary_sen, hourly_rate_sen,
                                  ot_eligible, epf_no, socso_no, income_tax_no, effective_from)
        values (:e, :pt, :b, :h, :ot, :epf, :soc, :tax, :d)
    """), {"e": emp_id, "pt": pay_type,
           "b": int(round(float(basic or emp.basic_salary or 0) * 100)) or None,
           "h": int(round(float(hourly or emp.hourly_rate or 0) * 100)) or None,
           "ot": bool(body.get("ot_eligible", float(basic or emp.basic_salary or 0) <= 4000)),
           "epf": body.get("epf_no"), "soc": body.get("socso_no"),
           "tax": body.get("income_tax_no"), "d": hire})
    db.execute(text("""
        insert into employee_status_history (employee_id, status, effective_date, reason, changed_by)
        values (:e, 'active', :d, 'HR approval', :u)
    """), {"e": emp_id, "d": hire, "u": user.username})
    _audit(db, user.username, "approve", "employee", emp_id)
    db.commit()
    return {"ok": True, "employee_no": emp.emp_code, "status": "active"}


@router.post("/employees/{emp_id}/reject")
def reject(emp_id: int, body: dict = Body(default={}),
           user: User = Depends(require_hr), db: Session = Depends(get_db)):
    emp = _emp(db, emp_id)
    if emp.status not in ("applicant", "pending_review"):
        raise HTTPException(409, "Only applicants can be rejected.")
    db.execute(text("""
        insert into employee_status_history (employee_id, status, effective_date, reason, changed_by)
        values (:e, 'rejected', current_date, :r, :u)
    """), {"e": emp_id, "r": str(body.get("reason") or "").strip() or None,
           "u": user.username})
    _audit(db, user.username, "reject", "employee", emp_id)
    db.commit()
    return {"ok": True}


@router.post("/employees/{emp_id}/resign")
def resign(emp_id: int, body: dict = Body(...),
           user: User = Depends(require_hr), db: Session = Depends(get_db)):
    emp = _emp(db, emp_id)
    if emp.status != "active":
        raise HTTPException(409, "Only active employees can resign.")
    try:
        notice = dt.date.fromisoformat(body["resignation_notice_date"])
        last = dt.date.fromisoformat(body["last_working_day"])
    except (KeyError, ValueError):
        raise HTTPException(422, "resignation_notice_date and last_working_day (ISO dates) are required.")
    emp.resignation_notice_date = notice
    emp.last_working_day = last
    db.flush()
    db.execute(text("""
        insert into employee_status_history (employee_id, status, effective_date, reason, changed_by)
        values (:e, 'resigned', :d, :r, :u)
    """), {"e": emp_id, "d": last, "r": str(body.get("reason") or "") or None,
           "u": user.username})
    _audit(db, user.username, "resign", "employee", emp_id)
    db.commit()
    return {"ok": True}


@router.post("/employees/{emp_id}/{status}")
def terminate(emp_id: int, status: str, body: dict = Body(default={}),
              user: User = Depends(require_hr), db: Session = Depends(get_db)):
    if status not in ("terminated", "absconded"):
        raise HTTPException(404, "Unknown action.")
    emp = _emp(db, emp_id)
    if emp.status != "active":
        raise HTTPException(409, "Only active employees can be terminated.")
    try:
        last = dt.date.fromisoformat(body["last_working_day"])
    except (KeyError, ValueError):
        raise HTTPException(422, "last_working_day (ISO date) is required.")
    emp.last_working_day = last
    db.flush()
    db.execute(text("""
        insert into employee_status_history (employee_id, status, effective_date, reason, changed_by)
        values (:e, :st, :d, :r, :u)
    """), {"e": emp_id, "st": status, "d": last,
           "r": str(body.get("reason") or "") or None, "u": user.username})
    _audit(db, user.username, status, "employee", emp_id)
    db.commit()
    return {"ok": True}


GOOGLE_SHEET_ID = __import__("os").environ.get(
    "GOOGLE_SHEET_ID", "1uQxJ4Pa6YIc6bIz01WB5bBUU78V6nvtSIIU5Jv5oE_A")


@router.post("/sync-google-sheet")
def sync_google_sheet(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    """Pull the live Google Form responses sheet and import any new rows as
    pending_review applicants. Idempotent (keyed GF-<row>); employees HR has
    already approved/rejected are never modified."""
    import io as _io
    import sys as _sys
    from pathlib import Path as _Path

    import httpx
    import openpyxl

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"
    try:
        r = httpx.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "Could not download the Google Sheet — check link sharing is on.")

    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    from import_legacy_form import import_worksheet

    wb = openpyxl.load_workbook(_io.BytesIO(r.content), data_only=True)
    ws = wb[wb.sheetnames[0]]
    report = import_worksheet(db, ws)
    _audit(db, user.username, "sync_google_sheet", "employees", "batch")
    db.commit()
    return {
        "rows": report["rows"], "created": report["created"],
        "updated": report["matched"], "settled_untouched": report["skipped_settled"],
        "flags": report["flags"], "blockers": len(report["urgent"]),
    }


@router.get("/compliance")
def compliance(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    db.execute(text("select raise_expiry_flags()"))
    db.commit()
    expiries = db.execute(text("""
        select e.emp_code, e.name, d.doc_type::text, d.expiry_date::text
        from employee_documents d join employees e on e.id = d.employee_id
        where e.status = 'active' and d.expiry_date is not null
          and d.expiry_date < current_date + interval '60 days'
        order by d.expiry_date
    """)).mappings().all()
    blocked = db.execute(text("select * from payroll_blocked_view order by employee_no")).mappings().all()
    return {"expiries": [dict(r) for r in expiries],
            "blocked": [dict(r) for r in blocked]}
