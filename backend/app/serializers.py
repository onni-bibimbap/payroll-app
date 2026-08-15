"""Model → JSON-safe dict converters for the API layer."""

from __future__ import annotations

from decimal import Decimal

from .models import Employee, Payslip, PayrollRun, Settings, User

SETTINGS_FIELDS = [
    "company_name", "default_work_days", "default_ot_rate",
    "epf_emp_rate", "epf_er_rate_low", "epf_er_rate_high", "epf_er_threshold",
    "socso_eis_ceiling", "socso_c1_emp", "socso_c1_er", "socso_c2_er", "eis_rate",
    "personal_relief", "epf_relief_cap", "tax_rebate", "rebate_ceiling",
    "default_include_allowance", "default_include_ot",
    "ft_default_epf", "ft_default_socso", "pt_default_epf", "pt_default_socso",
    "lindung_24jam_rate",
]

SLIP_INPUT_NUMBERS = ["basic", "rate", "units", "allowance", "deduction",
                      "ot_hours", "ot_rate"]
SLIP_OUTPUT_NUMBERS = [
    "base_earning", "allowance_total", "gross", "statutory_wage", "ot_pay",
    "total_remuneration", "epf_employee", "epf_employer", "socso_employee",
    "socso_employer", "eis_employee", "eis_employer", "chargeable_income",
    "pcb", "lindung_amount", "deduction_amount", "total_employee_deduction",
    "net_salary", "employer_statutory", "employer_cost",
]
SLIP_FLAGS = ["count_by_day", "hourly", "allowance_enabled", "deduction_enabled",
              "ot_enabled", "epf_enabled", "socso_enabled", "pcb_enabled",
              "lindung_optin", "include_allowance", "include_ot", "over_60", "foreign"]


def _num(v):
    if v is None:
        return None
    return float(v) if isinstance(v, Decimal) else v


def user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name,
            "role": u.role, "can_prepare": u.can_prepare, "can_approve": u.can_approve}


def employee_dict(e: Employee) -> dict:
    return {
        "id": e.id, "emp_code": e.emp_code, "name": e.name, "email": e.email,
        "phone": e.phone, "nric": e.nric,
        "dob": e.dob.isoformat() if e.dob else None,
        "bank_name": e.bank_name, "bank_account": e.bank_account,
        "position": e.position, "employment_type": e.employment_type,
        "basic_salary": _num(e.basic_salary), "hourly_rate": _num(e.hourly_rate),
        "ot_rate": _num(e.ot_rate), "epf_enabled": e.epf_enabled,
        "socso_enabled": e.socso_enabled, "pcb_enabled": e.pcb_enabled,
        "lindung_optin": e.lindung_optin, "allowance_eligible": e.allowance_eligible,
        "is_foreign": e.is_foreign, "active": e.active,
        "is_confirmed": e.is_confirmed, "status": e.status,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        "inactive_reason": e.inactive_reason, "needs_review": e.needs_review,
        "import_note": e.import_note,
    }


def run_dict(r: PayrollRun, user: User | None = None) -> dict:
    d = {
        "id": r.id, "year": r.year, "month": r.month, "status": r.status,
        "status_label": r.status_label, "period_label": r.period_label,
        "note": r.note, "remarks": r.remarks,
        "work_days_default": r.work_days_default,
        "prepared_by": r.prepared_by, "approved_by": r.approved_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "is_editable": r.is_editable,
    }
    if user is not None:
        d["editable_by_me"] = r.editable_by(user)
    return d


def slip_dict(s: Payslip) -> dict:
    d = {
        "id": s.id, "run_id": s.run_id, "employee_id": s.employee_id,
        "emp_code": s.emp_code, "name": s.name, "bank_name": s.bank_name,
        "bank_account": s.bank_account, "employment_type": s.employment_type,
        "deduction_reason": s.deduction_reason, "notes": s.notes,
        "pcb_override": _num(s.pcb_override),
        "confirmed": bool(s.employee and s.employee.is_confirmed),
    }
    for f in SLIP_INPUT_NUMBERS + SLIP_OUTPUT_NUMBERS:
        d[f] = _num(getattr(s, f))
    for f in SLIP_FLAGS:
        d[f] = getattr(s, f)
    return d


def settings_dict(s: Settings) -> dict:
    return {f: _num(getattr(s, f)) for f in SETTINGS_FIELDS}


def totals_dict(t: dict) -> dict:
    return {k: _num(v) for k, v in t.items()}
