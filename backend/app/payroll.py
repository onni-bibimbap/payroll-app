"""Payroll-run orchestration: build runs from employees and recompute payslips."""

from __future__ import annotations

import calendar
import datetime as dt
import logging
from decimal import Decimal

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import statutory
from .models import BankAccount, Employee, HrReviewFlag, Payslip, PayrollRun

logger = logging.getLogger(__name__)

# Statuses that may still draw final pay for the month containing their
# last working day (GAP-03: leavers stay payable through that month).
LEAVER_STATUSES = ("resigned", "terminated", "absconded")


class PayrollError(Exception):
    """A payroll-run integrity rule was violated (surfaced as HTTP 409)."""

# Editable input fields the preparer can change on the review screen.
NUMBER_FIELDS = ["basic", "rate", "units", "allowance", "deduction",
                 "ot_hours", "ot_rate"]
TEXT_FIELDS = ["deduction_reason", "notes"]
# In the table, allowance/deduction/OT are enabled implicitly by their amounts,
# so those three flags are derived in the save handler rather than posted.
# EPF/SOCSO/EIS eligibility is derived from Employee.is_confirmed (permanent,
# passed probation) and the statutory base (basic + allowance, never OT) is
# fixed — none of that is user-editable, so those flags aren't posted either.
# NOTE: over_60 and foreign are re-derived from the employee master row on
# every recompute (see derive_statutory_flags), so posted values are advisory
# only and a DOB/nationality correction takes effect on the next save.
FLAG_FIELDS = ["count_by_day", "over_60", "foreign"]


def month_end(year: int, month: int) -> dt.date:
    """Last calendar day of the given month."""
    return dt.date(year, month, calendar.monthrange(year, month)[1])


# --- run population: who may be paid (STAT-07 / DL-01 / GAP-03) --------------
# Mirrors payroll_master_view's predicate: lifecycle-active (or a leaver in
# their final-pay month), hired on/before period end, no open blocker flag,
# and a verified bank account. The flag/bank tables are feature-detected so
# legacy SQLite databases that predate the employee-master schema degrade to
# the old behavior instead of crashing.

_TABLE_CACHE: dict[tuple[str, str], bool] = {}


def _has_table(db: Session, name: str) -> bool:
    """Whether ``name`` exists on this session's database (cached per engine)."""
    bind = db.get_bind()
    key = (str(bind.url), name)
    if key not in _TABLE_CACHE:
        _TABLE_CACHE[key] = sa_inspect(bind).has_table(name)
        if not _TABLE_CACHE[key]:
            logger.warning("table %s missing — related payroll checks are "
                           "skipped on this database", name)
    return _TABLE_CACHE[key]


def open_blocker_map(db: Session) -> dict[int, list[str]] | None:
    """Open blocker flag types per employee id; None when the table is absent."""
    if not _has_table(db, HrReviewFlag.__tablename__):
        return None
    out: dict[int, list[str]] = {}
    rows = db.scalars(select(HrReviewFlag).where(
        HrReviewFlag.status == "open", HrReviewFlag.severity == "blocker"))
    for flag in rows:
        out.setdefault(flag.employee_id, []).append(flag.flag_type)
    return out


def verified_bank_map(db: Session) -> dict[int, BankAccount] | None:
    """Latest verified bank account per employee id; None when table absent."""
    if not _has_table(db, BankAccount.__tablename__):
        return None
    out: dict[int, BankAccount] = {}
    rows = db.scalars(select(BankAccount).where(BankAccount.verified.is_(True))
                      .order_by(BankAccount.created_at))
    for acct in rows:            # ascending order → the latest row wins
        out[acct.employee_id] = acct
    return out


