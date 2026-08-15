import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, money, BADGE } from '../api.js'
import { useApp } from '../App.jsx'

const num = (v) => (v === null || v === undefined || v === '' ? '' : String(+v))

function Cell({ value, onChange, w = 'w-20', editable }) {
  return (
    <input type="number" inputMode="decimal" step="any" readOnly={!editable}
      value={value ?? ''} onChange={(e) => onChange(e.target.value)}
      className={`${w} text-right rounded border border-slate-200 px-1.5 py-1 text-sm ` +
        (!editable ? 'bg-slate-50 text-slate-500' : '')} />
  )
}

function AddStaff({ available, onAdd, onSync }) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [picked, setPicked] = useState(null)
  const options = useMemo(() => available.filter((e) =>
    `${e.name} ${e.emp_code}`.toLowerCase().includes(q.toLowerCase())), [available, q])
  return (
    <div className="bg-white rounded-xl shadow p-3 mb-4 flex flex-col sm:flex-row sm:items-end gap-2">
      <div className="flex-1">
        <label className="block text-[11px] font-medium text-slate-500 mb-1">Add staff — type a name</label>
        <div className="relative">
          <input value={q} autoComplete="off" placeholder="Start typing…"
            onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)}
            onChange={(e) => { setQ(e.target.value); setPicked(null); setOpen(true) }}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          {open && (
            <div className="absolute z-30 mt-1 w-full max-h-64 overflow-auto bg-white border border-slate-200 rounded-lg shadow-lg">
              {options.map((e) => (
                <div key={e.id} onMouseDown={() => { setPicked(e); setQ(`${e.name} ${e.emp_code}`) }}
                  className="px-3 py-2 text-sm hover:bg-slate-100 cursor-pointer">
                  {e.name} <span className="text-slate-400 text-xs">
                    · {e.emp_code} · {e.employment_type === 'full_time'
                      ? `FT ${money(e.basic_salary)}` : `PT ${money(e.hourly_rate)}/hr`}</span>
                </div>
              ))}
              {options.length === 0 && <div className="px-3 py-2 text-sm text-slate-400">No matches</div>}
            </div>
          )}
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => picked && onAdd(picked)}
          className="px-4 py-2 rounded-lg bg-moss text-white text-sm font-semibold">+ Add</button>
        <button onClick={onSync}
          className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm whitespace-nowrap">
          Add all ({available.length})</button>
      </div>
    </div>
  )
}

// Mobile-first entry sheet shown after picking a staff member: key in the pay
// inputs on a phone-sized form, then Confirm adds them to the run.
function AddSheet({ emp, onConfirm, onCancel }) {
  const hourly = emp.employment_type === 'part_time'
  const [f, setF] = useState({
    basic: num(emp.basic_salary), rate: num(emp.hourly_rate), units: '',
    allowance: '', ot_hours: '', ot_rate: num(emp.ot_rate), deduction: '',
  })
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const inp = 'w-full rounded-lg border border-slate-300 px-3 py-3 text-base text-right'
  // render helper (not a component) — keeps input focus across re-renders
  const field = (label, k, ph) => (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <input type="number" inputMode="decimal" step="any" placeholder={ph || '0'}
        value={f[k]} onChange={set(k)} className={inp} />
    </label>
  )
  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-end sm:items-center sm:justify-center"
      onClick={onCancel}>
      <div onClick={(e) => e.stopPropagation()}
        className="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-5 max-h-[92vh] overflow-y-auto">
        <div className="mx-auto w-10 h-1 rounded bg-slate-300 mb-3 sm:hidden" />
        <h2 className="font-bold text-lg">{emp.name}</h2>
        <p className="text-xs text-slate-500 mb-4">{emp.emp_code} · {hourly ? 'Part-time (hourly)' : 'Full-time (monthly)'}</p>
        <div className="space-y-3">
          {hourly ? (
            <div className="grid grid-cols-2 gap-3">
              {field('Hourly rate (RM)', 'rate')}
              {field('Hours worked', 'units')}
            </div>
          ) : (
            field('Basic salary (RM/month)', 'basic')
          )}
          <div className="grid grid-cols-2 gap-3">
            {field('OT hours', 'ot_hours')}
            {field('OT rate (RM/hr)', 'ot_rate')}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {field('Allowance (RM)', 'allowance')}
            {field('Deduction (RM)', 'deduction')}
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onCancel}
            className="flex-1 rounded-xl border border-slate-300 py-3 text-sm font-semibold">Cancel</button>
          <button onClick={() => onConfirm(f)}
            className="flex-[2] rounded-xl bg-moss text-white py-3 text-sm font-semibold">
            Confirm — add to payroll</button>
        </div>
      </div>
    </div>
  )
}

