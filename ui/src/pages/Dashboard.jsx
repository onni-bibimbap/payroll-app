import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, money, money0, BADGE } from '../api.js'
import { useApp } from '../App.jsx'

const SEGS = [
  ['Net', 'net_salary', '#548235'], ['EPF', 'epf_employee', '#1F3864'],
  ['SOCSO', 'socso_employee', '#2E75B6'], ['EIS', 'eis_employee', '#6f9fd8'],
  ['PCB', 'pcb', '#b45309'], ['Deduction', 'deduction_amount', '#9ca3af'],
]

function Card({ label, value, sub, accent = 'text-brand' }) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`text-lg sm:text-2xl font-bold mt-1 break-words ${accent}`}>{value}</div>
      <div className="text-[11px] text-slate-400">{sub}</div>
    </div>
  )
}

export default function Dashboard() {
  const { runId } = useParams()
  const { user, flash } = useApp()
  const nav = useNavigate()
  const [d, setD] = useState(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectNote, setRejectNote] = useState('')

  const load = () => api.get(`/api/runs/${runId}/dashboard`).then(setD)
    .catch((e) => flash(e.message, 'error'))
  useEffect(() => { load() }, [runId])

  if (!d) return null
  const { run, slips, totals, by_bank, breakdowns, settings } = d
  const maxbank = by_bank.length ? by_bank[0].amount : 1
  const pct = (v) => (Number(v) * 100)

  const approve = async () => {
    if (!window.confirm('Approve and lock this payroll?')) return
    try { await api.post(`/api/runs/${runId}/approve`); flash(`${run.period_label} approved.`); load() }
    catch (e) { flash(e.message, 'error') }
  }
  const reject = async () => {
    try {
      await api.post(`/api/runs/${runId}/reject`, { note: rejectNote })
      flash(`${run.period_label} returned to the preparer.`)
      nav(`/payroll/${runId}`)
    } catch (e) { flash(e.message, 'error') }
  }

  const glossary = [
    ['Base earning', 'Monthly basic, or day/hour rate × units for daily/hourly staff.'],
    ['Allowance', 'Extra pay when eligible. Paid to staff; only in statutory if ticked.'],
    ['Overtime', 'OT hours × OT rate. Paid; only in statutory if ticked.'],
    ['Gross', 'Base + allowance + overtime — the total paid before deductions.'],
    ['Statutory wage', 'The base EPF/SOCSO/EIS/PCB are charged on (basic + any included allowance/OT).'],
    ['EPF / KWSP', `Employee ${pct(settings.epf_emp_rate).toFixed(2)}%, employer ${pct(settings.epf_er_rate_low).toFixed(0)}% (≤RM${money0(settings.epf_er_threshold)}) / ${pct(settings.epf_er_rate_high).toFixed(0)}%.`],
    ['SOCSO', `PERKESO band table, ceiling RM${money0(settings.socso_eis_ceiling)}. Cat 1 employee ${pct(settings.socso_c1_emp).toFixed(2)}% + employer ${pct(settings.socso_c1_er).toFixed(2)}%.`],
    ['EIS', `${pct(settings.eis_rate).toFixed(2)}% each side (skipped for age ≥60 & foreign).`],
    ['PCB (tax)', 'MTD estimate on annualised income less reliefs. Override with the LHDN figure.'],
    ['Deduction', 'Manual deduction with a stated reason (e.g. unpaid leave, advance).'],
    ['Net salary', 'Gross − EPF − SOCSO − EIS − PCB − deduction. What the employee receives.'],
    ['Employer cost', 'Gross + employer EPF/SOCSO/EIS. What it costs the company.'],
  ]

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <Link to={`/payroll/${run.id}`} className="text-sm text-slate-500 hover:underline">← {run.period_label}</Link>
        <h1 className="text-xl sm:text-2xl font-bold">Review — {run.period_label}</h1>
        <span className={'text-xs font-medium px-2 py-1 rounded ' + BADGE[run.status]}>{run.status_label}</span>
        <div className="w-full sm:w-auto sm:ml-auto flex flex-wrap gap-2">
          {run.editable_by_me &&
            <Link to={`/payroll/${run.id}`} className="px-3 py-2 rounded-lg bg-brand text-white text-sm font-semibold">✎ Edit payroll</Link>}
          <a href={`/api/runs/${run.id}/pdf`} target="_blank" rel="noreferrer"
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm">Summary PDF</a>
          {run.status === 'pending' && user.can_approve && (
            <>
              <button onClick={approve} className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold">✓ Approve</button>
              <button onClick={() => setRejectOpen((v) => !v)} className="px-3 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold">Reject</button>
            </>
          )}
        </div>
      </div>
      {rejectOpen && (
        <div className="mb-3 bg-white border rounded-lg p-3 flex flex-col sm:flex-row gap-2">
          <input value={rejectNote} onChange={(e) => setRejectNote(e.target.value)}
            placeholder="Reason for returning…" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={reject} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold">Return to preparer</button>
        </div>
      )}
      {run.remarks &&
        <div className="mb-4 text-sm bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-3 py-2">
          <b>Preparer remarks:</b> {run.remarks}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <Card label="Headcount" value={totals.headcount} sub={`${d.full_time} FT · ${d.part_time} PT`} />
        <Card label="Net payout" value={`RM ${money(totals.net_salary)}`} sub="total take-home" accent="text-emerald-700" />
        <Card label="Gross + OT" value={`RM ${money(totals.total_remuneration)}`} sub="total paid" />
        <Card label="Employer cost" value={`RM ${money(totals.employer_cost)}`} sub="incl. statutory" accent="text-moss" />
        <Card label="Net Overtime" value={`RM ${money(totals.ot_pay)}`} sub="OT pay earned" />
        <Card label="Net EPF" value={`RM ${money((+totals.epf_employee || 0) + (+totals.epf_employer || 0))}`}
          sub="staff + employer" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">Statutory totals (employee / employer)</h2>
          <table className="w-full text-sm"><tbody className="divide-y">
            <tr><td className="py-1.5">EPF / KWSP</td><td className="text-right">{money(totals.epf_employee)}</td><td className="text-right text-slate-500">{money(totals.epf_employer)}</td></tr>
            <tr><td className="py-1.5">SOCSO</td><td className="text-right">{money(totals.socso_employee)}</td><td className="text-right text-slate-500">{money(totals.socso_employer)}</td></tr>
            <tr><td className="py-1.5">EIS</td><td className="text-right">{money(totals.eis_employee)}</td><td className="text-right text-slate-500">{money(totals.eis_employer)}</td></tr>
            <tr><td className="py-1.5">PCB (tax)</td><td className="text-right">{money(totals.pcb)}</td><td className="text-right text-slate-300">—</td></tr>
          </tbody></table>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">Net payout by bank</h2>
          <div className="space-y-2 text-sm">
            {by_bank.slice(0, 8).map((b) => (
              <div key={b.bank}>
                <div className="flex justify-between"><span>{b.bank}</span><span className="font-medium">{money(b.amount)}</span></div>
                <div className="h-1.5 bg-slate-100 rounded">
                  <div className="h-1.5 bg-brand-light rounded" style={{ width: `${(b.amount / maxbank * 100).toFixed(1)}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-5 mb-5">
        <h2 className="font-semibold mb-1">What each column means</h2>
        <p className="text-xs text-slate-400 mb-3">Rates below are the live platform settings.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          {glossary.map(([term, desc]) => (
            <div key={term}>
              <div className="font-medium text-brand">{term}</div>
              <div className="text-slate-500 text-[13px]">{desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="font-semibold mb-1">Per-employee breakdown</h2>
        <p className="text-xs text-slate-400 mb-3">
          Tap a row to see how every figure was derived. The bar splits the total paid into take-home and each deduction.</p>
        <div className="space-y-2">
          {slips.map((s) => {
            const total = Number(s.total_remuneration) || 1
            const segs = SEGS.map(([label, key, color]) => ({ label, color, val: Number(s[key] || 0) }))
              .filter((x) => x.val > 0)
            return (
              <details key={s.id} className="border rounded-lg">
                <summary className="cursor-pointer px-3 py-2 flex flex-wrap items-center gap-2 hover:bg-slate-50">
                  <span className="font-medium">{s.name}</span>
                  <span className="text-[11px] text-slate-400 font-mono">{s.emp_code}</span>
                  <span className="ml-auto text-sm">Net <b className="text-emerald-700">RM {money(s.net_salary)}</b>{' '}
                    <span className="text-slate-400 text-xs">/ gross {money(s.total_remuneration)}</span></span>
                </summary>
                <div className="px-3 pb-3">
                  <div className="whitespace-nowrap overflow-hidden rounded my-2 w-full leading-none">
                    {segs.map((x) => (
                      <span key={x.label} className="seg" title={`${x.label}: RM ${money(x.val)}`}
                        style={{ width: `${(x.val / total * 100).toFixed(2)}%`, background: x.color }} />
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-500 mb-2">
                    {segs.map((x) => (
                      <span key={x.label}>
                        <span className="inline-block w-2.5 h-2.5 rounded-sm align-middle" style={{ background: x.color }} />{' '}
                        {x.label} {money(x.val)}</span>
                    ))}
                  </div>
                  <table className="w-full text-sm">
                    <thead className="text-[11px] text-slate-400 text-left">
                      <tr><th className="py-1">Item</th><th className="text-right">Employee</th><th className="text-right">Employer</th></tr>
                    </thead>
                    <tbody className="divide-y">
                      {(breakdowns[s.id] || []).map((row) => (
                        <tr key={row.key}>
                          <td className="py-1.5 align-top">
                            <div className="font-medium">{row.label}</div>
                            <div className="text-[11px] text-slate-400">{row.note}</div>
                          </td>
                          <td className="py-1.5 text-right align-top whitespace-nowrap">{money(row.value)}</td>
                          <td className="py-1.5 text-right align-top whitespace-nowrap text-slate-500">
                            {row.employer !== null && row.employer !== undefined ? money(row.employer) : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {s.notes && <div className="text-[11px] text-slate-500 mt-2"><b>Notes:</b> {s.notes}</div>}
                  <Link to={`/payroll/${run.id}/payslip/${s.id}`} className="text-xs text-brand-light hover:underline">
                    Open payslip →</Link>
                </div>
              </details>
            )
          })}
        </div>
      </div>
    </>
  )
}
