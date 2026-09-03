"""SQLAlchemy ORM models: User, Employee, PayrollRun, Payslip."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, Date, DateTime, ForeignKey, Integer,
                        Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core import rates
from .database import Base

MONEY = Numeric(12, 2)


RATE = Numeric(7, 5)


class Settings(Base):
    """Singleton (id=1) holding platform-wide default configuration."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(64), default="Onni")
    default_work_days: Mapped[int] = mapped_column(Integer, default=26)
    default_ot_rate: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("15"))
    # EPF / KWSP — defaults imported from core/rates.py, the single source of
    # truth for statutory rates. Never re-type the literals here (QT-02: the
    # SOCSO employee share once diverged, under-deducting every employee).
    epf_emp_rate: Mapped[Decimal] = mapped_column(RATE, default=rates.EPF_EMP_RATE)
    epf_er_rate_low: Mapped[Decimal] = mapped_column(
        RATE, default=rates.EPF_ER_RATE_LOW)
    epf_er_rate_high: Mapped[Decimal] = mapped_column(
        RATE, default=rates.EPF_ER_RATE_HIGH)
    epf_er_threshold: Mapped[Decimal] = mapped_column(
        MONEY, default=rates.EPF_ER_THRESHOLD)
    # SOCSO / EIS
    socso_eis_ceiling: Mapped[Decimal] = mapped_column(
        MONEY, default=rates.SOCSO_EIS_CEILING)
    socso_c1_emp: Mapped[Decimal] = mapped_column(RATE, default=rates.SOCSO_C1_EMP)
    socso_c1_er: Mapped[Decimal] = mapped_column(RATE, default=rates.SOCSO_C1_ER)
    socso_c2_er: Mapped[Decimal] = mapped_column(RATE, default=rates.SOCSO_C2_ER)
    eis_rate: Mapped[Decimal] = mapped_column(RATE, default=rates.EIS_RATE)
    # PCB
    personal_relief: Mapped[Decimal] = mapped_column(
        MONEY, default=rates.PERSONAL_RELIEF)
    epf_relief_cap: Mapped[Decimal] = mapped_column(MONEY, default=rates.EPF_RELIEF_CAP)
    tax_rebate: Mapped[Decimal] = mapped_column(MONEY, default=rates.TAX_REBATE)
    rebate_ceiling: Mapped[Decimal] = mapped_column(MONEY, default=rates.REBATE_CEILING)
    # defaults applied to new payroll lines (STAT-12/QT-05: these are read by
    # payroll._new_payslip and main.run_save — the seeded defaults reproduce
    # the long-standing behavior of "allowance in statutory base, OT never").
    default_include_allowance: Mapped[bool] = mapped_column(Boolean, default=True)
    default_include_ot: Mapped[bool] = mapped_column(Boolean, default=False)
    # defaults applied to new employees (KWSP off by default per company policy)
    ft_default_epf: Mapped[bool] = mapped_column(Boolean, default=False)
    ft_default_socso: Mapped[bool] = mapped_column(Boolean, default=True)
    pt_default_epf: Mapped[bool] = mapped_column(Boolean, default=False)
    pt_default_socso: Mapped[bool] = mapped_column(Boolean, default=False)
    # LINDUNG 24Jam — placeholder scheme, rate unconfirmed; RM0 does nothing
    lindung_24jam_rate: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="preparer")  # preparer|approver|admin
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    @property
    def can_prepare(self) -> bool:
        return self.role in ("preparer", "admin")

    @property
    def can_approve(self) -> bool:
        return self.role in ("approver", "admin")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    emp_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    reg_ref: Mapped[str | None] = mapped_column(String(64), default=None)  # id from reg form
    name: Mapped[str] = mapped_column(String(128), index=True)
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    phone: Mapped[str | None] = mapped_column(String(48), default=None)
    nric: Mapped[str | None] = mapped_column(String(48), default=None)
    dob: Mapped[dt.date | None] = mapped_column(Date, default=None)
    bank_name: Mapped[str | None] = mapped_column(String(64), default=None)
    bank_account: Mapped[str | None] = mapped_column(String(64), default=None)
    position: Mapped[str | None] = mapped_column(String(64), default=None)

    employment_type: Mapped[str] = mapped_column(String(16), default="full_time")  # full_time|part_time
    # passed probation -> permanent staff; forces EPF + SOCSO on save
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False,
                                               server_default="false")
    basic_salary: Mapped[Decimal] = mapped_column(MONEY, default=0)
    hourly_rate: Mapped[Decimal] = mapped_column(MONEY, default=0)
    ot_rate: Mapped[Decimal] = mapped_column(MONEY, default=0)   # 0 => use platform default

    epf_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    socso_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pcb_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # LINDUNG 24Jam — placeholder scheme opt-in; rate set in Settings
    lindung_optin: Mapped[bool] = mapped_column(Boolean, default=False)
    allowance_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    is_foreign: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    inactive_reason: Mapped[str | None] = mapped_column(String(64), default=None)

    # --- employee master data (Supabase migrations 0002+) -------------------
    status: Mapped[str] = mapped_column(
        String(16).with_variant(
            postgresql.ENUM("applicant", "pending_review", "active", "resigned",
                            "terminated", "absconded", "rejected",
                            name="employment_status", create_type=False),
            "postgresql"),
        default="applicant", server_default="applicant")
    identity_type: Mapped[str] = mapped_column(
        String(16).with_variant(
            postgresql.ENUM("nric", "passport", "unhcr", "other",
                            name="identity_type", create_type=False),
            "postgresql"),
        default="nric", server_default="nric")
    residential_address: Mapped[str | None] = mapped_column(Text, default=None)
    nationality: Mapped[str] = mapped_column(String(8), default="MY",
                                             server_default="MY")
    hire_date: Mapped[dt.date | None] = mapped_column(Date, default=None)
    probation_end_date: Mapped[dt.date | None] = mapped_column(Date, default=None)
    resignation_notice_date: Mapped[dt.date | None] = mapped_column(Date, default=None)
    last_working_day: Mapped[dt.date | None] = mapped_column(Date, default=None)
    outlet: Mapped[str] = mapped_column(String(64), default="Setapak",
                                        server_default="Setapak")

    updated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    import_note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    payslips: Mapped[list["Payslip"]] = relationship(back_populates="employee")

    def age_on(self, when: dt.date) -> int | None:
        """Age in whole years on ``when``; None when DOB is unknown."""
        if not self.dob or self.dob.year > when.year:
            return None
        return when.year - self.dob.year - (
            (when.month, when.day) < (self.dob.month, self.dob.day))

    def over_60_on(self, when: dt.date) -> bool | None:
        """True when aged 60 or more on ``when``; None when DOB is unknown."""
        age = self.age_on(when)
        return None if age is None else age >= 60


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_run_year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|pending|approved|rejected
    note: Mapped[str | None] = mapped_column(Text, default=None)      # approver's rejection reason
    remarks: Mapped[str | None] = mapped_column(Text, default=None)   # preparer's free-text remarks
    work_days_default: Mapped[int] = mapped_column(Integer, default=26)

    prepared_by: Mapped[str | None] = mapped_column(String(64), default=None)
    approved_by: Mapped[str | None] = mapped_column(String(64), default=None)
    # DL-15: timezone-aware stamps (app writes Asia/Kuala_Lumpur time; the
    # columns are timestamptz on Postgres via migration 0010).
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None)
    approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None)

    payslips: Mapped[list["Payslip"]] = relationship(
        back_populates="run", cascade="all, delete-orphan")

    MONTHS = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    @property
    def period_label(self) -> str:
        return f"{self.MONTHS[self.month]} {self.year}"

    @property
    def status_label(self) -> str:
        return {"draft": "Draft", "pending": "Pending approval",
                "approved": "Approved", "rejected": "Rejected"}.get(self.status, self.status)

    @property
    def is_editable(self) -> bool:
        return self.status in ("draft", "rejected")

    def editable_by(self, user) -> bool:
        """Whether ``user`` may edit payslip figures in the current state.

        Only draft/rejected runs are editable, and only by a preparer.
        A pending run is read-only for everyone (STAT-14): the approver
        reviews exactly the submitted figures, and their only moves are the
        approve/reject transitions — a rejection reopens editing.
        """
        if self.status in ("draft", "rejected"):
            return bool(user and user.can_prepare)
        return False


