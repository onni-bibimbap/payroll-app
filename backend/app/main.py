"""FastAPI JSON API backend for the Onni Payroll SPA.

Exports: app (FastAPI instance).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import time
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from sqlalchemy import func, inspect as sa_inspect, select, text as sql_text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import payroll, pdf, store
from .hr import router as hr_router
from .payroll_export import router as export_router
from .registration import router as registration_router
from .config import COMPANY_NAME, DATABASE_URL, SECRET_KEY, APP_ENV, VERSION

DATABASE_URL_IS_SQLITE = DATABASE_URL.startswith("sqlite")
from .database import SessionLocal, get_db, init_db
from .models import AuditLog, Employee, Payslip, PayrollRun, User
from .payroll import FLAG_FIELDS, NUMBER_FIELDS, TEXT_FIELDS, PayrollError
from .security import (current_user, hash_password, require_admin,
                       require_approver, require_preparer, require_user,
                       verify_password)
from .serializers import (SETTINGS_FIELDS, employee_dict, run_dict,
                          settings_dict, slip_dict, totals_dict, user_dict)

logger = logging.getLogger(__name__)

#: Company timezone (PROJECT_PROFILE §8) — all lifecycle stamps are aware.
KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def now_kl() -> dt.datetime:
    """Current timezone-aware time in Asia/Kuala_Lumpur (DL-15)."""
    return dt.datetime.now(KL_TZ)


# --- Startup / shutdown (lifespan) (QT-13) ---
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for FastAPI 0.93+."""
    # Startup
    init_db()
    with SessionLocal() as db:
        store.get_settings(db)

    from . import storage
    try:
        storage.ensure_bucket()
    except Exception as e:
        logger.warning("Failed to configure Supabase bucket: %s", e)

    if not DATABASE_URL_IS_SQLITE:
        with SessionLocal() as db:
            try:
                db.execute(sql_text("select raise_expiry_flags()"))
                db.commit()
            except Exception as e:
                logger.warning(
                    "raise_expiry_flags() unavailable (migrations not applied): %s", e
                )

    yield
    # Shutdown (nothing to do currently)


app = FastAPI(
    title=f"{COMPANY_NAME} Payroll API",
    lifespan=lifespan
)

# SEC-07: Harden session middleware based on deployment environment.
# In production: https_only=True, same_site="strict".
# In development: https_only=False for local http, same_site="lax".
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=60 * 60 * 12,
    https_only=(APP_ENV == "production"),
    same_site="strict" if APP_ENV == "production" else "lax",
)

app.include_router(registration_router)
app.include_router(hr_router)
app.include_router(export_router)


# --- Rate limiting (SEC-03, SEC-13) ---
# Simple in-memory sliding window rate limiter: (key, ts) -> count
_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_LOGIN_RATE_LIMIT = 5    # attempts per window per user+IP


def _rate_limit_check(bucket_key: str, limit: int = _LOGIN_RATE_LIMIT) -> bool:
    """Check and update rate limit for a bucket_key; return True if allowed."""
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW
    bucket = _rate_limit_buckets[bucket_key]

    # Remove expired entries
    bucket[:] = [ts for ts in bucket if ts > cutoff]

    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def _err(status: int, message: str) -> HTTPException:
    return HTTPException(status, message)


# --- audit trail (SEC-06 / DL-04) -------------------------------------------
_AUDIT_TABLE_CACHE: dict[str, bool] = {}


def _audit(db: Session, actor: str, action: str, entity: str, entity_id,
           fields: list[str] | None = None) -> None:
    """Append an audit_log row — field NAMES only, never values (§7).

    No-op (with a warning) on databases without the audit_log table, so the
    SQLite dev fallback keeps working; on any schema built by init_db or the
    Supabase migrations the table exists and every row is recorded.
    """
    key = str(db.get_bind().url)
    if key not in _AUDIT_TABLE_CACHE:
        _AUDIT_TABLE_CACHE[key] = sa_inspect(db.get_bind()).has_table("audit_log")
    if not _AUDIT_TABLE_CACHE[key]:
        logger.warning("audit_log table missing — %s %s/%s not recorded",
                       action, entity, entity_id)
        return
    db.add(AuditLog(actor=actor, action=action, entity=entity,
                    entity_id=str(entity_id), changed_fields=fields))


