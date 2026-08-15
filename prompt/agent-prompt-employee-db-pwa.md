# Agent Task: Employee Master Database (Supabase Postgres, PROD) + Employee Registration PWA

You are working on the production Supabase Postgres database for **Onni**, a Malaysian F&B business (outlets in KL/Setapak). Payroll is already handled by an external payroll app (PayrollPanda-style, Malaysian statutory compliant). Your job is to make this database the single source of truth for employee master data, import the legacy Google Form registrations, and build a PWA so new staff register directly into the system.

**Attached input:** `employee-registration-form.xlsx` — sheet `Form Responses 1`, the legacy Google Form export (~60 rows). Column mapping and known data problems are listed in Phase 3. Read the actual file yourself before importing; do not trust this prompt's row counts.

---

## Ground rules (read first, non-negotiable)

1. **This is PROD.** Never run destructive DDL (`DROP`, `TRUNCATE`, column type changes in place). All schema changes go through versioned migration files (`supabase/migrations/*.sql`), applied additively. Take a `pg_dump` backup before the first migration and before the data import. Wrap the import in a transaction. Every script must be idempotent (safe to re-run).
2. **Discover before you build.** Do not assume the `employees` table doesn't exist. Inspect first (Phase 0) and report findings to me before creating or altering anything.
3. **Do NOT rebuild payroll.** No EPF/SOCSO/EIS/PCB rate tables, no statutory calculation logic in this database or app. Statutory computation belongs to the payroll app. This DB only stores the employee master data the payroll app needs (identity, employment type, pay type, rates, bank, statutory registration numbers) and exposes it cleanly.
4. **PDPA (Malaysia) applies.** NRIC/passport numbers, bank accounts, and salary data are sensitive: restrict via RLS by role, never expose in logs or error messages, store document images in a **private** Supabase Storage bucket (signed URLs only), and record access/changes in an audit table.
5. **Identity numbers, bank accounts, and phone numbers are TEXT, always.** The legacy data was corrupted precisely because spreadsheets treated them as numbers (scientific notation, lost leading zeros). Enforce this in schema, validation, and the UI (`inputmode="numeric"` but string storage).
6. **Money in integer sen (MYR), dates as `date`, timestamps as `timestamptz` with `Asia/Kuala_Lumpur` awareness.**
7. **Nothing imported from the legacy file goes live silently.** Every imported record lands as `pending_review` with explicit flags for the HR admin to resolve. HR approval is the gate to `active`.

---

## Phase 0 — Discover and report

Connect to the Supabase project (ask me for the project ref / connection string if not configured). Then:

1. List all tables in `public` (and any custom schemas) via `information_schema.tables`. Check specifically whether any employee/staff/HR table already exists (`employees`, `staff`, `employee`, `users` with HR columns, etc.).
2. If found: dump its structure (`information_schema.columns`), row count, constraints, RLS policies, and any foreign keys pointing at it. Check whether the payroll app reads from it.
3. Report back: what exists, what's missing versus the target schema below, and your proposed migration plan (extend existing tables vs. create new). **Stop and wait for my confirmation before running migrations** if any existing table would be altered or if any existing table already contains employee rows.
4. If nothing exists, proceed with Phase 1 and note that in your report.

---

## Phase 1 — Target schema

Design for easy maintenance: small focused tables, one concern each, status history rather than overwritten fields, enums for controlled vocabularies. Use this as the baseline; adapt names to any existing conventions you found in Phase 0.

