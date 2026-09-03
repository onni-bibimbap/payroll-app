# Worklog — Onni Payroll (Payroll 2.0 revamp)

Mandatory log per CLAUDE.md Part 4. IDs: `ERR-` errors, `FIX-` fixes, `DEC-` decisions, `LL-` lessons.
Severity: 🔥 critical / 🟠 high / 🟡 medium / 🟢 low · Status: 🔴 open / 🟡 in progress / ✅ fixed / ⚪ won't fix.

---

## Errors

| ID | Date | File:Line | Type | Description | Severity | Status | Fix Ref |
|---|---|---|---|---|---|---|---|
| ERR-001 | 2026-09-03 14:42 | repo (git index) | security/PDPA | Real employee PII tracked in git: `*.xlsx` registration + monthly payroll files, `webapp/payroll.db`, `backups/*.sql`, `backups/payroll.db.20260802` | 🔥 | 🔴 | pending human DECISION (history rewrite is destructive) |
| ERR-002 | 2026-09-03 14:42 | docker-compose.yml:21 | security/infra | Default `DATABASE_URL` targets **prod Supabase**; local `db` service hidden behind `local-db` profile — trial builds run against production data | 🔥 | 🔴 | — |
| ERR-003 | 2026-09-03 14:43 | backend/ (repo-wide) | test gap | Zero automated tests for a money-computing system; statutory engine guarded only by an inline `__main__` self-test | 🔥 | 🔴 | — |

**ERR-001 context:** Found during ORCH-01 boot via `git ls-files`. Root cause: working data files committed alongside code since early commits. PDPA-sensitive (NRIC, bank accounts, salaries).
**ERR-002 context:** `docker-compose.yml` env default + `Makefile up` target. Root cause: convenience default pointing at prod. Violates security_skills TRIAL rule 1 (synthetic data only).
**ERR-003 context:** `find . -name "test_*"` empty; no pytest config, no pyproject.toml. Root cause: app grew from scripts without a test harness. Statutory calc regressed before (git 587d436 "Fix EPF and SOCSO…").


### Audit findings imported 2026-09-03 (evidence + proposed fixes: docs/audit-findings-2026-09-03.json, verified by 2 adversarial refuters each)

