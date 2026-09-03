"""API tests for payroll-run integrity (STAT-13/STAT-14/QT-07/SEC-06/DL-15).

Exercises the FastAPI endpoints over SQLite in-memory: typed request
validation (422 on garbage instead of silent 0-coercion), the pending-run
read-only rule, the self-approval ban, audit-trail rows, delete restrictions
and Kuala Lumpur timezone-aware lifecycle stamps.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, BankAccount, Employee, User
from app.security import hash_password

D = Decimal

# One hash for every test user — pbkdf2 is deliberately slow, hash it once.
_PW_HASH = hash_password("pw")


def _mk_users(db: Session) -> None:
    for username, role in (("prep", "preparer"), ("appr", "approver"),
                           ("boss", "admin")):
        db.add(User(username=username, full_name=username.title(), role=role,
                    password_hash=_PW_HASH))
    db.commit()


def _login(client, username: str) -> None:
    resp = client.post("/api/auth/login",
                       json={"username": username, "password": "pw"})
    assert resp.status_code == 200, resp.text


def _mk_employee(db: Session, code: str = "E001") -> Employee:
    emp = Employee(emp_code=code, name=f"Employee {code}",
                   employment_type="full_time", is_confirmed=True,
                   basic_salary=D("3000"), epf_enabled=True,
                   socso_enabled=True, active=True, status="active",
                   dob=dt.date(1990, 1, 1))
    db.add(emp)
    db.flush()
    db.add(BankAccount(employee_id=emp.id, bank_name="Maybank",
                       account_no="1234500067", verified=True))
    db.commit()
    return emp


def _mk_run(client, db: Session, year: int = 2026, month: int = 6) -> dict:
    """Create a run with one synced employee; returns the run dict."""
    resp = client.post("/api/runs", json={"year": year, "month": month})
    assert resp.status_code == 200, resp.text
    run = resp.json()
    resp = client.post(f"/api/runs/{run['id']}/sync")
    assert resp.status_code == 200, resp.text
    return run


def _actions(db: Session) -> list[str]:
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.id)))


# --- request validation (STAT-13 / QT-07) ------------------------------------
@pytest.mark.integration
def test_run_create_rejects_month_13(client, db: Session) -> None:
    _mk_users(db)
    _login(client, "prep")
    assert client.post("/api/runs", json={"year": 2026, "month": 13}).status_code == 422
    assert client.post("/api/runs", json={"month": 6}).status_code == 422
    assert client.post("/api/runs", json={"year": 2026, "month": 0}).status_code == 422


@pytest.mark.integration
def test_login_missing_fields_is_422(client, db: Session) -> None:
    assert client.post("/api/auth/login", json={"username": "x"}).status_code == 422


@pytest.mark.integration
def test_run_save_rejects_garbage_and_negative_money(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    slip_id = client.get(f"/api/runs/{run['id']}").json()["slips"][0]["id"]

    # Garbage must 422, never silently zero the payslip (STAT-13).
    resp = client.put(f"/api/runs/{run['id']}",
                      json={"slips": [{"id": slip_id, "basic": "1,2o0"}]})
    assert resp.status_code == 422
    # Negative money must 422.
    resp = client.put(f"/api/runs/{run['id']}",
                      json={"slips": [{"id": slip_id, "allowance": -50}]})
    assert resp.status_code == 422
    # The slip is untouched by the rejected saves.
    slip = client.get(f"/api/runs/{run['id']}").json()["slips"][0]
    assert slip["basic"] == 3000.0
    # Comma-formatted input still works (UI habit).
    resp = client.put(f"/api/runs/{run['id']}",
                      json={"slips": [{"id": slip_id, "basic": "2,500"}]})
    assert resp.status_code == 200
    assert resp.json()["slips"][0]["basic"] == 2500.0


@pytest.mark.integration
def test_run_save_negative_pcb_override_rejected(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    slip_id = client.get(f"/api/runs/{run['id']}").json()["slips"][0]["id"]
    resp = client.put(f"/api/runs/{run['id']}",
                      json={"slips": [{"id": slip_id, "pcb_override": "-1"}]})
    assert resp.status_code == 422


# --- run detail shape --------------------------------------------------------
@pytest.mark.integration
def test_run_detail_surfaces_blocked_employees(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db, "OK1")
    bankless = Employee(emp_code="NB1", name="No Bank", active=True,
                       status="active", basic_salary=D("2000"))
    db.add(bankless)
    db.commit()
    _login(client, "prep")
    run = _mk_run(client, db)

    detail = client.get(f"/api/runs/{run['id']}").json()

    assert [s["emp_code"] for s in detail["slips"]] == ["OK1"]
    assert [b["emp_code"] for b in detail["blocked"]] == ["NB1"]
    assert "no verified bank account" in "; ".join(detail["blocked"][0]["reasons"])


# --- pending runs are read-only (STAT-14) ------------------------------------
@pytest.mark.integration
def test_pending_run_rejects_edits_from_everyone(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    slip_id = client.get(f"/api/runs/{run['id']}").json()["slips"][0]["id"]
    assert client.post(f"/api/runs/{run['id']}/submit").status_code == 200

    body = {"slips": [{"id": slip_id, "basic": "9999"}]}
    assert client.put(f"/api/runs/{run['id']}", json=body).status_code == 409
    _login(client, "appr")
    assert client.put(f"/api/runs/{run['id']}", json=body).status_code == 409
    _login(client, "boss")
    assert client.put(f"/api/runs/{run['id']}", json=body).status_code == 409
    # A rejection reopens editing for the preparer.
    _login(client, "appr")
    assert client.post(f"/api/runs/{run['id']}/reject",
                       json={"note": "fix basic"}).status_code == 200
    _login(client, "prep")
    assert client.put(f"/api/runs/{run['id']}", json=body).status_code == 200


# --- self-approval ban & delete rules (SEC-06) -------------------------------
@pytest.mark.integration
def test_admin_cannot_approve_own_run(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "boss")                       # admin prepares AND submits
    run = _mk_run(client, db)
    assert client.post(f"/api/runs/{run['id']}/submit").status_code == 200

    resp = client.post(f"/api/runs/{run['id']}/approve")
    assert resp.status_code == 409
    assert "different approver" in resp.json()["detail"]
    # A different approver may approve.
    _login(client, "appr")
    assert client.post(f"/api/runs/{run['id']}/approve").status_code == 200


@pytest.mark.integration
def test_pending_and_approved_runs_cannot_be_deleted(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    assert client.post(f"/api/runs/{run['id']}/submit").status_code == 200
    assert client.delete(f"/api/runs/{run['id']}").status_code == 409

    _login(client, "appr")
    client.post(f"/api/runs/{run['id']}/reject", json={"note": "n"})
    _login(client, "prep")
    assert client.delete(f"/api/runs/{run['id']}").status_code == 200


# --- audit trail (SEC-06 / DL-04) --------------------------------------------
@pytest.mark.integration
def test_lifecycle_writes_audit_rows(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    slip_id = client.get(f"/api/runs/{run['id']}").json()["slips"][0]["id"]
    client.put(f"/api/runs/{run['id']}",
               json={"slips": [{"id": slip_id, "allowance": "150"}]})
    client.post(f"/api/runs/{run['id']}/submit")
    _login(client, "appr")
    client.post(f"/api/runs/{run['id']}/approve")

    actions = _actions(db)
    for expected in ("run_create", "run_sync", "slip_edit", "run_submit",
                     "run_approve"):
        assert expected in actions, f"missing audit action {expected}"
    edit = db.scalar(select(AuditLog).where(AuditLog.action == "slip_edit"))
    assert edit is not None
    assert edit.actor == "prep"
    assert edit.entity == "payslip"
    # Field NAMES only — never values (§7 RESTRICTED: salary amounts).
    assert "allowance" in edit.changed_fields
    assert all(str(f).replace("_", "").isalpha() for f in edit.changed_fields)
    approve = db.scalar(select(AuditLog).where(AuditLog.action == "run_approve"))
    assert approve is not None and approve.actor == "appr"


@pytest.mark.integration
def test_run_delete_writes_audit_row(client, db: Session) -> None:
    _mk_users(db)
    _login(client, "prep")
    resp = client.post("/api/runs", json={"year": 2026, "month": 6})
    run_id = resp.json()["id"]
    assert client.delete(f"/api/runs/{run_id}").status_code == 200
    row = db.scalar(select(AuditLog).where(AuditLog.action == "run_delete"))
    assert row is not None and row.actor == "prep"


# --- timezone-aware stamps (DL-15) -------------------------------------------
@pytest.mark.unit
def test_now_kl_is_aware_kuala_lumpur() -> None:
    from app.main import now_kl

    stamp = now_kl()
    assert stamp.tzinfo is not None
    assert stamp.utcoffset() == dt.timedelta(hours=8)


@pytest.mark.integration
def test_lifecycle_stamps_use_kl_time(client, db: Session, monkeypatch) -> None:
    """submit/approve stamp Asia/Kuala_Lumpur wall time, timezone-aware.

    SQLite loses the offset on round-trip (Postgres timestamptz keeps it —
    migration 0010), so the assertion pins the KL wall-clock value written.
    """
    from app import main as main_module

    fixed = dt.datetime(2026, 6, 15, 12, 0, 0, tzinfo=main_module.KL_TZ)
    monkeypatch.setattr(main_module, "now_kl", lambda: fixed)
    _mk_users(db)
    _mk_employee(db)
    _login(client, "prep")
    run = _mk_run(client, db)
    detail = client.post(f"/api/runs/{run['id']}/submit").json()
    assert detail["run"]["submitted_at"].startswith("2026-06-15T12:00:00")
    _login(client, "appr")
    detail = client.post(f"/api/runs/{run['id']}/approve").json()
    assert detail["run"]["approved_at"].startswith("2026-06-15T12:00:00")


# --- statutory-base settings are honored on save (STAT-12 / QT-05) -----------
@pytest.mark.integration
def test_run_save_honors_include_settings(client, db: Session) -> None:
    _mk_users(db)
    _mk_employee(db)
    _login(client, "boss")
    assert client.put("/api/settings",
                      json={"default_include_ot": True}).status_code == 200
    _login(client, "prep")
    run = _mk_run(client, db)
    slip_id = client.get(f"/api/runs/{run['id']}").json()["slips"][0]["id"]

    resp = client.put(f"/api/runs/{run['id']}", json={
        "slips": [{"id": slip_id, "ot_hours": "10", "ot_rate": "20"}]})

    slip = resp.json()["slips"][0]
    assert slip["include_ot"] is True
    assert slip["ot_pay"] == 200.0
    assert slip["statutory_wage"] == 3200.0      # OT now in the statutory base
