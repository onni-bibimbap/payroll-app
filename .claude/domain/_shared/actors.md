# Actors — _shared
Sources: README.md (demo accounts), PRD RLS roles, `backend/app/security.py` (skimmed) · Last verified: 2026-09-03

| actor | device/face | frequency | must never see |
|---|---|---|---|
| preparer (payroll clerk) | desktop payroll UI | monthly window (25th–1st) | user admin, rate settings |
| approver | desktop payroll UI + HR dashboard | monthly + review queue | — (sees RESTRICTED with audit) |
| admin | everything incl. settings | ad hoc | — |
| applicant (anon) | mobile PWA `/register`, EN+BM | once | any read of any table |
| staff | (planned) own record | rare | others' bank/NRIC/pay |
| system | scheduled jobs (`raise_expiry_flags`) | daily | — |

- [confirmed] Demo credentials preparer/approver/admin with `*123` passwords are seeded and printed by README/Makefile — TRIAL-only; must never reach prod.
- [confirmed] PRD role model (hr_admin/manager/staff/anon RLS) is richer than the current backend roles (preparer/approver/admin) — the backend is the only DB client and enforces roles at the API layer; RLS is deny-by-default beneath it.
