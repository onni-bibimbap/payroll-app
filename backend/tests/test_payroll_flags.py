"""Tests for the over_60/foreign derivation on payroll paths (STAT-05).

The age-60 cutoff is month-end based: an employee who turns 60 at any point
on/before the last day of the run month is Category 2 for that whole month.
Recompute must re-derive both flags from the employee master row instead of
trusting the stored slip flags, and a missing DOB must surface a warning.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app import payroll
from app.core.rates import DEFAULT_CONFIG
from app.models import BankAccount, Employee

D = Decimal


def _employee(**overrides: object) -> Employee:
    """Build a minimal confirmed, statutory-enabled employee row."""
    defaults: dict[str, object] = dict(
        emp_code="T001", name="Test Person", employment_type="full_time",
        is_confirmed=True, basic_salary=D("3000"), epf_enabled=True,
        socso_enabled=True, active=True, status="active",
    )
    defaults.update(overrides)
    return Employee(**defaults)


def _make_payable(db: Session, emp: Employee) -> Employee:
    """Persist ``emp`` with a verified bank account so payroll accepts it."""
    db.add(emp)
    db.flush()
    db.add(BankAccount(employee_id=emp.id, bank_name="Maybank",
                       account_no="1122334455", verified=True))
    db.commit()
    return emp


@pytest.mark.unit
def test_month_end() -> None:
    assert payroll.month_end(2026, 6) == dt.date(2026, 6, 30)
    assert payroll.month_end(2024, 2) == dt.date(2024, 2, 29)
    assert payroll.month_end(2026, 12) == dt.date(2026, 12, 31)


@pytest.mark.unit
def test_derive_turns_60_mid_month_is_category_2() -> None:
    """Turning 60 on the 15th makes the whole run month Category 2."""
    emp = _employee(dob=dt.date(1966, 6, 15))
    over_60, foreign, warning = payroll.derive_statutory_flags(emp, 2026, 6)
    assert over_60 is True
    assert foreign is False
    assert warning is None


@pytest.mark.unit
def test_derive_turns_60_on_last_day_is_category_2() -> None:
    emp = _employee(dob=dt.date(1966, 6, 30))
    over_60, _, _ = payroll.derive_statutory_flags(emp, 2026, 6)
    assert over_60 is True


@pytest.mark.unit
def test_derive_still_59_all_month_is_category_1() -> None:
    """Birthday on the 1st of the NEXT month keeps the run in Category 1."""
    emp = _employee(dob=dt.date(1966, 7, 1))
    over_60, _, _ = payroll.derive_statutory_flags(emp, 2026, 6)
    assert over_60 is False
    # ...and the month before the birthday month is still Category 1 too.
    emp2 = _employee(dob=dt.date(1966, 6, 15))
    over_60_may, _, _ = payroll.derive_statutory_flags(emp2, 2026, 5)
    assert over_60_may is False


@pytest.mark.unit
def test_derive_missing_dob_warns_when_socso_relevant() -> None:
    emp = _employee(dob=None)
    over_60, _, warning = payroll.derive_statutory_flags(
        emp, 2026, 6, socso_relevant=True)
    assert over_60 is False
    assert warning is not None and "date of birth" in warning


@pytest.mark.unit
def test_derive_missing_dob_silent_when_socso_irrelevant() -> None:
    emp = _employee(dob=None)
    _, _, warning = payroll.derive_statutory_flags(
        emp, 2026, 6, socso_relevant=False)
    assert warning is None


@pytest.mark.unit
def test_derive_foreign_comes_from_master_row() -> None:
    emp = _employee(is_foreign=True, dob=dt.date(1990, 1, 1))
    _, foreign, _ = payroll.derive_statutory_flags(emp, 2026, 6)
    assert foreign is True


@pytest.mark.unit
def test_new_payslip_derives_over_60_at_month_end(db: Session) -> None:
    """A run-month 60th birthday lands the new slip in Category 2."""
    emp = _employee(dob=dt.date(1966, 6, 15))
    _make_payable(db, emp)
    run = payroll.generate_run(db, 2026, 6)
    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is True
    slip = run.payslips[0]
    assert slip.over_60 is True
    assert slip.socso_employee == D("0.00")           # Category 2
    assert slip.eis_employee == D("0.00")
    assert slip.socso_employer > D("0")


@pytest.mark.unit
def test_recompute_rederives_stale_slip_flags(db: Session) -> None:
    """A stale stored flag is corrected from Employee.dob on recompute."""
    emp = _employee(dob=dt.date(1960, 1, 1))          # 66 in 2026
    _make_payable(db, emp)
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    slip.over_60 = False                              # simulate stale flag
    slip.foreign = True
    warning = payroll.recompute(slip, DEFAULT_CONFIG)
    assert warning is None
    assert slip.over_60 is True
    assert slip.foreign is False
    assert slip.socso_employee == D("0.00")


@pytest.mark.unit
def test_recompute_dob_correction_propagates(db: Session) -> None:
    """Fixing a missing DOB flips the slip category on the next recompute."""
    emp = _employee(dob=None)
    _make_payable(db, emp)
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    assert slip.over_60 is False
    warning = payroll.recompute(slip, DEFAULT_CONFIG)
    assert warning is not None and "date of birth" in warning
    emp.dob = dt.date(1960, 1, 1)                     # HR corrects the record
    warning = payroll.recompute(slip, DEFAULT_CONFIG)
    assert warning is None
    assert slip.over_60 is True


@pytest.mark.unit
def test_recompute_no_warning_when_socso_disabled(db: Session) -> None:
    """Missing DOB is only worth a warning when SOCSO/EIS applies."""
    emp = _employee(dob=None, is_confirmed=False)     # unconfirmed: no SOCSO
    _make_payable(db, emp)
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    assert slip.socso_enabled is False
    assert payroll.recompute(slip, DEFAULT_CONFIG) is None
