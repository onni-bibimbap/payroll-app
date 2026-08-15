-- 0005_status_lifecycle.sql — status transition guard, status sync trigger,
-- updated_at trigger, and the daily document-expiry flag job (pg_cron when
-- available; the backend also runs the same function daily as a fallback).
begin;

-- updated_at maintenance
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists trg_employees_updated_at on employees;
create trigger trg_employees_updated_at
  before update on employees
  for each row execute function set_updated_at();

-- Allowed lifecycle transitions
create or replace function check_status_transition() returns trigger
language plpgsql as $$
declare ok boolean;
begin
  if old.status = new.status then return new; end if;
  -- data-migration bypass: set by the import scripts only
  if current_setting('onni.bypass_lifecycle', true) = '1' then
    new.active := (new.status = 'active');
    return new;
  end if;
  ok := case old.status
    when 'applicant'      then new.status in ('pending_review','rejected')
    when 'pending_review' then new.status in ('active','rejected')
    when 'active'         then new.status in ('resigned','terminated','absconded')
    else false
  end;
  if not ok then
    raise exception 'invalid status transition % -> %', old.status, new.status;
  end if;
  if new.status = 'resigned'
     and (new.resignation_notice_date is null or new.last_working_day is null) then
    raise exception 'resigned requires resignation_notice_date and last_working_day';
  end if;
  if new.status in ('terminated','absconded') and new.last_working_day is null then
    raise exception '% requires last_working_day', new.status;
  end if;
  -- keep the payroll app's boolean in sync
  new.active := (new.status = 'active');
  return new;
end $$;

drop trigger if exists trg_employees_status on employees;
create trigger trg_employees_status
  before update of status on employees
  for each row execute function check_status_transition();

-- Append-only history keeps employees.status as the latest row
create or replace function apply_status_history() returns trigger
language plpgsql as $$
begin
  update employees set status = new.status where id = new.employee_id;
  return new;
end $$;

drop trigger if exists trg_status_history on employee_status_history;
create trigger trg_status_history
  after insert on employee_status_history
  for each row execute function apply_status_history();

-- Daily expiry flags (typhoid 30d, work permit 60d). Idempotent per day.
create or replace function raise_expiry_flags() returns integer
language plpgsql as $$
declare n integer := 0;
begin
  insert into hr_review_flags (employee_id, flag_type, severity, details)
  select d.employee_id,
         case when d.expiry_date < current_date then 'typhoid_expired'
              else 'typhoid_expiring' end,
         case when d.expiry_date < current_date then 'blocker' else 'warning' end,
         jsonb_build_object('doc_id', d.id, 'expiry_date', d.expiry_date)
  from employee_documents d
  join employees e on e.id = d.employee_id and e.status = 'active'
  where d.doc_type = 'typhoid_proof'
    and d.expiry_date is not null
    and d.expiry_date < current_date + interval '30 days'
    and not exists (select 1 from hr_review_flags f
                    where f.employee_id = d.employee_id and f.status = 'open'
                      and f.flag_type in ('typhoid_expiring','typhoid_expired')
                      and (f.details->>'doc_id')::bigint = d.id);
  get diagnostics n = row_count;

  insert into hr_review_flags (employee_id, flag_type, severity, details)
  select d.employee_id, 'work_permit_expiring', 'warning',
         jsonb_build_object('doc_id', d.id, 'expiry_date', d.expiry_date)
  from employee_documents d
  join employees e on e.id = d.employee_id and e.status = 'active'
  where d.doc_type = 'work_permit'
    and d.expiry_date is not null
    and d.expiry_date < current_date + interval '60 days'
    and not exists (select 1 from hr_review_flags f
                    where f.employee_id = d.employee_id and f.status = 'open'
                      and f.flag_type = 'work_permit_expiring'
                      and (f.details->>'doc_id')::bigint = d.id);
  return n;
end $$;

-- Schedule daily at 01:00 KL (17:00 UTC) if pg_cron is installed.
do $$ begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('raise-expiry-flags', '0 17 * * *',
                          'select raise_expiry_flags()');
  end if;
end $$;

commit;
