import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'

// field -> kind; pct fields are fractions in the API, shown as % here
const KINDS = {
  company_name: 'str', default_work_days: 'int', default_ot_rate: 'money',
  epf_emp_rate: 'pct', epf_er_rate_low: 'pct', epf_er_rate_high: 'pct',
  epf_er_threshold: 'money', socso_eis_ceiling: 'money',
  socso_c1_emp: 'pct', socso_c1_er: 'pct', socso_c2_er: 'pct', eis_rate: 'pct',
  personal_relief: 'money', epf_relief_cap: 'money',
  tax_rebate: 'money', rebate_ceiling: 'money',
  lindung_24jam_rate: 'money',
}

export default function Settings() {
  const { flash, setCompany } = useApp()
  const [form, setForm] = useState(null)   // display values (% for pct)
  const [unlocked, setUnlocked] = useState(false)

  useEffect(() => {
    api.get('/api/settings').then((s) => {
      const f = {}
      for (const [k, kind] of Object.entries(KINDS)) {
        f[k] = kind === 'pct' ? String(+((Number(s[k]) * 100).toFixed(6))) : (kind === 'bool' ? !!s[k] : String(s[k] ?? ''))
      }
      setForm(f)
    }).catch((e) => flash(e.message, 'error'))
  }, [])

  if (!form) return null

  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    const body = {}
    for (const [k, kind] of Object.entries(KINDS)) {
      if (kind === 'bool') body[k] = !!form[k]
      else if (kind === 'pct') body[k] = Number(form[k] || 0) / 100
      else if (kind === 'int') body[k] = parseInt(form[k] || '26', 10)
      else if (kind === 'money') body[k] = Number(form[k] || 0)
      else body[k] = form[k]
    }
    try {
      const s = await api.put('/api/settings', body)
      setCompany(s.company_name)
      flash('Settings saved. New rates apply to payroll recalculated from now on.')
    } catch (err) { flash(err.message, 'error') }
  }

  const money = (label, k, hint = '') => (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
      <div className="flex items-center rounded-lg border border-slate-300 overflow-hidden bg-white">
        <span className="px-2 text-slate-400 text-sm bg-slate-50 py-2">RM</span>
        <input type="number" step="any" value={form[k]} onChange={set(k)} readOnly={!unlocked}
          className={'flex-1 px-2 py-2 text-sm outline-none ' + (!unlocked ? 'bg-slate-50' : '')} />
      </div>
      {hint && <div className="text-[11px] text-slate-400 mt-0.5">{hint}</div>}
    </div>
  )
  const pct = (label, k, hint = '') => (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
      <div className="flex items-center rounded-lg border border-slate-300 overflow-hidden bg-white">
        <input type="number" step="any" value={form[k]} onChange={set(k)} readOnly={!unlocked}
          className={'flex-1 px-2 py-2 text-sm outline-none ' + (!unlocked ? 'bg-slate-50' : '')} />
        <span className="px-2 text-slate-400 text-sm bg-slate-50 py-2">%</span>
      </div>
      {hint && <div className="text-[11px] text-slate-400 mt-0.5">{hint}</div>}
    </div>
  )
  const check = (label, k) => (
    <label className="flex items-center gap-2">
      <input type="checkbox" checked={!!form[k]} onChange={set(k)} /> {label}
    </label>
  )

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Platform Settings</h1>
      <p className="text-sm text-slate-500 mb-5">Defaults applied across the whole platform. Statutory rates
        feed every EPF / SOCSO / EIS / PCB calculation. Changes apply to any payroll{' '}
        <b>recalculated after saving</b>; already-approved runs keep the rates they were approved with.</p>

      <form onSubmit={submit} className="space-y-5">
        <section className="bg-white rounded-xl shadow p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">Statutory rates</h2>
              <p className="text-xs text-slate-400">Read-only until unlocked to avoid accidental changes.</p>
            </div>
            <label className="flex items-center gap-2 text-xs text-red-600 whitespace-nowrap">
              <input type="checkbox" checked={unlocked} onChange={(e) => setUnlocked(e.target.checked)} />
              Unlock rates to edit</label>
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">General</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Company name (payslips & PDFs)</label>
              <input value={form.company_name} onChange={set('company_name')}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Default working days / month</label>
              <input type="number" value={form.default_work_days} onChange={set('default_work_days')}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            {money('Default OT rate (fallback)', 'default_ot_rate', 'Used when an employee has no OT rate set')}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">EPF / KWSP</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {pct('Employee rate', 'epf_emp_rate')}
            {pct('Employer rate (≤ threshold)', 'epf_er_rate_low')}
            {pct('Employer rate (> threshold)', 'epf_er_rate_high')}
            {money('Employer rate threshold', 'epf_er_threshold', '13% at/below, 12% above')}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">SOCSO / EIS</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {money('Wage ceiling', 'socso_eis_ceiling', 'Contribution capped at this wage')}
            {pct('SOCSO Cat 1 employee', 'socso_c1_emp')}
            {pct('SOCSO Cat 1 employer', 'socso_c1_er')}
            {pct('SOCSO Cat 2 employer (age ≥60)', 'socso_c2_er')}
            {pct('EIS rate (each side)', 'eis_rate')}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-3">PCB (income tax) reliefs</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {money('Personal relief / yr', 'personal_relief')}
            {money('EPF relief cap / yr', 'epf_relief_cap')}
            {money('Rebate', 'tax_rebate')}
            {money('Rebate ceiling', 'rebate_ceiling', 'Rebate applies at/below this chargeable income')}
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Resident tax brackets are fixed to YA2024/2025.
            PCB remains an MTD estimate; use the per-line PCB override for the official LHDN figure.</p>
        </section>

        <p className="text-xs text-slate-400">
          EPF/SOCSO/EIS apply automatically to confirmed (passed-probation) staff only, on
          basic + allowance — this is fixed platform-wide and set per employee, not here.
        </p>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold mb-1">LINDUNG 24Jam</h2>
          <p className="text-xs text-slate-400 mb-3">
            Placeholder scheme — rate not yet confirmed with the official PERKESO circular.
            Leave at RM0 until confirmed; it deducts nothing at RM0 even for opted-in staff.
          </p>
          <div className="grid md:grid-cols-4 gap-4">
            {money('Monthly rate (RM, employee-paid)', 'lindung_24jam_rate')}
          </div>
        </section>

        <div className="flex items-center gap-3">
          <button className="bg-brand hover:bg-brand-light text-white font-semibold rounded-lg px-6 py-2.5">
            Save settings</button>
          <span className="text-xs text-slate-400">Percentages are entered as whole numbers (e.g. 11 = 11%).</span>
        </div>
      </form>
    </div>
  )
}