def eligibility_reasons(emp: Employee, year: int, month: int,
                        blockers: dict[int, list[str]] | None,
                        banks: dict[int, BankAccount] | None,
                        ) -> tuple[bool, list[str]]:
    """Evaluate one employee against the run period's payability rules.

    Args:
        emp: Employee master row.
        year: Run year.
        month: Run month (1-12).
        blockers: Result of :func:`open_blocker_map` (None → check skipped).
        banks: Result of :func:`verified_bank_map` (None → check skipped).

    Returns:
        ``(in_window, reasons)``. ``in_window`` is False when the employee is
        simply outside the period (hired after it, or left before it) — such
        people are not "blocked", they just don't belong on this run.
        ``reasons`` is the list of human-readable blockers; empty means the
        employee is eligible for the run.
    """
    period_start = dt.date(year, month, 1)
    period_end = month_end(year, month)
    # Period window (runs-and-exports R3/H1).
    if emp.hire_date and emp.hire_date > period_end:
        return False, [f"hired {emp.hire_date.isoformat()}, after this period"]
    if emp.last_working_day and emp.last_working_day < period_start:
        return False, [f"left on {emp.last_working_day.isoformat()}, "
                       "before this period"]
    reasons: list[str] = []
    # Lifecycle: active, or a leaver drawing final pay this month (GAP-03).
    if emp.status == "active":
        if not emp.active:
            reasons.append("marked inactive"
                           + (f" ({emp.inactive_reason})" if emp.inactive_reason else ""))
    elif emp.status in LEAVER_STATUSES and emp.last_working_day:
        pass                     # final-pay month — window already checked
    elif emp.active:
        # Legacy rows the old builder would have paid (active flag set but
        # never activated through the HR lifecycle): surface as blocked
        # rather than dropping them silently — a human must resolve these.
        reasons.append(f"status is '{emp.status}', not activated through HR")
    else:
        return False, [f"status is '{emp.status}', not payable"]
    if blockers is not None and emp.id in blockers:
        reasons.append("open blocker flag(s): "
                       + ", ".join(sorted(blockers[emp.id])))
    if banks is not None and emp.id not in banks:
        reasons.append("no verified bank account")
    return True, reasons


def payroll_candidates(db: Session, run: PayrollRun,
                       ) -> tuple[list[tuple[Employee, BankAccount | None]],
                                  list[dict]]:
    """Split all employees into (eligible, blocked) for the run's period.

    Returns:
        ``(eligible, blocked)`` — ``eligible`` pairs each payable employee
        with their verified bank account (None on legacy databases without
        the bank_accounts table); ``blocked`` lists employees who belong to
        the period but are excluded ("blocked from payroll"), each as a dict
        with ``employee_id``/``emp_code``/``name``/``reasons``.
    """
    blockers = open_blocker_map(db)
    banks = verified_bank_map(db)
    eligible: list[tuple[Employee, BankAccount | None]] = []
    blocked: list[dict] = []
    employees = db.scalars(select(Employee).order_by(Employee.emp_code)).all()
    for emp in employees:
        in_window, reasons = eligibility_reasons(emp, run.year, run.month,
                                                 blockers, banks)
        if not in_window:
            continue
        if reasons:
            blocked.append({"employee_id": emp.id, "emp_code": emp.emp_code,
                            "name": emp.name, "reasons": reasons})
        else:
            eligible.append((emp, banks.get(emp.id) if banks else None))
    return eligible, blocked


def blocked_for_run(db: Session, run: PayrollRun) -> list[dict]:
    """Employees excluded from this run's period ("blocked from payroll")."""
    return payroll_candidates(db, run)[1]


# --- proration (STAT-09, policy DEC-006) -------------------------------------
def prorate_basic(basic: Decimal, hire_date: dt.date | None,
                  last_working_day: dt.date | None, year: int, month: int,
                  ) -> tuple[Decimal, str | None]:
    """Calendar-day proration of a monthly basic for a partial month.

    Policy DEC-006: monthly staff whose hire_date or last_working_day falls
    inside the run month earn ``basic × (calendar days employed in the month
    / days in the month)``, rounded to the sen, BEFORE statutory compute.
    The preparer may still override the prorated figure on the run screen.

    Args:
        basic: Full monthly basic salary (RM).
        hire_date: Employee's hire date (None → employed since before month).
        last_working_day: Final day of service (None → employed past month).
        year: Run year.
        month: Run month (1-12).

    Returns:
        ``(amount, note)`` — the (possibly prorated) basic and a
        human-readable proration basis for the payslip note, or
        ``(basic, None)`` when the employee was employed the whole month.
    """
    period_start = dt.date(year, month, 1)
    period_end = month_end(year, month)
    start = hire_date if hire_date and hire_date > period_start else period_start
    end = (last_working_day if last_working_day
           and last_working_day < period_end else period_end)
    if start == period_start and end == period_end:
        return basic, None
    days_in_month = period_end.day
    employed_days = max((end - start).days + 1, 0)
    prorated = statutory.money(
        statutory.D(basic) * employed_days / days_in_month)
    parts = []
    if start != period_start:
        parts.append(f"joined {start.isoformat()}")
    if end != period_end:
        parts.append(f"last working day {end.isoformat()}")
    note = (f"Prorated basic (DEC-006): {employed_days}/{days_in_month} "
            f"calendar days employed ({'; '.join(parts)}) — "
            f"RM{basic:,.2f} × {employed_days}/{days_in_month} = RM{prorated:,.2f}")
    return prorated, note


