"""FastAPI JSON API backend for the Onni Payroll SPA."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import payroll, pdf, store
from .hr import router as hr_router
from .payroll_export import router as export_router
from .registration import router as registration_router
from .config import COMPANY_NAME, DATABASE_URL, SECRET_KEY

DATABASE_URL_IS_SQLITE = DATABASE_URL.startswith("sqlite")
from .database import SessionLocal, get_db, init_db
from .models import Employee, Payslip, PayrollRun, User
from .payroll import FLAG_FIELDS, NUMBER_FIELDS, TEXT_FIELDS
from .security import (current_user, require_approver, require_preparer,
                       require_user, verify_password)
from .serializers import (SETTINGS_FIELDS, employee_dict, run_dict,
                          settings_dict, slip_dict, totals_dict, user_dict)

app = FastAPI(title=f"{COMPANY_NAME} Payroll API")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 12)
app.include_router(registration_router)
app.include_router(hr_router)
app.include_router(export_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    with SessionLocal() as db:      # ensure the Settings singleton exists
        store.get_settings(db)
    # employee-master extras (no-ops when not on Postgres / not configured)
    from sqlalchemy import text as _text
    from . import storage
    try:
        storage.ensure_bucket()
    except Exception:
        pass
    if not DATABASE_URL_IS_SQLITE:
        with SessionLocal() as db:  # daily expiry flags fallback (idempotent)
            db.execute(_text("select raise_expiry_flags()"))
            db.commit()


def _dec(raw, default="0") -> Decimal:
    try:
        return Decimal(str(raw).replace(",", "").strip() or default)
    except (InvalidOperation, AttributeError):
        return Decimal(default)


def _err(status: int, message: str) -> HTTPException:
    return HTTPException(status, message)


# --- health ------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True}


# --- auth ----------------------------------------------------------------
@app.post("/api/auth/login")
def login(request: Request, body: dict = Body(...), db: Session = Depends(get_db)):
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        raise _err(401, "Invalid username or password.")
    request.session["user_id"] = user.id
    return {"user": user_dict(user), "company": store.company()}


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise _err(401, "Not signed in")
    return {"user": user_dict(user), "company": store.company()}


# --- employees -------------------------------------------------------------
@app.get("/api/employees")
def employees_list(show: str = "active", user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    q = select(Employee).order_by(Employee.emp_code)
    if show == "active":
        q = q.where(Employee.active.is_(True))
    elif show == "review":
        q = q.where(Employee.needs_review.is_(True))
    employees = db.scalars(q).all()
    counts = {
        "active": db.scalar(select(func.count()).where(Employee.active.is_(True))),
        "all": db.scalar(select(func.count()).select_from(Employee)),
        "review": db.scalar(select(func.count()).where(Employee.needs_review.is_(True))),
    }
    return {"employees": [employee_dict(e) for e in employees], "counts": counts}


@app.get("/api/employees/{emp_id}")
def employee_get(emp_id: int, user: User = Depends(require_preparer),
                 db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise _err(404, "Employee not found")
    return employee_dict(emp)


@app.post("/api/employees")
def employee_save(body: dict = Body(...), user: User = Depends(require_preparer),
                  db: Session = Depends(get_db)):
    emp_id = body.get("id")
    emp_code = str(body.get("emp_code", "")).strip()
    name = str(body.get("name", "")).strip()
    if not emp_code or not name:
        raise _err(422, "Employee code and name are required.")
    emp = db.get(Employee, int(emp_id)) if emp_id else None
    existing = db.scalar(select(Employee).where(Employee.emp_code == emp_code))
    if existing and (not emp or existing.id != emp.id):
        raise _err(409, f"Employee code {emp_code} already exists.")
    if not emp:
        emp = Employee(emp_code=emp_code)
        db.add(emp)
    emp.emp_code = emp_code
    emp.name = name
    emp.employment_type = body.get("employment_type", "full_time")
    emp.basic_salary = _dec(body.get("basic_salary", 0))
    emp.hourly_rate = _dec(body.get("hourly_rate", 0))
    emp.ot_rate = _dec(body.get("ot_rate", 0))
    for f in ("bank_name", "bank_account", "email", "phone", "nric", "position"):
        setattr(emp, f, str(body.get(f) or "").strip() or None)
    dob = str(body.get("dob") or "").strip()
    emp.dob = dt.date.fromisoformat(dob) if dob else None
    for f in ("allowance_eligible", "is_foreign", "active", "is_confirmed",
              "epf_enabled", "socso_enabled", "lindung_optin"):
        setattr(emp, f, bool(body.get(f)))
    # PCB defaults to on; "pcb_enabled" is only present in the body when the
    # employee form explicitly posts it (checkbox default-checked semantics).
    emp.pcb_enabled = bool(body.get("pcb_enabled", True))
    # EPF/SOCSO/EIS are only ever possible for confirmed (passed-probation)
    # permanent staff; within that, either can still be unchecked (exemption).
    if not emp.is_confirmed:
        emp.epf_enabled = False
        emp.socso_enabled = False
    if body.get("clear_review"):
        emp.needs_review = False
    db.commit()
    return employee_dict(emp)


@app.post("/api/employees/{emp_id}/toggle")
def employee_toggle(emp_id: int, user: User = Depends(require_preparer),
                    db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise _err(404, "Employee not found")
    emp.active = not emp.active
    db.commit()
    return employee_dict(emp)


# --- payroll runs ----------------------------------------------------------
def _get_run(db: Session, run_id: int) -> PayrollRun:
    run = db.get(PayrollRun, run_id)
    if not run:
        raise _err(404, "Payroll run not found")
    return run


@app.get("/api/runs")
def runs_list(user: User = Depends(require_user), db: Session = Depends(get_db)):
    runs = db.scalars(select(PayrollRun).order_by(
        PayrollRun.year.desc(), PayrollRun.month.desc())).all()
    today = dt.date.today()
    return {
        "runs": [{**run_dict(r, user), "totals": totals_dict(payroll.run_totals(r))}
                 for r in runs],
        "active_emps": db.scalar(select(func.count()).where(Employee.active.is_(True))),
        "this_year": today.year, "this_month": today.month,
        "default_work_days": store.get_settings(db).default_work_days,
    }


@app.post("/api/runs")
def run_create(body: dict = Body(...), user: User = Depends(require_preparer),
               db: Session = Depends(get_db)):
    year, month = int(body["year"]), int(body["month"])
    work_days = int(body.get("work_days", 26))
    exists = db.scalar(select(PayrollRun).where(
        PayrollRun.year == year, PayrollRun.month == month))
    if exists:
        raise HTTPException(409, detail={
            "message": f"A payroll run for {exists.period_label} already exists.",
            "run_id": exists.id})
    run = payroll.generate_run(db, year, month, work_days)
    run.prepared_by = user.username
    db.commit()
    return run_dict(run, user)


def _run_detail(db: Session, run: PayrollRun, user: User) -> dict:
    slips = sorted(run.payslips, key=lambda s: s.emp_code)
    available = payroll.available_employees(db, run) if run.is_editable else []
    return {
        "run": run_dict(run, user),
        "slips": [slip_dict(s) for s in slips],
        "totals": totals_dict(payroll.run_totals(run)),
        "available": [employee_dict(e) for e in available],
    }


@app.get("/api/runs/{run_id}")
def run_get(run_id: int, user: User = Depends(require_user),
            db: Session = Depends(get_db)):
    return _run_detail(db, _get_run(db, run_id), user)


@app.post("/api/runs/{run_id}/slips")
def run_add_slip(run_id: int, body: dict = Body(...),
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "This run is locked.")
    if not payroll.add_employee(db, run, int(body["employee_id"]),
                                store.rate_config(db), store.get_settings(db)):
        raise _err(409, "Employee is already on this run.")
    return _run_detail(db, run, user)


@app.delete("/api/runs/{run_id}/slips/{slip_id}")
def run_remove_slip(run_id: int, slip_id: int, user: User = Depends(require_user),
                    db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "This run is locked.")
    slip = db.get(Payslip, slip_id)
    if slip and slip.run_id == run_id:
        db.delete(slip)
        db.commit()
    return _run_detail(db, run, user)


@app.put("/api/runs/{run_id}")
def run_save(run_id: int, body: dict = Body(...),
             user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "You cannot edit this run in its current state.")
    cfg = store.rate_config(db)
    lindung_rate = store.get_settings(db).lindung_24jam_rate or Decimal("0")
    slips_in = {int(s["id"]): s for s in body.get("slips", [])}
    for slip in run.payslips:
        data = slips_in.get(slip.id)
        if not data:
            continue
        for field in NUMBER_FIELDS:
            if field in data:
                setattr(slip, field, _dec(data[field]))
        for field in TEXT_FIELDS:
            if field in data:
                setattr(slip, field, str(data[field] or "").strip() or None)
        if "pcb_override" in data:
            raw = data["pcb_override"]
            slip.pcb_override = _dec(raw) if str(raw or "").strip() != "" else None
        for flag in FLAG_FIELDS:
            if flag in data:
                setattr(slip, flag, bool(data[flag]))
        # allowance / deduction / OT are enabled implicitly by their amounts
        slip.allowance_enabled = (slip.allowance or 0) > 0
        slip.deduction_enabled = (slip.deduction or 0) > 0
        slip.ot_enabled = (slip.ot_hours or 0) > 0
        # EPF/SOCSO/EIS: only possible for confirmed (passed-probation) staff,
        # and only editable per-employee (not per payslip). Statutory base is
        # always basic + allowance; OT never counts toward it.
        emp = db.get(Employee, slip.employee_id)
        slip.epf_enabled = bool(emp and emp.is_confirmed and emp.epf_enabled)
        slip.socso_enabled = bool(emp and emp.is_confirmed and emp.socso_enabled)
        slip.pcb_enabled = bool(emp is None or emp.pcb_enabled)
        slip.lindung_optin = bool(emp and emp.lindung_optin)
        slip.include_allowance = True
        slip.include_ot = False
        # "create instantly": if the employee had no basic on record, store it
        if emp and not slip.hourly and slip.basic and slip.basic > 0 and not (emp.basic_salary or 0):
            emp.basic_salary = slip.basic
        payroll.recompute(slip, cfg, lindung_rate)
    if "remarks" in body:
        run.remarks = str(body["remarks"] or "").strip() or None
    db.commit()
    return _run_detail(db, run, user)


@app.post("/api/runs/{run_id}/sync")
def run_sync(run_id: int, user: User = Depends(require_user),
             db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "This run is locked.")
    added = payroll.sync_new_employees(db, run, store.rate_config(db),
                                       store.get_settings(db))
    return {"added": added, **_run_detail(db, run, user)}


@app.post("/api/runs/{run_id}/submit")
def run_submit(run_id: int, user: User = Depends(require_preparer),
               db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status not in ("draft", "rejected"):
        raise _err(409, "Only a draft can be sent for approval.")
    if not run.payslips:
        raise _err(409, "Add at least one employee before sending for approval.")
    run.status = "pending"
    run.prepared_by = user.username
    run.submitted_at = dt.datetime.now()
    db.commit()
    return _run_detail(db, run, user)


@app.post("/api/runs/{run_id}/approve")
def run_approve(run_id: int, user: User = Depends(require_approver),
                db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        raise _err(409, "Only a pending run can be approved.")
    run.status = "approved"
    run.approved_by = user.username
    run.approved_at = dt.datetime.now()
    db.commit()
    return _run_detail(db, run, user)


@app.post("/api/runs/{run_id}/reject")
def run_reject(run_id: int, body: dict = Body(default={}),
               user: User = Depends(require_approver), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        raise _err(409, "Only a pending run can be rejected.")
    run.status = "rejected"
    run.note = str(body.get("note") or "").strip() or None
    db.commit()
    return _run_detail(db, run, user)


@app.delete("/api/runs/{run_id}")
def run_delete(run_id: int, user: User = Depends(require_preparer),
               db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status == "approved":
        raise _err(409, "Approved runs cannot be deleted.")
    db.delete(run)
    db.commit()
    return {"ok": True}


@app.get("/api/runs/{run_id}/dashboard")
def run_dashboard(run_id: int, user: User = Depends(require_user),
                  db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    slips = sorted(run.payslips, key=lambda s: s.net_salary or 0, reverse=True)
    cfg = store.rate_config(db)
    by_bank: dict[str, Decimal] = {}
    for s in run.payslips:
        key = s.bank_name or "—"
        by_bank[key] = by_bank.get(key, Decimal("0")) + (s.net_salary or 0)
    ft = sum(1 for s in run.payslips if s.employment_type == "full_time")

    def _rows(slip):
        return [{**row, "value": float(row["value"] or 0),
                 "employer": float(row["employer"]) if row["employer"] is not None else None}
                for row in payroll.breakdown(slip, cfg)]

    return {
        "run": run_dict(run, user),
        "slips": [slip_dict(s) for s in slips],
        "totals": totals_dict(payroll.run_totals(run)),
        "by_bank": [{"bank": b, "amount": float(a)}
                    for b, a in sorted(by_bank.items(), key=lambda x: -x[1])],
        "full_time": ft, "part_time": len(run.payslips) - ft,
        "breakdowns": {s.id: _rows(s) for s in slips},
        "settings": settings_dict(store.get_settings(db)),
    }


@app.get("/api/runs/{run_id}/slips/{slip_id}")
def slip_get(run_id: int, slip_id: int, user: User = Depends(require_user),
             db: Session = Depends(get_db)):
    slip = db.get(Payslip, slip_id)
    if not slip or slip.run_id != run_id:
        raise _err(404, "Payslip not found")
    return {"slip": slip_dict(slip), "run": run_dict(slip.run, user),
            "company": store.company()}


# --- settings (admin) ------------------------------------------------------
def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise _err(403, "Administrator role required for Settings.")
    return user


# field name -> ("pct" | "money" | "int" | "bool" | "str"); pct values travel
# through the API as fractions (0.11 = 11%) — the UI converts for display.
SETTING_KINDS = {
    "company_name": "str", "default_work_days": "int", "default_ot_rate": "money",
    "epf_emp_rate": "pct", "epf_er_rate_low": "pct", "epf_er_rate_high": "pct",
    "epf_er_threshold": "money", "socso_eis_ceiling": "money",
    "socso_c1_emp": "pct", "socso_c1_er": "pct", "socso_c2_er": "pct", "eis_rate": "pct",
    "personal_relief": "money", "epf_relief_cap": "money",
    "tax_rebate": "money", "rebate_ceiling": "money",
    "default_include_allowance": "bool", "default_include_ot": "bool",
    "ft_default_epf": "bool", "ft_default_socso": "bool",
    "pt_default_epf": "bool", "pt_default_socso": "bool",
    "lindung_24jam_rate": "money",
}
assert set(SETTING_KINDS) == set(SETTINGS_FIELDS)


@app.get("/api/settings/defaults")
def settings_defaults(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """New-employee toggle defaults — readable by any signed-in user."""
    s = store.get_settings(db)
    return {"ft_default_epf": s.ft_default_epf, "ft_default_socso": s.ft_default_socso,
            "pt_default_epf": s.pt_default_epf, "pt_default_socso": s.pt_default_socso}


@app.get("/api/settings")
def settings_get(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return settings_dict(store.get_settings(db))


@app.put("/api/settings")
def settings_save(body: dict = Body(...), user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    s = store.get_settings(db)
    for field, kind in SETTING_KINDS.items():
        if field not in body:
            continue
        val = body[field]
        if kind == "bool":
            setattr(s, field, bool(val))
        elif kind == "str":
            setattr(s, field, str(val or "").strip() or "Onni")
        elif kind == "int":
            setattr(s, field, int(_dec(val, "26")))
        else:                                     # money & pct (already fraction)
            setattr(s, field, _dec(val))
    db.commit()
    store.refresh_cache(s)
    return settings_dict(s)


# --- PDFs ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/pdf")
def run_pdf(run_id: int, user: User = Depends(require_user),
            db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    data = pdf.run_summary_pdf(run, payroll.run_totals(run))
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="payroll_{run.year}_{run.month:02d}.pdf"'})


@app.get("/api/runs/{run_id}/slips/{slip_id}/pdf")
def slip_pdf(run_id: int, slip_id: int, user: User = Depends(require_user),
             db: Session = Depends(get_db)):
    slip = db.get(Payslip, slip_id)
    if not slip or slip.run_id != run_id:
        raise _err(404, "Payslip not found")
    data = pdf.payslip_pdf(slip, slip.run)
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="payslip_{slip.emp_code}_{slip.run.year}{slip.run.month:02d}.pdf"'})
