"""FastAPI application: auth, employee CRUD, payroll runs, approval, dashboard, PDF."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import payroll, pdf, store
from .config import COMPANY_NAME, SECRET_KEY
from .database import SessionLocal, get_db, init_db
from .models import Employee, Payslip, PayrollRun, Settings, User
from .payroll import FLAG_FIELDS, NUMBER_FIELDS, TEXT_FIELDS
from .security import (current_user, require_approver, require_preparer,
                       require_user, verify_password)

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title=f"{COMPANY_NAME} Payroll")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 12)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def _startup() -> None:
    init_db()
    with SessionLocal() as db:      # ensure the Settings singleton exists
        store.get_settings(db)


@app.exception_handler(401)
async def _unauthorized(request: Request, exc):
    """Send browsers to the login page instead of a raw 401 body."""
    return RedirectResponse("/login", status_code=303)


# --- template helpers ------------------------------------------------------
def _money(v) -> str:
    d = Decimal(str(v if v not in (None, "") else 0))
    return f"{d:,.2f}" if d else "-"


def _money0(v) -> str:
    d = Decimal(str(v if v not in (None, "") else 0))
    return f"{d:,.0f}" if d else "-"


templates.env.filters["money"] = _money
templates.env.filters["money0"] = _money0
templates.env.globals["company"] = COMPANY_NAME
templates.env.globals["now_year"] = dt.date.today().year


def flash(request: Request, message: str, level: str = "success") -> None:
    request.session.setdefault("_flash", []).append({"msg": message, "level": level})


def render(request: Request, name: str, user: User | None, **ctx) -> HTMLResponse:
    messages = request.session.pop("_flash", [])
    return templates.TemplateResponse(
        request, name, {"user": user, "messages": messages,
                        "company": store.company(), **ctx})


def _dec(raw, default="0") -> Decimal:
    try:
        return Decimal(str(raw).replace(",", "").strip() or default)
    except (InvalidOperation, AttributeError):
        return Decimal(default)


# --- auth ------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Session = Depends(get_db)):
    if current_user(request, db):
        return RedirectResponse("/payroll", status_code=303)
    return render(request, "login.html", None)


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username.strip()))
    if not user or not verify_password(password, user.password_hash):
        flash(request, "Invalid username or password.", "error")
        return RedirectResponse("/login", status_code=303)
    request.session["user_id"] = user.id
    flash(request, f"Welcome, {user.full_name or user.username}.")
    return RedirectResponse("/payroll", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/")
def index():
    return RedirectResponse("/payroll", status_code=303)


# --- employees -------------------------------------------------------------
@app.get("/employees", response_class=HTMLResponse)
def employees_list(request: Request, show: str = "active",
                   user: User = Depends(require_user), db: Session = Depends(get_db)):
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
    return render(request, "employees_list.html", user, employees=employees,
                  show=show, counts=counts)


@app.get("/employees/new", response_class=HTMLResponse)
def employee_new(request: Request, user: User = Depends(require_preparer),
                 db: Session = Depends(get_db)):
    return render(request, "employee_form.html", user, emp=None, s=store.get_settings(db))


@app.get("/employees/{emp_id}", response_class=HTMLResponse)
def employee_edit(emp_id: int, request: Request, user: User = Depends(require_preparer),
                  db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return render(request, "employee_form.html", user, emp=emp, s=store.get_settings(db))


@app.post("/employees")
def employee_create(request: Request, user: User = Depends(require_preparer),
                    db: Session = Depends(get_db), emp_id: str = Form(""),
                    emp_code: str = Form(...), name: str = Form(...),
                    employment_type: str = Form("full_time"),
                    basic_salary: str = Form("0"), hourly_rate: str = Form("0"),
                    ot_rate: str = Form("0"),
                    bank_name: str = Form(""), bank_account: str = Form(""),
                    email: str = Form(""), phone: str = Form(""), nric: str = Form(""),
                    dob: str = Form(""), position: str = Form(""),
                    epf_enabled: str = Form(""), socso_enabled: str = Form(""),
                    allowance_eligible: str = Form(""),
                    is_foreign: str = Form(""), active: str = Form(""),
                    clear_review: str = Form("")):
    emp = db.get(Employee, int(emp_id)) if emp_id else None
    existing = db.scalar(select(Employee).where(Employee.emp_code == emp_code.strip()))
    if existing and (not emp or existing.id != emp.id):
        flash(request, f"Employee code {emp_code} already exists.", "error")
        return RedirectResponse(request.headers.get("referer", "/employees"), 303)
    if not emp:
        emp = Employee(emp_code=emp_code.strip())
        db.add(emp)
    emp.emp_code = emp_code.strip()
    emp.name = name.strip()
    emp.employment_type = employment_type
    emp.basic_salary = _dec(basic_salary)
    emp.hourly_rate = _dec(hourly_rate)
    emp.ot_rate = _dec(ot_rate)
    emp.bank_name = bank_name.strip() or None
    emp.bank_account = bank_account.strip() or None
    emp.email = email.strip() or None
    emp.phone = phone.strip() or None
    emp.nric = nric.strip() or None
    emp.position = position.strip() or None
    emp.dob = dt.date.fromisoformat(dob) if dob else None
    emp.epf_enabled = bool(epf_enabled)
    emp.socso_enabled = bool(socso_enabled)
    emp.allowance_eligible = bool(allowance_eligible)
    emp.is_foreign = bool(is_foreign)
    emp.active = bool(active)
    if clear_review:
        emp.needs_review = False
    db.commit()
    flash(request, f"Saved {emp.name} ({emp.emp_code}).")
    return RedirectResponse("/employees", status_code=303)


@app.post("/employees/{emp_id}/toggle")
def employee_toggle(emp_id: int, request: Request,
                    user: User = Depends(require_preparer), db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if emp:
        emp.active = not emp.active
        db.commit()
        flash(request, f"{emp.name} is now {'active' if emp.active else 'inactive'}.")
    return RedirectResponse(request.headers.get("referer", "/employees"), 303)


# --- payroll runs ----------------------------------------------------------
@app.get("/payroll", response_class=HTMLResponse)
def payroll_list(request: Request, user: User = Depends(require_user),
                 db: Session = Depends(get_db)):
    runs = db.scalars(select(PayrollRun).order_by(
        PayrollRun.year.desc(), PayrollRun.month.desc())).all()
    active_emps = db.scalar(select(func.count()).where(Employee.active.is_(True)))
    today = dt.date.today()
    return render(request, "payroll_list.html", user, runs=runs,
                  totals={r.id: payroll.run_totals(r) for r in runs},
                  active_emps=active_emps, this_year=today.year, this_month=today.month,
                  default_work_days=store.get_settings(db).default_work_days)


@app.post("/payroll")
def payroll_create(request: Request, user: User = Depends(require_preparer),
                   db: Session = Depends(get_db), year: int = Form(...),
                   month: int = Form(...), work_days: int = Form(26)):
    exists = db.scalar(select(PayrollRun).where(
        PayrollRun.year == year, PayrollRun.month == month))
    if exists:
        flash(request, f"A payroll run for {exists.period_label} already exists.", "error")
        return RedirectResponse(f"/payroll/{exists.id}", status_code=303)
    run = payroll.generate_run(db, year, month, work_days)
    run.prepared_by = user.username
    db.commit()
    flash(request, f"Created {run.period_label}. Add employees by name, "
                   "or use ‘Add all active’.")
    return RedirectResponse(f"/payroll/{run.id}", status_code=303)


def _get_run(db: Session, run_id: int) -> PayrollRun:
    run = db.get(PayrollRun, run_id)
    if not run:
        raise HTTPException(404, "Payroll run not found")
    return run


@app.get("/payroll/{run_id}", response_class=HTMLResponse)
def payroll_run(run_id: int, request: Request, user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    slips = sorted(run.payslips, key=lambda s: s.emp_code)
    available = payroll.available_employees(db, run) if run.is_editable else []
    return render(request, "payroll_run.html", user, run=run, slips=slips,
                  totals=payroll.run_totals(run), available=available)


@app.post("/payroll/{run_id}/add")
def payroll_add(run_id: int, request: Request, employee_id: int = Form(...),
                user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        flash(request, "This run is locked.", "error")
    elif payroll.add_employee(db, run, employee_id, store.rate_config(db),
                              store.get_settings(db)):
        flash(request, "Employee added to the payroll.")
    else:
        flash(request, "Employee is already on this run.", "error")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/remove/{slip_id}")
def payroll_remove(run_id: int, slip_id: int, request: Request,
                   user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    slip = db.get(Payslip, slip_id)
    if not run.editable_by(user):
        flash(request, "This run is locked.", "error")
    elif slip and slip.run_id == run_id:
        db.delete(slip)
        db.commit()
        flash(request, f"Removed {slip.name} from the payroll.")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/save")
async def payroll_save(run_id: int, request: Request,
                       user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        flash(request, "You cannot edit this run in its current state.", "error")
        return RedirectResponse(f"/payroll/{run_id}", status_code=303)
    form = await request.form()
    cfg = store.rate_config(db)
    for slip in run.payslips:
        for field in NUMBER_FIELDS:
            key = f"{field}__{slip.id}"
            if key in form:
                setattr(slip, field, _dec(form[key]))
        for field in TEXT_FIELDS:
            key = f"{field}__{slip.id}"
            if key in form:
                setattr(slip, field, str(form[key]).strip() or None)
        pkey = f"pcb_override__{slip.id}"
        if pkey in form:
            raw = form[pkey]
            slip.pcb_override = _dec(raw) if str(raw).strip() != "" else None
        for flag in FLAG_FIELDS:
            setattr(slip, flag, f"{flag}__{slip.id}" in form)
        # allowance / deduction / OT are enabled implicitly by their amounts
        slip.allowance_enabled = (slip.allowance or 0) > 0
        slip.deduction_enabled = (slip.deduction or 0) > 0
        slip.ot_enabled = (slip.ot_hours or 0) > 0
        # "create instantly": if the employee had no basic on record, store it
        if not slip.hourly and slip.basic and slip.basic > 0:
            emp = db.get(Employee, slip.employee_id)
            if emp and not (emp.basic_salary or 0):
                emp.basic_salary = slip.basic
        payroll.recompute(slip, cfg)
    if "remarks" in form:
        run.remarks = str(form["remarks"]).strip() or None
    db.commit()
    flash(request, "Payroll recalculated and saved.")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/sync")
def payroll_sync(run_id: int, request: Request,
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        flash(request, "This run is locked.", "error")
    else:
        added = payroll.sync_new_employees(db, run, store.rate_config(db),
                                           store.get_settings(db))
        flash(request, f"Added {added} new employee(s)." if added
              else "No new active employees to add.")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/submit")
def payroll_submit(run_id: int, request: Request,
                   user: User = Depends(require_preparer), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status not in ("draft", "rejected"):
        flash(request, "Only a draft can be sent for approval.", "error")
    elif not run.payslips:
        flash(request, "Add at least one employee before sending for approval.", "error")
    else:
        run.status = "pending"
        run.prepared_by = user.username
        run.submitted_at = dt.datetime.now()
        db.commit()
        flash(request, f"{run.period_label} sent for approval.")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/approve")
def payroll_approve(run_id: int, request: Request,
                    user: User = Depends(require_approver), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        flash(request, "Only a pending run can be approved.", "error")
    else:
        run.status = "approved"
        run.approved_by = user.username
        run.approved_at = dt.datetime.now()
        db.commit()
        flash(request, f"{run.period_label} approved. Payslips are now final.")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/reject")
def payroll_reject(run_id: int, request: Request, note: str = Form(""),
                   user: User = Depends(require_approver), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        flash(request, "Only a pending run can be rejected.", "error")
    else:
        run.status = "rejected"
        run.note = note.strip() or None
        db.commit()
        flash(request, f"{run.period_label} returned to the preparer.", "error")
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/delete")
def payroll_delete(run_id: int, request: Request,
                   user: User = Depends(require_preparer), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status == "approved":
        flash(request, "Approved runs cannot be deleted.", "error")
        return RedirectResponse(f"/payroll/{run_id}", status_code=303)
    label = run.period_label
    db.delete(run)
    db.commit()
    flash(request, f"Deleted payroll run {label}.")
    return RedirectResponse("/payroll", status_code=303)


@app.get("/payroll/{run_id}/dashboard", response_class=HTMLResponse)
def payroll_dashboard(run_id: int, request: Request, user: User = Depends(require_user),
                      db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    slips = sorted(run.payslips, key=lambda s: s.net_salary or 0, reverse=True)
    totals = payroll.run_totals(run)
    cfg = store.rate_config(db)
    by_bank: dict[str, Decimal] = {}
    for s in run.payslips:
        by_bank[s.bank_name or "—"] = by_bank.get(s.bank_name or "—", Decimal("0")) + (s.net_salary or 0)
    ft = sum(1 for s in run.payslips if s.employment_type == "full_time")
    return render(request, "dashboard.html", user, run=run, slips=slips, totals=totals,
                  by_bank=sorted(by_bank.items(), key=lambda x: -x[1]),
                  full_time=ft, part_time=len(run.payslips) - ft,
                  breakdowns={s.id: payroll.breakdown(s, cfg) for s in slips},
                  settings=store.get_settings(db))


# --- settings (admin) ------------------------------------------------------
def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Administrator role required for Settings.")
    return user


# field name -> ("pct" | "money" | "int" | "bool" | "str")
SETTING_FIELDS = {
    "company_name": "str", "default_work_days": "int", "default_ot_rate": "money",
    "epf_emp_rate": "pct", "epf_er_rate_low": "pct", "epf_er_rate_high": "pct",
    "epf_er_threshold": "money", "socso_eis_ceiling": "money",
    "socso_c1_emp": "pct", "socso_c1_er": "pct", "socso_c2_er": "pct", "eis_rate": "pct",
    "personal_relief": "money", "epf_relief_cap": "money",
    "tax_rebate": "money", "rebate_ceiling": "money",
    "default_include_allowance": "bool", "default_include_ot": "bool",
    "ft_default_epf": "bool", "ft_default_socso": "bool",
    "pt_default_epf": "bool", "pt_default_socso": "bool",
}


@app.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request, user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    return render(request, "settings.html", user, s=store.get_settings(db),
                  fields=SETTING_FIELDS)


@app.post("/settings")
async def settings_save(request: Request, user: User = Depends(require_admin),
                        db: Session = Depends(get_db)):
    s = store.get_settings(db)
    form = await request.form()
    for field, kind in SETTING_FIELDS.items():
        if kind == "bool":
            setattr(s, field, field in form)
        elif kind == "str":
            setattr(s, field, str(form.get(field, "")).strip() or "Onni")
        elif kind == "int":
            setattr(s, field, int(_dec(form.get(field, "26"))))
        elif kind == "pct":                       # entered as %, stored as fraction
            setattr(s, field, _dec(form.get(field, "0")) / 100)
        else:                                     # money
            setattr(s, field, _dec(form.get(field, "0")))
    db.commit()
    store.refresh_cache(s)
    flash(request, "Settings saved. New rates apply to payroll recalculated from now on.")
    return RedirectResponse("/settings", status_code=303)


# --- PDF & payslip ---------------------------------------------------------
@app.get("/payroll/{run_id}/pdf")
def run_pdf(run_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    data = pdf.run_summary_pdf(run, payroll.run_totals(run))
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="payroll_{run.year}_{run.month:02d}.pdf"'})


@app.get("/payroll/{run_id}/payslip/{slip_id}", response_class=HTMLResponse)
def payslip_view(run_id: int, slip_id: int, request: Request,
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    slip = db.get(Payslip, slip_id)
    if not slip or slip.run_id != run_id:
        raise HTTPException(404, "Payslip not found")
    return render(request, "payslip.html", user, slip=slip, run=slip.run)


@app.get("/payroll/{run_id}/payslip/{slip_id}/pdf")
def payslip_pdf_view(run_id: int, slip_id: int, user: User = Depends(require_user),
                     db: Session = Depends(get_db)):
    slip = db.get(Payslip, slip_id)
    if not slip or slip.run_id != run_id:
        raise HTTPException(404, "Payslip not found")
    data = pdf.payslip_pdf(slip, slip.run)
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="payslip_{slip.emp_code}_{slip.run.year}{slip.run.month:02d}.pdf"'})