def derive_statutory_flags(emp: Employee, year: int, month: int,
                           socso_relevant: bool = True,
                           ) -> tuple[bool, bool, str | None]:
    """Derive ``(over_60, foreign, warning)`` from the employee master row.

    ``over_60`` is True when the employee turns 60 on or before the LAST day
    of the run month — PERKESO applies Category 2 (and stops EIS) from the
    month of the 60th birthday, so a mid-month birthday counts for the whole
    month. When DOB is missing, ``over_60`` stays False and, if SOCSO/EIS is
    relevant for the line, a human-readable warning is returned so callers
    can surface it for review before approval.

    Args:
        emp: The employee master row (source of DOB and nationality).
        year: Payroll-run year.
        month: Payroll-run month (1-12).
        socso_relevant: Whether SOCSO/EIS applies to this payslip; controls
            whether a missing DOB warrants a warning.

    Returns:
        ``(over_60, foreign, warning)`` where ``warning`` is None when the
        derivation needed no assumptions.
    """
    over_60 = emp.over_60_on(month_end(year, month))
    warning: str | None = None
    if over_60 is None and socso_relevant:
        warning = (f"{emp.emp_code} {emp.name}: no date of birth on record — "
                   "SOCSO/EIS assumed Category 1 (under 60); verify DOB "
                   "before approving this run.")
    return bool(over_60), bool(emp.is_foreign), warning


def recompute(slip: Payslip, cfg: statutory.RateConfig = statutory.DEFAULT_CONFIG,
              lindung_rate: Decimal = Decimal("0")) -> str | None:
    """Recalculate all statutory/output fields on a payslip from its inputs.

    Re-derives ``over_60``/``foreign`` from the linked employee row and run
    period (rather than trusting the stored slip flags) whenever both
    relationships are reachable, so DOB/nationality corrections propagate.
    Returns a review warning when the derivation had to assume a category
    (e.g. missing DOB), else None; the warning is also logged.
    """
    warning: str | None = None
    emp, run = slip.employee, slip.run
    if emp is not None and run is not None:
        slip.over_60, slip.foreign, warning = derive_statutory_flags(
            emp, run.year, run.month, socso_relevant=slip.socso_enabled)
        if warning:
            logger.warning(warning)
    inp = statutory.PayInputs(
        basic=slip.basic or 0, count_by_day=slip.count_by_day, hourly=slip.hourly,
        rate=slip.rate or 0, units=slip.units or 0,
        allowance_enabled=slip.allowance_enabled, allowance=slip.allowance or 0,
        deduction_enabled=slip.deduction_enabled, deduction=slip.deduction or 0,
        ot_enabled=slip.ot_enabled, ot_hours=slip.ot_hours or 0, ot_rate=slip.ot_rate or 0,
        epf_enabled=slip.epf_enabled, socso_enabled=slip.socso_enabled,
        include_allowance=slip.include_allowance, include_ot=slip.include_ot,
        over_60=slip.over_60, foreign=slip.foreign,
        # opted-out staff pay no PCB at all, regardless of any manual override
        pcb_override=Decimal("0") if not slip.pcb_enabled else slip.pcb_override,
    )
    res = statutory.compute(inp, cfg)
    for field, value in vars(res).items():
        setattr(slip, field, value)
    # LINDUNG 24Jam — placeholder scheme; RM0 rate (unconfirmed) does nothing.
    # Employee-paid, on top of the statutory deductions above.
    slip.lindung_amount = (lindung_rate or Decimal("0")) if slip.lindung_optin else Decimal("0")
    slip.total_employee_deduction += slip.lindung_amount
    slip.net_salary -= slip.lindung_amount
    return warning


def _ot_rate_for(emp: Employee, settings) -> Decimal:
    """Per-employee OT rate, falling back to the platform default."""
    if emp.ot_rate and emp.ot_rate > 0:
        return emp.ot_rate
    if emp.employment_type == "part_time" and emp.hourly_rate:
        return emp.hourly_rate
    return (settings.default_ot_rate if settings else Decimal("15")) or Decimal("15")