```sql
-- Controlled vocabularies
create type employment_status as enum
  ('applicant','pending_review','active','resigned','terminated','absconded','rejected');
create type employment_type as enum ('full_time','part_time','casual');
create type pay_type as enum ('monthly','hourly');
create type identity_type as enum ('nric','passport','unhcr','other');
create type doc_type as enum
  ('nric_front','nric_back','passport','work_permit','food_handler_cert',
   'typhoid_proof','education_transcript','profile_photo','other');
create type flag_status as enum ('open','resolved','dismissed');

-- Core identity + lifecycle (keep this aggregate small)
create table employees (
  id uuid primary key default gen_random_uuid(),
  employee_no text unique,                -- assigned on approval, e.g. ONNI-0001; NULL while applicant
  full_name text not null,
  email citext unique,
  phone text,                             -- normalized +60 format, TEXT
  residential_address text,
  date_of_birth date,
  nationality text,                       -- 'MY' default; infer non-MY from identity_type
  identity_type identity_type not null default 'nric',
  identity_no text,                       -- TEXT, raw as provided, no dashes stripped destructively
  status employment_status not null default 'applicant',  -- denormalized current status
  hire_date date,
  probation_end_date date,
  resignation_notice_date date,
  last_working_day date,                  -- authoritative for payroll cut-off
  outlet text,                            -- or FK to outlets table if multi-outlet
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Full status audit trail; a trigger keeps employees.status in sync with the latest row
create table employee_status_history (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  status employment_status not null,
  effective_date date not null,
  reason text,
  changed_by uuid,                        -- auth.users reference
  created_at timestamptz not null default now()
);

-- Position/job assignment (supports position changes over time)
create table employee_positions (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  position text not null,                 -- 'Waiter/Waitress','Chef','Kitchen Helper','Supervisor','Outlet Manager','Manager'
  employment_type employment_type not null,
  effective_from date not null,
  effective_to date                       -- NULL = current
);

-- Pay profile: exactly what payroll needs, nothing statutory computed here
create table pay_profiles (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  pay_type pay_type not null,
  basic_salary_sen integer,               -- monthly staff; MYR sen
  hourly_rate_sen integer,                -- hourly/part-time staff
  ot_eligible boolean,                    -- HR sets; statutory OT applies ≤ RM4,000/month basic — verify current rule, don't hardcode as logic
  epf_no text,
  socso_no text,
  income_tax_no text,
  effective_from date not null,
  effective_to date,
  check (
    (pay_type = 'monthly' and basic_salary_sen is not null) or
    (pay_type = 'hourly'  and hourly_rate_sen  is not null)
  )
);

-- Bank details, separated for tighter RLS; imported accounts are unverified until re-confirmed
create table bank_accounts (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  bank_name text not null,
  account_no text not null,               -- TEXT. Never numeric.
  account_holder_name text,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);

create table emergency_contacts (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  name text not null,
  phone text not null,
  relationship text
);

-- Documents live in a PRIVATE storage bucket; expiry powers compliance alerts
create table employee_documents (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  doc_type doc_type not null,
  storage_path text,                      -- Supabase Storage object path (private bucket 'employee-docs')
  source_url text,                        -- legacy Google Drive link from the import
  expiry_date date,                       -- typhoid proof, work permit, food handler cert
  verified boolean not null default false,
  uploaded_at timestamptz not null default now()
);

-- HR review queue: system- or human-raised issues on a record
create table hr_review_flags (
  id bigint generated always as identity primary key,
  employee_id uuid not null references employees(id),
  flag_type text not null,                -- see Phase 2 catalog
  severity text not null default 'warning',  -- 'info'|'warning'|'blocker'
  details jsonb,
  status flag_status not null default 'open',
  raised_by text not null default 'system',
  resolved_by uuid,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

-- Raw intake: every PWA submission and every legacy import row, verbatim
create table application_submissions (
  id bigint generated always as identity primary key,
  source text not null,                   -- 'google_form_import' | 'pwa'
  payload jsonb not null,
  employee_id uuid references employees(id),
  processed_at timestamptz,
  created_at timestamptz not null default now()
);

-- Audit: who changed what; store changed field NAMES, redact sensitive VALUES
create table audit_log (
  id bigint generated always as identity primary key,
  actor uuid,
  action text not null,
  entity text not null,
  entity_id text not null,
  changed_fields text[],
  created_at timestamptz not null default now()
);
```

