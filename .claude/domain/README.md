# Domain index — Onni Payroll

One line per file. A file not listed here does not exist to other agents.

## payroll/
- `payroll/statutory.md` — EPF/SOCSO/EIS/PCB rules, rounding, bands, worked scenarios W1–W3, hazards H1–H6.
- `payroll/runs-and-exports.md` — run lifecycle, blocked-employee exclusion, movements, sen conversion hazards.

## employee-master/
- `employee-master/lifecycle.md` — status machine, activation preconditions, flag catalog, NRIC/bank recovery hazards.

## frontend/
- `frontend/pwa-ui.md` — Tailwind-inline-in-vite-config constraint, PWA icons/installability, offline registration queue (IDB keys, token dedupe, TypeError-as-offline), dirty-save payroll editing, money() zero-vs-dash, 401 handling, nginx add_header inheritance.

## _shared/
- `_shared/glossary.md` — ubiquitous language (statutory wage, sen, movements, blocker flag…).
- `_shared/actors.md` — roles, devices, frequency, what each must never see.
- `_shared/integrations.md` — Supabase Postgres/Storage, legacy xlsx import, mocks.
- `_shared/compliance.md` — PDPA/LHDN/KKM, retention, timezone; OPEN: real data in git, prod-DB default.
