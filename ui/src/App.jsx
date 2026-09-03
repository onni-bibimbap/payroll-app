import React, { Suspense, createContext, lazy, useCallback, useContext, useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api, setUnauthorizedHandler } from './api.js'
import { Loading } from './components/Async.jsx'

// Route-level code splitting (FE-09): each page is its own chunk, so the
// public /register PWA never downloads the admin payroll bundle.
const Login = lazy(() => import('./pages/Login.jsx'))
const PayrollList = lazy(() => import('./pages/PayrollList.jsx'))
const PayrollRun = lazy(() => import('./pages/PayrollRun.jsx'))
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const Payslip = lazy(() => import('./pages/Payslip.jsx'))
const Employees = lazy(() => import('./pages/Employees.jsx'))
const EmployeeForm = lazy(() => import('./pages/EmployeeForm.jsx'))
const Settings = lazy(() => import('./pages/Settings.jsx'))
const Register = lazy(() => import('./pages/Register.jsx'))
const HRQueue = lazy(() => import('./pages/HRQueue.jsx'))
const HRDetail = lazy(() => import('./pages/HRDetail.jsx'))
const HRCompliance = lazy(() => import('./pages/HRCompliance.jsx'))

const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

function Nav() {
  const { user, company, setUser } = useApp()
  const cls = ({ isActive }) =>
    'text-sm sm:text-base hover:text-white/80' + (isActive ? ' font-semibold underline' : '')
  const logout = async () => {
    await api.post('/api/auth/logout')
    setUser(null)
  }
  return (
    <nav className="bg-brand text-white shadow sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 flex items-center gap-4 sm:gap-6 h-14">
        <Link to="/payroll" className="font-bold text-base sm:text-lg tracking-tight flex items-center gap-2 shrink-0">
          <span className="inline-block w-7 h-7 rounded bg-moss text-center leading-7">◎</span>
          <span className="hidden sm:inline">{company} Payroll</span>
        </Link>
        <NavLink to="/payroll" className={cls}>Payroll</NavLink>
        <NavLink to="/employees" className={cls}>Staff</NavLink>
        {(user.role === 'admin' || user.role === 'approver') && <NavLink to="/hr" className={cls}>HR</NavLink>}
        {user.role === 'admin' && <NavLink to="/settings" className={cls}>Settings</NavLink>}
        <div className="ml-auto flex items-center gap-2 sm:gap-3 text-sm">
          <span className="hidden sm:inline px-2 py-1 rounded bg-white/15">
            {user.full_name || user.username} <span className="opacity-70">· {user.role}</span>
          </span>
          <button onClick={logout} className="hover:underline opacity-90">Logout</button>
        </div>
      </div>
    </nav>
  )
}

function Flashes() {
  const { messages, dismiss } = useApp()
  return messages.map((m, i) => (
    <div key={i} onClick={() => dismiss(i)}
      className={'mb-3 rounded-lg px-4 py-2.5 text-sm border cursor-pointer ' +
        (m.level === 'error' ? 'bg-red-50 border-red-200 text-red-800'
          : 'bg-emerald-50 border-emerald-200 text-emerald-800')}>
      {m.msg}
    </div>
  ))
}

export default function App() {
  const [user, setUser] = useState(null)
  const [company, setCompany] = useState('Onni')
  const [ready, setReady] = useState(false)
  const [messages, setMessages] = useState([])
  const location = useLocation()

  useEffect(() => {
    api.get('/api/auth/me')
      .then((d) => { setUser(d.user); setCompany(d.company) })
      .catch(() => {})
      .finally(() => setReady(true))
  }, [])

  const flash = useCallback((msg, level = 'success') => {
    setMessages((ms) => [...ms, { msg, level }])
    setTimeout(() => setMessages((ms) => ms.slice(1)), 5000)
  }, [])

  // Session expiry (FE-07): any API 401 drops back to the login form in place.
  // The URL is untouched, so the intended route renders again after re-login.
  useEffect(() => {
    let handled = false // several in-flight requests may 401 together
    setUnauthorizedHandler(() => {
      if (!user || handled) return
      handled = true
      setUser(null)
      flash('Session expired — please sign in again.', 'error')
    })
    return () => setUnauthorizedHandler(null)
  }, [user, flash])
  const dismiss = (i) => setMessages((ms) => ms.filter((_, j) => j !== i))

  // clear flashes on navigation
  useEffect(() => { setMessages([]) }, [location.pathname])

  if (!ready) return null

  const ctx = { user, setUser, company, setCompany, messages, flash, dismiss }

  // public registration PWA — reachable with or without a session
  if (location.pathname.startsWith('/register')) {
    return (
      <AppCtx.Provider value={ctx}>
        <Suspense fallback={<Loading />}><Register /></Suspense>
      </AppCtx.Provider>
    )
  }

  if (!user) {
    return (
      <AppCtx.Provider value={ctx}>
        <main className="max-w-7xl mx-auto px-5 py-6">
          <Flashes />
          <Suspense fallback={<Loading />}><Login /></Suspense>
        </main>
      </AppCtx.Provider>
    )
  }
  return (
    <AppCtx.Provider value={ctx}>
      <Nav />
      <main className="max-w-7xl mx-auto px-5 py-6">
        <Flashes />
        <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Navigate to="/payroll" replace />} />
          <Route path="/login" element={<Navigate to="/payroll" replace />} />
          <Route path="/payroll" element={<PayrollList />} />
          <Route path="/payroll/:runId" element={<PayrollRun />} />
          <Route path="/payroll/:runId/dashboard" element={<Dashboard />} />
          <Route path="/payroll/:runId/payslip/:slipId" element={<Payslip />} />
          {(user.role === 'admin' || user.role === 'approver') && <>
            <Route path="/hr" element={<HRQueue />} />
            <Route path="/hr/compliance" element={<HRCompliance />} />
            <Route path="/hr/:empId" element={<HRDetail />} />
          </>}
          <Route path="/employees" element={<Employees />} />
          <Route path="/employees/new" element={<EmployeeForm />} />
          <Route path="/employees/:empId" element={<EmployeeForm />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/payroll" replace />} />
        </Routes>
        </Suspense>
      </main>
    </AppCtx.Provider>
  )
}