def _new_payslip(emp: Employee, run: PayrollRun, cfg: statutory.RateConfig,
                 settings=None, bank: BankAccount | None = None) -> Payslip:
    """Create a payslip pre-filled from an employee's standing data.

    Bank details are snapshotted from the *verified* bank account row when
    one is supplied (STAT-07/DL-01); the legacy employees columns are only a
    fallback for databases without the bank_accounts table. A monthly basic
    is prorated by calendar days when the employee joined or left inside the
    run month (STAT-09 / DEC-006) — before statutory compute, with the basis
    recorded in the payslip note; the preparer can still override it.
    """
    is_part = emp.employment_type == "part_time"
    over_60, foreign, warning = derive_statutory_flags(
        emp, run.year, run.month,
        socso_relevant=emp.is_confirmed and emp.socso_enabled)
    if warning:
        logger.warning(warning)
    basic, proration_note = Decimal("0"), None
    if not is_part:
        basic, proration_note = prorate_basic(
            statutory.D(emp.basic_salary or 0), emp.hire_date,
            emp.last_working_day, run.year, run.month)
    slip = Payslip(
        run_id=run.id, employee_id=emp.id, emp_code=emp.emp_code, name=emp.name,
        bank_name=bank.bank_name if bank else emp.bank_name,
        bank_account=bank.account_no if bank else emp.bank_account,
        employment_type=emp.employment_type,
        basic=basic,
        hourly=is_part,                                    # part-timers earn rate × hours
        rate=(emp.hourly_rate or 0) if is_part else Decimal("0"),
        ot_rate=_ot_rate_for(emp, settings),
        allowance_enabled=emp.allowance_eligible,
        # Statutory-base composition comes from the admin settings
        # (STAT-12/QT-05); the seeded defaults are allowance-in, OT-out.
        include_allowance=(bool(settings.default_include_allowance)
                           if settings is not None else True),
        include_ot=(bool(settings.default_include_ot)
                    if settings is not None else False),
        # EPF/SOCSO/EIS: only possible for confirmed permanent staff (passed
        # probation), and within that, either can be individually exempted.
        epf_enabled=emp.is_confirmed and emp.epf_enabled,
        socso_enabled=emp.is_confirmed and emp.socso_enabled,
        pcb_enabled=emp.pcb_enabled,
        lindung_optin=emp.lindung_optin,
        over_60=over_60, foreign=foreign,
        notes=proration_note,
    )
    recompute(slip, cfg, (settings.lindung_24jam_rate if settings else None) or Decimal("0"))
    return slip


def breakdown(slip: Payslip, cfg: statutory.RateConfig = statutory.DEFAULT_CONFIG) -> list[dict]:
    """Per-column figures + plain-English explanations for the reviewer view."""
    inc = []
    if slip.include_allowance:
        inc.append("allowance")
    if slip.include_ot:
        inc.append("OT")
    stat_note = "Basic/base earning" + (f" + {' + '.join(inc)}" if inc else " only")
    if slip.count_by_day:
        base_note = f"Daily: RM{slip.rate:,.2f} × {slip.units:g} days = RM{slip.base_earning:,.2f}"
    elif slip.hourly:
        base_note = f"Hourly: RM{slip.rate:,.2f} × {slip.units:g} hours = RM{slip.base_earning:,.2f}"
    else:
        base_note = f"Monthly basic RM{slip.base_earning:,.2f} (from salary record)"
    return [
        {"key": "base", "label": "Base earning", "value": slip.base_earning,
         "employer": None, "note": base_note},
        {"key": "allowance", "label": "Allowance", "value": slip.allowance_total,
         "employer": None, "note": ("Included in statutory wage" if slip.include_allowance
                                    else "Paid, but excluded from statutory") if slip.allowance_enabled
         else "No allowance"},
        {"key": "ot", "label": "Overtime", "value": slip.ot_pay, "employer": None,
         "note": (f"{slip.ot_hours:g} hrs × RM{slip.ot_rate:,.2f}"
                  + (" (in statutory)" if slip.include_ot else " (excluded from statutory)"))
         if slip.ot_enabled else "No overtime"},
        {"key": "gross", "label": "Gross (total paid)", "value": slip.total_remuneration,
         "employer": None, "note": "Base + allowance + overtime"},
        {"key": "stat", "label": "Statutory wage", "value": slip.statutory_wage,
         "employer": None, "note": stat_note + " — the base every contribution is charged on"},
        {"key": "epf", "label": "EPF / KWSP", "value": slip.epf_employee,
         "employer": slip.epf_employer,
         "note": statutory.kwsp.explain(slip.statutory_wage, slip.epf_enabled, cfg,
                                        over_60=slip.over_60, foreign=slip.foreign)},
        {"key": "socso", "label": "SOCSO", "value": slip.socso_employee,
         "employer": slip.socso_employer,
         "note": statutory.socso.explain(slip.statutory_wage, slip.over_60,
                                         slip.socso_enabled, cfg,
                                         foreign=slip.foreign)},
        {"key": "eis", "label": "EIS", "value": slip.eis_employee, "employer": slip.eis_employer,
         "note": statutory.eis.explain(slip.statutory_wage, slip.over_60, slip.foreign, slip.socso_enabled, cfg)},
        {"key": "pcb", "label": "PCB (tax)", "value": slip.pcb, "employer": None,
         "note": statutory.pcb.explain(slip.statutory_wage, slip.epf_employee, slip.pcb_override, cfg)},
        {"key": "deduction", "label": "Other deduction", "value": slip.deduction_amount,
         "employer": None, "note": (slip.deduction_reason or "no reason given")
         if slip.deduction_enabled else "None"},
        {"key": "net", "label": "Net salary", "value": slip.net_salary, "employer": None,
         "note": "Total paid − EPF − SOCSO − EIS − PCB − other deduction"},
        {"key": "ercost", "label": "Employer cost", "value": slip.employer_cost,
         "employer": None, "note": "Total paid + employer EPF/SOCSO/EIS"},
    ]


