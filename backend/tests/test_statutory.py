"""Golden regression tests for the statutory Decimal engine.

Ports the former ``app/statutory.py`` self-test (worked scenarios W1-W3 from
``.claude/domain/payroll/statutory.md``) to pytest under the current legislated
rates, and adds the band-edge, rounding, opt-in and age/nationality-branch
cases the audit found unguarded (STAT-02/03/06, GAP-01, QT-01).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app import store
from app.core import eis, kwsp, pcb, socso
from app.core.rates import DEFAULT_CONFIG, money, round5, roundup_ringgit
from app.statutory import PayInputs, compute

D = Decimal


# ---------------------------------------------------------------------------
# Worked scenarios W1-W3 (domain statutory.md), current rates
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_compute_w1_monthly_basic_5000_defaults() -> None:
    """W1: RM5,000 monthly basic with default flags (SOCSO emp 1.25%)."""
    r = compute(PayInputs(basic=D("5000")))
    assert (r.epf_employee, r.epf_employer) == (D("550.00"), D("650.00"))
    assert (r.socso_employee, r.socso_employer) == (D("61.90"), D("86.65"))
    assert (r.eis_employee, r.eis_employer) == (D("9.90"), D("9.90"))
    assert r.pcb == D("110.00")
    assert r.total_employee_deduction == D("731.80")
    assert r.net_salary == D("4268.20")
    assert r.employer_statutory == D("746.55")
    assert r.employer_cost == D("5746.55")


@pytest.mark.unit
def test_compute_w2_daily_rated_allowance_excluded() -> None:
    """W2: RM100/day x 26 days; RM300 allowance paid but not in statutory."""
    r = compute(PayInputs(count_by_day=True, rate=D("100"), units=D("26"),
                          allowance_enabled=True, allowance=D("300")))
    assert r.base_earning == D("2600.00")
    assert r.gross == D("2900.00")
    assert r.statutory_wage == D("2600.00")
    assert (r.epf_employee, r.epf_employer) == (D("286.00"), D("338.00"))


@pytest.mark.unit
def test_compute_w3_hourly_no_statutory() -> None:
    """W3: RM8/hr x 60 hrs part-timer with EPF and SOCSO off."""
    r = compute(PayInputs(hourly=True, rate=D("8"), units=D("60"),
                          epf_enabled=False, socso_enabled=False))
    assert r.net_salary == D("480.00")
    assert r.epf_employee == r.socso_employee == r.eis_employee == D("0.00")
    assert r.pcb == D("0.00")


# ---------------------------------------------------------------------------
# STAT-03: EPF Third-Schedule band widths
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.parametrize(
    ("wage", "expected"),
    [
        (D("0"), D("0")),
        (D("10"), D("20")),
        (D("2550"), D("2560")),          # RM20 bands below RM5,000
        (D("5000"), D("5000")),          # exact low-band edge
        (D("5000.01"), D("5100")),       # RM100 bands start
        (D("5050"), D("5100")),
        (D("5100"), D("5100")),
        (D("5100.01"), D("5200")),
        (D("20000"), D("20000")),        # last RM100 band top
        (D("20000.01"), D("20000.01")),  # above RM20,000: exact wage
    ],
)
def test_epf_band_upper_widths(wage: Decimal, expected: Decimal) -> None:
    assert kwsp.band_upper(wage) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wage", "expected"),
    [
        # (employee, employer) — official KWSP Third Schedule rows
        (D("2550"), (D("282"), D("333"))),
        (D("3350"), (D("370"), D("437"))),
        (D("5000"), (D("550"), D("650"))),      # 13% employer at/below RM5,000
        (D("5000.01"), (D("561"), D("612"))),   # 12% employer above RM5,000
        (D("5050"), (D("561"), D("612"))),      # STAT-03 verification row
        (D("20000"), (D("2200"), D("2400"))),
        (D("20000.01"), (D("2201"), D("2401"))),  # exact wage, roundup each side
    ],
)
def test_epf_contribution_band_edges(
    wage: Decimal, expected: tuple[Decimal, Decimal]
) -> None:
    assert kwsp.contribution(wage) == expected


# ---------------------------------------------------------------------------
# STAT-06: SOCSO/EIS low-band edges and midpoints
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.parametrize(
    ("wage", "midpoint"),
    [
        (D("30"), D("15")),
        (D("30.01"), D("40")),
        (D("50"), D("40")),
        (D("50.01"), D("60")),
        (D("70"), D("60")),
        (D("70.01"), D("85")),
        (D("100"), D("85")),
        (D("100.01"), D("120")),   # official >100-140 band, assumed wage 120
        (D("140"), D("120")),
        (D("140.01"), D("170")),   # official >140-200 band, assumed wage 170
        (D("200"), D("170")),
        (D("200.01"), D("250")),   # RM100 bands resume at RM200
        (D("300"), D("250")),
        (D("5000"), D("4950")),
        (D("6000"), D("5950")),
        (D("7000"), D("5950")),    # capped at the RM6,000 ceiling
    ],
)
def test_socso_band_midpoint_edges(wage: Decimal, midpoint: Decimal) -> None:
    assert socso.band_midpoint(wage) == midpoint


@pytest.mark.unit
def test_socso_contribution_low_band_figures() -> None:
    """RM120 earner sits on the 100-140 band (assumed wage 120), not 150."""
    assert socso.contribution(D("120")) == (D("1.50"), D("2.10"))
    assert eis.contribution(D("120")) == (D("0.25"), D("0.25"))


@pytest.mark.unit
def test_socso_contribution_ceiling() -> None:
    """Wages above RM6,000 charge on the top band's midpoint (RM5,950)."""
    assert socso.contribution(D("7000")) == (D("74.40"), D("104.15"))
    assert socso.contribution(D("6000")) == (D("74.40"), D("104.15"))


