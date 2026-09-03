# PROJECT_PROFILE — Onni Payroll (Payroll 2.0)

Generated 2026-09-03 by ORCH-01 from: `prompt/agent-prompt-employee-db-pwa.md` (PRD), `README.md`, `README_PAYROLL.md`, code (`backend/app/**`), `supabase/migrations/*.sql`. Depth lives in `.claude/domain/` — this file is the index.

## §1 Product & core guarantee
Onni Payroll: payroll + employee-master system for **Onni**, a Malaysian F&B business (KL/Setapak outlets). Three faces: (a) payroll engine — Malaysian statutory-compliant pay runs and payslips; (b) employee master DB — single source of truth for employee data, HR review/approval; (c) public registration PWA replacing a Google Form.
**Core guarantee: every active employee is paid the correct net salary with correct EPF/SOCSO/EIS/PCB contributions, from verified master data, with an auditable trail.** A wrong statutory figure or a payment to an unverified bank account violates the guarantee.
Critical journeys: register → HR review → approve → active; create payroll run → compute → approve → payslip PDF; monthly master/movements CSV export.

## §2 Users & volume
~60–200 employees, single company, a handful of HR/admin users, public applicants on mobile. Low traffic; correctness ≫ throughput.

## §3 Ubiquitous language
See `.claude/domain/_shared/glossary.md`. Key terms: statutory wage, EPF/KWSP, SOCSO/PERKESO Category 1/2, EIS/SIP, PCB/MTD, payroll run, movements, blocker flag, activation. Money is **integer sen** in the DB, `Decimal` in the engine; never floats for storage or math.

## §4 Roles
| Role | Face | Notes |
|---|---|---|
| `preparer` | payroll UI | creates/edits payroll runs |
| `approver` | payroll UI + HR | approves runs; HR review queue |
| `admin` | everything | settings, users, rates |
| applicant (anon) | public PWA `/register` | insert-only submission |
| `system` | jobs | expiry flags, seeds |
Tenancy: single tenant (one company). Isolation boundary = role, not tenant.

## §5 Architecture stance & contexts
S1 modular monolith (Scale Ladder): FastAPI backend (`backend/app`) + React/Vite SPA (`ui/`) + PostgreSQL (Supabase prod or local compose db). Bounded contexts: **payroll-engine** (`statutory.py`, `core/`, `payroll.py`, `pdf.py`, `payroll_export.py`), **employee-master** (`hr.py`, `registration.py`, `importer.py`, migrations), **platform** (auth `security.py`, `main.py`, `store.py`, `storage.py`). `webapp/` is the retired v1 monolith — reference only, never extended. RESTRICTED data travels as references, never payloads, in logs/URLs/errors.

## §6 High-risk paths
1. Statutory computation (`backend/app/core/*`, `statutory.py`) — money correctness.
2. Payroll run create/approve + payslip PDF — irreversible, externally visible.
3. Employee activation (approve → `active`) — gates who gets paid.
4. Payroll master/movements CSV export — feeds actual bank payments.
5. Bank-account verification; NRIC/identity handling.
6. Auth/RBAC (`security.py`) and anything touching §7 data.
All §6 work takes STRONG judge tier and [EVAL] verification.

## §7 Sensitive data
RESTRICTED: NRIC/passport/UNHCR numbers, bank account numbers, salary/pay profiles, PCB/tax numbers, payslips. INTERNAL: phone, address, DOB, emergency contacts, documents (photos, certs). PUBLIC: outlet names, position titles.
**Known violation (open):** real employee xlsx/DB/SQL-backup files are git-tracked (see SECURITY-FLAG in orchestration log).

## §8 Compliance
PDPA (Malaysia) for PII; LHDN/KWSP/PERKESO statutory rules; KKM food-handler requirements (typhoid cert). Retention: payroll & employee records kept ≥ 7 years (LHDN); nobody deleted, lifecycle via status. Timezone `Asia/Kuala_Lumpur`; timestamps `timestamptz`.

## §9 Integrations
Supabase (prod Postgres via `DATABASE_URL`; Storage bucket `employee-docs`, signed URLs, service key). Legacy Google Form xlsx import (`import_legacy_form.py`). No inbound webhooks. Outbound: none (CSV export is manual download).

## §10 Stack & datastore
Python 3.11+ FastAPI, SQLAlchemy, ReportLab (PDF), openpyxl; React 18 + Vite + nginx; PostgreSQL 16 (compose named volume `pgdata`) / Supabase prod. Migrations: `supabase/migrations/*.sql` additive, applied with psql (no migrate service yet — gap). Local dev fallback SQLite (allowed only for dev convenience; flagged).

## §11 Performance budgets
performance_skills defaults apply. Overrides: payslip PDF ≤ 3 s/employee; monthly run compute ≤ 10 s for 200 employees; CSV export ≤ 10 s. UI bundle default budget applies.

## §12 Peak events & critical windows
Month-end payroll window (25th–1st): payroll run + exports + payslips. Never run migrations or restructures inside it. Peak concurrency trivial (<10 users), so 2× peak load test is a formality — but run compute must be verified at 200 employees.

## §13 Criticality tier
**PROD-critical** (money + PDPA data). Current deployment posture is trial-grade; any real release must pass the security_skills PROD hard gate. Data currently in repo is REAL, not synthetic — treat repo as containing production data until remediated.

## §14 Domain rules (index — bodies in `.claude/domain/`)
- `payroll/statutory.md` — EPF band+rounding, SOCSO/EIS band-midpoint tables & ceiling, Category 1/2, foreign-worker EIS exclusion, PCB estimate vs e-PCB override, statutory-wage composition (allowance/OT opt-in).
- `payroll/runs-and-exports.md` — run lifecycle, blocked-employee exclusion, movements, integer-sen conversions.
- `employee-master/lifecycle.md` — status machine, activation preconditions, flag catalog, TEXT-always identity/bank/phone.
- Hazards: spreadsheet numeric corruption of NRIC/bank/phone; float money; band edge cases (RM30/50/70/…); age-60 and foreign-worker branches; month-boundary joins/leavers.

## §15 Judge tiers
STRONG: anything in §6, §7 handling, security review, statutory changes, exports. FAST: UI copy, docs, routine refactors, non-money endpoints. Escalation FAST → STRONG → human.

## §16 Project skills & references
Skills: the six library skills (`.claude/skills/*`). Agents: orchestrator, llm-judge, uiux-designer. Rubrics: `.claude/evaluation/rubrics/*`. No extra project skills yet.
