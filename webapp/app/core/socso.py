"""SOCSO / PERKESO core calculation.

Table-based on RM100 wage bands with a wage ceiling (RM6,000). The published
table is reproduced with ``contribution = round-to-5-sen(rate × band midpoint)``:
Category 1 (age < 60) charges employee 0.5% + employer 1.75%; Category 2
(age >= 60) charges the employer 1.25% only. Verified against the RM3,200 /
RM5,000 / RM6,000 rows of the official PERKESO table.
"""

from __future__ import annotations

from decimal import Decimal

from .rates import DEFAULT_CONFIG, D, RateConfig, pct, round5


def band_midpoint(wage, cfg: RateConfig = DEFAULT_CONFIG) -> Decimal:
    """Assumed-wage midpoint of the SOCSO/EIS band covering ``wage``."""
    ceiling = cfg.socso_eis_ceiling
    w = min(D(wage), ceiling)
    if w <= 0:
        return Decimal("0")
    edges = [0, 30, 50, 70] + list(range(100, int(ceiling) + 1, 100))
    for lo, hi in zip(edges, edges[1:]):
        if Decimal(lo) < w <= Decimal(hi):        # bands are exclusive-lower
            return (Decimal(lo) + Decimal(hi)) / 2
    return (Decimal(edges[-2]) + Decimal(edges[-1])) / 2   # ceiling band


def contribution(wage, over_60: bool = False, enabled: bool = True,
                 cfg: RateConfig = DEFAULT_CONFIG) -> tuple[Decimal, Decimal]:
    """Return ``(employee, employer)`` SOCSO contribution for the wage."""
    w = D(wage)
    if not enabled or w <= 0:
        return Decimal("0"), Decimal("0")
    mid = band_midpoint(w, cfg)
    if over_60:                                   # Category 2 (employer only)
        return Decimal("0"), round5(cfg.socso_c2_er * mid)
    return round5(cfg.socso_c1_emp * mid), round5(cfg.socso_c1_er * mid)


def explain(wage, over_60: bool = False, enabled: bool = True,
            cfg: RateConfig = DEFAULT_CONFIG) -> str:
    """Plain-English derivation of the SOCSO figures."""
    if not enabled:
        return "SOCSO not applied to this employee."
    w = D(wage)
    if w <= 0:
        return "No SOCSO wage, so no contribution."
    capped = min(w, cfg.socso_eis_ceiling)
    mid = band_midpoint(w, cfg)
    emp, er = contribution(w, over_60, True, cfg)
    cat = ("Category 2 (age ≥ 60): employer only" if over_60
           else "Category 1 (age < 60): employee + employer")
    cap_note = (f" (capped at the RM{cfg.socso_eis_ceiling:,.0f} ceiling)"
                if w > cfg.socso_eis_ceiling else "")
    rates = (f"employer {pct(cfg.socso_c2_er)}" if over_60
             else f"employee {pct(cfg.socso_c1_emp)} + employer {pct(cfg.socso_c1_er)}")
    return (f"{cat}. Wage RM{capped:,.2f}{cap_note} falls in the band with assumed "
            f"wage RM{mid:,.2f}; {rates} → employee RM{emp:,.2f}, employer RM{er:,.2f}.")