# --- request bodies (STAT-13 / QT-07) ---------------------------------------
# Money fields reject garbage with 422 (no silent 0-coercion) and forbid
# negatives; the UI's habit of posting "" / "1,200" strings is preserved.
def _clean_amount(v: object) -> object:
    """Normalize a posted amount: strip commas/spaces, '' and None → None."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if v == "":
            return None
    try:
        return Decimal(str(v))
    except InvalidOperation as exc:
        raise ValueError(f"not a valid amount: {v!r}") from exc


def _clean_amount_zero(v: object) -> object:
    """Like :func:`_clean_amount` but an empty value means zero."""
    cleaned = _clean_amount(v)
    return Decimal("0") if cleaned is None else cleaned


#: Non-negative amount; empty input clears the field to 0 (UI cell semantics).
MoneyZ = Annotated[Decimal, BeforeValidator(_clean_amount_zero),
                   Field(ge=0, le=Decimal("9999999.99"))]
#: Non-negative amount or None; empty input means "unset" (e.g. pcb_override).
MoneyOpt = Annotated[Decimal | None, BeforeValidator(_clean_amount),
                     Field(ge=0, le=Decimal("9999999.99"))]


def _clean_date(v: object) -> object:
    if isinstance(v, str) and not v.strip():
        return None
    return v


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    username: str
    password: str


class EmployeeSaveBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int | None = None
    emp_code: str = ""
    name: str = ""
    employment_type: str = "full_time"
    basic_salary: MoneyZ = Decimal("0")
    hourly_rate: MoneyZ = Decimal("0")
    ot_rate: MoneyZ = Decimal("0")
    bank_name: str | None = None
    bank_account: str | None = None
    email: str | None = None
    phone: str | None = None
    nric: str | None = None
    position: str | None = None
    dob: Annotated[dt.date | None, BeforeValidator(_clean_date)] = None
    allowance_eligible: bool = False
    is_foreign: bool = False
    active: bool = False
    is_confirmed: bool = False
    epf_enabled: bool = False
    socso_enabled: bool = False
    lindung_optin: bool = False
    pcb_enabled: bool = True
    clear_review: bool = False


class RunCreateBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    work_days: int = Field(default=26, ge=1, le=31)


class AddSlipBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    employee_id: int


class SlipEdit(BaseModel):
    """One payslip's posted edits; absent fields are left untouched."""

    model_config = ConfigDict(extra="ignore")
    id: int
    basic: MoneyZ | None = None
    rate: MoneyZ | None = None
    units: MoneyZ | None = None
    allowance: MoneyZ | None = None
    deduction: MoneyZ | None = None
    ot_hours: MoneyZ | None = None
    ot_rate: MoneyZ | None = None
    pcb_override: MoneyOpt = None
    deduction_reason: str | None = None
    notes: str | None = None
    count_by_day: bool | None = None
    over_60: bool | None = None
    foreign: bool | None = None


class RunSaveBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slips: list[SlipEdit] = Field(default_factory=list)
    remarks: str | None = None


class RejectBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note: str | None = None


class SettingsBody(BaseModel):
    """Admin settings save; every field optional, validated when present."""

    model_config = ConfigDict(extra="ignore")
    company_name: str | None = None
    default_work_days: int | None = Field(default=None, ge=1, le=31)
    default_ot_rate: MoneyOpt = None
    epf_emp_rate: MoneyOpt = Field(default=None, le=1)
    epf_er_rate_low: MoneyOpt = Field(default=None, le=1)
    epf_er_rate_high: MoneyOpt = Field(default=None, le=1)
    epf_er_threshold: MoneyOpt = None
    socso_eis_ceiling: MoneyOpt = None
    socso_c1_emp: MoneyOpt = Field(default=None, le=1)
    socso_c1_er: MoneyOpt = Field(default=None, le=1)
    socso_c2_er: MoneyOpt = Field(default=None, le=1)
    eis_rate: MoneyOpt = Field(default=None, le=1)
    personal_relief: MoneyOpt = None
    epf_relief_cap: MoneyOpt = None
    tax_rebate: MoneyOpt = None
    rebate_ceiling: MoneyOpt = None
    default_include_allowance: bool | None = None
    default_include_ot: bool | None = None
    ft_default_epf: bool | None = None
    ft_default_socso: bool | None = None
    pt_default_epf: bool | None = None
    pt_default_socso: bool | None = None
    lindung_24jam_rate: MoneyOpt = None


