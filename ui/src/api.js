// Thin fetch wrapper: JSON in/out, session cookie auth, error normalisation.

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

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

export const money = (v) => {
  const n = Number(v || 0)
  return n ? n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'
}
export const money0 = (v) => {
  const n = Number(v || 0)
  return n ? n.toLocaleString('en-MY', { maximumFractionDigits: 0 }) : '-'
}

export const BADGE = {
  draft: 'bg-slate-200 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-700',
}

export const MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']
