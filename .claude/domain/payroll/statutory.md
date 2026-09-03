# Statutory contributions — payroll
Sources: `backend/app/core/{rates,kwsp,socso,eis,pcb}.py`, `backend/app/statutory.py`, `backend/app/payroll.py`, `backend/tests/test_statutory.py`, `backend/tests/test_payroll_flags.py`, PRD `prompt/agent-prompt-employee-db-pwa.md` · Last verified: 2026-09-03 · Owner role: admin

## Rules (what must always hold)
- R1 [confirmed] **One statutory wage** feeds EPF, SOCSO, EIS, PCB: base earning (monthly basic, or rate×units for daily/hourly) + allowance and/or OT **only when opted in** (`include_allowance`, `include_ot`). Allowance/OT are always *paid*; they just may not attract statutory. — `statutory.py` docstring · test: `test_statutory.py::test_allowance_opt_in_*`, `test_ot_opt_in_*`.
- R2 [confirmed] **EPF (KWSP)**: employee 11%; employer 13% for wage ≤ RM5,000 else 12%; both computed on the Third-Schedule **band upper bound**, each rounded **up to the next ringgit**. Band widths: **RM20 up to RM5,000; RM100 for RM5,000.01–20,000; above RM20,000 the rates apply to the exact wage** (still roundup-ringgit each side). Verified against RM2,550/RM3,350/RM5,000/RM5,050 (→ 561/612) schedule rows; RM20,000 edge tested. — `core/kwsp.py` · tests: `test_epf_band_upper_widths`, `test_epf_contribution_band_edges`. (Fixes audit STAT-03: RM20 bands were previously applied to all wages, understating EPF above RM5,000.)
- R3 [confirmed] **SOCSO (PERKESO)**: band table with low-band edges **[0, 30, 50, 70, 100, 140, 200]** (exclusive-lower) then RM100 bands from RM200; wage ceiling RM6,000; contribution = round-half-up-to-5-sen(rate × band midpoint). Category 1 (<60): employee 1.25% (Invalidity 0.5% + SKBBK 0.75%, Employer Circular No. 2/2026, eff. 1 Jun 2026) + employer 1.75%. Category 2 (≥60): employer only 1.25%. — `core/socso.py` · tests: `test_socso_band_midpoint_edges`, `test_socso_contribution_*`. (Fixes audit STAT-06: 100–140 and 140–200 sub-bands were previously merged into one 100–200 band with midpoint 150.)
- R3a [derived] **SOCSO foreign workers**: Employment Injury scheme only — employer 1.25% (`SOCSO_FOREIGN_ER`), employee 0. Implemented via `socso.contribution(..., foreign=True)`; foreign takes precedence over the age split (same employer-only 1.25% either way). **Verify against the current PERKESO schedule before the next real payroll run.** — audit GAP-01 · test: `test_socso_category_2_and_foreign_are_employer_only`, `test_compute_foreign_worker_branch`.
- R4 [confirmed] **EIS**: 0.2% each side, same band midpoint + ceiling as SOCSO; **not charged** for age ≥60 or foreign workers. — `core/eis.py` · test: `test_compute_malaysian_over_60_branch`, `test_compute_foreign_worker_branch`.
- R4a [derived] **EPF age/nationality branches** (audit GAP-01): Malaysian ≥60 → employee **0%**, employer **4%** (`EPF_EMP_RATE_OVER_60`/`EPF_ER_RATE_OVER_60`); foreign worker → **2%/2%, mandatory since Oct 2025** (`EPF_EMP_RATE_FOREIGN`/`EPF_ER_RATE_FOREIGN`), both on the normal Third-Schedule band. Foreign takes precedence over over_60 in `kwsp.contribution` (foreign-60+ treatment is unresolved — see OPEN-3). **Rates are [derived] from the Oct 2025 KWSP changes — verify against the live KWSP Third Schedule / PERKESO schedules before the next real payroll run.** — `core/rates.py`, `core/kwsp.py` · tests: `test_compute_malaysian_over_60_branch`, `test_foreign_epf_uses_third_schedule_band`.
- R5 [confirmed] **PCB estimate**: annualised formula method — CI = wage×12 − RM9,000 personal relief − min(EPF_emp×12, RM4,000); progressive YA2024/25 resident brackets; RM400 rebate if CI ≤ RM35,000; ÷12, round to 5 sen. It is an **estimate only** — the per-line `pcb_override` (LHDN e-PCB figure) is authoritative. — `core/pcb.py` · test: `test_pcb_estimate_and_rebate`, `test_pcb_override_wins`.
- R6 [confirmed] All engine math in `Decimal`; DB money in **integer sen** (employee-master) / NUMERIC(12,2) ringgit (payroll tables); rounding helpers: `round5` (5 sen, half-up), `roundup_ringgit` (ceiling), `money` (2dp half-up). Floats only at the serialization edge (`as_floats`). — `core/rates.py` · test: `test_rounding_helpers`.
- R7 [confirmed] `net = total_remuneration − (epf_e + socso_e + eis_e + pcb + other deduction)`; `employer_cost = total_remuneration + employer statutory`. — `statutory.py compute()` · test: `test_compute_w1_monthly_basic_5000_defaults`.
- R8 [confirmed] **Single source of truth for rates**: `core/rates.py` constants. `Settings` ORM defaults import them (`models.py` — never re-type literals), and `store.rate_config()` fields not stored on the Settings row fall back to the `RateConfig` defaults. Migration `0009_socso_c1_emp_rate_fix.sql` repairs rows created with the stale 0.5% SOCSO employee default (idempotent; deliberate overrides survive). — audit STAT-01/QT-02 · test: `test_settings_defaults_match_engine_rates`.
- R9 [confirmed] **over_60 cutoff = month end**: an employee who turns 60 on/before the LAST day of the run month is Category 2 (and EIS-free) for that whole month. `payroll.derive_statutory_flags(emp, year, month)` derives `(over_60, foreign, warning)` from the Employee row; `payroll.recompute` **re-derives both flags on every recompute** (stored slip flags and posted FLAG_FIELDS values are advisory only). Missing DOB with SOCSO/EIS enabled → over_60 stays False and a review warning is returned + logged. — audit STAT-05, resolves OPEN-2 · tests: `test_payroll_flags.py`.

