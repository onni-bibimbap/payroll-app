"""Rate configuration and money rounding shared by the statutory core modules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

# --- statutory defaults (current Malaysian law, YA2024/2025) ----------------
EPF_EMP_RATE = Decimal("0.11")
EPF_ER_RATE_LOW = Decimal("0.13")        # total wage <= threshold
EPF_ER_RATE_HIGH = Decimal("0.12")       # total wage > threshold
EPF_ER_THRESHOLD = Decimal("5000")
SOCSO_EIS_CEILING = Decimal("6000")      # since 1 Oct 2024
SOCSO_C1_EMP = Decimal("0.0125")         # Invalidity 0.5% + Non-Employment Injury/SKBBK 0.75%
SOCSO_C1_ER = Decimal("0.0175")          # Employment Injury 1.25% + Invalidity 0.5%
SOCSO_C2_ER = Decimal("0.0125")          # age >= 60, employee share = 0
EIS_RATE = Decimal("0.002")
PERSONAL_RELIEF = Decimal("9000")
EPF_RELIEF_CAP = Decimal("4000")
TAX_REBATE = Decimal("400")
REBATE_CEILING = Decimal("35000")

# Resident income-tax brackets: (chargeable_from, rate, cumulative_tax_at_from)
TAX_BRACKETS: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0"), Decimal("0.00"), Decimal("0")),
    (Decimal("5000"), Decimal("0.01"), Decimal("0")),
    (Decimal("20000"), Decimal("0.03"), Decimal("150")),
    (Decimal("35000"), Decimal("0.06"), Decimal("600")),
    (Decimal("50000"), Decimal("0.11"), Decimal("1500")),
    (Decimal("70000"), Decimal("0.19"), Decimal("3700")),
    (Decimal("100000"), Decimal("0.25"), Decimal("9400")),
    (Decimal("400000"), Decimal("0.26"), Decimal("84400")),
    (Decimal("600000"), Decimal("0.28"), Decimal("136400")),
    (Decimal("2000000"), Decimal("0.30"), Decimal("528400")),
]


@dataclass
class RateConfig:
    """All platform-configurable statutory parameters (defaults = current law)."""

    epf_emp_rate: Decimal = EPF_EMP_RATE
    epf_er_rate_low: Decimal = EPF_ER_RATE_LOW
    epf_er_rate_high: Decimal = EPF_ER_RATE_HIGH
    epf_er_threshold: Decimal = EPF_ER_THRESHOLD
    socso_eis_ceiling: Decimal = SOCSO_EIS_CEILING
    socso_c1_emp: Decimal = SOCSO_C1_EMP
    socso_c1_er: Decimal = SOCSO_C1_ER
    socso_c2_er: Decimal = SOCSO_C2_ER
    eis_rate: Decimal = EIS_RATE
    personal_relief: Decimal = PERSONAL_RELIEF
    epf_relief_cap: Decimal = EPF_RELIEF_CAP
    tax_rebate: Decimal = TAX_REBATE
    rebate_ceiling: Decimal = REBATE_CEILING


DEFAULT_CONFIG = RateConfig()


def D(x) -> Decimal:
    """Coerce anything numeric-ish to Decimal (blank/None -> 0)."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x if x not in (None, "") else 0))


def round5(x) -> Decimal:
    """Round half-up to the nearest 5 sen (matches the PERKESO tables / MROUND)."""
    return (D(x) / Decimal("0.05")).quantize(Decimal("1"), ROUND_HALF_UP) * Decimal("0.05")


def roundup_ringgit(x) -> Decimal:
    """Round up to the next whole ringgit (EPF Third-Schedule convention)."""
    return D(x).quantize(Decimal("1"), ROUND_CEILING)


def money(x) -> Decimal:
    """Quantise to 2 decimals."""
    return D(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def pct(x) -> str:
    """Human percent, trimming trailing zeros (0.0175 -> '1.75%')."""
    return f"{(D(x) * 100).normalize():f}%"
