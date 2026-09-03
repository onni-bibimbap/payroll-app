"""Mid-month join/leave proration tests (STAT-09, policy DEC-006).

Monthly staff whose hire_date or last_working_day falls inside the run month
earn basic × (calendar days employed in month / days in month), rounded to
the sen, BEFORE statutory compute. The preparer may override the prorated
basic, and the proration basis is recorded in the payslip note.
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


def _payable(db: Session, **overrides: object) -> Employee:
    defaults: dict[str, object] = dict(
        emp_code="P001", name="Prorate Person", employment_type="full_time",
        is_confirmed=True, basic_salary=D("3000"), epf_enabled=True,
        socso_enabled=True, active=True, status="active",
        dob=dt.date(1990, 1, 1),
    )
    defaults.update(overrides)
    emp = Employee(**defaults)
    db.add(emp)
    db.flush()
    db.add(BankAccount(employee_id=emp.id, bank_name="Maybank",
                       account_no="1234500067", verified=True))
    db.commit()
    return emp


# --- pure function -----------------------------------------------------------
@pytest.mark.unit
def test_prorate_full_month_untouched() -> None:
    amount, note = payroll.prorate_basic(D("3000"), dt.date(2024, 1, 1),
                                         None, 2026, 6)
    assert amount == D("3000")
    assert note is None


@pytest.mark.unit
def test_prorate_mid_month_join() -> None:
    # June 2026 has 30 days; joining on the 19th leaves 12 employed days.
    amount, note = payroll.prorate_basic(D("3000"), dt.date(2026, 6, 19),
                                         None, 2026, 6)
    assert amount == D("1200.00")
    assert note is not None and "12/30" in note


@pytest.mark.unit
def test_prorate_mid_month_leave() -> None:
    amount, note = payroll.prorate_basic(D("3000"), dt.date(2024, 1, 1),
                                         dt.date(2026, 6, 10), 2026, 6)
    assert amount == D("1000.00")
    assert note is not None and "10/30" in note


@pytest.mark.unit
def test_prorate_single_day_employment() -> None:
    amount, note = payroll.prorate_basic(D("3000"), dt.date(2026, 6, 10),
                                         dt.date(2026, 6, 10), 2026, 6)
    assert amount == D("100.00")               # 1/30 of RM3,000
    assert note is not None and "1/30" in note


@pytest.mark.unit
def test_prorate_rounds_to_sen_half_up() -> None:
    # Feb 2026 (28 days), 13 employed days: 3333.33 × 13 / 28 = 1547.6175…
    amount, _ = payroll.prorate_basic(D("3333.33"), dt.date(2026, 2, 16),
                                      None, 2026, 2)
    assert amount == D("1547.62")


@pytest.mark.unit
def test_prorate_last_day_leave_is_full_month() -> None:
    amount, note = payroll.prorate_basic(D("3000"), None,
                                         dt.date(2026, 6, 30), 2026, 6)
    assert amount == D("3000")
    assert note is None


@pytest.mark.unit
def test_prorate_inverted_dates_clamps_to_zero() -> None:
    """Bad master data (hire after LWD in-month) never yields negative pay."""
    amount, _ = payroll.prorate_basic(D("3000"), dt.date(2026, 6, 20),
                                      dt.date(2026, 6, 5), 2026, 6)
    assert amount == D("0.00")


# --- through the payslip builder --------------------------------------------
@pytest.mark.unit
def test_new_payslip_prorates_before_statutory(db: Session) -> None:
    emp = _payable(db, hire_date=dt.date(2026, 6, 19))
    run = payroll.generate_run(db, 2026, 6)

    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is True

    slip = run.payslips[0]
    assert slip.basic == D("1200.00")
    assert slip.statutory_wage == D("1200.00")   # statutory on prorated basic
    assert slip.notes is not None and "Prorated" in slip.notes
    # EPF employee 11% on the Third Schedule band top — RM1,200 exactly.
    assert slip.epf_employee == D("132.00")


@pytest.mark.unit
def test_new_payslip_full_month_has_no_proration_note(db: Session) -> None:
    emp = _payable(db, hire_date=dt.date(2024, 1, 1))
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    assert slip.basic == D("3000")
    assert slip.notes is None


@pytest.mark.unit
def test_part_time_hourly_slip_is_not_prorated(db: Session) -> None:
    emp = _payable(db, employment_type="part_time", basic_salary=D("0"),
                   hourly_rate=D("10"), hire_date=dt.date(2026, 6, 19),
                   is_confirmed=False)
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    assert slip.hourly is True
    assert slip.basic == D("0")
    assert slip.notes is None                    # units-based, nothing to prorate


@pytest.mark.unit
def test_preparer_override_survives_recompute(db: Session) -> None:
    """The prorated basic is a default — an override is never re-prorated."""
    emp = _payable(db, hire_date=dt.date(2026, 6, 19))
    run = payroll.generate_run(db, 2026, 6)
    payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    slip = run.payslips[0]
    assert slip.basic == D("1200.00")

    slip.basic = D("1500")                       # preparer override
    payroll.recompute(slip, DEFAULT_CONFIG)

    assert slip.basic == D("1500")
    assert slip.statutory_wage == D("1500.00")