# --- health (QT-14) ---
@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Health check returning status, version, and timestamp.

    Includes a DB connectivity check (SELECT 1) to ensure the backend
    can reach its data store. Returns 503 if the database is unavailable.
    """
    try:
        db.execute(sql_text("SELECT 1"))
    except Exception as e:
        logger.warning("Health check: DB unavailable: %s", e)
        raise _err(503, "Database unavailable")

    return {
        "status": "ok",
        "version": VERSION,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


# --- auth ----
class ChangePasswordBody(BaseModel):
    """Request body for POST /api/auth/change-password."""

    model_config = ConfigDict(extra="ignore")
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10)


@app.post("/api/auth/login")
def login(request: Request, body: LoginBody, db: Session = Depends(get_db)) -> dict:
    """Authenticate a user and create a session.

    Returns a user dict and company info on success (200).
    Rate-limited to 5 attempts per 60 seconds per (username, client IP).
    """
    username = body.username.strip()
    password = body.password

    # SEC-03: Per-username+IP rate limiting with constant-time delay on failure.
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = f"login:{username}:{client_ip}"

    if not _rate_limit_check(bucket_key):
        logger.warning("Login rate limit exceeded: %s (IP %s)", username, client_ip)
        raise _err(429, "Too many login attempts. Try again in 60 seconds.")

    # Constant-time password verification (timing-attack resistant).
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        logger.info("Failed login attempt: %s (IP %s)", username, client_ip)
        raise _err(401, "Invalid username or password.")

    # SEC-07: Rotate session on login (clear old, set new).
    request.session.clear()
    request.session["user_id"] = user.id

    logger.info("Successful login: %s (IP %s)", username, client_ip)
    return {"user": user_dict(user), "company": store.company()}


@app.post("/api/auth/change-password")
def change_password(request: Request, body: ChangePasswordBody,
                    user: User = Depends(require_user),
                    db: Session = Depends(get_db)) -> dict:
    """Change the logged-in user's password.

    Requires the old password for verification. New password must be
    at least 10 characters. Audit-logged. Session is NOT rotated.
    """
    if not verify_password(body.old_password, user.password_hash):
        logger.warning("Password change failed (wrong old password): %s", user.username)
        raise _err(401, "Old password is incorrect.")

    if body.new_password == body.old_password:
        raise _err(422, "New password must be different from the old one.")

    user.password_hash = hash_password(body.new_password)
    _audit(db, user.username, "change_password", "user", user.id)
    db.commit()

    logger.info("Password changed: %s", user.username)
    return {"ok": True}


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
def employee_save(body: EmployeeSaveBody, user: User = Depends(require_preparer),
                  db: Session = Depends(get_db)):
    emp_code = body.emp_code.strip()
    name = body.name.strip()
    if not emp_code or not name:
        raise _err(422, "Employee code and name are required.")
    emp = db.get(Employee, body.id) if body.id else None
    existing = db.scalar(select(Employee).where(Employee.emp_code == emp_code))
    if existing and (not emp or existing.id != emp.id):
        raise _err(409, f"Employee code {emp_code} already exists.")
    created = emp is None
    if not emp:
        emp = Employee(emp_code=emp_code)
        db.add(emp)
    tracked = ("emp_code", "name", "employment_type", "basic_salary",
               "hourly_rate", "ot_rate", "bank_name", "bank_account", "email",
               "phone", "nric", "position", "dob", "allowance_eligible",
               "is_foreign", "active", "is_confirmed", "epf_enabled",
               "socso_enabled", "lindung_optin", "pcb_enabled")
    before = {f: getattr(emp, f, None) for f in tracked}
    emp.emp_code = emp_code
    emp.name = name
    emp.employment_type = body.employment_type
    emp.basic_salary = body.basic_salary
    emp.hourly_rate = body.hourly_rate
    emp.ot_rate = body.ot_rate
    for f in ("bank_name", "bank_account", "email", "phone", "nric", "position"):
        setattr(emp, f, str(getattr(body, f) or "").strip() or None)
    emp.dob = body.dob
    for f in ("allowance_eligible", "is_foreign", "active", "is_confirmed",
              "epf_enabled", "socso_enabled", "lindung_optin"):
        setattr(emp, f, bool(getattr(body, f)))
    # PCB defaults to on (checkbox default-checked semantics).
    emp.pcb_enabled = body.pcb_enabled
    # EPF/SOCSO/EIS are only ever possible for confirmed (passed-probation)
    # permanent staff; within that, either can still be unchecked (exemption).
    if not emp.is_confirmed:
        emp.epf_enabled = False
        emp.socso_enabled = False
    if body.clear_review:
        emp.needs_review = False
    changed = [f for f in tracked if getattr(emp, f, None) != before[f]]
    db.flush()                                  # assign id for new employees
    _audit(db, user.username, "employee_create" if created else "employee_save",
           "employee", emp.id, changed or None)
    db.commit()
    return employee_dict(emp)


@app.post("/api/employees/{emp_id}/toggle")
def employee_toggle(emp_id: int, user: User = Depends(require_preparer),
                    db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise _err(404, "Employee not found")
    emp.active = not emp.active
    _audit(db, user.username, "employee_toggle", "employee", emp_id, ["active"])
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
def run_create(body: RunCreateBody, user: User = Depends(require_preparer),
               db: Session = Depends(get_db)):
    exists = db.scalar(select(PayrollRun).where(
        PayrollRun.year == body.year, PayrollRun.month == body.month))
    if exists:
        raise HTTPException(409, detail={
            "message": f"A payroll run for {exists.period_label} already exists.",
            "run_id": exists.id})
    run = payroll.generate_run(db, body.year, body.month, body.work_days)
    run.prepared_by = user.username
    _audit(db, user.username, "run_create", "payroll_run",
           f"{run.id}:{run.year}-{run.month:02d}")
    db.commit()
    return run_dict(run, user)


def _run_detail(db: Session, run: PayrollRun, user: User) -> dict:
    slips = sorted(run.payslips, key=lambda s: s.emp_code)
    # "Blocked from payroll" (STAT-07/DL-01): employees in this period who
    # are excluded — open blocker flags, unverified bank, or lifecycle state.
    available: list[Employee] = []
    blocked: list[dict] = []
    if run.is_editable:
        eligible, blocked = payroll.payroll_candidates(db, run)
        have = {s.employee_id for s in run.payslips}
        available = sorted((e for e, _bank in eligible if e.id not in have),
                           key=lambda e: e.name)
    return {
        "run": run_dict(run, user),
        "slips": [slip_dict(s) for s in slips],
        "totals": totals_dict(payroll.run_totals(run)),
        "available": [employee_dict(e) for e in available],
        "blocked": blocked,
    }


@app.get("/api/runs/{run_id}")
def run_get(run_id: int, user: User = Depends(require_user),
            db: Session = Depends(get_db)):
    return _run_detail(db, _get_run(db, run_id), user)


@app.post("/api/runs/{run_id}/slips")
def run_add_slip(run_id: int, body: AddSlipBody,
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "This run is locked.")
    try:
        added = payroll.add_employee(db, run, body.employee_id,
                                     store.rate_config(db), store.get_settings(db))
    except PayrollError as exc:
        raise _err(409, str(exc)) from exc
    if not added:
        raise _err(409, "Employee is already on this run.")
    _audit(db, user.username, "slip_add", "payroll_run",
           f"{run.id}:{body.employee_id}")
    db.commit()
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
        _audit(db, user.username, "slip_remove", "payslip", slip_id)
        db.commit()
    return _run_detail(db, run, user)


@app.put("/api/runs/{run_id}")
def run_save(run_id: int, body: RunSaveBody,
             user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run.editable_by(user):
        raise _err(409, "You cannot edit this run in its current state.")
    cfg = store.rate_config(db)
    settings = store.get_settings(db)
    lindung_rate = settings.lindung_24jam_rate or Decimal("0")
    slips_in = {s.id: s for s in body.slips}
    for slip in run.payslips:
        data = slips_in.get(slip.id)
        if not data:
            continue
        posted = data.model_fields_set
        editable = NUMBER_FIELDS + TEXT_FIELDS + ["pcb_override"] + FLAG_FIELDS
        before = {f: getattr(slip, f) for f in editable}
        for field in NUMBER_FIELDS:
            if field in posted:
                setattr(slip, field, getattr(data, field) or Decimal("0"))
        for field in TEXT_FIELDS:
            if field in posted:
                setattr(slip, field, str(getattr(data, field) or "").strip() or None)
        if "pcb_override" in posted:
            slip.pcb_override = data.pcb_override
        for flag in FLAG_FIELDS:
            if flag in posted:
                setattr(slip, flag, bool(getattr(data, flag)))
        # allowance / deduction / OT are enabled implicitly by their amounts
        slip.allowance_enabled = (slip.allowance or 0) > 0
        slip.deduction_enabled = (slip.deduction or 0) > 0
        slip.ot_enabled = (slip.ot_hours or 0) > 0
        # EPF/SOCSO/EIS: only possible for confirmed (passed-probation) staff,
        # and only editable per-employee (not per payslip). The statutory-base
        # composition (allowance/OT opt-in) follows the admin settings
        # (STAT-12/QT-05).
        emp = db.get(Employee, slip.employee_id)
        slip.epf_enabled = bool(emp and emp.is_confirmed and emp.epf_enabled)
        slip.socso_enabled = bool(emp and emp.is_confirmed and emp.socso_enabled)
        slip.pcb_enabled = bool(emp is None or emp.pcb_enabled)
        slip.lindung_optin = bool(emp and emp.lindung_optin)
        slip.include_allowance = bool(settings.default_include_allowance)
        slip.include_ot = bool(settings.default_include_ot)
        # "create instantly": if the employee had no basic on record, store it
        if emp and not slip.hourly and slip.basic and slip.basic > 0 and not (emp.basic_salary or 0):
            emp.basic_salary = slip.basic
        payroll.recompute(slip, cfg, lindung_rate)
        changed = [f for f in editable if getattr(slip, f) != before[f]]
        if changed:                             # field names only, no values
            _audit(db, user.username, "slip_edit", "payslip", slip.id, changed)
    if "remarks" in body.model_fields_set:
        run.remarks = str(body.remarks or "").strip() or None
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
    if added:
        _audit(db, user.username, "run_sync", "payroll_run",
               f"{run.id}:+{added}")
        db.commit()
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
    run.submitted_at = now_kl()
    _audit(db, user.username, "run_submit", "payroll_run",
           f"{run.id}:{run.year}-{run.month:02d}")
    db.commit()
    return _run_detail(db, run, user)


@app.post("/api/runs/{run_id}/approve")
def run_approve(run_id: int, user: User = Depends(require_approver),
                db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        raise _err(409, "Only a pending run can be approved.")
    # Four-eyes rule (SEC-06): nobody — admins included — approves a run
    # they prepared themselves.
    if run.prepared_by and run.prepared_by == user.username:
        raise _err(409, "You prepared this run — a different approver must "
                        "review and approve it.")
    run.status = "approved"
    run.approved_by = user.username
    run.approved_at = now_kl()
    _audit(db, user.username, "run_approve", "payroll_run",
           f"{run.id}:{run.year}-{run.month:02d}")
    db.commit()
    return _run_detail(db, run, user)


@app.post("/api/runs/{run_id}/reject")
def run_reject(run_id: int, body: RejectBody | None = None,
               user: User = Depends(require_approver), db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "pending":
        raise _err(409, "Only a pending run can be rejected.")
    run.status = "rejected"
    run.note = str((body.note if body else None) or "").strip() or None
    _audit(db, user.username, "run_reject", "payroll_run",
           f"{run.id}:{run.year}-{run.month:02d}")
    db.commit()
    return _run_detail(db, run, user)


@app.delete("/api/runs/{run_id}")
def run_delete(run_id: int, user: User = Depends(require_preparer),
               db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    # Only unsubmitted work may be discarded (SEC-06): a pending run must be
    # rejected back to the preparer first, an approved run is immutable.
    if run.status not in ("draft", "rejected"):
        raise _err(409, "Only a draft or rejected run can be deleted — "
                        "a pending run must be rejected first.")
    _audit(db, user.username, "run_delete", "payroll_run",
           f"{run.id}:{run.year}-{run.month:02d}",
           [f"slips:{len(run.payslips)}"])
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
def settings_save(body: SettingsBody, user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    s = store.get_settings(db)
    changed: list[str] = []
    for field, kind in SETTING_KINDS.items():
        if field not in body.model_fields_set:
            continue
        val = getattr(body, field)
        if kind == "bool":
            val = bool(val)
        elif kind == "str":
            val = str(val or "").strip() or "Onni"
        elif kind == "int":
            val = int(val) if val is not None else 26
        else:                                     # money & pct (already fraction)
            val = val if val is not None else Decimal("0")
        if getattr(s, field) != val:
            changed.append(field)
        setattr(s, field, val)
    if changed:                                   # field names only, no values
        _audit(db, user.username, "settings_save", "settings", 1, changed)
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
