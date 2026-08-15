-- 0004_views.sql — payroll integration surface.
-- payroll_master_view: employees payable for a period (filter in the query
-- with :period_start / :period_end; the view exposes the raw dates).
-- Blocker-flagged or unverified-bank employees are excluded and surfaced in
-- payroll_blocked_view instead.
begin;

create or replace view payroll_master_view as
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
  (e.basic_salary * 100)::integer as basic_salary_sen,
  (e.hourly_rate  * 100)::integer as hourly_rate_sen,
  coalesce(pp.ot_eligible, e.basic_salary <= 4000) as ot_eligible,
  pp.epf_no, pp.socso_no, pp.income_tax_no,
  ba.bank_name, ba.account_no,
  e.hire_date, e.last_working_day
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
where e.status = 'active'
  and not exists (select 1 from hr_review_flags f
                  where f.employee_id = e.id
                    and f.status = 'open' and f.severity = 'blocker')
  and exists (select 1 from bank_accounts b
              where b.employee_id = e.id and b.verified);

create or replace view payroll_blocked_view as
select
  e.id as employee_id, e.emp_code as employee_no, e.name as full_name,
  e.status,
  coalesce(array_agg(distinct f.flag_type)
           filter (where f.status = 'open' and f.severity = 'blocker'),
           '{}') as open_blockers,
  not exists (select 1 from bank_accounts b
              where b.employee_id = e.id and b.verified) as bank_unverified
from employees e
left join hr_review_flags f on f.employee_id = e.id
where e.status = 'active'
group by e.id
having count(*) filter (where f.status = 'open' and f.severity = 'blocker') > 0
    or not exists (select 1 from bank_accounts b
                   where b.employee_id = e.id and b.verified);

-- Movements for a month: pass year/month by filtering on the exposed dates.
create or replace view payroll_movements_view as
select
  e.id as employee_id, e.emp_code as employee_no, e.name as full_name,
  e.position, e.employment_type, e.outlet,
  e.hire_date, e.resignation_notice_date, e.last_working_day, e.status,
  case
    when e.hire_date is not null and e.last_working_day is not null then 'hire_and_leave'
    when e.last_working_day is not null then 'leaver'
    else 'new_hire'
  end as movement,
  (e.status in ('resigned','terminated','absconded')) as final_pay_due
from employees e
where e.hire_date is not null or e.last_working_day is not null;

commit;
