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
- DEC-006 2026-09-03 (audit STAT-09) **Proration for mid-month joiners/leavers** — monthly staff whose hire_date or last_working_day falls inside the run month earn `basic × (calendar days employed in month / days in month)`, rounded to sen, BEFORE statutory compute. The preparer may override the prorated basic on the run screen. Joined 1 Sep, left 30 Sep, or full month → no proration. Implementation in `payroll.prorate_basic()` + slip.notes records the proration basis for the payslip summary. Revisit if the company switches to work-day proration (20/22 working days instead of calendar days).
- DEC-007 2026-09-03 (audit SEC-06) **Four-eyes rule: no self-approval** — a run prepared by a user can only be approved by a *different* approver. Code at `main.run_approve` checks `run.prepared_by != user.username` and returns 409 if equal. Admins are not exempt from this rule (verification in tests). Rationale: audit trail and segregation of duties on §6 high-risk path. Revisit if the business model requires single-person admin to approve own runs (rare; document as DECISION if forced).
- OPEN-1 Run approval flow (preparer creates, approver approves) — verify enforcement server-side in `payroll.py`/`main.py` ✓ (enforced; four-eyes rule live).

## Lessons
- L1 2026-09-03 Blocked-employee exclusion (R2) is now enforced in the app at run population time (`payroll.sync_new_employees`), mirroring the view predicate. Surface excluded employees in the run detail response as "blocked from payroll" with reasons (flag type, missing bank account, lifecycle state). Tests verify the exclusion works and runs cannot pay the wrong people. Previous gap: the old builder selected only `active=True` flag, ignoring the verified-bank and lifecycle gates that live in the view, allowing unverified accounts onto payslips.
