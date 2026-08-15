import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useApp } from '../App.jsx'

const SEV = { blocker: 'bg-red-100 text-red-700', warning: 'bg-amber-100 text-amber-800', info: 'bg-slate-100 text-slate-600' }
const inputCls = 'w-full rounded border border-slate-300 px-2 py-1.5 text-sm'

export default function HRDetail() {
  const { empId } = useParams()
  const { flash } = useApp()
  const [d, setD] = useState(null)
  const [approve, setApprove] = useState({ open: false, pay_type: 'monthly', basic_salary: '', hourly_rate: '', hire_date: new Date().toISOString().slice(0, 10) })
  const [resign, setResign] = useState({ open: false, resignation_notice_date: '', last_working_day: '' })

  const load = useCallback(() => api.get(`/api/hr/employees/${empId}`).then(setD).catch((e) => flash(e.message, 'error')), [empId])
  useEffect(() => { load() }, [load])
  if (!d) return null
  const e = d.employee
  const act = (fn) => async (...args) => {
    try { await fn(...args); await load() } catch (err) { flash(err.message, 'error') }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/hr" className="text-sm text-brand-light underline">← Queue</Link>
        <h1 className="text-xl font-bold">{e.name}</h1>
        <span className="font-mono text-xs text-slate-500">{e.emp_code}</span>
        <span className="text-xs rounded px-2 py-0.5 bg-slate-200">{e.status}</span>
        {(e.status === 'pending_review' || e.status === 'applicant') && <>
          <button onClick={() => setApprove((a) => ({ ...a, open: !a.open, pay_type: e.employment_type === 'part_time' ? 'hourly' : 'monthly' }))}
            className="ml-auto rounded bg-emerald-600 text-white text-sm px-3 py-1.5">Approve…</button>
          <button onClick={act(async () => { if (confirm('Reject this application?')) await api.post(`/api/hr/employees/${e.id}/reject`, { reason: prompt('Reason?') || '' }) })}
            className="rounded bg-red-600 text-white text-sm px-3 py-1.5">Reject</button>
        </>}
        {e.status === 'active' &&
          <button onClick={() => setResign((r) => ({ ...r, open: !r.open }))}
            className="ml-auto rounded bg-amber-600 text-white text-sm px-3 py-1.5">Resignation…</button>}
      </div>

      {approve.open && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 grid sm:grid-cols-5 gap-3 items-end">
          <label className="text-sm">Pay type
            <select className={inputCls} value={approve.pay_type} onChange={(ev) => setApprove((a) => ({ ...a, pay_type: ev.target.value }))}>
              <option value="monthly">monthly</option><option value="hourly">hourly</option>
            </select></label>
          {approve.pay_type === 'monthly'
            ? <label className="text-sm">Basic (RM)<input className={inputCls} inputMode="decimal" value={approve.basic_salary} onChange={(ev) => setApprove((a) => ({ ...a, basic_salary: ev.target.value }))} /></label>
            : <label className="text-sm">Hourly (RM)<input className={inputCls} inputMode="decimal" value={approve.hourly_rate} onChange={(ev) => setApprove((a) => ({ ...a, hourly_rate: ev.target.value }))} /></label>}
          <label className="text-sm">Hire date<input type="date" className={inputCls} value={approve.hire_date} onChange={(ev) => setApprove((a) => ({ ...a, hire_date: ev.target.value }))} /></label>
          <button onClick={act(async () => {
            const body = { pay_type: approve.pay_type, hire_date: approve.hire_date }
            if (approve.pay_type === 'monthly') body.basic_salary = +approve.basic_salary
            else body.hourly_rate = +approve.hourly_rate
            await api.post(`/api/hr/employees/${e.id}/approve`, body)
            flash(`Approved — ${e.emp_code} is now active.`)
          })} className="rounded bg-emerald-600 text-white text-sm px-3 py-2">Confirm approve</button>
          <p className="text-xs text-slate-500 sm:col-span-5">
            Requires: no open blocker flags, a verified bank account, and a position.
          </p>
        </div>
      )}

      {resign.open && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 grid sm:grid-cols-4 gap-3 items-end">
          <label className="text-sm">Notice date<input type="date" className={inputCls} value={resign.resignation_notice_date} onChange={(ev) => setResign((r) => ({ ...r, resignation_notice_date: ev.target.value }))} /></label>
          <label className="text-sm">Last working day<input type="date" className={inputCls} value={resign.last_working_day} onChange={(ev) => setResign((r) => ({ ...r, last_working_day: ev.target.value }))} /></label>
          <button onClick={act(async () => {
            await api.post(`/api/hr/employees/${e.id}/resign`, resign)
            flash('Marked as resigned.')
          })} className="rounded bg-amber-600 text-white text-sm px-3 py-2">Confirm resignation</button>
        </div>
      )}

      <section className="grid md:grid-cols-2 gap-5">
        <Card title="Submitted data">
          <Info k="Identity" v={`${e.identity_type} · ${e.nric || '—'}`} />
          <Info k="DOB" v={e.dob} /><Info k="Phone" v={e.phone} /><Info k="Email" v={e.email} />
          <Info k="Address" v={e.residential_address} />
          <Info k="Position" v={`${e.position || '—'} (${e.employment_type})`} />
          <Info k="Outlet" v={e.outlet} /><Info k="Nationality" v={e.nationality} />
          <Info k="Hire date" v={e.hire_date} /><Info k="Last working day" v={e.last_working_day} />
        </Card>

        <Card title={`Flags (${d.flags.filter((f) => f.status === 'open').length} open)`}>
          {d.flags.map((f) => (
            <div key={f.id} className="flex items-start gap-2 py-1.5 border-b border-slate-100 last:border-0 text-sm">
              <span className={'text-xs rounded px-1.5 py-0.5 shrink-0 ' + (SEV[f.severity] || SEV.info)}>{f.severity}</span>
              <div className="flex-1">
                <span className="font-medium">{f.flag_type}</span>
                {f.details?.note && <span className="block text-xs text-slate-500">{f.details.note}</span>}
              </div>
              {f.status === 'open' ? (
                <span className="flex gap-1 shrink-0">
                  <button onClick={act(() => api.post(`/api/hr/flags/${f.id}/resolve`))} className="text-xs rounded bg-emerald-600 text-white px-2 py-0.5">resolve</button>
                  <button onClick={act(() => api.post(`/api/hr/flags/${f.id}/dismiss`))} className="text-xs rounded bg-slate-400 text-white px-2 py-0.5">dismiss</button>
                </span>
              ) : <span className="text-xs text-slate-400">{f.status}</span>}
            </div>
          ))}
        </Card>

        <Card title="Bank accounts">
          {d.bank_accounts.length === 0 && <p className="text-sm text-slate-500">None on record.</p>}
          {d.bank_accounts.map((b) => (
            <div key={b.id} className="flex items-center gap-2 py-1.5 text-sm border-b border-slate-100 last:border-0">
              <span className="font-medium">{b.bank_name}</span>
              <span className="font-mono">{b.account_no}</span>
              <span className="text-xs text-slate-500">{b.account_holder_name}</span>
              {b.verified
                ? <span className="ml-auto text-xs rounded px-2 py-0.5 bg-emerald-100 text-emerald-700">verified</span>
                : <button onClick={act(async () => { if (confirm('Confirm this account was re-verified with the employee?')) await api.post(`/api/hr/bank/${b.id}/verify`) })}
                    className="ml-auto text-xs rounded bg-brand text-white px-2 py-0.5">verify</button>}
            </div>
          ))}
        </Card>

        <Card title="Documents">
          {d.documents.length === 0 && <p className="text-sm text-slate-500">None uploaded.</p>}
          {d.documents.map((doc) => (
            <div key={doc.id} className="flex items-center gap-2 py-1.5 text-sm border-b border-slate-100 last:border-0">
              <span className="flex-1">{doc.doc_type}{doc.expiry_date && <span className="text-xs text-slate-500"> · expires {doc.expiry_date}</span>}</span>
              {doc.signed_url && <a href={doc.signed_url} target="_blank" rel="noreferrer" className="text-xs text-brand-light underline">view</a>}
              {doc.source_url && <a href={doc.source_url} target="_blank" rel="noreferrer" className="text-xs text-slate-500 underline">Drive link</a>}
            </div>
          ))}
        </Card>

        <Card title="Status history">
          {d.status_history.map((h, i) => (
            <div key={i} className="text-sm py-1 border-b border-slate-100 last:border-0">
              <span className="font-medium">{h.status}</span>
              <span className="text-xs text-slate-500"> · {h.effective_date} · {h.changed_by}{h.reason ? ` · ${h.reason}` : ''}</span>
            </div>
          ))}
        </Card>

        <Card title="Raw submissions">
          {d.submissions.map((s) => (
            <details key={s.reference_no} className="text-sm py-1">
              <summary className="cursor-pointer">{s.reference_no} <span className="text-xs text-slate-500">({s.source}, {s.created_at?.slice(0, 10)})</span></summary>
              <pre className="text-xs bg-slate-50 rounded p-2 mt-1 overflow-x-auto">{JSON.stringify(s.payload, null, 2)}</pre>
            </details>
          ))}
        </Card>
      </section>
    </div>
  )
}

function Card({ title, children }) {
  return (
    <div className="rounded-lg bg-white border border-slate-200 p-4">
      <h2 className="font-semibold mb-2">{title}</h2>
      {children}
    </div>
  )
}
function Info({ k, v }) {
  return <p className="text-sm py-0.5"><span className="text-slate-500 inline-block w-32">{k}</span>{v || '—'}</p>
}
