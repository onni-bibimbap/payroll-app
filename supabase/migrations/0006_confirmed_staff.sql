-- 0006_confirmed_staff.sql — permanent/confirmed flag for staff who passed
-- probation. Confirmed staff get EPF + SOCSO/EIS enabled (PCB is computed in
-- the payroll run from chargeable income; no per-employee toggle exists).
begin;
alter table employees
  add column if not exists is_confirmed boolean not null default false;
commit;
