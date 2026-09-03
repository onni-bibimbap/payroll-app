import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useApp } from '../App.jsx'
import { ErrorState, Loading } from '../components/Async.jsx'

export default function HRQueue() {
  const { flash } = useApp()
  const [queue, setQueue] = useState(null)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const load = () => {
    setError(null)
    return api.get('/api/hr/queue').then((d) => setQueue(d.queue))
      .catch((e) => { setError(e.message); flash(e.message, 'error') })
  }
  useEffect(() => { load() }, [])

  const sync = async () => {
    setSyncing(true)
    try {
      const r = await api.post('/api/hr/sync-google-sheet')
      flash(`Synced ${r.rows} sheet rows — ${r.created} new applicant${r.created === 1 ? '' : 's'}, ` +
        `${r.updated} refreshed, ${r.settled_untouched} already settled (untouched), ${r.blockers} blocker flags.`)
      await load()
    } catch (e) { flash(e.message, 'error') } finally { setSyncing(false) }
  }

  if (error && !queue) return <ErrorState message={error} retry={load} />
  if (!queue) return <Loading label="Loading review queue…" />
  return (
    <div>
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <h1 className="text-xl font-bold">HR Review Queue</h1>
        <div className="flex items-center gap-3">
          <button onClick={sync} disabled={syncing}
            className="rounded bg-moss text-white text-sm px-3 py-1.5 disabled:opacity-50">
            {syncing ? 'Syncing…' : '⟳ Sync Google Sheet'}
          </button>
          <Link to="/hr/compliance" className="text-sm text-brand-light underline">Compliance board →</Link>
        </div>
      </div>
      {queue.length === 0 && <p className="text-slate-500">No pending applications. 🎉</p>}
      <div className="grid gap-2">
        {queue.map((r) => (
          <Link key={r.id} to={`/hr/${r.id}`}
            className="flex items-center gap-3 rounded-lg bg-white border border-slate-200 px-4 py-3 hover:border-brand-light">
            <span className="font-mono text-xs text-slate-500 w-20">{r.emp_code}</span>
            <span className="font-medium flex-1">{r.name}</span>
            <span className="text-sm text-slate-500 hidden sm:inline">{r.position || '—'}</span>
            {r.identity_type !== 'nric' &&
              <span className="text-xs rounded px-2 py-0.5 bg-violet-100 text-violet-700">{r.identity_type}</span>}
            {(r.flag_types || []).includes('resubmission_requested') &&
              <span className="text-xs rounded px-2 py-0.5 bg-sky-100 text-sky-700">resubmission requested</span>}
            {r.blockers > 0 &&
              <span className="text-xs rounded px-2 py-0.5 bg-red-100 text-red-700">{r.blockers} blocker{r.blockers > 1 ? 's' : ''}</span>}
            <span className="text-xs rounded px-2 py-0.5 bg-amber-100 text-amber-800">{r.open_flags} open</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
