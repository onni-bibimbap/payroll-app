"""Payroll orchestrator — combines the core KWSP/SOCSO/EIS/PCB modules.

There is a single **statutory wage** that every contribution is charged on: the
base earning (monthly basic, or rate × units for daily/hourly), plus allowance
and/or overtime only when they are opted in. Allowances and overtime are always
*paid* to the employee; they just do not attract statutory unless included.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from .core import eis, kwsp, pcb, socso
from .core.rates import (DEFAULT_CONFIG, D, RateConfig, money,  # re-exported
                         round5, roundup_ringgit)

__all__ = ["RateConfig", "DEFAULT_CONFIG", "PayInputs", "PayResult", "compute",
           "kwsp", "socso", "eis", "pcb"]


@dataclass
class PayInputs:
    basic: Decimal = Decimal("0")          # monthly basic (from the salary record)
    count_by_day: bool = False             # base = rate × units (days)
    hourly: bool = False                   # base = rate × units (hours) — part-timers
    rate: Decimal = Decimal("0")           # day/hour rate
    units: Decimal = Decimal("0")          # days/hours worked
    allowance_enabled: bool = False
    allowance: Decimal = Decimal("0")
    deduction_enabled: bool = False
    deduction: Decimal = Decimal("0")
    ot_enabled: bool = False
    ot_hours: Decimal = Decimal("0")
    ot_rate: Decimal = Decimal("0")
    epf_enabled: bool = True               # KWSP
    socso_enabled: bool = True
    include_allowance: bool = False        # add allowance to the statutory wage
    include_ot: bool = False               # add OT to the statutory wage
    over_60: bool = False
    foreign: bool = False
    pcb_override: Decimal | None = None


@dataclass
class PayResult:
    base_earning: Decimal
    allowance_total: Decimal
    gross: Decimal                 # base + allowance
    ot_pay: Decimal
    total_remuneration: Decimal    # gross + OT (total paid)
    statutory_wage: Decimal        # base for EPF / SOCSO / EIS / PCB
    epf_employee: Decimal
    epf_employer: Decimal
    socso_employee: Decimal
    socso_employer: Decimal
    eis_employee: Decimal
    eis_employer: Decimal
    chargeable_income: Decimal
    pcb: Decimal
    deduction_amount: Decimal
    total_employee_deduction: Decimal
    net_salary: Decimal
    employer_statutory: Decimal
    employer_cost: Decimal

    def as_floats(self) -> dict:
        return {k: float(v) for k, v in asdict(self).items()}


def base_earning(inp: PayInputs) -> Decimal:
    """The pay before allowances/OT: rate × units for daily/hourly, else basic."""
    if inp.hourly or inp.count_by_day:
        return D(inp.rate) * D(inp.units)
    return D(inp.basic)


def compute(inp: PayInputs, cfg: RateConfig = DEFAULT_CONFIG) -> PayResult:
    base = base_earning(inp)
    allowance = D(inp.allowance) if inp.allowance_enabled else Decimal("0")
    gross = base + allowance
    ot_pay = (D(inp.ot_hours) * D(inp.ot_rate)) if inp.ot_enabled else Decimal("0")
    total = gross + ot_pay

    stat = base
    if inp.include_allowance:
        stat += allowance
    if inp.include_ot:
        stat += ot_pay

    epf_e, epf_r = kwsp.contribution(stat, inp.epf_enabled, cfg)
    soc_e, soc_r = socso.contribution(stat, inp.over_60, inp.socso_enabled, cfg)
    eis_e, eis_r = eis.contribution(stat, inp.over_60, inp.foreign, inp.socso_enabled, cfg)
    ci = pcb.chargeable_income(stat, epf_e, cfg)
    pcb_amt = D(inp.pcb_override) if inp.pcb_override is not None else pcb.estimate(stat, epf_e, cfg)

    deduction = D(inp.deduction) if inp.deduction_enabled else Decimal("0")
    ee_deduction = epf_e + soc_e + eis_e + pcb_amt + deduction
    er_statutory = epf_r + soc_r + eis_r

    return PayResult(
        base_earning=money(base), allowance_total=money(allowance), gross=money(gross),
        ot_pay=money(ot_pay), total_remuneration=money(total), statutory_wage=money(stat),
        epf_employee=money(epf_e), epf_employer=money(epf_r),
        socso_employee=money(soc_e), socso_employer=money(soc_r),
        eis_employee=money(eis_e), eis_employer=money(eis_r),
        chargeable_income=money(ci), pcb=money(pcb_amt), deduction_amount=money(deduction),
        total_employee_deduction=money(ee_deduction), net_salary=money(total - ee_deduction),
        employer_statutory=money(er_statutory), employer_cost=money(total + er_statutory),
    )


if __name__ == "__main__":   # self-test against known figures
    r = compute(PayInputs(basic=Decimal("5000")))
    assert (r.epf_employee, r.epf_employer) == (550, 650), r
    assert (r.socso_employee, r.socso_employer) == (Decimal("24.75"), Decimal("86.65")), r
    assert r.eis_employee == Decimal("9.90") and r.pcb == Decimal("110.00"), r
    assert r.net_salary == Decimal("4305.35") and r.employer_cost == Decimal("5746.55"), r

    # daily-rated: 100/day × 26 days = 2,600 base; allowance excluded from statutory
    d = compute(PayInputs(count_by_day=True, rate=Decimal("100"), units=Decimal("26"),
                          allowance_enabled=True, allowance=Decimal("300")))
    assert d.base_earning == Decimal("2600.00") and d.gross == Decimal("2900.00"), d
    assert d.statutory_wage == Decimal("2600.00") and d.epf_employee == 286, d   # 2600*11%

    # hourly part-timer: 8/hr × 60 hrs, no statutory
    h = compute(PayInputs(hourly=True, rate=Decimal("8"), units=Decimal("60"),
                          epf_enabled=False, socso_enabled=False))
    assert h.net_salary == Decimal("480.00") and h.epf_employee == 0, h
    print("statutory self-test OK:", r.as_floats())
