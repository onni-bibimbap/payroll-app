"""Payroll-run orchestration: build runs from employees and recompute payslips."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import statutory
from .models import Employee, Payslip, PayrollRun

# Editable input fields the preparer can change on the review screen.
NUMBER_FIELDS = ["basic", "rate", "units", "allowance", "deduction",
                 "ot_hours", "ot_rate"]
TEXT_FIELDS = ["deduction_reason", "notes"]
# In the table, allowance/deduction/OT are enabled implicitly by their amounts,
# so those three flags are derived in the save handler rather than posted.
FLAG_FIELDS = ["count_by_day", "epf_enabled", "socso_enabled",
               "include_allowance", "include_ot", "over_60", "foreign"]


def recompute(slip: Payslip, cfg: statutory.RateConfig = statutory.DEFAULT_CONFIG) -> None:
    """Recalculate all statutory/output fields on a payslip from its inputs."""
    inp = statutory.PayInputs(
        basic=slip.basic or 0, count_by_day=slip.count_by_day, hourly=slip.hourly,
        rate=slip.rate or 0, units=slip.units or 0,
        allowance_enabled=slip.allowance_enabled, allowance=slip.allowance or 0,
        deduction_enabled=slip.deduction_enabled, deduction=slip.deduction or 0,
        ot_enabled=slip.ot_enabled, ot_hours=slip.ot_hours or 0, ot_rate=slip.ot_rate or 0,
        epf_enabled=slip.epf_enabled, socso_enabled=slip.socso_enabled,
        include_allowance=slip.include_allowance, include_ot=slip.include_ot,
        over_60=slip.over_60, foreign=slip.foreign, pcb_override=slip.pcb_override,
    )
    res = statutory.compute(inp, cfg)
    for field, value in vars(res).items():
        setattr(slip, field, value)


def _ot_rate_for(emp: Employee, settings) -> Decimal:
    """Per-employee OT rate, falling back to the platform default."""
    if emp.ot_rate and emp.ot_rate > 0:
        return emp.ot_rate
    if emp.employment_type == "part_time" and emp.hourly_rate:
        return emp.hourly_rate
    return (settings.default_ot_rate if settings else Decimal("15")) or Decimal("15")


def _new_payslip(emp: Employee, run: PayrollRun, cfg: statutory.RateConfig, settings=None) -> Payslip:
    """Create a payslip pre-filled from an employee's standing data."""
    period = dt.date(run.year, run.month, 1)
    age = emp.age_on(period)
    is_part = emp.employment_type == "part_time"
    slip = Payslip(
        run_id=run.id, employee_id=emp.id, emp_code=emp.emp_code, name=emp.name,
        bank_name=emp.bank_name, bank_account=emp.bank_account,
        employment_type=emp.employment_type,
        basic=Decimal("0") if is_part else (emp.basic_salary or 0),
        hourly=is_part,                                    # part-timers earn rate × hours
        rate=(emp.hourly_rate or 0) if is_part else Decimal("0"),
        ot_rate=_ot_rate_for(emp, settings),
        allowance_enabled=emp.allowance_eligible,
        include_allowance=bool(settings and settings.default_include_allowance),
        include_ot=bool(settings and settings.default_include_ot),
        epf_enabled=emp.epf_enabled, socso_enabled=emp.socso_enabled,
        over_60=bool(age is not None and age >= 60), foreign=emp.is_foreign,
    )
    recompute(slip, cfg)
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
         "note": statutory.kwsp.explain(slip.statutory_wage, slip.epf_enabled, cfg)},
        {"key": "socso", "label": "SOCSO", "value": slip.socso_employee,
         "employer": slip.socso_employer,
         "note": statutory.socso.explain(slip.statutory_wage, slip.over_60, slip.socso_enabled, cfg)},
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
    """Add a single employee (by id) to the run if not already present."""
    if any(s.employee_id == employee_id for s in run.payslips):
        return False
    emp = db.get(Employee, employee_id)
    if not emp:
        return False
    db.add(_new_payslip(emp, run, cfg, settings))
    db.commit()
    return True


def sync_new_employees(db: Session, run: PayrollRun, cfg: statutory.RateConfig,
                       settings=None) -> int:
    """Add payslips for every active employee not already on the run."""
    have = {s.employee_id for s in run.payslips}
    employees = db.scalars(
        select(Employee).where(Employee.active.is_(True)).order_by(Employee.emp_code)
    ).all()
    added = 0
    for emp in employees:
        if emp.id not in have:
            db.add(_new_payslip(emp, run, cfg, settings))
            added += 1
    if added:
        db.commit()
    return added


def available_employees(db: Session, run: PayrollRun) -> list[Employee]:
    """Active employees not yet on the run (for the add-by-name selector)."""
    have = {s.employee_id for s in run.payslips}
    return [e for e in db.scalars(
        select(Employee).where(Employee.active.is_(True)).order_by(Employee.name)
    ).all() if e.id not in have]


def run_totals(run: PayrollRun) -> dict[str, Decimal]:
    """Aggregate money columns across a run's payslips."""
    fields = ["gross", "ot_pay", "total_remuneration", "epf_employee",
              "epf_employer", "socso_employee", "socso_employer", "eis_employee",
              "eis_employer", "pcb", "total_employee_deduction", "net_salary",
              "employer_statutory", "employer_cost"]
    totals = {f: Decimal("0") for f in fields}
    for slip in run.payslips:
        for f in fields:
            totals[f] += getattr(slip, f) or Decimal("0")
    totals["headcount"] = len(run.payslips)
    return totals