| ID | Date | File:Line | Type | Description | Severity | Status | Fix Ref |
|---|---|---|---|---|---|---|---|
| ERR-004 | 2026-09-03 | backend/app/models.py:37 | audit:STAT-01 | Live SOCSO employee rate is 0.5% — Settings default contradicts rates.py 1.25% (R3) | 🔥 | 🔴 | — |
| ERR-005 | 2026-09-03 | backend/app/statutory.py:116 | audit:STAT-02 | Statutory self-test fails against current rates and is the engine's only guard | 🟠 | 🔴 | — |
| ERR-006 | 2026-09-03 | backend/app/core/kwsp.py:16 | audit:STAT-03 | EPF uses RM20 bands for all wages; Third Schedule uses RM100 bands above RM5,000 | 🟠 | 🔴 | — |
| ERR-007 | 2026-09-03 | backend/app/payroll.py:63 | audit:STAT-05 | Age-60 cutoff evaluated on the 1st of the run month, never re-derived, silently false without DOB | 🟡 | 🔴 | — |
| ERR-008 | 2026-09-03 | backend/app/core/socso.py:33 | audit:STAT-06 | SOCSO/EIS band table missing the 100–140 and 140–200 sub-bands | 🟢 | 🔴 | — |
| ERR-009 | 2026-09-03 | backend/app/payroll.py:165 | audit:STAT-07 | Run population ignores blocker/verified-bank exclusion and the period window | 🟠 | 🔴 | — |
| ERR-010 | 2026-09-03 | backend/app/models.py:200 | audit:STAT-08 | No unique constraint on payslips (run_id, employee_id) — duplicate payslips possible | 🟡 | 🔴 | — |
| ERR-011 | 2026-09-03 | backend/app/payroll.py:69 | audit:STAT-09 | No proration for mid-month joiners/leavers; work_days_default never used in computation | 🟡 | 🔴 | — |
| ERR-012 | 2026-09-03 | supabase/migrations/0004_views.sql:66 | audit:STAT-10 | Movements view labels every leaver 'hire_and_leave' — classification ignores dates' month | 🟡 | 🔴 | — |
| ERR-013 | 2026-09-03 | backend/app/main.py:53 | audit:STAT-13 | Money inputs accept negatives and silently coerce garbage to 0 | 🟡 | 🔴 | — |
| ERR-014 | 2026-09-03 | backend/app/pdf.py:91 | audit:STAT-11 | Payslip PDF omits the LINDUNG deduction line while its total includes it | 🟢 | 🔴 | — |
| ERR-015 | 2026-09-03 | backend/app/payroll.py:74 | audit:STAT-12 | default_include_allowance / default_include_ot settings are dead — hardcoded True/False override them | 🟢 | 🔴 | — |
| ERR-016 | 2026-09-03 | backend/app/models.py:192 | audit:STAT-14 | Preparer can edit payslip figures while the run is pending approval | 🟢 | 🔴 | — |
| ERR-017 | 2026-09-03 | backend/app/models.py:15 | audit:STAT-15 | Payroll tables store Numeric(12,2) ringgit, contradicting the confirmed integer-sen storage rule | 🟢 | 🔴 | — |
| ERR-018 | 2026-09-03 | backend/app/config.py:16 | audit:SEC-01 | Forgeable sessions: hardcoded default session-signing secret with no production guard | 🔥 | 🔴 | — |
| ERR-019 | 2026-09-03 | supabase/migrations/0004_views.sql:8 | audit:SEC-02 | payroll_master_view (NRIC, bank account, salary) likely readable via Supabase anon key — RLS bypassed by security-definer views created after the revoke | 🔥 | 🔴 | — |
| ERR-020 | 2026-09-03 | backend/app/config.py:20 | audit:SEC-03 | Default weak credentials (admin/admin123) force-reset on every container start, no password change path, no login rate limiting | 🟠 | 🔴 | — |
| ERR-021 | 2026-09-03 | backend/app/registration.py:171 | audit:SEC-04 | Anonymous IDOR: predictable reference numbers let anyone overwrite documents of any employee, including active staff | 🟠 | 🔴 | — |
| ERR-022 | 2026-09-03 | backend/app/main.py:144 | audit:SEC-05 | Preparer can activate employees and change bank accounts, bypassing HR blocker/verified-bank gates, with zero audit | 🟠 | 🔴 | — |
| ERR-023 | 2026-09-03 | backend/app/main.py:357 | audit:SEC-06 | No audit trail for payroll-run lifecycle; runs are hard-deletable and admins can self-approve their own runs | 🟠 | 🔴 | — |
| ERR-024 | 2026-09-03 | backend/app/main.py:29 | audit:SEC-07 | Session cookie not hardened: no Secure flag, no server-side invalidation, no rotation on login | 🟡 | 🔴 | — |
| ERR-025 | 2026-09-03 | backend/app/hr.py:308 | audit:SEC-08 | Hardcoded real Google Sheet ID of a link-shared spreadsheet containing live applicant PII | 🟠 | 🔴 | — |
| ERR-026 | 2026-09-03 | backend/Dockerfile:9 | audit:SEC-09 | Real employee PII baked into the backend Docker image and hardcoded in seed.py source | 🟡 | 🔴 | — |
| ERR-027 | 2026-09-03 | backend/seed.py:116 | audit:SEC-10 | seed.py force-resets every employee's active flag from a hardcoded roster on every container restart, overriding HR lifecycle decisions | 🟠 | 🔴 | — |
| ERR-028 | 2026-09-03 | backend/app/registration.py:185 | audit:SEC-11 | Upload validation trusts client-declared Content-Type only — no magic-byte verification | 🟡 | 🔴 | — |
| ERR-029 | 2026-09-03 | ui/nginx.conf:1 | audit:SEC-12 | No security headers on the UI/nginx layer | 🟢 | 🔴 | — |
| ERR-030 | 2026-09-03 | backend/app/registration.py:62 | audit:SEC-13 | Public registration endpoint has no rate limiting/anti-automation and a racy emp_code generator | 🟢 | 🔴 | — |
| ERR-031 | 2026-09-03 | backend/app/hr.py:49 | audit:SEC-14 | PII masking helper exists but is never applied — full NRIC/bank numbers returned everywhere, including raw submission payloads | 🟢 | 🔴 | — |
| ERR-032 | 2026-09-03 | backend/Dockerfile:12 | audit:INFRA-01 | Every container boot re-runs seed.py against the default (prod Supabase) DB, resetting passwords and rewriting the employee roster | 🔥 | 🔴 | — |
| ERR-033 | 2026-09-03 | docker-compose.yml:4 | audit:INFRA-02 | Default `docker compose up` targets prod Supabase; db is behind an opt-in profile and the contract's dev/test/prod profiles do not exist | 🔥 | 🔴 | — |
| ERR-034 | 2026-09-03 | docker-compose.yml:1 | audit:INFRA-03 | No migrate service: supabase/migrations are applied manually with psql, and the local-db profile never applies them — backend startup crashes on `raise_expiry_flags()` | 🟠 | 🔴 | — |
| ERR-035 | 2026-09-03 | backend/app/database.py:35 | audit:INFRA-04 | App code creates tables: Base.metadata.create_all runs at every app startup and in seed.py, competing with supabase/migrations as schema source | 🟠 | 🔴 | — |
| ERR-036 | 2026-09-03 | Makefile:23 | audit:INFRA-05 | `make clean` runs `docker compose down -v`, casually wiping the pgdata volume — forbidden without a human DECISION | 🟠 | 🔴 | — |
| ERR-037 | 2026-09-03 | Makefile:1 | audit:INFRA-06 | Makefile lacks the contract targets: no `test`, `migrate`, `psql`, `backup`, `restore`; `up` lacks `--wait`; no backup story for a PROD-critical payroll DB | 🟠 | 🔴 | — |
| ERR-038 | 2026-09-03 | .env.example | audit:INFRA-07 | .env.example is absent although .env is required for the app to boot at all | 🟠 | 🔴 | — |
| ERR-039 | 2026-09-03 | backend/seed.py:29 | audit:INFRA-08 | Seeds are real production data, not synthetic: real-employee xlsx baked into the Docker image and real names hardcoded in seed.py; .gitignore does not exclude the PII files | 🟠 | 🔴 | — |
| ERR-040 | 2026-09-03 | docker-compose.yml:17 | audit:INFRA-09 | backend and ui services have no healthcheck, no restart policy, and no service_healthy dependencies; /api/health checks nothing | 🟡 | 🔴 | — |
| ERR-041 | 2026-09-03 | backend/Dockerfile:1 | audit:INFRA-10 | Both images run as root, backend image is single-stage, and no image is pinned by digest | 🟡 | 🔴 | — |
| ERR-042 | 2026-09-03 | backend/app/config.py:12 | audit:INFRA-11 | Silent SQLite fallback in config.py for a payroll API — data would land in an untracked local file / container layer | 🟡 | 🔴 | — |
| ERR-043 | 2026-09-03 | docker-compose.yml:22 | audit:INFRA-12 | Default secrets shipped in compose and config: forgeable session key and hardcoded DB password | 🟡 | 🔴 | — |
| ERR-044 | 2026-09-03 | ui/Dockerfile:3 | audit:INFRA-13 | ui image build ignores the committed package-lock.json (`npm install` on package.json only) — unreproducible dependency tree | 🟢 | 🔴 | — |
| ERR-045 | 2026-09-03 | backend/app/payroll.py:166 | audit:DL-01 | Payroll run path pays from the boolean `active` flag and unverified employees.bank_account, bypassing the entire verification/blocker model | 🔥 | 🔴 | — |
| ERR-046 | 2026-09-03 | backend/import_legacy_form.py:251 | audit:DL-02 | Session-scoped `set onni.bypass_lifecycle='1'` leaks into the connection pool, disabling status-transition enforcement for all later requests | 🔥 | 🔴 | — |
| ERR-047 | 2026-09-03 | backend/app/hr.py:183 | audit:DL-03 | HR approve accepts status 'applicant' but the DB trigger forbids applicant→active — activation 500s for every payroll-UI-created or seeded employee | 🟠 | 🔴 | — |
| ERR-048 | 2026-09-03 | backend/app/main.py:332 | audit:DL-04 | audit_log is written only by the HR router — zero audit on payroll §6 actions (run approve/reject, payslip edits, statutory settings, bank/salary edits, exports) | 🟠 | 🔴 | — |
| ERR-049 | 2026-09-03 | backend/import_legacy_form.py:355 | audit:DL-05 | Re-running the sheet sync deletes ALL satellite rows for matched employees — including HR-verified bank accounts, PWA-uploaded documents, and the append-only status history | 🟠 | 🔴 | — |
| ERR-050 | 2026-09-03 | backend/app/importer.py:95 | audit:DL-06 | Seed importer silently 'fixes' float-corrupted NRIC/bank cells, raises no flags, and activates employees — violating the zero-silent-fixes rule | 🟠 | 🔴 | — |
| ERR-051 | 2026-09-03 | backend/app/database.py:31 | audit:DL-07 | Two schema sources: startup create_all vs SQL migrations — fresh-Postgres boot fails on missing enum types, SQLite fallback lacks all 9 master tables | 🟡 | 🔴 | — |
| ERR-052 | 2026-09-03 | supabase/migrations/0004_views.sql:19 | audit:DL-08 | pay_profiles (integer sen, the declared master pay record) is write-only — payroll and the master CSV read salary from legacy employees.basic_salary instead | 🟡 | 🔴 | — |
| ERR-053 | 2026-09-03 | backend/app/models.py:15 | audit:DL-09 | Money-representation rule drift: RM NUMERIC(12,2) storage (float on SQLite) and float round-trips in the sen conversion on the approval path | 🟡 | 🔴 | — |
| ERR-054 | 2026-09-03 | supabase/migrations/0005_status_lifecycle.sql:85 | audit:DL-10 | raise_expiry_flags never escalates an expired typhoid cert to blocker while the earlier 'typhoid_expiring' warning is still open | 🟡 | 🔴 | — |
| ERR-055 | 2026-09-03 | supabase/migrations/0004_views.sql:66 | audit:DL-11 | payroll_movements_view classifies every leaver as 'hire_and_leave' — movement labels ignore the reporting period | 🟡 | 🔴 | — |
| ERR-056 | 2026-09-03 | backend/app/hr.py:309 | audit:DL-12 | Hardcoded live Google Sheet ID (source of real NRIC/bank data) committed as the in-code default | 🟡 | 🔴 | — |
| ERR-057 | 2026-09-03 | backend/app/registration.py:117 | audit:DL-13 | Concurrent registrations race on MAX()-based emp_code generation — duplicate ONNI codes crash the public submit endpoint | 🟢 | 🔴 | — |
| ERR-058 | 2026-09-03 | supabase/migrations/0002_employee_master.sql:151 | audit:DL-14 | audit_log has no indexes and no tamper protection; duplicate-detection columns unindexed | 🟢 | 🔴 | — |
| ERR-059 | 2026-09-03 | backend/app/main.py:327 | audit:DL-15 | Naive local timestamps and TIMESTAMP WITHOUT TIME ZONE on payroll approval fields, against the §8 timestamptz rule | 🟢 | 🔴 | — |
| ERR-060 | 2026-09-03 | backend/migrate_sqlite.py:30 | audit:DL-16 | migrate_sqlite.py wipe-and-replace fails or orphans master data on any target that has satellite rows | 🟢 | 🔴 | — |
| ERR-061 | 2026-09-03 | backend/app/statutory.py:116 | audit:QT-01 | Statutory engine's only regression guard (self-test) fails on current code and is never executed | 🔥 | 🔴 | — |
| ERR-062 | 2026-09-03 | backend/app/models.py:37 | audit:QT-02 | SOCSO employee rate duplicated in Settings ORM default (0.005) and diverged from engine constant (0.0125) — live compute path uses the stale rate | 🔥 | 🔴 | — |
| ERR-063 | 2026-09-03 | backend/app/statutory.py:113 | audit:QT-03 | No test suite exists anywhere in the live app — every §6 high-risk path is unguarded | 🟠 | 🔴 | — |
| ERR-064 | 2026-09-03 | Makefile:1 | audit:QT-04 | No pyproject.toml, lint/type/test config, dev dependencies, or CI — and ruff/mypy currently fail | 🟠 | 🔴 | — |
| ERR-065 | 2026-09-03 | backend/app/models.py:47 | audit:QT-05 | Dead settings: default_include_allowance / default_include_ot are stored and admin-editable but never read by any code path | 🟡 | 🔴 | — |
| ERR-066 | 2026-09-03 | backend/app/main.py:45 | audit:QT-06 | Zero logging in the entire backend; startup errors swallowed by silent broad excepts; print() used in operational scripts | 🟡 | 🔴 | — |
| ERR-067 | 2026-09-03 | backend/app/main.py:201 | audit:QT-07 | All mutation endpoints take untyped `body: dict = Body(...)` — no Pydantic validation on money-critical inputs, malformed input yields 500s | 🟡 | 🔴 | — |
| ERR-068 | 2026-09-03 | backend/app/hr.py:230 | audit:QT-08 | HR activation path converts money via float and coerces zero to NULL when writing pay_profiles sen values | 🟡 | 🔴 | — |
| ERR-069 | 2026-09-03 | build_payroll.py:105 | audit:QT-09 | Statutory engine exists in three diverged copies (backend/app, webapp/app, build_payroll.py) — divergence already produced conflicting rates | 🟠 | 🔴 | — |
| ERR-070 | 2026-09-03 | backend/app/main.py:66 | audit:QT-10 | Missing return-type annotations and docstrings across the public API surface; core calculators take untyped wage params | 🟢 | 🔴 | — |
| ERR-071 | 2026-09-03 | backend/app/hr.py:308 | audit:QT-11 | Request-time sys.path mutation and __import__ hack with a real hardcoded Google Sheet ID fallback | 🟢 | 🔴 | — |
| ERR-072 | 2026-09-03 | backend/app/registration.py:117 | audit:QT-12 | Employee-code generation via select max()+1 is race-prone and 500s on collision | 🟢 | 🔴 | — |
| ERR-073 | 2026-09-03 | backend/app/main.py:428 | audit:QT-13 | Module-level `assert` guards API/serializer field consistency — stripped under python -O; deprecated on_event startup hook | 🟢 | 🔴 | — |
| ERR-074 | 2026-09-03 | backend/app/main.py:65 | audit:QT-14 | Health endpoint returns only {ok: true} — no status/version/timestamp per the API convention | 🟢 | 🔴 | — |
| ERR-075 | 2026-09-03 | ui/vite.config.js:21 | audit:FE-01 | PWA manifest icons do not exist — installability (PRD Phase 5 hard requirement) fails | 🟠 | 🔴 | — |
| ERR-076 | 2026-09-03 | ui/index.html:7 | audit:FE-02 | Production styling depends on the Tailwind Play CDN — third-party runtime script, no SRI, breaks offline app shell | 🟡 | 🔴 | — |
| ERR-077 | 2026-09-03 | ui/src/pages/Register.jsx:149 | audit:FE-03 | Offline-queued registration silently drops all uploaded documents with no retry path | 🟡 | 🔴 | — |
| ERR-078 | 2026-09-03 | ui/src/pages/Register.jsx:148 | audit:FE-04 | Registration queue race can double-submit, and navigator.onLine misdetection skips queueing on flaky networks | 🟢 | 🔴 | — |
| ERR-079 | 2026-09-03 | ui/src/pages/Login.jsx:50 | audit:FE-05 | Demo credentials for all three roles are hardcoded into the Login page and ship in every build | 🟠 | 🔴 | — |
| ERR-080 | 2026-09-03 | ui/src/pages/PayrollRun.jsx:292 | audit:FE-06 | Payroll run: unsaved cell edits are silently excluded when submitting/approving — approved run can differ from what the preparer sees | 🟡 | 🔴 | — |
| ERR-081 | 2026-09-03 | ui/src/pages/HRQueue.jsx:10 | audit:FE-07 | No 401/session-expiry handling and several pages have no error or loading state — failures render a permanent blank page | 🟡 | 🔴 | — |
| ERR-082 | 2026-09-03 | ui/src/api.js:36 | audit:FE-08 | money() renders legitimate zero amounts as '-' on payslips and payroll tables | 🟢 | 🔴 | — |
| ERR-083 | 2026-09-03 | ui/src/App.jsx:4 | audit:FE-09 | No route-level code splitting — public /register applicants download the entire admin payroll bundle | 🟢 | 🔴 | — |
| ERR-084 | 2026-09-03 | ui/Dockerfile:3 | audit:FE-10 | UI Docker build ignores package-lock.json and uses npm install — unpinned, non-reproducible builds | 🟢 | 🔴 | — |
| ERR-085 | 2026-09-03 | ui/nginx.conf:2 | audit:FE-11 | UI served over plain HTTP with no security headers — service worker and install silently fail on any non-localhost deployment | 🟡 | 🔴 | — |
| ERR-086 | 2026-09-03 | ui/src/pages/Employees.jsx:122 | audit:FE-13 | One-click Deactivate on the employee list, adjacent to Edit, with no confirmation | 🟢 | 🔴 | — |
| ERR-087 | 2026-09-03 | backend/app/statutory.py:92 | audit:GAP-01 | Foreign-worker and age-60 statutory branches missing: SOCSO charges foreigners Category 1, EPF ignores the 2% foreign rule and the 60+ (0%/4%) rates | 🔥 | 🔴 | — |
| ERR-088 | 2026-09-03 | backend/app/importer.py:115 | audit:GAP-02 | Statutory nationality inferred from bank name ('merchantrade') and EPF silently disabled for all part-time staff | 🟠 | 🔴 | — |
| ERR-089 | 2026-09-03 | supabase/migrations/0004_views.sql:36 | audit:GAP-03 | Leavers vanish from payroll_master_view (and the master CSV the clerk pays from) the moment they resign — final month's pay is never exported | 🟠 | 🔴 | — |
| ERR-090 | 2026-09-03 | supabase/rls_test.sql:6 | audit:GAP-04 | rls_test.sql proves almost nothing: 4 of 14 tables, no views, no staff/manager cases, no assertions — yet README cites it as proof | 🟡 | 🔴 | — |
| ERR-091 | 2026-09-03 | backend/app/security.py:57 | audit:GAP-05 | PRD role model unimplemented: no staff self-service role, no outlet-scoped manager role, no per-role RLS policies | 🟡 | 🔴 | — |
| ERR-092 | 2026-09-03 | backend/app/hr.py:1 | audit:GAP-06 | HR 'request re-submission' action (PRD Phase 5B) does not exist in backend or UI | 🟡 | 🔴 | — |
| ERR-093 | 2026-09-03 | build_payroll.py:317 | audit:GAP-07 | Uninventoried PII surfaces: real names, full bank account numbers and salaries hardcoded in build_payroll.py, plus seven git-tracked data files no SEC/INFRA finding names | 🟠 | 🔴 | — |
| ERR-094 | 2026-09-03 | prompt/agent-prompt-employee-db-pwa.md:296 | audit:GAP-08 | PRD deliverables never produced or verified: Phase 0 discovery report absent, no deployment/Lighthouse/airplane-mode verification, daily expiry job a silent no-op without pg_cron | 🟡 | 🔴 | — |
| ERR-095 | 2026-09-03 | README.md:57 | audit:GAP-09 | Documentation asserts things the code contradicts; mandated worklog is skeletal | 🟢 | 🔴 | — |
| ERR-096 | 2026-09-03 | supabase/migrations/0004_views.sql:21 | audit:GAP-10 | OT-eligibility fallback hardcodes the RM4,000 rule as logic in payroll_master_view, which the PRD explicitly forbade | 🟢 | 🔴 | — |

