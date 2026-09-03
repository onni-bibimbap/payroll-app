-- 0010_payroll_run_integrity.sql — payroll-run integrity fixes (audit
-- 2026-09-03: STAT-08/STAT-10/STAT-12/DL-08/DL-11/DL-15/GAP-03/GAP-10).
-- Additive and idempotent: guarded DDL, create-or-replace views.
begin;

-- ---------------------------------------------------------------------------
-- STAT-08: one payslip per employee per run. Dedupe first (keep the lowest
-- id — the original row), then enforce with a unique index so concurrent or
-- retried sync/add-slip requests can never double-pay anyone.
delete from payslips p
 using payslips q
 where p.run_id = q.run_id
   and p.employee_id = q.employee_id
   and p.id > q.id;

create unique index if not exists uq_payslip_run_employee
  on payslips (run_id, employee_id);

-- ---------------------------------------------------------------------------
-- DL-15: lifecycle timestamps become timestamptz. Existing naive values were
-- written by containers/DB sessions running UTC (python:3.12-slim default and
-- the Supabase default timezone), so they are interpreted as UTC. Guarded so
-- re-running never double-shifts values.
do $$
begin
  if exists (select 1 from information_schema.columns
              where table_name = 'payroll_runs' and column_name = 'created_at'
                and data_type = 'timestamp without time zone') then
    alter table payroll_runs
      alter column created_at   type timestamptz using created_at   at time zone 'UTC',
      alter column submitted_at type timestamptz using submitted_at at time zone 'UTC',
      alter column approved_at  type timestamptz using approved_at  at time zone 'UTC';
  end if;
  if exists (select 1 from information_schema.columns
              where table_name = 'users' and column_name = 'created_at'
                and data_type = 'timestamp without time zone') then
    alter table users
      alter column created_at type timestamptz using created_at at time zone 'UTC';
  end if;
  if exists (select 1 from information_schema.columns
              where table_name = 'employees' and column_name = 'created_at'
                and data_type = 'timestamp without time zone') then
    alter table employees
      alter column created_at type timestamptz using created_at at time zone 'UTC';
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- STAT-12/QT-05: the app now reads default_include_allowance/default_include_ot
-- when building payslips. Until now both settings were dead (behavior was
-- hardcoded "allowance in the statutory base, OT never"), so the stored value
-- carries no meaning — align it with the behavior every deployment already had.
update settings set default_include_allowance = true
 where default_include_allowance = false;

-- ---------------------------------------------------------------------------
-- payroll_master_view (GAP-03 / DL-08 / GAP-10):
--   * GAP-03 — a leaver stays visible until the export's period filter drops
--     them: the month containing last_working_day is their final-pay month.
--     The appended `leaving` column flags them for the clerk.
--   * DL-08 — pay figures come from the current pay_profiles row (integer
--     sen, the HR-approved master record) and fall back to the legacy
--     employees RM columns only when no profile row exists.
--   * GAP-10 — no more `basic_salary <= 4000` guess for ot_eligible: the
--     view exposes the HR-set value as-is; NULL means "not set" and the
--     appended `ot_eligible_unset` column flags it for review (the employee
--     is still included — never silently guessed at).
-- security_invoker keeps table RLS in force through the view (PG15+).
create or replace view payroll_master_view
  with (security_invoker = true) as
select
  e.id            as employee_id,
  e.emp_code      as employee_no,
  e.name          as full_name,
  e.nric          as identity_no,
  e.identity_type,
  e.employment_type,
  e.position,
  e.outlet,
  case when e.employment_type = 'part_time' then 'hourly' else 'monthly' end as pay_type,
  coalesce(pp.basic_salary_sen, (e.basic_salary * 100)::integer) as basic_salary_sen,
  coalesce(pp.hourly_rate_sen,  (e.hourly_rate  * 100)::integer) as hourly_rate_sen,
  pp.ot_eligible,
  pp.epf_no, pp.socso_no, pp.income_tax_no,
  ba.bank_name, ba.account_no,
  e.hire_date, e.last_working_day,
  (e.status <> 'active' or e.last_working_day is not null) as leaving,
  (pp.ot_eligible is null) as ot_eligible_unset
from employees e
left join lateral (
  select * from pay_profiles p
  where p.employee_id = e.id and p.effective_to is null
  order by p.effective_from desc limit 1
) pp on true
left join lateral (
  select * from bank_accounts b
  where b.employee_id = e.id and b.verified
  order by b.created_at desc limit 1
) ba on true
where (e.status = 'active'
       or (e.status in ('resigned','terminated','absconded')
           and e.last_working_day is not null))
  and not exists (select 1 from hr_review_flags f
                  where f.employee_id = e.id
                    and f.status = 'open' and f.severity = 'blocker')
  and exists (select 1 from bank_accounts b
              where b.employee_id = e.id and b.verified);

-- ---------------------------------------------------------------------------
-- payroll_movements_view (STAT-10 / DL-11): one row per movement EVENT, with
-- the dates scoped to that event, so the export's month filter picks exactly
-- the right rows and labels. Hire and leave in the same month collapse into
-- a single 'hire_and_leave' row; otherwise the hire month shows 'new_hire'
-- and the last-working-day month shows 'leaver' (previously every leaver
-- with a hire_date on record was mislabelled 'hire_and_leave').
create or replace view payroll_movements_view
  with (security_invoker = true) as
select
  e.id as employee_id, e.emp_code as employee_no, e.name as full_name,
  e.position, e.employment_type, e.outlet,
  e.hire_date,
  e.resignation_notice_date,
  case when e.last_working_day is not null
        and date_trunc('month', e.last_working_day) = date_trunc('month', e.hire_date)
       then e.last_working_day end as last_working_day,
  e.status,
  case when e.last_working_day is not null
        and date_trunc('month', e.last_working_day) = date_trunc('month', e.hire_date)
       then 'hire_and_leave' else 'new_hire' end as movement,
  (e.status in ('resigned','terminated','absconded')
   and e.last_working_day is not null
   and date_trunc('month', e.last_working_day) = date_trunc('month', e.hire_date)
  ) as final_pay_due
from employees e
where e.hire_date is not null
union all
select
  e.id, e.emp_code, e.name,
  e.position, e.employment_type, e.outlet,
  null::date as hire_date,
  e.resignation_notice_date,
  e.last_working_day,
  e.status,
  'leaver' as movement,
  (e.status in ('resigned','terminated','absconded')) as final_pay_due
from employees e
where e.last_working_day is not null
  and (e.hire_date is null
       or date_trunc('month', e.hire_date) <> date_trunc('month', e.last_working_day));

commit;
