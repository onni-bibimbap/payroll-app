"""KWSP / EPF (Employees Provident Fund) core calculation.

Employee 11%, employer 13% for wages up to the threshold else 12%, applied to
the Third-Schedule wage-band upper bound and rounded up to the next ringgit.
The schedule tabulates RM20-wide bands up to RM5,000 and RM100-wide bands from
RM5,000.01 to RM20,000; above RM20,000 the rates apply to the exact wage (each
side still rounded up to the next ringgit). Verified against the RM2,550 /
RM3,350 / RM5,000 / RM5,050 rows of the official KWSP Third Schedule
(effective 1 October 2025). Rates are configurable.

Branches: Malaysian employees aged 60+ contribute 0% with employer 4%; foreign
workers contribute 2%/2% (mandatory since October 2025). Both live as engine
defaults in :mod:`rates` — verify against the current schedules before a real
payroll run.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from .rates import DEFAULT_CONFIG, D, RateConfig, pct, roundup_ringgit

BAND_WIDTH_LOW = Decimal("20")      # band width for wages up to BAND_LIMIT_LOW
BAND_WIDTH_HIGH = Decimal("100")    # band width for wages up to BAND_LIMIT_HIGH
BAND_LIMIT_LOW = Decimal("5000")    # RM20 bands end here
BAND_LIMIT_HIGH = Decimal("20000")  # RM100 bands end here; above: exact wage


def band_upper(wage) -> Decimal:
    """Upper bound of the EPF Third-Schedule wage band covering ``wage``.

    RM20-wide bands up to RM5,000, RM100-wide bands from RM5,000.01 to
    RM20,000; above RM20,000 the schedule applies the rates to the exact
    wage, so the wage itself is returned.
    """
    w = D(wage)
    if w <= 0:
        return Decimal("0")
    if w > BAND_LIMIT_HIGH:
        return w
    width = BAND_WIDTH_LOW if w <= BAND_LIMIT_LOW else BAND_WIDTH_HIGH
    return (w / width).quantize(Decimal("1"), ROUND_CEILING) * width


def employer_rate(wage, cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Employer contribution rate for the given monthly wage."""
    return cfg.epf_er_rate_low if D(wage) <= cfg.epf_er_threshold else cfg.epf_er_rate_high


def contribution(wage, enabled: bool = True, cfg: RateConfig = DEFAULT_CONFIG,
                 over_60: bool = False,
                 foreign: bool = False) -> tuple[Decimal, Decimal]:
    """Return ``(employee, employer)`` EPF contribution for the wage.

    ``foreign`` selects the mandatory foreign-worker rates (2%/2% since
    Oct 2025) and takes precedence over ``over_60``, which selects the
    Malaysian age-60+ rates (employee 0%, employer 4%).
    """
    w = D(wage)
    if not enabled or w <= 0:
        return Decimal("0"), Decimal("0")
    band = band_upper(w)
    if foreign:
        emp_rate, er_rate = cfg.epf_emp_rate_foreign, cfg.epf_er_rate_foreign
    elif over_60:
        emp_rate, er_rate = cfg.epf_emp_rate_over_60, cfg.epf_er_rate_over_60
    else:
        emp_rate, er_rate = cfg.epf_emp_rate, employer_rate(w, cfg)
    emp = roundup_ringgit(band * emp_rate)
    er = roundup_ringgit(band * er_rate)
    return emp, er


def explain(wage, enabled: bool = True, cfg: RateConfig = DEFAULT_CONFIG,
            over_60: bool = False, foreign: bool = False) -> str:
    """Plain-English derivation of the EPF figures."""
    if not enabled:
        return "EPF/KWSP not applied to this employee."
    w = D(wage)
    if w <= 0:
        return "No EPF wage, so no contribution."
    band = band_upper(w)
    emp_amt, er_amt = contribution(w, True, cfg, over_60, foreign)
    band_note = f" (band upper RM{band:,.2f})" if band != w else ""
    if foreign:
        emp_rate, er_rate = cfg.epf_emp_rate_foreign, cfg.epf_er_rate_foreign
        tier = "foreign-worker rates (mandatory since Oct 2025)"
    elif over_60:
        emp_rate, er_rate = cfg.epf_emp_rate_over_60, cfg.epf_er_rate_over_60
        tier = "age-60+ rates (employee share nil)"
    else:
        emp_rate, er_rate = cfg.epf_emp_rate, employer_rate(w, cfg)
        tier = (f"{pct(cfg.epf_er_rate_low)} at/below RM{cfg.epf_er_threshold:,.0f}, "
                f"else {pct(cfg.epf_er_rate_high)}")
    return (f"Employee {pct(emp_rate)} × RM{w:,.2f}{band_note} = RM{emp_amt:,.2f} "
            f"(Third-Schedule band, rounded up). Employer {pct(er_rate)} × "
            f"RM{w:,.2f}{band_note} = RM{er_amt:,.2f} (employer rate: {tier}).")
