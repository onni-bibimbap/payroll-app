-- 0002_employee_master.sql — employee master data: enums, extended employees
-- columns, and the satellite tables (status history, positions, pay profiles,
-- bank accounts, contacts, documents, review flags, submissions, audit log).
-- Additive only; idempotent.
begin;

create extension if not exists citext;

do $$ begin
  create type employment_status as enum
    ('applicant','pending_review','active','resigned','terminated','absconded','rejected');
exception when duplicate_object then null; end $$;

do $$ begin
  create type employment_type_t as enum ('full_time','part_time','casual');
exception when duplicate_object then null; end $$;

do $$ begin
  create type pay_type as enum ('monthly','hourly');
exception when duplicate_object then null; end $$;

do $$ begin
  create type identity_type as enum ('nric','passport','unhcr','other');
exception when duplicate_object then null; end $$;

do $$ begin
  create type doc_type as enum
    ('nric_front','nric_back','passport','work_permit','food_handler_cert',
     'typhoid_proof','education_transcript','profile_photo','other');
exception when duplicate_object then null; end $$;

do $$ begin
  create type flag_status as enum ('open','resolved','dismissed');
exception when duplicate_object then null; end $$;

-- Extend the existing payroll employees table (integer PK kept — the payroll
-- app's payslips FK on it). Master-data columns are additive.
alter table employees
  add column if not exists status employment_status not null default 'applicant',
  add column if not exists identity_type identity_type not null default 'nric',
  add column if not exists residential_address text,
  add column if not exists nationality text not null default 'MY',
  add column if not exists hire_date date,
  add column if not exists probation_end_date date,
  add column if not exists resignation_notice_date date,
  add column if not exists last_working_day date,
  add column if not exists outlet text not null default 'Setapak',
  add column if not exists updated_at timestamptz not null default now();

create index if not exists ix_employees_status on employees (status);

create table if not exists employee_status_history (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  status employment_status not null,
  effective_date date not null,
  reason text,
  changed_by text,
  created_at timestamptz not null default now()
);
create index if not exists ix_esh_employee on employee_status_history (employee_id);

create table if not exists employee_positions (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  position text not null,
  employment_type employment_type_t not null,
  effective_from date not null,
  effective_to date
);
create index if not exists ix_pos_employee on employee_positions (employee_id);

create table if not exists pay_profiles (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  pay_type pay_type not null,
  basic_salary_sen integer,
  hourly_rate_sen integer,
  ot_eligible boolean,
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
create index if not exists ix_payprof_employee on pay_profiles (employee_id);

create table if not exists bank_accounts (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  bank_name text not null,
  account_no text not null,               -- TEXT, never numeric
  account_holder_name text,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists ix_bank_employee on bank_accounts (employee_id);

create table if not exists emergency_contacts (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  name text not null,
  phone text not null,
  relationship text
);
create index if not exists ix_emerg_employee on emergency_contacts (employee_id);

create table if not exists employee_documents (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  doc_type doc_type not null,
  storage_path text,                      -- private bucket 'employee-docs'
  source_url text,                        -- legacy Google Drive link
  expiry_date date,
  verified boolean not null default false,
  uploaded_at timestamptz not null default now()
);
create index if not exists ix_docs_employee on employee_documents (employee_id);
create index if not exists ix_docs_expiry on employee_documents (expiry_date);

create table if not exists hr_review_flags (
  id bigint generated always as identity primary key,
  employee_id integer not null references employees(id),
  flag_type text not null,
  severity text not null default 'warning',   -- info|warning|blocker
  details jsonb,
  status flag_status not null default 'open',
  raised_by text not null default 'system',
  resolved_by text,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);
create index if not exists ix_flags_employee on hr_review_flags (employee_id);
create index if not exists ix_flags_status on hr_review_flags (status);

create table if not exists application_submissions (
  id bigint generated always as identity primary key,
  source text not null,                   -- 'google_form_import' | 'pwa'
  reference_no text unique,
  payload jsonb not null,
  employee_id integer references employees(id),
  processed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists ix_subs_employee on application_submissions (employee_id);

create table if not exists audit_log (
  id bigint generated always as identity primary key,
  actor text,
  action text not null,
  entity text not null,
  entity_id text not null,
  changed_fields text[],
  created_at timestamptz not null default now()
);

commit;
