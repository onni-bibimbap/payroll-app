# Payroll 2.0 — FEAT register

Requirements per features_skills. Finding ids refer to `docs/audit-findings-2026-09-03.json`; domain rule ids (R/H) to `.claude/domain/`.

---

## FEAT-001 Statutory engine correctness
Problem      : The live app under-deducts SOCSO (Settings default 0.5% vs legislated 1.25%, R3), understates EPF above RM5,000 (RM20 bands used everywhere, R2), lacks the 100–140/200 SOCSO sub-bands, and has no age-60/foreign-worker EPF/SOCSO branches (GAP-01). The engine's only guard (a `__main__` self-test) fails and never runs.
Actor & role : system (compute); preparer/approver consume results.
Scope        : IN — rates single-source (rates.py → Settings), EPF band widths incl. >RM20k exact-wage rule, SOCSO/EIS low bands, EPF 60+/foreign branches, SOCSO foreign employer-only branch, over_60 derived at run-month end from DOB, pytest golden suite. OUT — PCB e-PCB parity (override stays authoritative), hardcoded SOCSO official table (OPEN-1).
Acceptance   :
- AC-1 Given RM5,000 statutory wage, when computed with current defaults, then SOCSO employee = 61.90, employer = 86.65, net = 4,268.20 (W1 revised).
- AC-2 Given RM5,050, when computed, then EPF = (561, 612) per Third-Schedule RM100 band.
- AC-3 Given wages at 30/50/70/100/140/200/6,000 boundaries, then band midpoints match the official assumed wages (H3, STAT-06 edges).
- AC-4 Given a Malaysian employee aged ≥60, then EPF employee 0%/employer 4%, SOCSO Category 2, no EIS; given a foreign worker, then EPF 2%/2%, SOCSO employer-only, no EIS [derived rates — human verification required before next real run].
- AC-5 Given an employee turning 60 mid-run-month, then Category 2 applies for that month; over_60/foreign are re-derived from the Employee row on every recompute.
- AC-6 A fresh Settings row always equals rates.py constants (test-enforced); migration 0009 corrects deployed 0.5% rows.
Data touched : settings (statutory rates — RESTRICTED-adjacent), payslips (recompute outputs).
Context      : payroll-engine. Dependencies: none (root of the PIPE).

## FEAT-002 Payroll-run integrity
Problem      : Runs pay from a bare `active` flag with unverified bank snapshots (DL-01/STAT-07); duplicate payslips possible (STAT-08); no proration (STAT-09); pending runs editable (STAT-14); negative/garbage money accepted (STAT-13); no audit on run lifecycle and self-approval allowed (SEC-06/DL-04); views misclassify movements and drop leavers before final pay (STAT-10/GAP-03).
Actor & role : preparer, approver.
Scope        : IN — population predicate (blockers/verified bank/period window), unique (run_id, employee_id), calendar-day proration (DEC-006), Pydantic validation, run audit rows + self-approval ban, view fixes (movements, leaver final month, ot_eligible no-guess, pay_profiles as pay source), LINDUNG PDF line, wire dead include-allowance/OT settings, timestamptz. OUT — integer-sen storage unification (P-3 proposal).
Acceptance   :
- AC-1 Given an employee with an open blocker flag or unverified bank, when a run syncs, then they are excluded and listed as "blocked from payroll".
- AC-2 Given two concurrent add-slip calls for one employee, then exactly one payslip exists (DB constraint).
- AC-3 Given a joiner on the 16th of a 30-day month with basic RM3,000, then prorated basic = 1,500.00 before statutory compute.
- AC-4 Given a pending run, when a preparer edits a slip, then 409; given the preparing user approving their own run, then 409.
- AC-5 Given a leaver with last_working_day in the run month, then they appear in the master view for that month (final pay) and in movements as "leaver".
- AC-6 Given a negative basic in run save, then 422, nothing persisted.
Data touched : payroll_runs, payslips, audit_log, views (RESTRICTED: bank, salary).
Context      : payroll-engine. Dependencies: FEAT-001 (compute), FEAT-003 (flag tables exist).

