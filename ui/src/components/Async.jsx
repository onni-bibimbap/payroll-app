import React from 'react'

// Shared loading / error states so data pages never render a permanent blank
// screen (FE-07). Use <Loading/> while fetching and <ErrorState/> on failure.

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-400">
      <span className="inline-block w-5 h-5 rounded-full border-2 border-slate-300 border-t-brand animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorState({ message, retry }) {
  return (
    <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-center my-6">
      <p className="text-sm text-red-700 font-medium">Could not load this page.</p>
      {message && <p className="text-xs text-red-600 mt-1">{message}</p>}
      {retry && (
        <button onClick={retry}
          className="mt-3 px-4 py-2 rounded-lg bg-brand text-white text-sm font-semibold">
          Try again
        </button>
      )}
    </div>
  )
}
