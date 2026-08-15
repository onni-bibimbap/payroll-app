import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, money } from '../api.js'
import { useApp } from '../App.jsx'

export default function Payslip() {
  const { runId, slipId } = useParams()
  const { flash } = useApp()
  const [d, setD] = useState(null)

  useEffect(() => {
    api.get(`/api/runs/${runId}/slips/${slipId}`).then(setD)
      .catch((e) => flash(e.message, 'error'))
  }, [runId, slipId])

  if (!d) return null
  const { slip, run, company } = d
  const baseLabel = slip.count_by_day ? 'Base (daily)' : slip.hourly ? 'Base (hourly)' : 'Basic'

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-3 no-print">
        <Link to={`/payroll/${run.id}`} className="text-sm text-slate-500 hover:underline">← {run.period_label}</Link>
        <div className="ml-auto flex gap-2">
          <a href={`/api/runs/${run.id}/slips/${slip.id}/pdf`} target="_blank" rel="noreferrer"
            className="px-3 py-2 rounded-lg bg-brand text-white text-sm font-semibold">Download PDF</a>
          <button onClick={() => window.print()}
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm">Print</button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-8 print-card">
        <div className="flex items-start justify-between border-b pb-4 mb-4">
          <div>
            <div className="text-2xl font-bold text-brand">{company}</div>
            <div className="text-sm text-slate-500">Payslip — {run.period_label}</div>
          </div>
          <div className="text-right text-sm">
            <div className="font-semibold">{slip.name}</div>
            <div className="text-slate-500 font-mono text-xs">{slip.emp_code}</div>
            <div className="text-slate-500 text-xs">{slip.bank_name || '—'} · {slip.bank_account || '—'}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-xs uppercase tracking-wide text-moss font-semibold mb-2">Earnings</h3>
            <table className="w-full text-sm"><tbody className="divide-y">
              <tr><td className="py-1">{baseLabel}</td><td className="text-right">{money(slip.base_earning)}</td></tr>
              {slip.allowance_enabled && !!slip.allowance_total &&
                <tr><td className="py-1">Allowance</td><td className="text-right">{money(slip.allowance_total)}</td></tr>}
              {slip.ot_enabled && !!slip.ot_pay &&
                <tr><td className="py-1">Overtime pay</td><td className="text-right">{money(slip.ot_pay)}</td></tr>}
              <tr className="font-semibold border-t-2">
                <td className="py-1.5">Gross (incl. OT)</td><td className="text-right">{money(slip.total_remuneration)}</td></tr>
            </tbody></table>
          </div>
          <div>
            <h3 className="text-xs uppercase tracking-wide text-brand font-semibold mb-2">Employee deductions</h3>
            <table className="w-full text-sm"><tbody className="divide-y">
              <tr><td className="py-1">EPF / KWSP</td><td className="text-right">{money(slip.epf_employee)}</td></tr>
              <tr><td className="py-1">SOCSO</td><td className="text-right">{money(slip.socso_employee)}</td></tr>
              <tr><td className="py-1">EIS</td><td className="text-right">{money(slip.eis_employee)}</td></tr>
              <tr><td className="py-1">PCB (tax)</td><td className="text-right">{money(slip.pcb)}</td></tr>
              {slip.deduction_enabled && !!slip.deduction_amount &&
                <tr><td className="py-1">Deduction — {slip.deduction_reason || 'other'}</td>
                  <td className="text-right">{money(slip.deduction_amount)}</td></tr>}
              <tr className="font-semibold border-t-2">
                <td className="py-1.5">Total deductions</td><td className="text-right">{money(slip.total_employee_deduction)}</td></tr>
            </tbody></table>
          </div>
        </div>

        <div className="mt-5 rounded-xl bg-moss text-white px-5 py-4 flex items-center justify-between">
          <span className="font-semibold">NET SALARY (take-home)</span>
          <span className="text-2xl font-bold">RM {money(slip.net_salary)}</span>
        </div>

        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-wide text-slate-400 font-semibold mb-2">
            Employer contributions (not deducted)</h3>
          <div className="grid grid-cols-4 gap-3 text-sm">
            {[['EPF', slip.epf_employer], ['SOCSO', slip.socso_employer],
              ['EIS', slip.eis_employer], ['Total cost', slip.employer_cost]].map(([k, v]) => (
              <div key={k} className="bg-slate-50 rounded-lg p-2">
                <div className="text-xs text-slate-400">{k}</div>
                <div className="font-semibold">{money(v)}</div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-[11px] text-slate-400 mt-5 border-t pt-3">
          Statutory contributions computed per KWSP / PERKESO / LHDN (YA2024/25). PCB is an MTD estimate —
          refer to LHDN e-PCB for the official figure. Computer-generated payslip.
        </p>
      </div>
    </div>
  )
}