@pytest.mark.unit
def test_socso_category_2_and_foreign_are_employer_only() -> None:
    assert socso.contribution(D("5000"), over_60=True) == (D("0"), D("61.90"))
    assert socso.contribution(D("5000"), foreign=True) == (D("0"), D("61.90"))


# ---------------------------------------------------------------------------
# Rounding helpers (R6)
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_rounding_helpers() -> None:
    assert round5(D("61.875")) == D("61.90")     # 5-sen tie rounds half-up
    assert round5(D("0.1875")) == D("0.20")
    assert round5(D("102.35")) == D("102.35")    # already on a 5-sen step
    assert roundup_ringgit(D("281.60")) == D("282")
    assert roundup_ringgit(D("550")) == D("550")  # whole ringgit unchanged
    assert money(D("1.005")) == D("1.01")


# ---------------------------------------------------------------------------
# R1: allowance / OT statutory opt-in
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_allowance_opt_in_changes_statutory_wage_only() -> None:
    base = dict(basic=D("2000"), allowance_enabled=True, allowance=D("500"))
    incl = compute(PayInputs(**base, include_allowance=True))
    excl = compute(PayInputs(**base, include_allowance=False))
    assert incl.gross == excl.gross == D("2500.00")
    assert incl.statutory_wage == D("2500.00")
    assert excl.statutory_wage == D("2000.00")
    assert incl.epf_employee == D("275.00")   # 11% x RM2,500 band
    assert excl.epf_employee == D("220.00")   # 11% x RM2,000 band


@pytest.mark.unit
def test_ot_opt_in_changes_statutory_wage_only() -> None:
    base = dict(basic=D("2000"), ot_enabled=True, ot_hours=D("10"),
                ot_rate=D("15"))
    incl = compute(PayInputs(**base, include_ot=True))
    excl = compute(PayInputs(**base, include_ot=False))
    assert incl.total_remuneration == excl.total_remuneration == D("2150.00")
    assert incl.statutory_wage == D("2150.00")
    assert excl.statutory_wage == D("2000.00")
    assert incl.epf_employee == D("238.00")   # band RM2,160 x 11%, rounded up
    assert excl.epf_employee == D("220.00")


# ---------------------------------------------------------------------------
# GAP-01: age-60 and foreign-worker branches
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_compute_malaysian_over_60_branch() -> None:
    """Malaysian aged 60+: EPF 0%/4%, SOCSO Category 2, no EIS."""
    r = compute(PayInputs(basic=D("5000"), over_60=True))
    assert (r.epf_employee, r.epf_employer) == (D("0.00"), D("200.00"))
    assert (r.socso_employee, r.socso_employer) == (D("0.00"), D("61.90"))
    assert (r.eis_employee, r.eis_employer) == (D("0.00"), D("0.00"))


@pytest.mark.unit
def test_compute_foreign_worker_branch() -> None:
    """Foreign worker: EPF 2%/2%, SOCSO employer-only 1.25%, no EIS."""
    r = compute(PayInputs(basic=D("2600"), foreign=True))
    assert (r.epf_employee, r.epf_employer) == (D("52.00"), D("52.00"))
    assert (r.socso_employee, r.socso_employer) == (D("0.00"), D("31.90"))
    assert (r.eis_employee, r.eis_employer) == (D("0.00"), D("0.00"))


@pytest.mark.unit
def test_foreign_epf_uses_third_schedule_band() -> None:
    """Foreign 2%/2% still charges on the band upper bound (RM5,100)."""
    assert kwsp.contribution(D("5050"), foreign=True) == (D("102"), D("102"))


# ---------------------------------------------------------------------------
# R5: PCB estimate
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_pcb_estimate_and_rebate() -> None:
    assert pcb.estimate(D("5000"), D("550")) == D("110.00")
    # RM2,500 wage: chargeable RM17,700, tax RM127 wiped by the RM400 rebate.
    assert pcb.estimate(D("2500"), D("275")) == D("0.00")


@pytest.mark.unit
def test_pcb_override_wins() -> None:
    r = compute(PayInputs(basic=D("5000"), pcb_override=D("123.45")))
    assert r.pcb == D("123.45")


# ---------------------------------------------------------------------------
# STAT-01 / QT-02: Settings defaults == engine constants (single source)
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_settings_defaults_match_engine_rates(db: Session) -> None:
    """A freshly-defaulted Settings row must equal the rates.py constants."""
    settings = store.get_settings(db)
    for field in store._RATE_FIELDS:
        assert Decimal(getattr(settings, field)) == getattr(
            DEFAULT_CONFIG, field
        ), f"Settings.{field} diverged from core/rates.py"
    # The live compute path builds RateConfig from Settings — it must be
    # indistinguishable from the engine defaults (QT-02 regression).
    assert store.rate_config(db) == DEFAULT_CONFIG


@pytest.mark.unit
def test_settings_socso_c1_emp_is_current_rate(db: Session) -> None:
    """Regression for STAT-01: the stale 0.5% default under-deducted SOCSO."""
    settings = store.get_settings(db)
    assert Decimal(settings.socso_c1_emp) == Decimal("0.0125")
