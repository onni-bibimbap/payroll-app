"""Payroll integration surface — CSV exports of the master & movements views.

The clerk's monthly routine: download both CSVs, key only part-time hours and
OT hours into the payroll run. Employees with open blockers or unverified
bank accounts never appear in the master export; they are listed on the
compliance board instead.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .hr import require_hr
from .models import User

router = APIRouter(prefix="/api/payroll-export", tags=["payroll-export"])


def _csv(rows, filename: str) -> Response:
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/master")
def master_csv(year: int, month: int, user: User = Depends(require_hr),
               db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select employee_no, full_name, identity_no, identity_type::text,
               employment_type, position, outlet, pay_type,
               round(basic_salary_sen / 100.0, 2) as basic_salary_rm,
               round(hourly_rate_sen / 100.0, 2) as hourly_rate_rm,
               ot_eligible, epf_no, socso_no, income_tax_no,
               bank_name, account_no, hire_date, last_working_day
        from payroll_master_view
        where (hire_date is null or hire_date <= make_date(:y, :m, 1) + interval '1 month' - interval '1 day')
          and (last_working_day is null or last_working_day >= make_date(:y, :m, 1))
        order by employee_no
    """), {"y": year, "m": month}).mappings().all()
    return _csv([dict(r) for r in rows], f"payroll_master_{year}{month:02d}.csv")


@router.get("/movements")
def movements_csv(year: int, month: int, user: User = Depends(require_hr),
                  db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select employee_no, full_name, position, employment_type, outlet,
               movement, hire_date, resignation_notice_date, last_working_day,
               status::text, final_pay_due
        from payroll_movements_view
        where (hire_date >= make_date(:y, :m, 1)
               and hire_date < make_date(:y, :m, 1) + interval '1 month')
           or (last_working_day >= make_date(:y, :m, 1)
               and last_working_day < make_date(:y, :m, 1) + interval '1 month')
        order by employee_no
    """), {"y": year, "m": month}).mappings().all()
    return _csv([dict(r) for r in rows], f"payroll_movements_{year}{month:02d}.csv")
