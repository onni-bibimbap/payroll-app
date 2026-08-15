import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, money } from '../api.js'
import { useApp } from '../App.jsx'

const STATUS_BADGE = {
  active: 'bg-emerald-100 text-emerald-700',
  pending_review: 'bg-amber-100 text-amber-800',
  applicant: 'bg-sky-100 text-sky-700',
  resigned: 'bg-slate-200 text-slate-600',
  terminated: 'bg-red-100 text-red-700',
  absconded: 'bg-red-100 text-red-700',
  rejected: 'bg-slate-200 text-slate-500',
  _: 'bg-slate-100 text-slate-500',
}

export default function Employees() {
  const { user, flash } = useApp()
  const [params, setParams] = useSearchParams()
  const show = params.get('show') || 'active'
  const [data, setData] = useState(null)

  const load = () => api.get(`/api/employees?show=${show}`).then(setData)
    .catch((e) => flash(e.message, 'error'))
  useEffect(() => { load() }, [show])

  const toggle = async (e) => {
    try {
      const upd = await api.post(`/api/employees/${e.id}/toggle`)
      flash(`${upd.name} is now ${upd.active ? 'active' : 'inactive'}.`)
      load()
    } catch (err) { flash(err.message, 'error') }
  }

  if (!data) return null

  // employees touched in the last 2 months, newest first — surfaced for review
  const cutoff = new Date(); cutoff.setMonth(cutoff.getMonth() - 2)
  const recent = [...data.employees]
    .filter((e) => e.updated_at && new Date(e.updated_at) >= cutoff)
    .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))

  const tab = (key, label, activeCls) => (
    <button onClick={() => setParams({ show: key })}
      className={'px-3 py-1.5 rounded-lg border ' +
        (show === key ? activeCls : 'bg-white border-slate-300')}>{label}</button>
  )

  return (
    <>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h1 className="text-2xl font-bold">Employees</h1>
        <div className="ml-auto flex items-center gap-2 text-sm flex-wrap">
          {tab('active', `Active (${data.counts.active})`, 'bg-brand text-white border-brand')}
          {tab('all', `All (${data.counts.all})`, 'bg-brand text-white border-brand')}
          {tab('review', `⚠ Review (${data.counts.review})`, 'bg-amber-500 text-white border-amber-500')}
          {user.can_prepare &&
            <Link to="/employees/new" className="px-3 py-1.5 rounded-lg bg-moss text-white font-semibold">+ New employee</Link>}
        </div>
      </div>

      {recent.length > 0 && (
        <div className="mb-4 bg-white rounded-xl shadow border-l-4 border-brand-light p-4">
          <div className="flex items-baseline gap-2 mb-2">
            <h2 className="font-semibold text-sm">Updated in the last 2 months — review</h2>
            <span className="text-xs text-slate-400">{recent.length} record{recent.length === 1 ? '' : 's'}</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
            {recent.map((e) => (
              <Link key={e.id} to={`/employees/${e.id}`}
                title={`updated ${new Date(e.updated_at).toLocaleDateString('en-MY')}`}
                className="inline-flex items-center gap-1.5 text-xs rounded-full border border-slate-200 pl-2 pr-2.5 py-1 hover:border-brand-light">
                <span className={'w-1.5 h-1.5 rounded-full ' +
                  (e.status === 'active' ? 'bg-emerald-500' : e.status === 'pending_review' ? 'bg-amber-400' : 'bg-slate-300')} />
                {e.name}
                <span className="text-slate-400">{new Date(e.updated_at).toLocaleDateString('en-MY', { day: 'numeric', month: 'short' })}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-left">
            <tr className="border-b">
              <th className="px-3 py-2.5">Code</th><th className="px-3 py-2.5">Name</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5">Type</th><th className="px-3 py-2.5 text-right">Basic / Rate</th>
              <th className="px-3 py-2.5">Bank</th><th className="px-3 py-2.5 text-center">EPF</th>
              <th className="px-3 py-2.5 text-center">SOCSO</th><th></th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.employees.map((e) => (
              <tr key={e.id} className={'border-b last:border-0 hover:bg-slate-50 ' + (e.needs_review ? 'bg-amber-50' : '')}>
                <td className="px-3 py-2 font-mono text-xs">{e.emp_code}</td>
                <td className="px-3 py-2 font-medium">{e.name}{' '}
                  {!e.active && <span className="text-xs text-slate-400">(inactive)</span>}{' '}
                  {e.is_confirmed && <span className="text-[10px] bg-emerald-100 text-emerald-700 rounded px-1">confirmed</span>}{' '}
                  {e.is_foreign && <span className="text-[10px] bg-slate-200 rounded px-1">foreign</span>}{' '}
                  {e.needs_review && <span title={e.import_note || ''}
                    className="text-[10px] bg-amber-200 text-amber-800 rounded px-1">⚠ review</span>}
                </td>
                <td className="px-3 py-2">
                  <span className={'text-[11px] font-medium rounded px-1.5 py-0.5 ' + (STATUS_BADGE[e.status] || STATUS_BADGE._)}>
                    {e.status || '—'}</span>
                </td>
                <td className="px-3 py-2">{e.employment_type === 'full_time' ? 'Full-time' : 'Part-time'}</td>
                <td className="px-3 py-2 text-right">
                  {e.employment_type === 'full_time' ? money(e.basic_salary)
                    : <span className="text-slate-500">{money(e.hourly_rate)}/hr</span>}
                </td>
                <td className="px-3 py-2 text-slate-600">{e.bank_name || '—'}</td>
                <td className="px-3 py-2 text-center">{e.epf_enabled ? '✓' : '·'}</td>
                <td className="px-3 py-2 text-center">{e.socso_enabled ? '✓' : '·'}</td>
                {user.can_prepare ? (
                  <>
                    <td className="px-3 py-2 text-right">
                      <Link to={`/employees/${e.id}`} className="text-brand-light hover:underline">Edit</Link></td>
                    <td className="px-2 py-2">
                      <button onClick={() => toggle(e)} className="text-xs text-slate-400 hover:text-red-600">
                        {e.active ? 'Deactivate' : 'Activate'}</button></td>
                  </>
                ) : (<><td></td><td></td></>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