## Fixes

| ID | Date | Error Ref | File(s) | Description | Verified |
|---|---|---|---|---|---|

## Decisions

| ID | Date | Topic | Decision | Rationale | Revisit If |
|---|---|---|---|---|---|
| DEC-001 | 2026-09-03 14:31 | Revamp scope | ORCH-01 claims whole repo; `webapp/` (legacy v1) is read-only reference, upgraded app is `backend/`+`ui/` | README declares webapp superseded; two live copies would double every fix | human wants webapp removed (propose-only) |
| DEC-002 | 2026-09-03 14:40 | Project binding | Generated `.claude/PROJECT_PROFILE.md` + 7 domain files from PRD/README/code before any fix work | Library gates (features/domain skills) require binding first; agents need §6/§7/§14 to judge risk | PRD changes |
| DEC-003 | 2026-09-03 14:45 | Audit before fixes | "Fix every single item" → enumerate first: [FANOUT x6] audit workflow with adversarial verify + completeness critic (run wf_aae45b23-c85) | Can't claim "every item" without a verified inventory; workflow_skills mandates fan-out + verification | audit misses surfaces (critic exists for this) |
| DEC-004 | 2026-09-03 15:12 | Fix decomposition | FEAT-001→003 sequential backend pipeline (shared files), FEAT-004/005 parallel (disjoint files), FEAT-006 docs last; workflow wf_f7a0e62d-cf4 | File-collision analysis: main.py/models.py touched by 3 packages → PIPE; ui//compose touch nothing shared → FANOUT | a worker reports a cross-boundary need |
| DEC-005 | 2026-09-03 15:12 | Payroll money storage | Keep NUMERIC(12,2) RM in payroll tables for 2.0; drop the SQLite float path instead; integer-sen unification proposed as P-3 (PENDING-APPROVAL) | NUMERIC is exact on Postgres; sen migration touches every serializer + the whole UI — too much blast radius unaudited | human approves P-3 |
| DEC-006 | 2026-09-03 15:12 | Proration policy | Mid-month joiners/leavers: monthly basic × calendar days employed ÷ calendar days in month, rounded to sen, preparer-overridable | Common Malaysian Employment Act practice; simple, explainable on the payslip | company policy differs (human review) |
| DEC-007 | 2026-09-03 15:12 | Self-approval | The user who prepared a run cannot approve it, admins included | Four-eyes on money release (§6 path 2) | human waives for single-operator periods |
| DEC-008 | 2026-09-03 15:13 | API envelope | Global CLAUDE.md Part 3 response envelope NOT retrofitted onto the existing JSON API in 2.0 (only /api/health upgraded) | Envelope change breaks every UI call site for zero user value in this release; risk outweighs conformance | human asks for envelope conformance |
| DEC-009 | 2026-09-03 15:13 | Descoped from 2.0 | Staff/manager self-service roles (GAP-05→P-2), git history rewrite (P-1), legacy copy deletion (P-4), server-side session store, deployed-origin Lighthouse run | New scope / destructive / needs deployment — all propose-only or human-gated | human DECISIONs on P-1..P-4 |

## Lessons learned

| ID | Date | Context | Lesson | Apply next time |
|---|---|---|---|---|

---

## Session log

### 2026-09-03 — Session 1: Payroll 2.0 revamp kickoff (in progress)
Objectives: bind project, audit everything, fix every verified item, pass 3 gates (features/performance/security), deliver Payroll 2.0.
Progress notes appended as work completes.
