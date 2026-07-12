# Malaysia Monthly Payroll — Seamless Solution

**Deliverable:** `emp_payroll_2606.xlsx` (June 2026, reusable every month)
**Generator:** `build_payroll.py` (re-run to rebuild the workbook from scratch)
**Source image:** `payroll_2606.png`  **Prior model:** `emp_payroll_2605.xlsx` (May)

---

## What it does

You type each employee's monthly figures (from the payroll image) into the **blue**
cells. The workbook then auto-derives, for **both employee and employer**:

| Contribution | Employee | Employer | Method |
|---|---|---|---|
| **EPF / KWSP** | 11% | 13% (≤RM5,000) / 12% (>RM5,000) | % of EPF wage, rounded up to next RM |
| **SOCSO / PERKESO** | 0.5% (Cat 1) | 1.75% (Cat 1) / 1.25% (Cat 2) | Official RM100-band table, ceiling RM6,000 |
| **EIS** | 0.2% | 0.2% | Same band table, ceiling RM6,000 |
| **PCB (income tax)** | estimate + override | — | Annualised MTD on YA2024/25 brackets |

Outputs per person: **NET SALARY (take-home)** and **EMPLOYER TOTAL COST**, with a
TOTALS row footing every money column.

## The 3 sheets

1. **Payroll** — one row per employee. Blue = you type; black = formula; green =
   pulled from the Rates sheet; **yellow = verify against the image**.
2. **Rates** — every statutory rate and the full SOCSO/EIS band table, all
   formula-driven. Change a rate here and the whole workbook updates.
3. **How to use** — step-by-step instructions and the sources.

## Each month (4 steps)

1. Update `Payroll!B2` (pay month) and each employee's inputs (Basic, allowances,
   Work/Unpaid Days, OT Hours, OT Rate).
2. Set `Type`, `Apply EPF?`, `Apply SOCSO+EIS?`, `Age ≥ 60?` per person.
3. Open the image and confirm every **yellow** cell.
4. Read NET SALARY and EMPLOYER TOTAL COST. For exact PCB, put the LHDN e-PCB
   figure in `PCB Override` (it always beats the estimate).

## Verified correct

Cross-checked against the real May figures in `emp_payroll_2605.xlsx`:

| Employee | EPF ee/er | SOCSO ee/er | EIS | Employer total cost |
|---|---|---|---|---|
| cheong fong cheng (RM5,000) | 550 / 650 | 24.75 / 86.65 | 9.90 | **5,746.55** ✓ (= May) |
| Tan Kui Thean (RM3,200) | 352 / 416 | 15.75 / 55.15 | 6.30 | 3,677.45 ✓ |

PCB estimate for the RM5,000 earner = **RM110** vs the May sheet's RM109.45.
LibreOffice recalculation: **0 formula errors** across 649 formulas.

---

## Build log (for review)

**Decisions**
- **New workbook, not an edit of the May file.** The May sheet hard-codes every EPF/
  SOCSO/EIS/PCB value by hand (error-prone). Replaced with a formula + lookup engine so
  the numbers can never drift from the statutory tables.
- **SOCSO/EIS via band-midpoint formula**, not hand-typed table values: contribution =
  `MROUND(rate × midpoint, 0.05)`. Reproduces the official PERKESO table exactly
  (verified at RM1,000 / 2,000 / 3,200 / 5,000 / 6,000) and stays auditable.
- **EPF wage = Basic + allowances (excl. OT)**, matching the May sheet's convention.
  Note: petrol/travel allowance is technically EPF/SOCSO-exempt; included to match the
  existing sheet — move it out if you prefer.
- **PCB is an estimate with a manual override.** Exact MTD depends on marital status,
  children, zakat, prior YTD, etc.; the override column lets the official LHDN figure win.
- **Uncertain image reads flagged yellow** (whited-out basics, ambiguous OT rows) rather
  than guessed — payroll accuracy over convenience.

**Error / fix**
- `SyntaxError: f-string expression part cannot include a backslash` (Py 3.10) — column
  keys contain `\n`. Fixed by resolving column letters into variables before the f-string.

**Statutory sources**
- PERKESO SOCSO/EIS: https://www.perkeso.gov.my/en/rate-of-contribution.html
- KWSP/EPF Third Schedule: https://www.kwsp.gov.my/en/employer/responsibilities/mandatory-contribution
- LHDN individual tax (YA2024/25): https://www.hasil.gov.my/en/individual/
