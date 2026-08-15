-- 0008_pcb_optout.sql — per-employee opt-out of PCB (income tax deduction).
-- Defaults to true (PCB applies as before); uncheck on the employee record to
-- exempt someone entirely (e.g. non-resident on a different tax arrangement).
begin;
alter table employees
  add column if not exists pcb_enabled boolean not null default true;
alter table payslips
  add column if not exists pcb_enabled boolean not null default true;
commit;