def generate_run(db: Session, year: int, month: int,
                 work_days_default: int = 26) -> PayrollRun:
    """Create an empty payroll run; employees are added by name afterwards."""
    run = PayrollRun(year=year, month=month, status="draft",
                     work_days_default=work_days_default)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def add_employee(db: Session, run: PayrollRun, employee_id: int,
                 cfg: statutory.RateConfig, settings=None) -> bool:
    """Add a single employee (by id) to the run if not already present.

    Returns:
        True when a payslip was created; False when the employee is already
        on the run (including a concurrent insert caught by the unique
        constraint) or does not exist.

    Raises:
        PayrollError: When the employee is blocked from payroll or outside
            the run's period (STAT-07/DL-01).
    """
    if any(s.employee_id == employee_id for s in run.payslips):
        return False
    emp = db.get(Employee, employee_id)
    if not emp:
        return False
    blockers = open_blocker_map(db)
    banks = verified_bank_map(db)
    in_window, reasons = eligibility_reasons(emp, run.year, run.month,
                                             blockers, banks)
    if not in_window:
        raise PayrollError(f"{emp.name} is outside {run.period_label}: "
                           + "; ".join(reasons))
    if reasons:
        raise PayrollError(f"{emp.name} is blocked from payroll: "
                           + "; ".join(reasons))
    try:
        db.add(_new_payslip(emp, run, cfg, settings,
                            bank=banks.get(emp.id) if banks else None))
        db.commit()
    except IntegrityError:                      # concurrent duplicate (STAT-08)
        db.rollback()
        logger.warning("duplicate payslip suppressed: run=%s employee=%s",
                       run.id, employee_id)
        return False
    return True


def sync_new_employees(db: Session, run: PayrollRun, cfg: statutory.RateConfig,
                       settings=None) -> int:
    """Add payslips for every *eligible* employee not already on the run.

    Eligibility mirrors payroll_master_view (STAT-07/DL-01): lifecycle
    active (or leaver in their final-pay month), inside the period window,
    no open blocker flags, verified bank account. Duplicate payslips are
    suppressed by the (run_id, employee_id) unique constraint (STAT-08).
    """
    have = {s.employee_id for s in run.payslips}
    eligible, blocked = payroll_candidates(db, run)
    if blocked:
        logger.info("run %s: %d employee(s) blocked from payroll", run.id,
                    len(blocked))
    added = 0
    for emp, bank in eligible:
        if emp.id in have:
            continue
        try:
            with db.begin_nested():             # savepoint per slip (STAT-08)
                db.add(_new_payslip(emp, run, cfg, settings, bank=bank))
            added += 1
        except IntegrityError:
            logger.warning("duplicate payslip suppressed: run=%s employee=%s",
                           run.id, emp.id)
    if added:
        db.commit()
    return added


def available_employees(db: Session, run: PayrollRun) -> list[Employee]:
    """Eligible employees not yet on the run (for the add-by-name selector)."""
    have = {s.employee_id for s in run.payslips}
    eligible, _ = payroll_candidates(db, run)
    return sorted((e for e, _bank in eligible if e.id not in have),
                  key=lambda e: e.name)


def run_totals(run: PayrollRun) -> dict[str, Decimal]:
    """Aggregate money columns across a run's payslips."""
    fields = ["gross", "ot_pay", "total_remuneration", "epf_employee",
              "epf_employer", "socso_employee", "socso_employer", "eis_employee",
              "eis_employer", "pcb", "lindung_amount", "total_employee_deduction",
              "net_salary", "employer_statutory", "employer_cost"]
    totals = {f: Decimal("0") for f in fields}
    for slip in run.payslips:
        for f in fields:
            totals[f] += getattr(slip, f) or Decimal("0")
    totals["headcount"] = len(run.payslips)
    return totals
