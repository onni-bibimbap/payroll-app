# Payroll runs & exports — payroll
Sources: `README.md` (§ Monthly payroll routine), PRD Phase 4, `backend/app/{payroll,payroll_export,pdf}.py` (skimmed), migrations `0001,0004` · Last verified: 2026-09-03 · Owner role: preparer/approver

## Rules
- R1 [confirmed] Clerk's monthly job reduces to keying **part-time hours and OT hours only**; everything else flows from master data. — PRD Phase 4.
- R2 [confirmed] An employee with any open **blocker** flag or unverified bank account is **excluded** from `payroll_master_view` and listed separately as "blocked from payroll". — PRD Phase 4.4, README.
- R3 [confirmed] Master view includes only employees `active` on/before period end with `last_working_day` NULL or ≥ period start; movements view lists the month's hires and leavers (final-pay reminder). — PRD Phase 4.
- R4 [confirmed] Money stored as integer sen; views/exports convert at the edge. — PRD ground rule 6.
- R5 [derived] Payroll runs and payslips are append-only history; leavers drop out of views after `last_working_day` but are never deleted (7-year retention). — PRD Phase 2.

## Hazards
- H1 [confirmed] Month-boundary joins/leavers: hire or last-working-day mid-month → proration and movements listing; a leaver with last month's `last_working_day` must NOT appear this month. — PRD acceptance 4.
- H2 [derived] Sen↔ringgit conversion points are corruption hazards — mixing float RM into sen integer paths.
- H3 [derived] Re-running/computing a run twice must not double-write payslips (idempotency on §6 endpoints).

## Vocabulary
| term | means | never confuse with |
|---|---|---|
| movements | month's new hires + leavers list | status history |
| master CSV | payroll input export of active unblocked staff | employee list export |

## Decisions & open questions
- OPEN-1 Run approval flow (preparer creates, approver approves) — verify enforcement server-side in `payroll.py`/`main.py`.

## Lessons
- (none yet)
