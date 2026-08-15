import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useApp } from '../App.jsx'

const EMPTY = {
  emp_code: '', name: '', employment_type: 'full_time',
  basic_salary: '0', hourly_rate: '0', ot_rate: '0',
  bank_name: '', bank_account: '', email: '', phone: '', nric: '',
  dob: '', position: '', epf_enabled: false, socso_enabled: false, pcb_enabled: true,
  allowance_eligible: false, is_foreign: false, active: true, clear_review: false,
  is_confirmed: false, lindung_optin: false,
}

export default function EmployeeForm() {
  const { empId } = useParams()
  const isNew = !empId
  const { flash } = useApp()
  const nav = useNavigate()
  const [emp, setEmp] = useState(null)     // loaded employee (edit mode)
  const [form, setForm] = useState(EMPTY)

  useEffect(() => {
    if (isNew) return
    api.get(`/api/employees/${empId}`).then((e) => {
      setEmp(e)
      setForm({
        ...EMPTY, ...Object.fromEntries(Object.entries(e).map(([k, v]) => [k, v ?? ''])),
        basic_salary: String(e.basic_salary ?? 0), hourly_rate: String(e.hourly_rate ?? 0),
        ot_rate: String(e.ot_rate ?? 0), dob: e.dob || '', clear_review: false,
      })
    }).catch((err) => flash(err.message, 'error'))
  }, [empId])

  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const setConfirmed = (e) => {
    const on = e.target.checked
    // EPF/SOCSO only apply once confirmed; default both on when confirming,
    // force both off when un-confirming (exemptions only make sense while confirmed)
    setForm((f) => ({ ...f, is_confirmed: on, epf_enabled: on, socso_enabled: on }))
  }

  const setType = (e) =>
    setForm((f) => ({ ...f, employment_type: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    try {
      const saved = await api.post('/api/employees', { ...form, id: emp?.id })
      flash(`Saved ${saved.name} (${saved.emp_code}).`)
      nav('/employees')
    } catch (err) { flash(err.message, 'error') }
  }

  if (!isNew && !emp) return null

  // plain render helpers (not components — keeps input focus across re-renders)
  const field = (label, k, type = 'text', ph = '') => (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <input type={type} value={form[k] ?? ''} onChange={set(k)} placeholder={ph}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-light outline-none" />
    </div>
  )
  const check = (label, k, cls = '') => (
    <label className={'flex items-center gap-2 ' + cls}>
      <input type="checkbox" checked={!!form[k]} onChange={set(k)} /> {label}
    </label>
  )

  return (
    <div className="max-w-3xl mx-auto">
      <Link to="/employees" className="text-sm text-slate-500 hover:underline">← Employees</Link>
      <h1 className="text-2xl font-bold mb-1 mt-1">{emp ? 'Edit employee' : 'New employee'}</h1>
      {emp?.needs_review && (
        <div className="mb-3 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-3 py-2">
          ⚠ Imported with low confidence: {emp.import_note}
        </div>
      )}

      <form onSubmit={submit} className="bg-white rounded-xl shadow p-6 grid grid-cols-2 gap-4">
        {field('Employee code', 'emp_code', 'text', 'e.g. ONNI0059')}
        {field('Full name', 'name')}

        <div>
          <label className="block text-sm font-medium mb-1">Employment type</label>
          <select value={form.employment_type} onChange={setType}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white">
            <option value="full_time">Full-time (monthly)</option>
            <option value="part_time">Part-time (hourly)</option>
          </select>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {field('Basic salary (RM/mth)', 'basic_salary', 'number')}
          {field('Hourly rate (RM/hr)', 'hourly_rate', 'number')}
          {field('OT rate (RM/hr, 0=default)', 'ot_rate', 'number')}
        </div>

        {field('Bank name', 'bank_name')}
        {field('Bank account', 'bank_account')}
        {field('Email', 'email', 'email')}
        {field('Phone', 'phone')}
        {field('NRIC / Passport', 'nric')}
        {field('Date of birth', 'dob', 'date')}
        {field('Position', 'position')}

        <div className="col-span-2 border-t pt-4">
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5" checked={!!form.is_confirmed}
              onChange={setConfirmed} />
            <span>
              <span className="font-medium">Confirmed / permanent staff</span>
              <span className="block text-xs text-slate-500">
                Passed probation — EPF, SOCSO/EIS and PCB can apply, on basic + allowance
                (OT never counts toward statutory wage). Uncheck either below to exempt.
              </span>
            </span>
          </label>
          {form.is_confirmed && (
            <div className="flex gap-4 mt-2 ml-6 text-sm">
              {check('Apply EPF', 'epf_enabled')}
              {check('Apply SOCSO/EIS', 'socso_enabled')}
            </div>
          )}
        </div>

        <div className="col-span-2 grid grid-cols-2 md:grid-cols-4 gap-3 border-t pt-4 text-sm">
          {check('Eligible for allowance', 'allowance_eligible')}
          {check('Foreign worker', 'is_foreign')}
          {check('Active', 'active')}
          {check('Apply PCB', 'pcb_enabled')}
          {emp?.needs_review && check('Mark reviewed', 'clear_review', 'text-amber-700')}
        </div>
        <p className="col-span-2 -mt-2 text-xs text-slate-400">
          PCB (income tax) applies regardless of confirmation status — uncheck to exempt
          this person entirely (e.g. non-resident on a different tax arrangement).
        </p>

        <div className="col-span-2 border-t pt-4">
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5" checked={!!form.lindung_optin}
              onChange={set('lindung_optin')} />
            <span>
              <span className="font-medium">Opt in to LINDUNG 24Jam</span>
              <span className="block text-xs text-slate-500">
                Placeholder scheme — rate is set in Settings (RM0 until confirmed with PERKESO).
                Deducted from pay only once both this is checked and a rate is set.
              </span>
            </span>
          </label>
        </div>

        <div className="col-span-2 flex gap-3 pt-2">
          <button className="bg-brand hover:bg-brand-light text-white font-semibold rounded-lg px-5 py-2.5">
            Save employee</button>
          <Link to="/employees" className="px-5 py-2.5 rounded-lg border border-slate-300">Cancel</Link>
        </div>
      </form>
    </div>
  )
}
