-- 0003_rls.sql — enable RLS, deny by default.
-- The FastAPI backend connects as the table owner (postgres) and is exempt;
-- role enforcement (hr_admin / manager / staff / anon) happens in the API
-- layer. RLS here locks out Supabase PostgREST anon/authenticated keys so no
-- PII is reachable without going through the backend.
begin;

alter table employees                 enable row level security;
alter table users                     enable row level security;
alter table settings                  enable row level security;
alter table payroll_runs              enable row level security;
alter table payslips                  enable row level security;
alter table employee_status_history   enable row level security;
alter table employee_positions        enable row level security;
alter table pay_profiles              enable row level security;
alter table bank_accounts             enable row level security;
alter table emergency_contacts        enable row level security;
alter table employee_documents        enable row level security;
alter table hr_review_flags           enable row level security;
alter table application_submissions   enable row level security;
alter table audit_log                 enable row level security;

-- No policies are created: anon/authenticated get zero rows, zero writes.
-- Revoke the default PostgREST grants for good measure.
revoke all on all tables in schema public from anon, authenticated;

commit;