## Hazards (what competent outsiders get wrong)
- H1 [confirmed] SOCSO round-to-5-sen(midpoint) formula can differ from the legislated discrete table by 5 sen at exact halfway ties (e.g. RM5,800.01–5,900 band: official RM102.35/RM73.10 vs formula RM102.40/RM73.15). Exact compliance requires a hardcoded official table. — `core/socso.py` docstring.
- H2 [confirmed] EPF is computed on the **band upper bound**, not the exact wage, below RM20,000 — applying 11% to raw wage gives wrong figures (e.g. RM5,050 → 561, not 555.50→556). Above RM20,000 the exact wage IS the base.
- H3 [confirmed] SOCSO bands are **exclusive-lower** (`lo < w <= hi`); off-by-one at band edges (RM30/50/70/100/140/200…) flips the midpoint. Band-edge goldens at 100/100.01/140/140.01/200/200.01 now guard this.
- H4 [confirmed] Age-60 boundary: derivation is now owned by `payroll.derive_statutory_flags` (month-end cutoff, R9) — do NOT re-introduce caller-owned booleans or 1st-of-month derivation. A manual `over_60` flip via the UI is overwritten on the next save/recompute; correct the DOB instead.
- H5 [confirmed] Foreign workers: no EIS; employer-only SOCSO (R3a); EPF 2%/2% (R4a). Misclassifying identity_type/nationality mispays statutory. `foreign` is re-derived from `Employee.is_foreign` on every recompute.
- H6 [confirmed] PCB estimate ≠ e-PCB; presenting the estimate as authoritative is a compliance error. Use override for filing.
- H7 [derived] The `FLAG_FIELDS` over_60/foreign posted by the UI are dead inputs since the R9 re-derivation — removing them from the UI (out of this scope) would avoid clerk confusion.

