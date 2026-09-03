# Compliance — _shared
Sources: PRD ground rules, README.md, `core/*` docstrings · Last verified: 2026-09-03

## Regimes
- [confirmed] **PDPA (Malaysia)** — NRIC/passport, bank accounts, salary are sensitive: role-restricted, never in logs/error messages, documents in a private bucket with signed URLs, access/changes audited.
- [confirmed] **LHDN / KWSP / PERKESO** — statutory rates and tables per `payroll/statutory.md`; PCB engine output is an estimate, e-PCB override is authoritative.
- [confirmed] **KKM** — food-handler cert + typhoid proof mandatory for F&B food handlers; expiry tracking with daily flags.

## Retention & deletion
- [confirmed] Employees are never deleted (payroll history, EA forms, audit) — lifecycle by status only.
- [derived] Payroll/tax records retained ≥ 7 years (standard LHDN requirement) — no automated deletion job exists or is currently needed; revisit before any purge feature.

## Jurisdiction & time
- [confirmed] Malaysia; timezone `Asia/Kuala_Lumpur`; money MYR integer sen; dates as `date`, timestamps `timestamptz`.

## Unresolved
- OPEN-1 Real employee data is committed to git (xlsx/db/sql backups) — PDPA exposure. PARTIAL (FEAT-004, 2026-09-03): all PII/data files removed from the git index (`git rm --cached`; files stay on disk) and `.gitignore` now blocks `*.xlsx`/`*.db`/`backups/`/`2607/`; `seed.py` and `build_payroll.py` rosters replaced with synthetic data. The **history rewrite** (`git filter-repo`) is still pending a human DECISION — every past commit still contains the files.
- OPEN-2 Trial builds run against prod Supabase by default — RESOLVED (FEAT-004, 2026-09-03): `dev`/`test` compose profiles are hardcoded to the local/ephemeral db; Supabase requires the explicit `prod` profile plus `DATABASE_URL` in `.env` (no in-file default).
