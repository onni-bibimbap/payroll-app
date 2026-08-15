import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, money, BADGE, MONTHS } from '../api.js'
import { useApp } from '../App.jsx'

export default function PayrollList() {
  const { user, flash } = useApp()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [workDays, setWorkDays] = useState(26)

  useEffect(() => {
    api.get('/api/runs').then((d) => {
      setData(d)
      setMonth(d.this_month); setYear(d.this_year); setWorkDays(d.default_work_days)
    }).catch((e) => flash(e.message, 'error'))
  }, [])

  const create = async (e) => {
    e.preventDefault()
    try {
      const run = await api.post('/api/runs', { year, month, work_days: workDays })
      flash(`Created ${run.period_label}. Add employees by name, or use 'Add all active'.`)
      nav(`/payroll/${run.id}`)
    } catch (err) {
      flash(err.message, 'error')
      if (err.data?.run_id) nav(`/payroll/${err.data.run_id}`)
    }
  }

  if (!data) return null
  return (
    <>
      <div className="flex items-center mb-4">
        <h1 className="text-2xl font-bold">Monthly Payroll</h1>
        <span className="ml-3 text-sm text-slate-500">{data.active_emps} active employees</span>
      </div>

      {user.can_prepare && (
        <form onSubmit={create} className="bg-white rounded-xl shadow p-4 mb-5 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Month</label>
            <select value={month} onChange={(e) => setMonth(+e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white">
              {MONTHS.slice(1).map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Year</label>
            <input type="number" value={year} onChange={(e) => setYear(+e.target.value)}
              className="w-24 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Working days</label>
            <input type="number" value={workDays} onChange={(e) => setWorkDays(+e.target.value)}
              className="w-20 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <button className="bg-moss text-white font-semibold rounded-lg px-5 py-2.5">+ Create payroll run</button>
          <span className="text-xs text-slate-400">Generates a draft payslip for every active employee.</span>
        </form>
      )}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-left">
            <tr className="border-b">
              <th className="px-4 py-2.5">Period</th><th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5 text-right">Headcount</th>
              <th className="px-4 py-2.5 text-right">Net payout</th>
              <th className="px-4 py-2.5 text-right">Employer cost</th>
              <th className="px-4 py-2.5">Prepared / Approved</th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.runs.length === 0 && (
              <tr><td colSpan="7" className="px-4 py-8 text-center text-slate-400">
                No payroll runs yet. Create one above.</td></tr>
            )}
            {data.runs.map((r) => (
              <tr key={r.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-4 py-3 font-semibold">
                  <Link to={`/payroll/${r.id}`} className="hover:underline">{r.period_label}</Link></td>
                <td className="px-4 py-3">
                  <span className={'text-xs font-medium px-2 py-1 rounded ' + BADGE[r.status]}>{r.status_label}</span></td>
                <td className="px-4 py-3 text-right">{r.totals.headcount}</td>
                <td className="px-4 py-3 text-right font-medium">{money(r.totals.net_salary)}</td>
                <td className="px-4 py-3 text-right">{money(r.totals.employer_cost)}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{r.prepared_by || '—'} / {r.approved_by || '—'}</td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <Link to={`/payroll/${r.id}`} className="text-brand-light hover:underline">Open</Link>
                  <Link to={`/payroll/${r.id}/dashboard`} className="text-brand-light hover:underline ml-2">Dashboard</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