Add indexes on every FK, on `employees(status)`, `employee_documents(expiry_date)`, and `hr_review_flags(status)`. Add `updated_at` triggers.

**RLS roles** (use Supabase auth + a `user_roles` table or JWT claim):
- `hr_admin` — full read/write everywhere.
- `manager` — read employees of their outlet; no bank_accounts, no identity document images, no pay_profiles.
- `staff` — read/update own row's contact fields and upload own documents only.
- `anon` / applicant — insert-only into `application_submissions` and upload into a quarantined storage path. No reads.

Enable RLS on every table. Deny by default.

---

## Phase 2 — Business logic

**Status lifecycle (enforce transitions in a trigger or edge function):**

```
applicant → pending_review → active → resigned | terminated | absconded
applicant → rejected
pending_review → rejected
```

- Moving to `active` requires: HR approval, `employee_no` assigned, a current `employee_positions` row, a `pay_profiles` row, a verified `bank_accounts` row, and no open `blocker` flags. Enforce this as the approval routine, not scattered UI checks.
- Moving to `resigned` requires `resignation_notice_date` and `last_working_day`. Terminated/absconded require `last_working_day`. History rows are append-only.
- Resigned/terminated employees are never deleted (payroll history, EA forms, audit). They simply drop out of the payroll view after `last_working_day`.

**HR review flag catalog** (raise automatically on import and on PWA submission):

| flag_type | trigger | severity |
|---|---|---|
| `invalid_identity_no` | NRIC not 12 digits after normalization / unparseable | blocker |
| `corrupted_bank_account` | account came from a numeric/scientific-notation cell, or fails basic length check | blocker |
| `work_authorization_review` | identity_type ≠ nric (passport/UNHCR) → HR must verify work permit (PLKS) before activation; note foreign workers have different EPF/SOCSO treatment and no EIS — handled in the payroll app, but HR must classify correctly here | blocker |
| `missing_document` | required doc absent for the role (food handler cert + typhoid proof are mandatory for all F&B food handlers under KKM rules) | warning→blocker at activation |
| `typhoid_expiring` / `typhoid_expired` | expiry within 30 days / past | warning / blocker |
| `work_permit_expiring` | permit expiry within 60 days | warning |
| `ambiguous_salary` | expected-salary text mixes hourly/monthly or unparseable | warning |
| `suspicious_dob` | DOB equals submission date, age < 15 or > 70, or invalid date | warning |
| `duplicate_suspect` | same identity_no, email, or phone as another record | blocker |
| `unverified_bank_account` | any imported bank account until employee/HR re-confirms | blocker for payroll inclusion |

Build a small scheduled job (Supabase cron / pg_cron) that raises the expiry flags daily.

**Expected salary vs. actual pay:** the form's "Expected Salary" is an applicant expectation. Store it in the submission payload only. The real `pay_profiles` row is created by HR at approval — parse the expectation as a suggestion (contains "hour" → hourly), never auto-commit it.

---

## Phase 3 — Import the legacy form data

Source: `employee-registration-form.xlsx`, sheet `Form Responses 1`. One header row, then one row per applicant. The form evolved over time, so later columns are empty for early rows — handle ragged rows.

**Column → target mapping:**