class Payslip(Base):
    __tablename__ = "payslips"
    # STAT-08: one payslip per employee per run — concurrent/retried sync or
    # add-slip requests must not double-pay (migration 0010 enforces this on
    # existing Postgres databases via a unique index after deduplication).
    __table_args__ = (UniqueConstraint("run_id", "employee_id",
                                       name="uq_payslip_run_employee"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)

    # immutable snapshot of employee identity
    emp_code: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(128))
    bank_name: Mapped[str | None] = mapped_column(String(64), default=None)
    bank_account: Mapped[str | None] = mapped_column(String(64), default=None)
    employment_type: Mapped[str] = mapped_column(String(16), default="full_time")

    # inputs (only the columns that matter — checkbox-driven in the UI)
    basic: Mapped[Decimal] = mapped_column(MONEY, default=0)
    count_by_day: Mapped[bool] = mapped_column(Boolean, default=False)
    hourly: Mapped[bool] = mapped_column(Boolean, default=False)   # part-time base
    rate: Mapped[Decimal] = mapped_column(MONEY, default=0)        # day / hour rate
    units: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)  # days / hours
    allowance_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    allowance: Mapped[Decimal] = mapped_column(MONEY, default=0)
    deduction_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    deduction: Mapped[Decimal] = mapped_column(MONEY, default=0)
    deduction_reason: Mapped[str | None] = mapped_column(String(160), default=None)
    ot_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ot_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    ot_rate: Mapped[Decimal] = mapped_column(MONEY, default=0)
    epf_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    socso_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pcb_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lindung_optin: Mapped[bool] = mapped_column(Boolean, default=False)
    include_allowance: Mapped[bool] = mapped_column(Boolean, default=False)
    include_ot: Mapped[bool] = mapped_column(Boolean, default=False)
    over_60: Mapped[bool] = mapped_column(Boolean, default=False)
    foreign: Mapped[bool] = mapped_column(Boolean, default=False)
    pcb_override: Mapped[Decimal | None] = mapped_column(MONEY, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # outputs
    base_earning: Mapped[Decimal] = mapped_column(MONEY, default=0)
    allowance_total: Mapped[Decimal] = mapped_column(MONEY, default=0)
    gross: Mapped[Decimal] = mapped_column(MONEY, default=0)
    statutory_wage: Mapped[Decimal] = mapped_column(MONEY, default=0)
    ot_pay: Mapped[Decimal] = mapped_column(MONEY, default=0)
    total_remuneration: Mapped[Decimal] = mapped_column(MONEY, default=0)
    epf_employee: Mapped[Decimal] = mapped_column(MONEY, default=0)
    epf_employer: Mapped[Decimal] = mapped_column(MONEY, default=0)
    socso_employee: Mapped[Decimal] = mapped_column(MONEY, default=0)
    socso_employer: Mapped[Decimal] = mapped_column(MONEY, default=0)
    eis_employee: Mapped[Decimal] = mapped_column(MONEY, default=0)
    eis_employer: Mapped[Decimal] = mapped_column(MONEY, default=0)
    chargeable_income: Mapped[Decimal] = mapped_column(MONEY, default=0)
    pcb: Mapped[Decimal] = mapped_column(MONEY, default=0)
    lindung_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)
    deduction_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)
    total_employee_deduction: Mapped[Decimal] = mapped_column(MONEY, default=0)
    net_salary: Mapped[Decimal] = mapped_column(MONEY, default=0)
    employer_statutory: Mapped[Decimal] = mapped_column(MONEY, default=0)
    employer_cost: Mapped[Decimal] = mapped_column(MONEY, default=0)

    run: Mapped["PayrollRun"] = relationship(back_populates="payslips")
    employee: Mapped["Employee"] = relationship(back_populates="payslips")


