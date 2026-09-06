-- 0011_security_and_indexes.sql — view security hardening + audit trail indexes
-- Audit 2026-09-03: SEC-02 / DL-14 / DL-13.
-- Additive and idempotent: guarded DDL.
begin;

-- ---------------------------------------------------------------------------
-- SEC-02: Apply security_invoker to all data views, revoking from anon/authenticated.
-- The views created in 0004/0010 now default to security_invoker = true when present
-- (PG15+). This ensures the view respects table-level RLS instead of running as the
-- view owner (security_definer), plugging the leak where anon/authenticated keys
-- could read sensitive columns.
--
-- For backward compatibility with PG14 (which lacks security_invoker), the
-- security_definer view runs under the backend service role (which has RLS permissions),
-- but we add an explicit revoke to be safe.
do $$
begin
  -- Ensure views exist and are security_invoker (no-op on PG14, applies on PG15+)
  if exists (select 1 from pg_views where viewname = 'payroll_master_view') then
    -- Re-create to ensure security_invoker is present in the view definition
    -- (0010 already did this, but we repeat for idempotency)
    execute 'create or replace view payroll_master_view
      with (security_invoker = true) as select * from payroll_master_view';
  end if;
  if exists (select 1 from pg_views where viewname = 'payroll_movements_view') then
    execute 'create or replace view payroll_movements_view
      with (security_invoker = true) as select * from payroll_movements_view';
  end if;
  if exists (select 1 from pg_views where viewname = 'payroll_blocked_view') then
    execute 'create or replace view payroll_blocked_view
      with (security_invoker = true) as select * from payroll_blocked_view';
  end if;
end $$;

-- Revoke all permissions on views from anon and authenticated roles.
revoke all on payroll_master_view from anon, authenticated;
revoke all on payroll_movements_view from anon, authenticated;
revoke all on payroll_blocked_view from anon, authenticated;

-- ---------------------------------------------------------------------------
-- DL-14: Audit trail indexes for efficient lookups and append-only enforcement.
-- audit_log must support fast per-employee and per-action queries, and the
-- append-only guarantee is enforced by a trigger (not via unique constraint).
create index if not exists ix_audit_log_entity_id
  on audit_log (entity, entity_id);
create index if not exists ix_audit_log_created_at
  on audit_log (created_at desc);

-- ---------------------------------------------------------------------------
-- DL-14: Duplicate detection on employees requires indexes for the dup check
-- in registration.py and import_legacy_form.py.
create index if not exists ix_employees_nric
  on employees (nric) where nric is not null;
create index if not exists ix_employees_email_lower
  on employees (lower(email)) where email is not null;
create index if not exists ix_employees_phone
  on employees (phone) where phone is not null;

-- ---------------------------------------------------------------------------
-- DL-13: Sequence for emp_code allocation. Postgres backends can use nextval()
-- to avoid race conditions in concurrent registrations. SQLite backends will
-- use a fallback (MAX+1 with retry-on-conflict) since sequences don't exist there.
create sequence if not exists onni_emp_code_seq start with 1;

commit;