## FEAT-003 Platform security & HR/data flows
Problem      : Forgeable default session secret (SEC-01), views likely anon-readable (SEC-02), anonymous IDOR on document upload (SEC-04), preparer can bypass HR gates (SEC-05), silent import "fixes" (DL-06/GAP-02), sheet re-sync deletes verified rows (DL-05), approve 500s for applicants (DL-03), pool-leaked lifecycle bypass (DL-02), PII unmasked everywhere (SEC-14), no logging (QT-06).
Actor & role : all roles + anon applicant.
Scope        : IN — env-tiered secrets (prod fail-closed), session hardening, login rate limit + password change, upload token + magic bytes, RBAC tightening + audit, masking on lists, importer flags-not-fixes, resilient re-sync, security_invoker views, sequence-based codes, request-resubmission action, logging + health/version, create_all confined to SQLite tests. OUT — staff/manager role model (P-2), server-side session store (documented follow-up).
Acceptance   :
- AC-1 Given APP_ENV=production and a default/absent PAYROLL_SECRET or demo credentials, then the app refuses to boot.
- AC-2 Given 6 failed logins in the window, then 429 on the next attempt.
- AC-3 Given a document upload with a guessed reference number and no submission token, then 403/404; given a PNG-named executable, then 422 (magic bytes).
- AC-4 Given a preparer editing bank account or NRIC, then 403; the change is possible for admin and audited by field name.
- AC-5 Given a legacy import row with a corrupted bank cell, then the value is imported flagged `corrupted_bank_account` and never silently normalized; re-running the sync never deletes a verified bank row.
- AC-6 Given an employee list request, then NRIC/bank render masked (last 4); full values only on detail for approver/admin.
- AC-7 /api/health returns {status, version: "2.0.0", timestamp}.
Data touched : users, sessions, application_submissions, employee_documents, hr_review_flags, audit_log, views (RESTRICTED).
Context      : platform + employee-master. Dependencies: FEAT-002.

## FEAT-004 Infra compliance (infra_skills contract)
Problem      : Default boot targets prod Supabase and reseeds it (INFRA-01/02), no migrate service (INFRA-03), `make clean` wipes volumes casually (INFRA-05), no test/backup/restore targets (INFRA-06), no .env.example (INFRA-07), real PII in seeds/images/git (INFRA-08, SEC-09/10, GAP-07), root single-stage images (INFRA-10), no healthchecks (INFRA-09).
Actor & role : admin/operator.
Scope        : IN — local-db default with dev/test/prod profiles, migrate runner + tracking table, one-shot gated synthetic seeding, Makefile contract targets with guarded clean, .env.example, PII untracked from git index + .gitignore, non-root pinned multi-stage images, npm ci. OUT — git history rewrite (P-1, human-only), MinIO (no local blob store need yet — Supabase Storage external per §9).
Acceptance   :
- AC-1 `docker compose config` parses for dev/test/prod; default `make up` touches only the local db.
- AC-2 Fresh clone + `make up --wait`: migrations applied by the migrate service before backend start; `docker compose down && up` preserves data.
- AC-3 `make test` runs the backend suite in the test profile and propagates the exit code.
- AC-4 `make clean` without CONFIRM=wipe-data refuses; backup/restore round-trips on the test profile.
- AC-5 `git ls-files` shows no xlsx/db/sql data files; seed data contains no real names/accounts; backend image contains no xlsx.
Data touched : none at runtime (operational surface).
Context      : platform. Dependencies: independent (parallel).

## FEAT-005 Frontend & PWA
Problem      : PWA uninstallable (icons missing, FE-01), styling via runtime CDN (FE-02), offline queue drops documents (FE-03), demo creds shipped in the login bundle (FE-05), silent edit loss on submit/approve (FE-06), no 401 handling (FE-07), no route splitting (FE-09), no security headers (FE-11/SEC-12).
Actor & role : applicant (mobile), preparer, approver, admin.
Scope        : IN — real maskable icons, build-time Tailwind, IndexedDB document persistence + queue dedupe, cred removal, dirty-state guard, central 401 + loading/error states, money(0)=0.00, lazy routes, nginx headers/CSP, inline deactivate confirm, request-resubmission UI. OUT — full uiux-designer shell redesign (no template/shell changes in 2.0).
Acceptance   :
- AC-1 `npm run build` succeeds self-contained (no CDN scripts); manifest icons exist at declared paths.
- AC-2 Given a registration submitted offline with documents, when connectivity returns, then documents upload with the queued submission exactly once.
- AC-3 Given an expired session on any page, then redirect to /login with return path.
- AC-4 Given unsaved payroll cell edits, when Submit/Approve is clicked, then edits are saved first or the action is blocked visibly.
- AC-5 /register loads without the admin bundle chunk (verified in build output).
Data touched : none server-side; IndexedDB drafts (INTERNAL on-device).
Context      : ui. Dependencies: GAP-06 endpoint contract from FEAT-003.

## FEAT-006 Docs, traceability & release
Problem      : Docs assert what code contradicts (GAP-09); PRD deliverables unverified (GAP-08); RLS test proves little (GAP-04); no CHANGELOG/version.
Scope        : IN — README/README_PAYROLL corrections, retro discovery report, PRD-deliverable traceability table, expanded rls_test.sql, CHANGELOG.md + version 2.0.0, worklog session summary. OUT — deployment + Lighthouse run (needs a deployed origin — listed as post-release step).
Acceptance   : AC-1 every PRD deliverable maps to evidence or a logged descope DECISION; AC-2 docs contain no claim contradicted by code (spot-audited by judge); AC-3 CHANGELOG documents 2.0.0 breaking changes (compose default DB, seeding, auth hardening).
Context      : docs. Dependencies: all prior FEATs (written after their final state).
