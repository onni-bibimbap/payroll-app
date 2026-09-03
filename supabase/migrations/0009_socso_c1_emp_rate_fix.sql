-- 0009_socso_c1_emp_rate_fix.sql — correct the SOCSO Category 1 employee share.
-- The legislated rate is 1.25% (Invalidity 0.5% + Non-Employment Injury/SKBBK
-- 0.75%, PERKESO Employer Circular No. 2/2026, effective 1 June 2026), but the
-- Settings ORM default used to be the stale 0.5%, so rows created by the app
-- hold 0.005 and every Category 1 employee was under-deducted (audit STAT-01).
-- Idempotent: only rows still on the stale default are touched, so a
-- deliberate admin override of the rate survives re-runs.
begin;
update settings set socso_c1_emp = 0.0125 where socso_c1_emp = 0.005;
commit;
