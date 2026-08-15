"""PDF generation for individual payslips and full run summaries (reportlab)."""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import store
from .models import Payslip, PayrollRun

NAVY = colors.HexColor("#1F3864")
GREEN = colors.HexColor("#548235")
LIGHT = colors.HexColor("#EAF0F8")
GREY = colors.HexColor("#F2F2F2")

_styles = getSampleStyleSheet()
_H = ParagraphStyle("h", parent=_styles["Title"], textColor=NAVY, fontSize=18, spaceAfter=2)
_SUB = ParagraphStyle("sub", parent=_styles["Normal"], textColor=colors.grey, fontSize=9)
_SEC = ParagraphStyle("sec", parent=_styles["Normal"], textColor=colors.white,
                      fontName="Helvetica-Bold", fontSize=10)
_SMALL = ParagraphStyle("sm", parent=_styles["Normal"], fontSize=8, textColor=colors.grey)


def _m(v) -> str:
    d = Decimal(str(v or 0))
    return f"{d:,.2f}" if d else "-"


def payslip_pdf(slip: Payslip, run: PayrollRun) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"Payslip {slip.name} {run.period_label}")
    el: list = []
    el.append(Paragraph(store.company(), _H))
    el.append(Paragraph(f"Payslip — {run.period_label}", _SUB))
    el.append(Spacer(1, 8))

    info = Table([
        ["Employee", slip.name, "Employee ID", slip.emp_code],
        ["Bank", slip.bank_name or "-", "Account", slip.bank_account or "-"],
        ["Type", slip.employment_type.replace("_", " ").title(),
         "Status", run.status_label],
    ], colWidths=[28 * mm, 62 * mm, 28 * mm, 52 * mm])
    info.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY), ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    el.append(info)
    el.append(Spacer(1, 12))

    def section(title, rows, total_label, total_val, color=NAVY):
        data = [[Paragraph(title, _SEC), ""]]
        for label, val in rows:
            data.append([label, _m(val)])
        data.append([total_label, _m(total_val)])
        t = Table(data, colWidths=[120 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (-1, 0), color),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.lightgrey),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), GREY),
            ("TOPPADDING", (0, 1), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]))
        return t

    base_label = ("Base (daily)" if slip.count_by_day else
                  "Base (hourly)" if slip.hourly else "Basic")
    earnings = [(base_label, slip.base_earning)]
    if slip.allowance_enabled and slip.allowance_total:
        earnings.append(("Allowance", slip.allowance_total))
    if slip.ot_enabled and slip.ot_pay:
        earnings.append(("Overtime pay", slip.ot_pay))
    el.append(section("EARNINGS", earnings, "Gross earnings (incl. OT)",
                      slip.total_remuneration, GREEN))
    el.append(Spacer(1, 8))
    deductions = [("EPF / KWSP", slip.epf_employee), ("SOCSO", slip.socso_employee),
                  ("EIS", slip.eis_employee), ("PCB (tax)", slip.pcb)]
    if slip.deduction_enabled and slip.deduction_amount:
        deductions.append((f"Deduction — {slip.deduction_reason or 'other'}", slip.deduction_amount))
    el.append(section("EMPLOYEE DEDUCTIONS", deductions, "Total deductions",
                      slip.total_employee_deduction, NAVY))
    el.append(Spacer(1, 8))

    net = Table([["NET SALARY (take-home)", _m(slip.net_salary)]],
                colWidths=[120 * mm, 50 * mm])
    net.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    el.append(net)
    el.append(Spacer(1, 10))

    el.append(section("EMPLOYER CONTRIBUTIONS (not deducted from employee)", [
        ("EPF / KWSP (12–13%)", slip.epf_employer), ("SOCSO", slip.socso_employer),
        ("EIS", slip.eis_employer),
    ], "Total employer cost (incl. gross)", slip.employer_cost, colors.HexColor("#7F7F7F")))
    el.append(Spacer(1, 14))
    el.append(Paragraph(
        "Statutory contributions computed per KWSP / PERKESO / LHDN (YA2024/25). "
        "PCB is an MTD estimate — refer to LHDN e-PCB for the official figure. "
        "This is a computer-generated payslip.", _SMALL))
    doc.build(el)
    return buf.getvalue()


def run_summary_pdf(run: PayrollRun, totals: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=14 * mm,
                            bottomMargin=14 * mm, leftMargin=10 * mm, rightMargin=10 * mm,
                            title=f"Payroll {run.period_label}")
    el: list = [Paragraph(f"{store.company()} — Payroll Summary", _H),
                Paragraph(f"{run.period_label} · {run.status_label} · "
                          f"{totals['headcount']} employees", _SUB), Spacer(1, 8)]

    head = ["Code", "Name", "Type", "Gross", "OT", "EPF (e)", "EPF (r)",
            "SOCSO (e)", "SOCSO (r)", "EIS (e)", "PCB", "Net Salary", "Employer Cost"]
    rows = [head]
    for s in sorted(run.payslips, key=lambda x: x.emp_code):
        rows.append([s.emp_code, s.name[:24], s.employment_type[:4], _m(s.gross),
                     _m(s.ot_pay), _m(s.epf_employee), _m(s.epf_employer),
                     _m(s.socso_employee), _m(s.socso_employer), _m(s.eis_employee),
                     _m(s.pcb), _m(s.net_salary), _m(s.employer_cost)])
    rows.append(["", "TOTALS", "", _m(totals["gross"]), _m(totals["ot_pay"]),
                 _m(totals["epf_employee"]), _m(totals["epf_employer"]),
                 _m(totals["socso_employee"]), _m(totals["socso_employer"]),
                 _m(totals["eis_employee"]), _m(totals["pcb"]),
                 _m(totals["net_salary"]), _m(totals["employer_cost"])])

    w = [18, 46, 12] + [21] * 10
    t = Table(rows, colWidths=[x * mm for x in w], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"), ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, GREY]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2EFDA")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY), ("GRID", (0, 1), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    el.append(t)
    el.append(Spacer(1, 8))
    el.append(Paragraph(
        f"Prepared by {run.prepared_by or '—'} · Approved by {run.approved_by or '—'}. "
        "Statutory figures per KWSP/PERKESO/LHDN. PCB is an MTD estimate.", _SMALL))
    doc.build(el)
    return buf.getvalue()
