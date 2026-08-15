-- 0007_lindung_24jam.sql — placeholder opt-in for the "LINDUNG 24Jam" SOCSO
-- scheme. Rate is not yet confirmed with the official PERKESO circular, so it
-- defaults to RM0 in settings and does nothing until both the employee opts
-- in and the rate is set.
begin;
alter table employees
  add column if not exists lindung_optin boolean not null default false;
alter table payslips
  add column if not exists lindung_optin boolean not null default false;
alter table payslips
  add column if not exists lindung_amount numeric(12,2) not null default 0;
alter table settings
  add column if not exists lindung_24jam_rate numeric(12,2) not null default 0;
commit;
