import React, { useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'

export default function Login() {
  const { setUser, setCompany, company, flash } = useApp()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const d = await api.post('/api/auth/login', { username, password })
      setCompany(d.company)
      setUser(d.user)
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-6">
          <div className="mx-auto w-12 h-12 rounded-xl bg-brand text-white text-2xl leading-[3rem]">◎</div>
          <h1 className="text-xl font-bold mt-3">{company} Payroll</h1>
          <p className="text-sm text-slate-500">Sign in to continue</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:ring-2 focus:ring-brand-light outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:ring-2 focus:ring-brand-light outline-none" />
          </div>
          <button disabled={busy}
            className="w-full bg-brand hover:bg-brand-light text-white font-semibold rounded-lg py-2.5 transition disabled:opacity-60">
            Sign in
          </button>
        </form>
        <div className="mt-5 text-xs text-slate-400 border-t pt-3">
          Demo accounts — <b>preparer</b>/preparer123 · <b>approver</b>/approver123 · <b>admin</b>/admin123
        </div>
      </div>
    </div>
  )
}
