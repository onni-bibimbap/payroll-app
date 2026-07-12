# Onni Payroll — Web App

A **mobile-first** FastAPI + SQLite web app for running Malaysian monthly payroll.
Each statutory contribution has its own core module — [`app/core/kwsp.py`](app/core/kwsp.py),
[`app/core/socso.py`](app/core/socso.py), [`app/core/eis.py`](app/core/eis.py),
[`app/core/pcb.py`](app/core/pcb.py) — sharing rates in [`app/core/rates.py`](app/core/rates.py)
and combined by [`app/statutory.py`](app/statutory.py). Every module exposes both the
numbers and an `explain()` derivation (verified against the original `emp_payroll_2605.xlsx`).

## Quick start

```bash
cd webapp
chmod +x run.sh
./run.sh                 # installs deps, seeds DB, starts the server
# open http://127.0.0.1:8077
```

Sign in with one of the seeded accounts (change these via env vars in production):

| Role | Username | Password | Can do |
|------|----------|----------|--------|
| Preparer | `preparer` | `preparer123` | Create/edit employees & payroll, send for approval |
| Approver | `approver` | `approver123` | Approve / reject a pending run |
| Admin | `admin` | `admin123` | Both of the above |

## What it does

1. **Employees (the salary record)** — create/edit **full-time** (monthly basic) or
   **part-time** (hourly rate) staff; toggle EPF / SOCSO+EIS / **allowance
   eligibility** / foreign / active. The first 58 staff were imported from
   `employee-registration-form (1).xlsx`; 11 rows with ambiguous salary/DOB are
   flagged **⚠ Review** for you to confirm.
2. **Create the month's payroll**, then **add employees by name**. Selecting a name
   pulls that person's **basic straight from their salary record** (a new hire just
   needs their basic set once on the Employees page). "Add all active" bulk-adds.
3. **Review & recalculate** — a **PayrollPanda-style editable table** (one row per
   employee, ~10-at-a-glance), responsive with a sticky Employee/KWSP/SOCSO column and
   horizontal scroll on mobile. Type an **Allowance / OT hours+rate / Deduction** inline
   and it applies on **Save**; the **▾** row-expander holds Count-by-day, "include
   allowance/OT in statutory", deduction reason, age≥60, foreign, PCB override and notes.
   Part-timers show rate × hours. Basic is pulled from the salary record and entered inline
   for new staff (saved back). Add staff with a **type-to-search** box. EPF, SOCSO, EIS and
   PCB (employee *and* employer) derive on **Save & Recalculate**; a sticky bar shows live
   net payout; a per-run **Remarks** box passes notes to the approver.
   *Statutory wage = basic by default; tick include-allowance/OT (in ▾) to add it across all
   contributions.*
4. **Approval workflow** — Preparer *Sends for approval* (→ Pending); the **Approver can
   edit the run on the spot** while it's pending, then *Approves* (locks it — payslips
   final) or *Rejects* it back. Approved runs keep their figures and rates.
5. **Reviewer dashboard** — for the approver: cards + statutory split + net-payout-by-bank,
   a **glossary explaining every column** with the live rates, and an **expandable
   per-employee breakdown** — a stacked bar (net vs each deduction) plus a table where
   each figure carries its plain-English derivation.
6. **Output** — per-employee **payslip PDF** and a landscape **run summary PDF**.
7. **Settings (admin only)** — a platform-wide configuration tab with a **read-only
   statutory reference table** and every EPF/SOCSO/EIS rate + wage ceiling/threshold, PCB
   reliefs & rebate, company name, default working days, default OT rate, and default
   toggles. **Statutory rates are locked by default** — flip "Unlock rates to edit" to
   change them. **KWSP defaults off** (only staff you enable get EPF). All statutory calculations read
   these. Changes apply to any payroll **recalculated after saving**; approved runs keep the
   rates they were approved with. (Percentages are entered as whole numbers, e.g. `11` = 11%.)

## How pay is calculated

There is **one statutory wage** that EPF, SOCSO, EIS **and** PCB are all charged on,
and it is the **basic salary only by default**. Overtime and allowances are excluded
from every contribution unless you opt in per line with the **+Alw** / **+OT** ticks —
which apply **across EPF, SOCSO, EIS and tax at once**. Excluded OT/allowances are
still paid to the employee (they appear in gross and net); they just don't attract
statutory contributions.

| Item | Employee | Employer | Charged on the statutory wage |
|------|----------|----------|------|
| EPF / KWSP | 11% | 13% (≤RM5,000) / 12% (>RM5,000) | rounded up to next RM |
| SOCSO | 0.5% (Cat 1) | 1.75% (Cat 1) / 1.25% (Cat 2, age ≥60) | RM100-band table, ceiling RM6,000 |
| EIS | 0.2% | 0.2% | same table; skipped for age ≥60 & foreign |
| PCB | estimate / override | — | annualised MTD (YA2024/25); override wins |

**Statutory wage = basic + (allowance if +Alw) + (OT if +OT).** The employer 12%/13%
EPF split is decided by that same wage.

**Part-time:** the OT/hours rate is the **hourly rate on the employee record and is
read-only by default** — tick the small box beside it to adjust for that run.

Verified: RM5,000 basic (no allowance/OT) → EPF 550/650, SOCSO 24.75/86.65, EIS 9.90,
net RM4,305.35, employer cost RM5,746.55 (matches the May workbook exactly). Adding a
RM500 allowance + OT with **+Alw/+OT off** leaves every statutory figure unchanged;
ticking them lifts EPF, SOCSO, EIS and PCB together.

## Architecture

```
webapp/
  app/
    core/          # per-contribution calc modules, each with calculate + explain()
      kwsp.py  socso.py  eis.py  pcb.py  rates.py (RateConfig + rounding)
    statutory.py   # orchestrator: PayInputs -> PayResult (self-test: python -m app.statutory)
    models.py      # Settings, User, Employee, PayrollRun, Payslip (SQLAlchemy)
    store.py       # load platform Settings -> RateConfig; company-name cache
    payroll.py     # run generation + recompute (uses the configured rates)
    importer.py    # parse the registration-form spreadsheet
    security.py    # pbkdf2 password hashing + role guards
    pdf.py         # reportlab payslip + summary
    main.py        # FastAPI routes (incl. admin Settings)
  templates/       # Jinja2 + Tailwind (CDN)
  seed.py          # create tables, seed users, import employees
  run.sh
```

Config via env vars (see `app/config.py`): `PAYROLL_DB`, `PAYROLL_SECRET`,
`PAYROLL_COMPANY`, and the seed-account credentials. PCB is an MTD **estimate** —
enter the official LHDN e-PCB figure in the *PCB override* column when needed.
