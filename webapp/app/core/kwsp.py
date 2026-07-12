"""KWSP / EPF (Employees Provident Fund) core calculation.

Employee 11%, employer 13% for wages up to the threshold else 12%, each rounded
up to the next ringgit (EPF Third-Schedule convention). Rates are configurable.
"""

from __future__ import annotations

from decimal import Decimal

from .rates import DEFAULT_CONFIG, D, RateConfig, pct, roundup_ringgit


def employer_rate(wage, cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Employer contribution rate for the given monthly wage."""
    return cfg.epf_er_rate_low if D(wage) <= cfg.epf_er_threshold else cfg.epf_er_rate_high


def contribution(wage, enabled: bool = True,
                 cfg: RateConfig = DEFAULT_CONFIG) -> tuple[Decimal, Decimal]:
    """Return ``(employee, employer)`` EPF contribution for the wage."""
    w = D(wage)
    if not enabled or w <= 0:
        return Decimal("0"), Decimal("0")
    emp = roundup_ringgit(w * cfg.epf_emp_rate)
    er = roundup_ringgit(w * employer_rate(w, cfg))
    return emp, er


def explain(wage, enabled: bool = True, cfg: RateConfig = DEFAULT_CONFIG) -> str:
    """Plain-English derivation of the EPF figures."""
    if not enabled:
        return "EPF/KWSP not applied to this employee."
    w = D(wage)
    if w <= 0:
        return "No EPF wage, so no contribution."
    er = employer_rate(w, cfg)
    emp_amt, er_amt = contribution(w, True, cfg)
    band = (f"{pct(cfg.epf_er_rate_low)} at/below RM{cfg.epf_er_threshold:,.0f}, "
            f"else {pct(cfg.epf_er_rate_high)}")
    return (f"Employee {pct(cfg.epf_emp_rate)} × RM{w:,.2f} = RM{emp_amt:,.2f} "
            f"(rounded up). Employer {pct(er)} × RM{w:,.2f} = RM{er_amt:,.2f} "
            f"(employer rate: {band}).")