// Small labeled read-only figure — used in the mobile card's computed row.
function Stat({ label, value, className = '' }) {
  return (
    <div className={className}>
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="text-sm font-medium">{money(value)}</div>
    </div>
  )
}

// Mobile-first stacked card: every field fills top-to-bottom, no horizontal
// scrolling. Shown instead of the wide table below the `md` breakpoint.
function SlipCard({ s, editable, setField, isOpen, toggleOpen, onRemove }) {
  const field = (label, k, w) => (
    <label className="block">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <Cell value={num(s[k])} w={w || 'w-full'} editable={editable}
        onChange={(v) => setField(s.id, k, v)} />
    </label>
  )
  return (
    <div className="bg-white rounded-xl shadow p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-semibold">{s.name}</div>
          <div className="text-[11px] text-slate-400 font-mono">{s.emp_code} · {s.hourly ? 'PT' : 'FT'}</div>
        </div>
        {editable &&
          <button onClick={() => onRemove(s)} title="Remove"
            className="text-slate-300 hover:text-red-600 text-sm">✕</button>}
      </div>

      <div className="text-[11px] text-slate-400">
        EPF {s.epf_enabled ? 'on' : 'off'} · SOCSO/EIS {s.socso_enabled ? 'on' : 'off'} · PCB {s.pcb_enabled ? 'on' : 'off'}
        {' '}({s.confirmed ? 'confirmed staff' : 'not confirmed — set on the employee record'})
      </div>

      {s.hourly ? (
        <div className="grid grid-cols-2 gap-3">
          {field('Rate (RM/hr)', 'rate')}
          {field('Hours worked', 'units')}
        </div>
      ) : field('Basic (RM/month)', 'basic')}

      <div className="grid grid-cols-2 gap-3">
        {field('Allowance (RM)', 'allowance')}
        {field('Deduction (RM)', 'deduction')}
      </div>
      <div className="grid grid-cols-2 gap-3">
        {field('OT hours', 'ot_hours')}
        {field('OT rate (RM/hr)', 'ot_rate')}
      </div>

      <div className="grid grid-cols-3 gap-y-3 border-t border-slate-100 pt-3">
        <Stat label="Gross" value={s.total_remuneration} />
        <Stat label="Net OT" value={s.ot_pay} />
        <Stat label="PCB" value={s.pcb} />
        {s.lindung_optin && <Stat label="LINDUNG 24Jam" value={s.lindung_amount} />}
        <Stat label="EPF (staff)" value={s.epf_employee} />
        <Stat label="EPF (employer)" value={s.epf_employer} />
        <Stat label="Net EPF" value={(+s.epf_employee || 0) + (+s.epf_employer || 0)} />
        <Stat label="SOCSO (staff)" value={s.socso_employee} />
        <Stat label="SOCSO (employer)" value={s.socso_employer} />
        <Stat label="EIS (staff)" value={s.eis_employee} />
        <Stat label="EIS (employer)" value={s.eis_employer} />
        <Stat label="Net salary" value={s.net_salary} className="text-emerald-700 font-bold" />
        <Stat label="Employer cost" value={s.employer_cost} />
      </div>

      <button onClick={toggleOpen} className="text-xs text-brand font-medium">
        {isOpen ? '▴ Fewer options' : '▾ More options'}</button>

      {isOpen && (
        <div className="space-y-3 border-t border-slate-100 pt-3">
          {!s.hourly && (
            <label className="flex items-center gap-2 text-sm flex-wrap">
              <input type="checkbox" checked={s.count_by_day} disabled={!editable}
                onChange={(e) => setField(s.id, 'count_by_day', e.target.checked)} />
              Count by day
              {s.count_by_day && (
                <span className="flex items-center gap-1">
                  <Cell value={num(s.rate)} w="w-16" editable={editable}
                    onChange={(v) => setField(s.id, 'rate', v)} /> × days
                  <Cell value={num(s.units)} w="w-14" editable={editable}
                    onChange={(v) => setField(s.id, 'units', v)} />
                </span>
              )}
            </label>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={s.over_60} disabled={!editable}
              onChange={(e) => setField(s.id, 'over_60', e.target.checked)} />
            Age ≥60</label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={s.foreign} disabled={!editable}
              onChange={(e) => setField(s.id, 'foreign', e.target.checked)} />
            Foreign worker</label>
          <label className="block">
            <span className="text-[11px] font-medium text-slate-500">Deduction reason</span>
            <input value={s.deduction_reason || ''} readOnly={!editable}
              onChange={(e) => setField(s.id, 'deduction_reason', e.target.value)}
              className={'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm ' + (!editable ? 'bg-slate-50' : '')} />
          </label>
          <label className="block">
            <span className="text-[11px] font-medium text-slate-500">PCB override</span>
            <Cell value={num(s.pcb_override)} w="w-full" editable={editable}
              onChange={(v) => setField(s.id, 'pcb_override', v)} />
          </label>
          <label className="block">
            <span className="text-[11px] font-medium text-slate-500">Notes</span>
            <input value={s.notes || ''} readOnly={!editable}
              onChange={(e) => setField(s.id, 'notes', e.target.value)}
              className={'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm ' + (!editable ? 'bg-slate-50' : '')} />
          </label>
        </div>
      )}
    </div>
  )
}

export default function PayrollRun() {
  const { runId } = useParams()
  const { user, flash } = useApp()
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [slips, setSlips] = useState([])
  const [remarks, setRemarks] = useState('')
  const [expanded, setExpanded] = useState({})
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectNote, setRejectNote] = useState('')
  const [sheetEmp, setSheetEmp] = useState(null)   // employee being added via the mobile sheet

  const apply = (d) => {
    setDetail(d)
    setSlips(d.slips)
    setRemarks(d.run.remarks || '')
  }

  useEffect(() => {
    api.get(`/api/runs/${runId}`).then(apply).catch((e) => flash(e.message, 'error'))
  }, [runId])

  if (!detail) return null
  const { run, totals, available } = detail
  const editable = run.editable_by_me

  const setField = (id, field, value) =>
    setSlips((ss) => ss.map((s) => (s.id === id ? { ...s, [field]: value } : s)))

  const act = (fn, okMsg) => async () => {
    try {
      const d = await fn()
      if (d?.run) apply(d)
      if (okMsg) flash(typeof okMsg === 'function' ? okMsg(d) : okMsg)
    } catch (e) { flash(e.message, 'error') }
  }

  const save = act(() => api.put(`/api/runs/${runId}`, { remarks, slips }),
    'Payroll recalculated and saved.')
  // Confirm on the mobile sheet: create the slip, then save the keyed-in
  // amounts so the run recalculates before the table is shown.
  const confirmAdd = async (emp, f) => {
    try {
      const d1 = await api.post(`/api/runs/${runId}/slips`, { employee_id: emp.id })
      const slip = d1.slips.find((s) => s.employee_id === emp.id)
      const patch = { id: slip.id }
      for (const k of ['basic', 'rate', 'units', 'allowance', 'ot_hours', 'ot_rate', 'deduction'])
        if (f[k] !== '' && f[k] !== undefined) patch[k] = f[k]
      const d2 = await api.put(`/api/runs/${runId}`, { slips: [patch] })
      apply(d2)
      setSheetEmp(null)
      flash(`${emp.name} added — net RM ${money(d2.slips.find((s) => s.id === slip.id)?.net_salary)}.`)
    } catch (e) { flash(e.message, 'error') }
  }
  const sync = act(() => api.post(`/api/runs/${runId}/sync`),
    (d) => (d.added ? `Added ${d.added} new employee(s).` : 'No new active employees to add.'))
  const remove = (slip) => act(() => api.del(`/api/runs/${runId}/slips/${slip.id}`),
    `Removed ${slip.name} from the payroll.`)()
  const submit = () => window.confirm('Save your edits first. Send for approval now?') &&
    act(() => api.post(`/api/runs/${runId}/submit`), `${run.period_label} sent for approval.`)()
  const approve = () => window.confirm('Approve and lock this payroll?') &&
    act(() => api.post(`/api/runs/${runId}/approve`), `${run.period_label} approved. Payslips are now final.`)()
  const reject = act(() => api.post(`/api/runs/${runId}/reject`, { note: rejectNote }),
    `${run.period_label} returned to the preparer.`)
  const remove_run = async () => {
    if (!window.confirm('Delete this entire payroll run?')) return
    try {
      await api.del(`/api/runs/${runId}`)
      flash(`Deleted payroll run ${run.period_label}.`)
      nav('/payroll')
    } catch (e) { flash(e.message, 'error') }
  }

  return (
    <>
      <div className="mb-1"><Link to="/payroll" className="text-sm text-slate-500 hover:underline">← Payroll</Link></div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">{run.period_label}</h1>
        <span className={'text-xs font-medium px-2 py-1 rounded ' + BADGE[run.status]}>{run.status_label}</span>
        <span className="text-sm text-slate-500">{totals.headcount} staff</span>
        {run.status === 'pending' && user.can_approve &&
          <span className="text-xs text-amber-700">— you can edit and approve below</span>}
        <div className="w-full sm:w-auto sm:ml-auto flex flex-wrap items-center gap-2">
          <Link to={`/payroll/${run.id}/dashboard`} className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm">Dashboard</Link>
          <a href={`/api/runs/${run.id}/pdf`} target="_blank" rel="noreferrer"
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm">PDF</a>
          {run.status !== 'approved' && user.can_prepare &&
            <button onClick={remove_run} className="px-3 py-2 rounded-lg border border-red-200 text-red-600 bg-white text-sm">Delete</button>}
        </div>
      </div>

      {run.status === 'rejected' && run.note &&
        <div className="mb-3 text-sm bg-red-50 border border-red-200 text-red-800 rounded-lg px-3 py-2">
          Returned by approver: {run.note}</div>}

      {rejectOpen && run.status === 'pending' && user.can_approve && (
        <div className="mb-3 bg-white border rounded-lg p-3 flex flex-col sm:flex-row gap-2">
          <input value={rejectNote} onChange={(e) => setRejectNote(e.target.value)}
            placeholder="Reason for returning to preparer…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={reject} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold">
            Return to preparer</button>
        </div>
      )}

      {editable && <AddStaff available={available} onAdd={setSheetEmp} onSync={sync} />}
      {sheetEmp && editable &&
        <AddSheet emp={sheetEmp} onCancel={() => setSheetEmp(null)}
          onConfirm={(f) => confirmAdd(sheetEmp, f)} />}

      {slips.length === 0 ? (
        <div className="bg-white rounded-xl shadow p-10 text-center text-slate-400">
          No staff on this run yet.{editable && ' Add staff above.'}</div>
      ) : (
        <div className="pb-24">
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Stat label="Net Emp Salary" value={totals.net_salary} className="bg-white rounded-xl shadow p-3 text-emerald-700 font-bold" />
            <Stat label="Net Overtime" value={totals.ot_pay} className="bg-white rounded-xl shadow p-3" />
            <Stat label="Net EPF" value={(+totals.epf_employee || 0) + (+totals.epf_employer || 0)} className="bg-white rounded-xl shadow p-3" />
          </div>

          <div className="space-y-3 md:hidden">
            {slips.map((s) => (
              <SlipCard key={s.id} s={s} editable={editable} setField={setField}
                isOpen={!!expanded[s.id]}
                toggleOpen={() => setExpanded((x) => ({ ...x, [s.id]: !x[s.id] }))}
                onRemove={remove} />
            ))}
          </div>

          <div className="hidden md:block bg-white rounded-xl shadow overflow-x-auto">
            <table className="text-xs whitespace-nowrap min-w-full payroll-grid">
              <thead>
                <tr className="bg-brand text-white text-left">
                  <th className="sticky left-0 bg-brand px-3 py-2 z-10">Employee</th>
                  <th className="px-2 py-2 text-right">Basic / Rate·Hrs</th>
                  <th className="px-2 py-2 text-right">Allowance</th>
                  <th className="px-2 py-2 text-right">OT hrs</th>
                  <th className="px-2 py-2 text-right">OT rate</th>
                  <th className="px-2 py-2 text-right">Deduction</th>
                  <th className="px-2 py-2 text-right">Gross</th>
                  <th className="px-2 py-2 text-right" title="Overtime pay earned">Net Overtime</th>
                  <th className="px-2 py-2 text-right" title="Staff EPF deduction">S.EPF</th>
                  <th className="px-2 py-2 text-right" title="Employer EPF contribution">E.EPF</th>
                  <th className="px-2 py-2 text-right" title="Staff + employer EPF">Net EPF</th>
                  <th className="px-2 py-2 text-right" title="Staff SOCSO deduction">S.SOCSO</th>
                  <th className="px-2 py-2 text-right" title="Employer SOCSO contribution">E.SOCSO</th>
                  <th className="px-2 py-2 text-right" title="Staff EIS deduction">S.EIS</th>
                  <th className="px-2 py-2 text-right" title="Employer EIS contribution">E.EIS</th>
                  <th className="px-2 py-2 text-right">PCB</th>
                  <th className="px-2 py-2 text-right" title="LINDUNG 24Jam (placeholder scheme)">LINDUNG</th>
                  <th className="px-2 py-2 text-right bg-moss" title="Take-home pay">Net Emp Salary</th>
                  <th className="px-2 py-2 text-right bg-moss">Emp cost</th>
                  <th className="px-2 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {slips.map((s) => (
                  <React.Fragment key={s.id}>
                    <tr className="border-b hover:bg-slate-50 align-top">
                      <td className="sticky left-0 bg-white px-3 py-2 z-10">
                        <div className="font-medium">{s.name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {s.emp_code} · {s.hourly ? 'PT' : 'FT'} ·{' '}
                          <span className={s.epf_enabled ? 'text-emerald-600' : 'text-slate-300'}>EPF {s.epf_enabled ? 'on' : 'off'}</span>
                          {' '}<span className={s.socso_enabled ? 'text-emerald-600' : 'text-slate-300'}>SOC {s.socso_enabled ? 'on' : 'off'}</span>
                          {!s.confirmed && <span className="text-amber-600"> · not confirmed</span>}
                        </div>
                      </td>
                      <td className="px-2 py-2 text-right">
                        {s.hourly ? (
                          <div className="flex items-center gap-1 justify-end">
                            <Cell value={num(s.rate)} w="w-14" editable={editable}
                              onChange={(v) => setField(s.id, 'rate', v)} />
                            <span className="text-slate-400">×</span>
                            <Cell value={num(s.units)} w="w-14" editable={editable}
                              onChange={(v) => setField(s.id, 'units', v)} />
                          </div>
                        ) : (
                          <Cell value={num(s.basic)} editable={editable}
                            onChange={(v) => setField(s.id, 'basic', v)} />
                        )}
                      </td>
                      <td className="px-2 py-2 text-right">
                        <Cell value={num(s.allowance)} editable={editable}
                          onChange={(v) => setField(s.id, 'allowance', v)} /></td>
                      <td className="px-2 py-2 text-right">
                        <Cell value={num(s.ot_hours)} w="w-14" editable={editable}
                          onChange={(v) => setField(s.id, 'ot_hours', v)} /></td>
                      <td className="px-2 py-2 text-right">
                        <Cell value={num(s.ot_rate)} w="w-14" editable={editable}
                          onChange={(v) => setField(s.id, 'ot_rate', v)} /></td>
                      <td className="px-2 py-2 text-right">
                        <Cell value={num(s.deduction)} editable={editable}
                          onChange={(v) => setField(s.id, 'deduction', v)} /></td>
                      <td className="px-2 py-2 text-right bg-emerald-50/40 font-medium">{money(s.total_remuneration)}</td>
                      <td className="px-2 py-2 text-right">{money(s.ot_pay)}</td>
                      <td className="px-2 py-2 text-right">{money(s.epf_employee)}</td>
                      <td className="px-2 py-2 text-right text-slate-500">{money(s.epf_employer)}</td>
                      <td className="px-2 py-2 text-right font-medium">{money((+s.epf_employee || 0) + (+s.epf_employer || 0))}</td>
                      <td className="px-2 py-2 text-right">{money(s.socso_employee)}</td>
                      <td className="px-2 py-2 text-right text-slate-500">{money(s.socso_employer)}</td>
                      <td className="px-2 py-2 text-right">{money(s.eis_employee)}</td>
                      <td className="px-2 py-2 text-right text-slate-500">{money(s.eis_employer)}</td>
                      <td className="px-2 py-2 text-right">{s.pcb_enabled ? money(s.pcb) : '—'}</td>
                      <td className="px-2 py-2 text-right">{s.lindung_optin ? money(s.lindung_amount) : '—'}</td>
                      <td className="px-2 py-2 text-right font-bold text-emerald-700 bg-emerald-50">{money(s.net_salary)}</td>
                      <td className="px-2 py-2 text-right">{money(s.employer_cost)}</td>
                      <td className="px-2 py-2 text-right whitespace-nowrap">
                        <button onClick={() => setExpanded((x) => ({ ...x, [s.id]: !x[s.id] }))}
                          className="text-slate-400 hover:text-brand" title="More">▾</button>
                        {editable &&
                          <button onClick={() => remove(s)} title="Remove"
                            className="text-slate-300 hover:text-red-600 ml-1">✕</button>}
                      </td>
                    </tr>
                    {expanded[s.id] && (
                      <tr className="bg-slate-50 border-b">
                        <td className="sticky left-0 bg-slate-50 px-3 py-2 z-10 text-[11px] text-slate-400">details</td>
                        <td colSpan="19" className="px-3 py-2">
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px]">
                            {!s.hourly && (
                              <label className="flex items-center gap-1">
                                <input type="checkbox" checked={s.count_by_day} disabled={!editable}
                                  onChange={(e) => setField(s.id, 'count_by_day', e.target.checked)} />
                                Count by day → rate
                                <Cell value={num(s.rate)} w="w-14" editable={editable}
                                  onChange={(v) => setField(s.id, 'rate', v)} />
                                × days
                                <Cell value={num(s.units)} w="w-12" editable={editable}
                                  onChange={(v) => setField(s.id, 'units', v)} />
                              </label>
                            )}
                            <label className="flex items-center gap-1">
                              <input type="checkbox" checked={s.over_60} disabled={!editable}
                                onChange={(e) => setField(s.id, 'over_60', e.target.checked)} />
                              Age ≥60</label>
                            <label className="flex items-center gap-1">
                              <input type="checkbox" checked={s.foreign} disabled={!editable}
                                onChange={(e) => setField(s.id, 'foreign', e.target.checked)} />
                              Foreign</label>
                            <label className="flex items-center gap-1">Deduction reason
                              <input value={s.deduction_reason || ''} readOnly={!editable}
                                onChange={(e) => setField(s.id, 'deduction_reason', e.target.value)}
                                className={'rounded border border-slate-200 px-2 py-1 ' + (!editable ? 'bg-slate-100' : '')} /></label>
                            <label className="flex items-center gap-1">PCB override
                              <Cell value={num(s.pcb_override)} w="w-16" editable={editable}
                                onChange={(v) => setField(s.id, 'pcb_override', v)} /></label>
                            <label className="flex items-center gap-1 flex-1 min-w-[12rem]">Notes
                              <input value={s.notes || ''} readOnly={!editable}
                                onChange={(e) => setField(s.id, 'notes', e.target.value)}
                                className={'flex-1 rounded border border-slate-200 px-2 py-1 ' + (!editable ? 'bg-slate-100' : '')} /></label>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-bold border-t-2 border-slate-300">
                  <td className="sticky left-0 bg-slate-100 px-3 py-2 z-10">TOTALS</td>
                  <td colSpan="5"></td>
                  <td className="px-2 py-2 text-right">{money(totals.total_remuneration)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.ot_pay)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.epf_employee)}</td>
                  <td className="px-2 py-2 text-right text-slate-500">{money(totals.epf_employer)}</td>
                  <td className="px-2 py-2 text-right">{money((+totals.epf_employee || 0) + (+totals.epf_employer || 0))}</td>
                  <td className="px-2 py-2 text-right">{money(totals.socso_employee)}</td>
                  <td className="px-2 py-2 text-right text-slate-500">{money(totals.socso_employer)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.eis_employee)}</td>
                  <td className="px-2 py-2 text-right text-slate-500">{money(totals.eis_employer)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.pcb)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.lindung_amount)}</td>
                  <td className="px-2 py-2 text-right text-emerald-700">{money(totals.net_salary)}</td>
                  <td className="px-2 py-2 text-right">{money(totals.employer_cost)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="bg-white rounded-xl shadow p-4 mt-4">
            <label className="block text-sm font-medium mb-1">Remarks for this payroll (optional)</label>
            <textarea rows="2" value={remarks} readOnly={!editable} placeholder="Notes for the approver…"
              onChange={(e) => setRemarks(e.target.value)}
              className={'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm ' + (!editable ? 'bg-slate-50' : '')} />
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Amounts drive it: type an Allowance / OT / Deduction and it's applied on <b>Save</b>.
            EPF/SOCSO/EIS apply automatically to confirmed (passed-probation) staff only, on basic + allowance —
            OT is never part of the statutory wage. Green = auto-derived.
          </p>

          <div className="fixed bottom-0 inset-x-0 z-20 bg-white/95 backdrop-blur border-t shadow-lg">
            <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center gap-3">
              <div className="text-xs sm:text-sm">
                <div><span className="text-slate-500">Net payout</span>{' '}
                  <b className="text-emerald-700">RM {money(totals.net_salary)}</b></div>
                <div className="text-slate-400 text-[11px] hidden sm:block">
                  Employer cost RM {money(totals.employer_cost)} · {totals.headcount} staff</div>
              </div>
              <div className="ml-auto flex items-center gap-2">
                {editable &&
                  <button onClick={save} className="px-4 py-2.5 rounded-lg bg-brand text-white text-sm font-semibold">
                    Save & Recalculate</button>}
                {(run.status === 'draft' || run.status === 'rejected') && user.can_prepare &&
                  <button onClick={submit} className="px-4 py-2.5 rounded-lg bg-moss text-white text-sm font-semibold">
                    Send →</button>}
                {run.status === 'pending' && user.can_approve && (
                  <>
                    <button onClick={approve} className="px-4 py-2.5 rounded-lg bg-emerald-600 text-white text-sm font-semibold">
                      ✓ Approve</button>
                    <button onClick={() => setRejectOpen((v) => !v)}
                      className="px-3 py-2.5 rounded-lg bg-red-600 text-white text-sm font-semibold">Reject</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