# --- employee-master mirrors -------------------------------------------------
# ORM mirrors of tables created by supabase/migrations/0002 so the payroll-run
# builder can enforce the blocked-from-payroll rule (STAT-07/DL-01) and write
# audit rows (SEC-06/DL-04) on every backend, including the SQLite test/dev
# fallback where the SQL migrations never run (create_all builds them there;
# on Postgres the migration-created tables already exist and are left alone).


class BankAccount(Base):
    """A bank account on record for an employee; only verified rows are paid.

    Mirrors ``bank_accounts`` from migration 0002 — account numbers are TEXT,
    never numeric (leading zeros must survive).
    """

    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    bank_name: Mapped[str] = mapped_column(Text)
    account_no: Mapped[str] = mapped_column(Text)
    account_holder_name: Mapped[str | None] = mapped_column(Text, default=None)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())


class HrReviewFlag(Base):
    """HR review flag; an open ``blocker`` severity excludes from payroll.

    Mirrors ``hr_review_flags`` from migration 0002.
    """

    __tablename__ = "hr_review_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    flag_type: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text, default="warning")  # info|warning|blocker
    details: Mapped[dict | None] = mapped_column(
        JSON().with_variant(postgresql.JSONB(), "postgresql"), default=None)
    status: Mapped[str] = mapped_column(
        String(16).with_variant(
            postgresql.ENUM("open", "resolved", "dismissed",
                            name="flag_status", create_type=False),
            "postgresql"),
        default="open", index=True)
    raised_by: Mapped[str] = mapped_column(Text, default="system")
    resolved_by: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None)


class AuditLog(Base):
    """Append-only audit trail row (actor, action, entity — names, no values).

    Mirrors ``audit_log`` from migration 0002; ``changed_fields`` holds field
    NAMES only, never values, so no RESTRICTED data can leak through auditing.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str | None] = mapped_column(Text, default=None)
    action: Mapped[str] = mapped_column(Text)
    entity: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[str] = mapped_column(Text)
    changed_fields: Mapped[list | None] = mapped_column(
        JSON().with_variant(postgresql.ARRAY(Text), "postgresql"), default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