| Form column | Target | Handling |
|---|---|---|
| Timestamp | `application_submissions.created_at` | Excel serial datetime (base 1899-12-30), convert to timestamptz KL time |
| Name | `employees.full_name` | trim; some are non-Latin (Chinese) — keep as-is, UTF-8 |
| Email | `employees.email` | lowercase, validate; at least one row has a typo TLD (`.con`) — flag, don't reject |
| Residential Address | `employees.residential_address` | one row is the number `29.0` — flag `missing_document`-style data issue |
| Phone number | `employees.phone` | TEXT; some arrived as floats/scientific notation (`1.82999098E8`, `6.0179401854E10`) — restore digits, normalize to `+60…`, flag if leading digits are ambiguous |
| NRIC | `identity_no` + `identity_type` | See recovery rules below |
| Upload NRIC Front / Back | `employee_documents` (`nric_front`/`nric_back`) | store Drive URL in `source_url`; downloading from Drive needs auth — leave `storage_path` NULL and raise one `missing_document` info-flag noting migration of files is pending |
| DOB | `employees.date_of_birth` | Excel serial → date. Several rows have DOB = submission date or garbage (`2/22/0028`) → import NULL + `suspicious_dob` flag |
| Bank Name / Bank Account | `bank_accounts` | TEXT. At least one row has name/account **swapped** (account text in bank column). Scientific-notation accounts: restore digits but assume corruption — `verified=false` + `corrupted_bank_account` flag. Two rows have 15–16 digit values at float precision limits: always blocker-flag those |
| Job Position Applied For | `employee_positions.position` (proposed) | some rows list multiple ("Chef, Waiter / Waitress") — take first as proposed, keep full text in payload; "Part time" is an employment_type signal, not a position |
| Emergency Contact Name / Number / Relationship | `emergency_contacts` | early rows mixed phone into the name field — split heuristically, keep raw in payload |
| Working Experience / Education / Skills / Referral source / Comments | `application_submissions.payload` only | free text, no dedicated columns |
| Expected Salary | payload only | parse hourly-vs-monthly hint per Phase 2 |
| Employee ID | **ignore** | column contains phone fragments, names, and junk — regenerate `employee_no` properly at approval (`ONNI-` + zero-padded sequence) |
| Upload Khusus Makanan Certification | `employee_documents` (`food_handler_cert`) | Drive URL as above |
| Upload Typhoid Vaccination Proof + Expiry Date | `employee_documents` (`typhoid_proof`, `expiry_date`) | expiry is Excel serial → date; raise expiry flags |
| Education Transcript / Profile Picture | `employee_documents` | as above |

**NRIC / identity recovery rules:**
- Clean 12-digit values (with or without dashes) → `identity_type='nric'`, store dashless, keep original in payload.
- Scientific-notation values (`9.00305146347E11` etc.): expand to digits. If 12 digits and the `YYMMDD` prefix parses as a valid date → probable NRIC, import + `invalid_identity_no` info-flag "recovered from corrupted cell — verify". If 11 digits, try prepending `0` (lost leading zero) and re-validate; still flag.
- Alpha-prefixed values (`MI992757`, `MJ174523`, `C9146269`) → `identity_type='passport'` + `work_authorization_review` flag.
- `UNHCR` → `identity_type='unhcr'` + blocker `work_authorization_review`.
- Junk (`Malay`, `RM02V03-24-4`) → NULL + blocker `invalid_identity_no`.

**Import mechanics:** write the raw row into `application_submissions` first (verbatim JSON, `source='google_form_import'`), then create the `employees` record with `status='pending_review'` (append the status-history row), documents, contacts, and flags. Upsert keyed on (email, identity_no) so re-runs don't duplicate. Run duplicate detection across the batch (there are sibling applicants with related phones — flag, don't merge). Print a summary report: rows imported, per-flag counts, rows needing urgent HR attention.

---

## Phase 4 — Payroll integration surface

The payroll app already computes statutory contributions and pay runs; the clerk's monthly job must reduce to keying **part-time hours and OT hours** only. Provide:

1. **`payroll_master_view`** — one row per employee `active` on/before the period end and with `last_working_day` null or ≥ period start: `employee_no, full_name, identity_no, employment_type, position, outlet, pay_type, basic_salary_sen, hourly_rate_sen, ot_eligible, epf_no, socso_no, income_tax_no, bank_name, account_no (verified only), hire_date, last_working_day`. Grant to `hr_admin` only.
2. **`payroll_movements_view`** — for a given month: new hires (hire_date in month) and leavers (last_working_day in month, with final-pay reminder fields). This mirrors the "movements" step of a Malaysian payroll cycle.
3. A **CSV export** (edge function or simple authed endpoint) of both views formatted for the payroll app's import, so nothing is re-typed except variable hours.
4. Hard rule: an employee with any open `blocker` flag or unverified bank account is excluded from `payroll_master_view` and listed separately as "blocked from payroll — resolve flags."