## Vocabulary
| term | means | never confuse with |
|---|---|---|
| statutory wage | base (+opted-in allowance/OT) that contributions charge on | total remuneration (what's paid) |
| Category 1 / 2 | SOCSO <60 / ≥60 schemes | EPF employer tiers (13%/12%) |
| Employment Injury scheme | foreign-worker SOCSO (employer-only 1.25%) | Category 2 (same rate, age-based) |
| band midpoint | SOCSO/EIS assumed wage | EPF band **upper** bound |
| PCB / MTD | monthly tax deduction | annual income tax filing |

## Worked scenarios (synthetic — all live as pytest goldens in `backend/tests/test_statutory.py`)
| id | input | expected output | source |
|---|---|---|---|
| W1 | monthly basic RM5,000, defaults | EPF 550/650 · SOCSO 61.90/86.65 · EIS 9.90/9.90 · PCB 110.00 · ee-deduction 731.80 · net 4,268.20 · employer cost 5,746.55 | `test_compute_w1_*` (updated for SOCSO emp 1.25%; the old 24.75/4,305.35 figures encoded the stale 0.5% rate) |
| W2 | daily RM100×26, allowance RM300 not included | base 2,600 · gross 2,900 · statutory wage 2,600 · EPF 286/338 | `test_compute_w2_*` |
| W3 | hourly RM8×60, EPF+SOCSO off | net 480.00, zero statutory | `test_compute_w3_*` |
| W4 | basic RM5,000, Malaysian over 60 | EPF 0/200 · SOCSO 0/61.90 · EIS 0/0 | `test_compute_malaysian_over_60_branch` [derived rates] |
| W5 | basic RM2,600, foreign worker | EPF 52/52 · SOCSO 0/31.90 · EIS 0/0 | `test_compute_foreign_worker_branch` [derived rates] |
| W6 | wage RM5,050 (EPF RM100 band) | EPF 561/612 (band top RM5,100, employer 12%) | `test_epf_contribution_band_edges` |

## Decisions & open questions
- DEC-1 2026-09-03 (audit STAT-05) over_60 cutoff = **turns 60 on/before the last day of the run month**; flags re-derived from the Employee row inside `recompute`/`_new_payslip`, never trusted from the slip. Missing DOB ⇒ Category 1 + warning. Revisit if PERKESO clarifies a different mid-month convention.
- DEC-2 2026-09-03 (audit GAP-01) Age-60/foreign EPF+SOCSO rates added as engine defaults only (no Settings columns yet) — `store.rate_config` leaves them at `RateConfig` defaults, so no serializer/UI change was needed. Revisit if admins must tune them per-deployment.
- OPEN-1 Should SOCSO use a hardcoded official table instead of the formula (kills H1)? · blocks: exact-compliance FEAT.
- ~~OPEN-2 Who derives `over_60`/`foreign`~~ → resolved by R9/DEC-1.
- OPEN-3 Foreign worker aged 60+: engine applies the foreign EPF rates (2%/2%) because `foreign` takes precedence; the pre-Oct-2025 schedule had a distinct non-citizen-60+ part. **Human must verify against the current KWSP schedule** before running payroll for any foreign employee near 60.
- OPEN-4 [derived] The GAP-01 rates (EPF 0%/4% over-60, 2%/2% foreign, SOCSO foreign employer-only 1.25%) were implemented from the audit's citation of the Oct 2025 changes, not from the official PDFs — verify against current KWSP/PERKESO schedules before the next real payroll run.

## Lessons
- L1 2026-08 (git 587d436) EPF and SOCSO calcs were previously wrong and fixed — statutory logic has regressed before. **2026-09-03: the engine is now guarded by 60 pytest goldens (`backend/tests/`, run `.venv/bin/python -m pytest backend/tests -q`); the `statutory.py __main__` self-test (which had itself gone stale-red) is retired to a pointer.**
- L2 2026-09-03 Defining the same rate in two places (rates.py constant + Settings ORM default literal) silently diverged for a month and under-deducted every employee's SOCSO (STAT-01). Rule R8 now forbids re-typed literals; `test_settings_defaults_match_engine_rates` enforces it.
