# Employee lifecycle & flags — employee-master
Sources: PRD Phases 1–3, `README.md`, migrations `0002,0003,0005,0006`, `backend/app/{hr,registration,importer}.py` (skimmed) · Last verified: 2026-09-03 · Owner role: approver/admin

## Rules
- R1 [confirmed] Status machine: `applicant → pending_review → active → resigned|terminated|absconded`; `applicant|pending_review → rejected`. Enforced by DB trigger `check_status_transition`. History append-only; **nobody is ever deleted**.
- R2 [confirmed] Activation (`POST /api/hr/employees/{id}/approve`) is the **only** path to `active` and requires: no open blocker flags, a verified bank account, a position, pay details; writes `employee_positions`, `pay_profiles`, status history, assigns `employee_no` (ONNI-… sequence).
- R3 [confirmed] Resignation requires notice date + last working day; terminated/absconded require last working day.
- R4 [confirmed] NRIC/passport, bank account, phone are **TEXT always** — spreadsheet numeric cells corrupted legacy data (scientific notation, lost leading zeros). Enforce in schema, validation, UI.
- R5 [confirmed] Flag catalog (severity, triggers) per README table: `invalid_identity_no`, `corrupted_bank_account`, `unverified_bank_account`, `work_authorization_review`, `missing_document`, `typhoid_expiring/expired`, `work_permit_expiring`, `ambiguous_salary`, `suspicious_dob`, `duplicate_suspect`. Imported/self-submitted bank accounts are blocker-flagged until HR verifies.
- R6 [confirmed] Legacy import is idempotent (keyed `application_submissions.reference_no = GF-<row>`); every recovery/guess raises a flag — **zero silent fixes**.
- R7 [confirmed] Expected salary from the form is a suggestion stored in payload only; the real `pay_profiles` row is created by HR at approval.

## Hazards
- H1 [confirmed] NRIC recovery: scientific-notation cells expand to 11–12 digits; 11 digits may mean a lost leading zero; YYMMDD prefix must parse as a date. Alpha-prefixed → passport; `UNHCR` → unhcr type + blocker.
- H2 [confirmed] Bank name/account swapped in some legacy rows; 15–16-digit values at float precision are always blocker-flagged.
- H3 [confirmed] Food-handler cert + typhoid proof are mandatory for F&B food handlers (KKM); typhoid expiry drives daily `raise_expiry_flags()`.
- H4 [derived] Duplicate detection (same NRIC/email/phone) must flag, not merge — sibling applicants share phones.

## Vocabulary
| term | means | never confuse with |
|---|---|---|
| blocker flag | blocks activation and payroll inclusion | warning/info flags |
| activation | HR approval → active + employee_no | mere status edit |

## Decisions & open questions
- OPEN-1 Document binaries still on Google Drive links; migration to `employee-docs` bucket pending (flagged per employee). — README.

## Lessons
- (none yet)
