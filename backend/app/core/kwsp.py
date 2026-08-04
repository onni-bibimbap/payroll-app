"""KWSP / EPF (Employees Provident Fund) core calculation.

Employee 11%, employer 13% for wages up to the threshold else 12%, applied to
the RM20 wage-band upper bound and rounded up to the next ringgit (EPF
Third-Schedule convention — the schedule tabulates by band, not the exact
wage). Verified against the RM2,550 / RM3,350 / RM5,000 rows of the official
KWSP Third Schedule (effective 1 October 2025). Rates are configurable.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from .rates import DEFAULT_CONFIG, D, RateConfig, pct, roundup_ringgit

BAND_WIDTH = Decimal("20")


def band_upper(wage, band_width: Decimal = BAND_WIDTH) -> Decimal:
    """Upper bound of the EPF Third-Schedule wage band covering ``wage``."""
    w = D(wage)
    if w <= 0:
        return Decimal("0")
    return (w / band_width).quantize(Decimal("1"), ROUND_CEILING) * band_width


def employer_rate(wage, cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Employer contribution rate for the given monthly wage."""
    return cfg.epf_er_rate_low if D(wage) <= cfg.epf_er_threshold else cfg.epf_er_rate_high


def contribution(wage, enabled: bool = True,
                 cfg: RateConfig = DEFAULT_CONFIG) -> tuple[Decimal, Decimal]:
    """Return ``(employee, employer)`` EPF contribution for the wage."""
    w = D(wage)
    if not enabled or w <= 0:
        return Decimal("0"), Decimal("0")
    band = band_upper(w)
    emp = roundup_ringgit(band * cfg.epf_emp_rate)
    er = roundup_ringgit(band * employer_rate(w, cfg))
    return emp, er


def explain(wage, enabled: bool = True, cfg: RateConfig = DEFAULT_CONFIG) -> str:
    """Plain-English derivation of the EPF figures."""
    if not enabled:
        return "EPF/KWSP not applied to this employee."
    w = D(wage)
    if w <= 0:
        return "No EPF wage, so no contribution."
    band = band_upper(w)
    er = employer_rate(w, cfg)
    emp_amt, er_amt = contribution(w, True, cfg)
    band_note = f" (band upper RM{band:,.2f})" if band != w else ""
    tier = (f"{pct(cfg.epf_er_rate_low)} at/below RM{cfg.epf_er_threshold:,.0f}, "
            f"else {pct(cfg.epf_er_rate_high)}")
    return (f"Employee {pct(cfg.epf_emp_rate)} × RM{w:,.2f}{band_note} = RM{emp_amt:,.2f} "
            f"(Third-Schedule band, rounded up). Employer {pct(er)} × RM{w:,.2f}{band_note} "
            f"= RM{er_amt:,.2f} (employer rate: {tier}).")
