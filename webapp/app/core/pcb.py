"""PCB / MTD (monthly income-tax deduction) core calculation.

An ESTIMATE using the annualised Formula Method on the resident YA2024/2025
brackets: annual chargeable income = statutory wage × 12 − personal relief −
capped EPF relief; progressive tax − rebate (if applicable), ÷ 12. It is not a
substitute for the official LHDN e-PCB figure (use the per-line override).
"""

from __future__ import annotations

from decimal import Decimal

from .rates import DEFAULT_CONFIG, D, TAX_BRACKETS, RateConfig, round5


def chargeable_income(monthly_wage, epf_emp_monthly,
                      cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Annual chargeable income used by the PCB estimate."""
    return max(
        Decimal("0"),
        D(monthly_wage) * 12
        - cfg.personal_relief
        - min(D(epf_emp_monthly) * 12, cfg.epf_relief_cap),
    )


def annual_tax(ci: Decimal, cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Progressive resident tax on a chargeable income, net of the rebate."""
    bracket = TAX_BRACKETS[0]
    for b in TAX_BRACKETS:
        if ci >= b[0]:
            bracket = b
        else:
            break
    tax = bracket[2] + (ci - bracket[0]) * bracket[1]
    if ci <= cfg.rebate_ceiling:
        tax -= cfg.tax_rebate
    return max(Decimal("0"), tax)


def estimate(monthly_wage, epf_emp_monthly,
             cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Estimated monthly PCB."""
    ci = chargeable_income(monthly_wage, epf_emp_monthly, cfg)
    return round5(annual_tax(ci, cfg) / 12)


def explain(monthly_wage, epf_emp_monthly, override=None,
            cfg: RateConfig = DEFAULT_CONFIG) -> str:
    """Plain-English derivation of the PCB figure."""
    if override is not None:
        return f"Manual PCB override of RM{D(override):,.2f} (from LHDN e-PCB)."
    ci = chargeable_income(monthly_wage, epf_emp_monthly, cfg)
    if ci <= 0:
        return ("Annual income after personal + EPF relief is nil, so estimated "
                "PCB is RM0.00.")
    tax = annual_tax(ci, cfg)
    monthly = estimate(monthly_wage, epf_emp_monthly, cfg)
    return (f"Estimate: (wage RM{D(monthly_wage):,.2f} × 12) − RM{cfg.personal_relief:,.0f} "
            f"personal − EPF relief = RM{ci:,.2f} chargeable; tax after rebate "
            f"RM{tax:,.2f} ÷ 12 ≈ RM{monthly:,.2f}. Estimate only — use e-PCB for the exact figure.")
