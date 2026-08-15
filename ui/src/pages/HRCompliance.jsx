import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function HRCompliance() {
  const [data, setData] = useState(null)
  const now = new Date()
  const [period, setPeriod] = useState({ y: now.getFullYear(), m: now.getMonth() + 1 })
  useEffect(() => { api.get('/api/hr/compliance').then(setData) }, [])
  if (!data) return null
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Compliance board</h1>

      <section>
        <h2 className="font-semibold mb-2">Expiries in the next 60 days</h2>
        {data.expiries.length === 0 ? <p className="text-sm text-slate-500">Nothing expiring. ✓</p> : (
          <table className="w-full text-sm bg-white rounded-lg border border-slate-200 overflow-hidden">
            <thead className="bg-slate-50 text-left">
              <tr><th className="p-2">Code</th><th className="p-2">Name</th><th className="p-2">Document</th><th className="p-2">Expiry</th></tr>
            </thead>
            <tbody>
              {data.expiries.map((e, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="p-2 font-mono text-xs">{e.emp_code}</td>
                  <td className="p-2">{e.name}</td>
                  <td className="p-2">{e.doc_type}</td>
                  <td className={'p-2 ' + (e.expiry_date < new Date().toISOString().slice(0, 10) ? 'text-red-600 font-semibold' : '')}>{e.expiry_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2 className="font-semibold mb-2">Blocked from payroll — resolve flags</h2>
        {data.blocked.length === 0 ? <p className="text-sm text-slate-500">No one is blocked. ✓</p> : (
          <div className="grid gap-2">
            {data.blocked.map((b) => (
              <Link key={b.employee_id} to={`/hr/${b.employee_id}`}
                className="flex items-center gap-3 rounded-lg bg-white border border-red-200 px-4 py-2.5 text-sm hover:border-red-400">
                <span className="font-mono text-xs text-slate-500">{b.employee_no}</span>
                <span className="font-medium flex-1">{b.full_name}</span>
                {b.bank_unverified && <span className="text-xs rounded px-2 py-0.5 bg-amber-100 text-amber-800">bank unverified</span>}
                {(b.open_blockers || []).map((f) => (
                  <span key={f} className="text-xs rounded px-2 py-0.5 bg-red-100 text-red-700">{f}</span>
                ))}
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="font-semibold mb-2">Monthly payroll export</h2>
        <div className="flex items-center gap-2 text-sm">
          <select className="rounded border-slate-300 border px-2 py-1.5" value={period.m}
            onChange={(e) => setPeriod((p) => ({ ...p, m: +e.target.value }))}>
            {Array.from({ length: 12 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
          </select>
          <input type="number" className="w-24 rounded border-slate-300 border px-2 py-1.5" value={period.y}
            onChange={(e) => setPeriod((p) => ({ ...p, y: +e.target.value }))} />
          <a className="rounded bg-brand text-white px-3 py-1.5"
            href={`/api/payroll-export/master?year=${period.y}&month=${period.m}`}>Master CSV</a>
          <a className="rounded bg-brand-light text-white px-3 py-1.5"
            href={`/api/payroll-export/movements?year=${period.y}&month=${period.m}`}>Movements CSV</a>
        </div>
      </section>
    </div>
  )
}
