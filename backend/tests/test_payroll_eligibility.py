"""Run-population integrity tests (STAT-07 / DL-01 / GAP-03 / STAT-08 / STAT-12).

The run builder must mirror payroll_master_view's predicate: only
lifecycle-active employees (or leavers in their final-pay month) with no open
blocker flags and a verified bank account are payable, inside the period
window. Bank details are snapshotted from the verified bank_accounts row, and
the (run_id, employee_id) unique constraint forbids duplicate payslips.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import payroll
from app.core.rates import DEFAULT_CONFIG
from app.models import BankAccount, Employee, HrReviewFlag, Payslip, Settings

D = Decimal


def _employee(code: str = "T001", **overrides: object) -> Employee:
    """Build a payable full-time employee row (bank added separately)."""
    defaults: dict[str, object] = dict(
        emp_code=code, name=f"Person {code}", employment_type="full_time",
        is_confirmed=True, basic_salary=D("3000"), epf_enabled=True,
        socso_enabled=True, active=True, status="active",
        dob=dt.date(1990, 1, 1),
    )
    defaults.update(overrides)
    return Employee(**defaults)


def _verified_bank(db: Session, emp: Employee, account: str = "1234500067",
                   bank: str = "Maybank") -> BankAccount:
    acct = BankAccount(employee_id=emp.id, bank_name=bank, account_no=account,
                       verified=True)
    db.add(acct)
    return acct


def _payable(db: Session, emp: Employee, **bank_kw: str) -> Employee:
    db.add(emp)
    db.flush()
    _verified_bank(db, emp, **bank_kw)
    db.commit()
    return emp


@pytest.mark.unit
def test_sync_includes_only_verified_unblocked_active(db: Session) -> None:
    # Arrange: one payable, one flagged, one bankless, one unverified bank.
    ok = _payable(db, _employee("OK1"))
    flagged = _payable(db, _employee("FL1"))
    db.add(HrReviewFlag(employee_id=flagged.id, flag_type="missing_nric",
                        severity="blocker", status="open"))
    bankless = _employee("NB1")
    db.add(bankless)
    db.flush()
    unverified = _employee("UV1")
    db.add(unverified)
    db.flush()
    db.add(BankAccount(employee_id=unverified.id, bank_name="CIMB",
                       account_no="777", verified=False))
    db.commit()
    run = payroll.generate_run(db, 2026, 6)

    # Act
    added = payroll.sync_new_employees(db, run, DEFAULT_CONFIG)

    # Assert: only the clean employee is paid; others are listed as blocked.
    assert added == 1
    assert [s.employee_id for s in run.payslips] == [ok.id]
    blocked = payroll.blocked_for_run(db, run)
    reasons = {b["emp_code"]: "; ".join(b["reasons"]) for b in blocked}
    assert "open blocker flag(s): missing_nric" in reasons["FL1"]
    assert "no verified bank account" in reasons["NB1"]
    assert "no verified bank account" in reasons["UV1"]


@pytest.mark.unit
def test_period_window_excludes_future_hire_and_past_leaver(db: Session) -> None:
    # Arrange: hired after the period; left before the period (H1).
    _payable(db, _employee("FUT", hire_date=dt.date(2026, 7, 1)))
    _payable(db, _employee("OLD", status="resigned", active=False,
                           last_working_day=dt.date(2026, 5, 20)))
    run = payroll.generate_run(db, 2026, 6)

    # Act / Assert: neither is synced nor listed as blocked (out of window).
    assert payroll.sync_new_employees(db, run, DEFAULT_CONFIG) == 0
    assert payroll.blocked_for_run(db, run) == []
    assert payroll.available_employees(db, run) == []


@pytest.mark.unit
def test_leaver_in_final_month_is_still_paid(db: Session) -> None:
    """GAP-03: a resignation mid-month keeps the final-pay month payable."""
    emp = _payable(db, _employee("LVR", status="resigned", active=False,
                                 hire_date=dt.date(2024, 1, 1),
                                 last_working_day=dt.date(2026, 6, 10)))
    run = payroll.generate_run(db, 2026, 6)

    added = payroll.sync_new_employees(db, run, DEFAULT_CONFIG)

    assert added == 1
    slip = run.payslips[0]
    assert slip.employee_id == emp.id
    assert slip.basic == D("1000.00")            # 10/30 days of RM3,000
    # ...and July's run must not include them.
    run7 = payroll.generate_run(db, 2026, 7)
    assert payroll.sync_new_employees(db, run7, DEFAULT_CONFIG) == 0


@pytest.mark.unit
def test_add_employee_refuses_blocked_with_reason(db: Session) -> None:
    emp = _employee("NOB")
    db.add(emp)
    db.commit()
    run = payroll.generate_run(db, 2026, 6)

    with pytest.raises(payroll.PayrollError, match="no verified bank account"):
        payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)
    assert run.payslips == []


@pytest.mark.unit
def test_add_employee_refuses_out_of_window(db: Session) -> None:
    emp = _payable(db, _employee("FUT2", hire_date=dt.date(2026, 8, 15)))
    run = payroll.generate_run(db, 2026, 6)

    with pytest.raises(payroll.PayrollError, match="outside"):
        payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG)


@pytest.mark.unit
def test_bank_snapshot_comes_from_verified_row(db: Session) -> None:
    """DL-01: the payslip snapshots the verified account, not the legacy column."""
    emp = _employee("SNAP", bank_name="OldBank", bank_account="000-legacy")
    _payable(db, emp, account="111222333", bank="CIMB")
    run = payroll.generate_run(db, 2026, 6)

    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is True

    slip = run.payslips[0]
    assert slip.bank_name == "CIMB"
    assert slip.bank_account == "111222333"


@pytest.mark.unit
def test_legacy_active_flag_without_hr_status_is_blocked(db: Session) -> None:
    """A row the old builder would pay (active=True, status applicant) is
    surfaced as blocked instead of silently dropped or silently paid."""
    emp = _employee("LEG", status="applicant")
    _payable(db, emp)
    run = payroll.generate_run(db, 2026, 6)

    assert payroll.sync_new_employees(db, run, DEFAULT_CONFIG) == 0
    blocked = payroll.blocked_for_run(db, run)
    assert len(blocked) == 1
    assert "not activated through HR" in "; ".join(blocked[0]["reasons"])


@pytest.mark.unit
def test_toggled_inactive_employee_is_blocked(db: Session) -> None:
    emp = _payable(db, _employee("TGL", active=False,
                                 inactive_reason="resigned"))
    run = payroll.generate_run(db, 2026, 6)

    assert payroll.sync_new_employees(db, run, DEFAULT_CONFIG) == 0
    blocked = payroll.blocked_for_run(db, run)
    assert [b["emp_code"] for b in blocked] == ["TGL"]
    assert "marked inactive" in "; ".join(blocked[0]["reasons"])


# --- STAT-08: duplicate payslips ---------------------------------------------
@pytest.mark.unit
def test_duplicate_payslip_rejected_by_unique_constraint(db: Session) -> None:
    emp = _payable(db, _employee("DUP"))
    run = payroll.generate_run(db, 2026, 6)
    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is True

    # A second in-Python add is refused...
    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is False
    # ...and a raw duplicate INSERT violates the DB constraint.
    db.add(Payslip(run_id=run.id, employee_id=emp.id, emp_code=emp.emp_code,
                   name=emp.name))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert len(run.payslips) == 1


@pytest.mark.unit
def test_sync_never_duplicates_existing_slips(db: Session) -> None:
    _payable(db, _employee("S1"))
    _payable(db, _employee("S2", emp_code="S2"))
    run = payroll.generate_run(db, 2026, 6)
    assert payroll.sync_new_employees(db, run, DEFAULT_CONFIG) == 2

    # Act: a repeated sync is a no-op (idempotency hazard H3).
    assert payroll.sync_new_employees(db, run, DEFAULT_CONFIG) == 0
    assert len(run.payslips) == 2


# --- STAT-12: statutory-base composition settings ----------------------------
@pytest.mark.unit
def test_new_payslip_reads_include_settings(db: Session) -> None:
    settings = Settings(id=1, default_include_allowance=False,
                        default_include_ot=True)
    db.add(settings)
    emp = _payable(db, _employee("INC", allowance_eligible=True))
    run = payroll.generate_run(db, 2026, 6)

    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG,
                                settings=settings) is True

    slip = run.payslips[0]
    assert slip.include_allowance is False
    assert slip.include_ot is True


@pytest.mark.unit
def test_new_payslip_defaults_without_settings(db: Session) -> None:
    """No settings row → the historical allowance-in / OT-out behavior."""
    emp = _payable(db, _employee("DEF"))
    run = payroll.generate_run(db, 2026, 6)
    assert payroll.add_employee(db, run, emp.id, DEFAULT_CONFIG) is True
    slip = run.payslips[0]
    assert slip.include_allowance is True
    assert slip.include_ot is False
