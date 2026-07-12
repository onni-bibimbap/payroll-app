"""EIS (Employment Insurance System) core calculation.

0.2% each side on the same RM100 band table and ceiling as SOCSO. Not charged
for employees aged 60+ or foreign workers.
"""

from __future__ import annotations

from decimal import Decimal

from .rates import DEFAULT_CONFIG, D, RateConfig, pct, round5
from .socso import band_midpoint


def contribution(wage, over_60: bool = False, foreign: bool = False,
                 enabled: bool = True,
                 cfg: RateConfig = DEFAULT_CONFIG) -> tuple[Decimal, Decimal]:
    """Return ``(employee, employer)`` EIS contribution (equal on both sides)."""
    w = D(wage)
    if not enabled or over_60 or foreign or w <= 0:
        return Decimal("0"), Decimal("0")
    v = round5(cfg.eis_rate * band_midpoint(w, cfg))
    return v, v


def explain(wage, over_60: bool = False, foreign: bool = False, enabled: bool = True,
            cfg: RateConfig = DEFAULT_CONFIG) -> str:
    """Plain-English derivation of the EIS figures."""
    if not enabled:
        return "EIS not applied to this employee."
    if over_60:
        return "EIS not charged for employees aged 60 and above."
    if foreign:
        return "EIS not charged for foreign workers."
    w = D(wage)
    if w <= 0:
        return "No EIS wage, so no contribution."
    mid = band_midpoint(w, cfg)
    v, _ = contribution(w, over_60, foreign, True, cfg)
    return (f"{pct(cfg.eis_rate)} each side on the band midpoint RM{mid:,.2f} "
            f"→ RM{v:,.2f} employee and RM{v:,.2f} employer.")