---

## Phase 5 — Registration PWA + HR review dashboard

Build one web app (recommend Next.js + Supabase JS; TypeScript) with two faces:

**A. Public registration form (replaces the Google Form).** Mobile-first — applicants fill this on phones.
- Fields mirror the form columns above, plus explicit `identity_type` selection (NRIC / Passport / Other) which drives validation (NRIC: 12 digits with date-prefix check; passport: free format + nationality field).
- Bank account, NRIC, phone captured as strings with `inputmode` hints; live validation; bank name from a dropdown of Malaysian banks (Maybank, CIMB, Public Bank, RHB, Hong Leong, AmBank, Bank Islam, Bank Muamalat, Alliance, BSN, GXBank, Merchantrade, other) to end the free-text chaos.
- Document capture: camera/file upload for NRIC front/back, food handler (Khusus Makanan) cert, typhoid proof + expiry date picker, transcript, profile photo → private `employee-docs` bucket under a quarantined applicant path.
- Bilingual labels (English + Bahasa Malaysia) — the applicant pool answers in EN/BM/中文, so keep field labels simple and add BM helper text at minimum.
- Submission → `application_submissions` + `employees (status='applicant'→'pending_review')` + auto-flags; show a confirmation with reference number.

**B. HR admin dashboard (authed, `hr_admin` role).**
- Queue of `pending_review` records with their open flags; detail view showing submitted data, documents (signed URLs), and flag list.
- Actions: resolve/dismiss flags, request re-submission, edit fields (audited), **Approve** (runs the activation routine from Phase 2: assign employee_no, set position/employment_type, create pay_profile, verify bank, set hire date → `active`), or **Reject**.
- Compliance board: typhoid/work-permit expiries in the next 60 days; employees blocked from payroll.
- Resignation workflow: set notice date + last working day → status `resigned`, appears in `payroll_movements_view`.

**PWA requirements (hard requirements, verify with Lighthouse):**
- Web app manifest (name, icons incl. 192/512 maskable, standalone display, theme color), installable on Android/iOS.
- Service worker (next-pwa or Workbox): precache app shell, offline fallback page, and **offline-tolerant form** — persist draft answers locally (IndexedDB) and queue the submission (Background Sync or retry-on-reconnect) so a spotty-connection applicant never loses a half-filled form. Uploads retry when back online.
- HTTPS, responsive ≥ 360px width, passes Lighthouse PWA installability checks.

---

## Deliverables & acceptance criteria

1. Phase 0 discovery report (before any migration).
2. Migration files in `supabase/migrations/`, applied; RLS enabled and tested per role (include a short RLS test script proving anon cannot read employees and staff cannot read others' bank rows).
3. Import script + run report: all legacy rows in `pending_review`, zero silent data fixes — every recovery/guess has a flag.
4. `payroll_master_view` + `payroll_movements_view` + CSV export working; a resigned test employee with `last_working_day` last month does not appear for this month.
5. PWA deployed (Vercel or Supabase hosting), installable, offline form-draft verified by toggling airplane mode mid-form; HR dashboard approve → employee becomes `active` with employee_no and appears in the payroll view.
6. README: schema diagram, status lifecycle, flag catalog, how to run the import again, and the monthly payroll-export routine for the clerk.

## Ask me before starting

1. Supabase project ref + how you'll authenticate (access token / connection string), and whether a staging branch exists to rehearse migrations.
2. What Phase 0 found — and confirmation to proceed if anything exists already.
3. The outlet list (single outlet or multiple?), and who should hold `hr_admin`.
4. Auth for the PWA: public link for applicants (recommended) and email-OTP login for HR — confirm.
5. Whether the payroll app can import CSV, and if so its exact column format, so the export matches it byte-for-byte.
