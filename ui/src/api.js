// Thin fetch wrapper: JSON in/out, session cookie auth, error normalisation.

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

// Session-expiry hook: App registers a handler that clears the user so the
// login form renders in place — the current URL (intended route) is preserved
// and the router shows it again right after re-login (FE-07).
let onUnauthorized = null
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  })
  let data = null
  try { data = await res.json() } catch { /* non-JSON (e.g. empty) */ }
  if (!res.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail
      : detail?.message || `Request failed (${res.status})`
    // auth endpoints handle their own 401s (bad password, initial /me probe)
    if (res.status === 401 && !path.startsWith('/api/auth/') && onUnauthorized)
      onUnauthorized()
    throw new ApiError(res.status, message, detail)
  }
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, body = {}) => request(p, { method: 'POST', body }),
  put: (p, body = {}) => request(p, { method: 'PUT', body }),
  del: (p) => request(p, { method: 'DELETE' }),
}

// '-' is reserved for "no value" (null/undefined/''); a genuine 0 must render
// as 0.00 — on a statutory pay document the two are not interchangeable (FE-08).
export const money = (v) => {
  if (v === null || v === undefined || v === '') return '-'
  return Number(v).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
export const money0 = (v) => {
  if (v === null || v === undefined || v === '') return '-'
  return Number(v).toLocaleString('en-MY', { maximumFractionDigits: 0 })
}

export const BADGE = {
  draft: 'bg-slate-200 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-700',
}

export const MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']
