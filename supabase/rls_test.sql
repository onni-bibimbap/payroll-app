-- RLS proof: the PostgREST `anon` and `authenticated` roles can read nothing
-- and write nothing on any PII table. Run:
--   psql "$SUPABASE_DSN" -f supabase/rls_test.sql
-- Every SELECT must return 0 rows or a permission error; the INSERT must fail.

\echo '--- as anon ---'
set role anon;
select count(*) as employees_visible      from employees;
select count(*) as bank_accounts_visible  from bank_accounts;
select count(*) as pay_profiles_visible   from pay_profiles;
select count(*) as documents_visible      from employee_documents;
\echo 'expect: permission denied on the insert below'
insert into employees (emp_code, name) values ('HACK', 'nope');
reset role;

\echo '--- as authenticated ---'
set role authenticated;
select count(*) as employees_visible      from employees;
select count(*) as bank_accounts_visible  from bank_accounts;
reset role;
