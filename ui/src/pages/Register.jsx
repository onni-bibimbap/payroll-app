import React, { useEffect, useRef, useState } from 'react'
import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval'

// Public, mobile-first staff registration form (EN + BM helper text).
// Drafts persist to IndexedDB on every change; if the network is down at
// submit time the submission is queued and retried when back online.

const DRAFT_KEY = 'onni-register-draft'
const QUEUE_KEY = 'onni-register-queue'

const FALLBACK_BANKS = ['Maybank', 'CIMB', 'Public Bank', 'RHB', 'Hong Leong',
  'AmBank', 'Bank Islam', 'Bank Muamalat', 'Alliance', 'BSN', 'GXBank',
  'Bank of China', 'Merchantrade', "Touch 'n Go", 'Other']

const POSITIONS = ['Waiter / Waitress', 'Chef', 'Kitchen Helper', 'Barista',
  'Cashier', 'Supervisor', 'Outlet Manager', 'Other']

const DOCS = [
  ['nric_front', 'NRIC Front', 'Depan Kad Pengenalan'],
  ['nric_back', 'NRIC Back', 'Belakang Kad Pengenalan'],
  ['food_handler_cert', 'Food Handler Cert (Khusus Makanan)', 'Sijil Pengendali Makanan'],
  ['typhoid_proof', 'Typhoid Vaccination Proof', 'Bukti Vaksin Tifoid'],
  ['education_transcript', 'Education Transcript', 'Transkrip Pendidikan'],
  ['profile_photo', 'Profile Photo', 'Gambar Profil (muka sahaja)'],
]

const EMPTY = {
  full_name: '', email: '', phone: '', identity_type: 'nric', identity_no: '',
  nationality: '', date_of_birth: '', residential_address: '', position: '',
  employment_type: 'full_time', expected_salary: '', bank_name: '', account_no: '',
  emergency_contact_name: '', emergency_contact_phone: '', emergency_contact_relationship: '',
  working_experience: '', education_background: '', skills: '', referral_source: '',
  typhoid_expiry: '',
}

function validNric(v) {
  const d = v.replace(/[\s-]/g, '')
  if (!/^\d{12}$/.test(d)) return false
  const yy = +d.slice(0, 2), mm = +d.slice(2, 4), dd = +d.slice(4, 6)
  const y = yy < 30 ? 2000 + yy : 1900 + yy
  const date = new Date(y, mm - 1, dd)
  return date.getMonth() === mm - 1 && date.getDate() === dd
}

function Field({ label, bm, error, children }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium">{label}</span>
      {bm && <span className="block text-xs text-slate-500">{bm}</span>}
      <div className="mt-1">{children}</div>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </label>
  )
}

const inputCls = 'w-full rounded-lg border border-slate-300 px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-brand-light bg-white'

export default function Register() {
  const [form, setForm] = useState(EMPTY)
  const [banks, setBanks] = useState(FALLBACK_BANKS)
  const [files, setFiles] = useState({})            // doc_type -> File
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)            // {reference_no, queued, docs}
  const [online, setOnline] = useState(navigator.onLine)
  const restored = useRef(false)

  // restore draft + watch connectivity + flush queue when back online
  useEffect(() => {
    idbGet(DRAFT_KEY).then((d) => { if (d) setForm({ ...EMPTY, ...d }); restored.current = true })
    fetch('/api/register/meta').then((r) => r.json())
      .then((m) => m.banks && setBanks(m.banks)).catch(() => {})
    const up = () => { setOnline(true); flushQueue() }
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    flushQueue()
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [])

  // persist draft on every change (after initial restore)
  useEffect(() => { if (restored.current) idbSet(DRAFT_KEY, form) }, [form])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  async function flushQueue() {
    const queued = await idbGet(QUEUE_KEY)
    if (!queued) return
    try {
      const ref = await postSubmission(queued.form)
      await idbDel(QUEUE_KEY)
      setDone({ reference_no: ref, queued: false, docs: 'pending' })
    } catch { /* still offline or server down — keep queued */ }
  }

  async function postSubmission(payload) {
    const res = await fetch('/api/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => null)
    if (!res.ok) throw new Error(data?.detail || 'Submission failed')
    return data.reference_no
  }

  async function uploadDocs(ref) {
    let ok = 0, fail = 0
    for (const [docType, file] of Object.entries(files)) {
      const fd = new FormData()
      fd.append('file', file)
      let url = `/api/register/${ref}/documents/${docType}`
      if (docType === 'typhoid_proof' && form.typhoid_expiry)
        url += `?expiry_date=${form.typhoid_expiry}`
      try {
        const r = await fetch(url, { method: 'POST', body: fd })
        r.ok ? ok++ : fail++
      } catch { fail++ }
    }
    return { ok, fail }
  }

  function validate() {
    const e = {}
    if (!form.full_name.trim()) e.full_name = 'Required / Wajib diisi'
    if (form.identity_type === 'nric' && !validNric(form.identity_no))
      e.identity_no = 'NRIC must be 12 digits with valid date / 12 digit dengan tarikh sah'
    if (form.identity_type !== 'nric' && !form.identity_no.trim())
      e.identity_no = 'Required / Wajib diisi'
    if (form.phone && !/^\+?[\d\s-]{9,15}$/.test(form.phone)) e.phone = 'Invalid phone / Nombor tidak sah'
    if (form.email && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(form.email)) e.email = 'Invalid email / Emel tidak sah'
    if (form.account_no && !/^[\d\s]{6,24}$/.test(form.account_no)) e.account_no = '6–20 digits only / 6–20 digit sahaja'
    if (form.account_no && !form.bank_name) e.bank_name = 'Select your bank / Pilih bank anda'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function submit(ev) {
    ev.preventDefault()
    if (!validate()) { window.scrollTo({ top: 0, behavior: 'smooth' }); return }
    setBusy(true)
    const payload = { ...form }
    try {
      const ref = await postSubmission(payload)
      const docs = await uploadDocs(ref)
      await idbDel(DRAFT_KEY)
      setDone({ reference_no: ref, queued: false, docs })
    } catch (err) {
      if (!navigator.onLine) {
        await idbSet(QUEUE_KEY, { form: payload, at: Date.now() })
        setDone({ queued: true })
      } else {
        setErrors({ _global: String(err.message || err) })
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    } finally { setBusy(false) }
  }

  if (done?.queued) {
    return (
      <Shell>
        <div className="rounded-xl bg-amber-50 border border-amber-300 p-6 text-center">
          <div className="text-3xl mb-2">📶</div>
          <h2 className="text-lg font-semibold">Saved — will send when back online</h2>
          <p className="text-sm text-slate-600 mt-2">
            Anda di luar talian. Borang anda telah disimpan dan akan dihantar secara
            automatik apabila talian pulih. Keep this page installed / open.
          </p>
        </div>
      </Shell>
    )
  }
  if (done?.reference_no) {
    return (
      <Shell>
        <div className="rounded-xl bg-emerald-50 border border-emerald-300 p-6 text-center">
          <div className="text-3xl mb-2">✅</div>
          <h2 className="text-lg font-semibold">Registration submitted / Pendaftaran dihantar</h2>
          <p className="mt-2">Your reference number / Nombor rujukan anda:</p>
          <p className="text-2xl font-mono font-bold mt-1">{done.reference_no}</p>
          {done.docs?.fail > 0 && (
            <p className="text-sm text-amber-700 mt-3">
              {done.docs.fail} document(s) failed to upload — HR will contact you, or
              re-open this page with internet and try again.
            </p>
          )}
          <p className="text-sm text-slate-600 mt-3">
            HR will review your application. Pihak HR akan menyemak permohonan anda.
          </p>
        </div>
      </Shell>
    )
  }

  return (
    <Shell>
      {!online && (
        <div className="mb-4 rounded-lg bg-amber-100 border border-amber-300 px-4 py-2 text-sm">
          Offline — your answers are being saved on this phone.
          / Luar talian — jawapan anda disimpan dalam telefon ini.
        </div>
      )}
      {errors._global && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-300 px-4 py-2 text-sm text-red-700">{errors._global}</div>
      )}
      <form onSubmit={submit} className="space-y-6">
        <Section title="Personal details / Maklumat peribadi">
          <Field label="Full name (as per IC/passport)" bm="Nama penuh" error={errors.full_name}>
            <input className={inputCls} value={form.full_name} onChange={set('full_name')} autoComplete="name" />
          </Field>
          <Field label="Identity type" bm="Jenis pengenalan">
            <select className={inputCls} value={form.identity_type} onChange={set('identity_type')}>
              <option value="nric">Malaysian NRIC</option>
              <option value="passport">Passport (non-Malaysian)</option>
              <option value="unhcr">UNHCR card</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field
            label={form.identity_type === 'nric' ? 'NRIC number (12 digits)' : 'Document number'}
            bm={form.identity_type === 'nric' ? 'No. Kad Pengenalan' : 'Nombor dokumen'}
            error={errors.identity_no}>
            <input className={inputCls} value={form.identity_no} onChange={set('identity_no')}
              inputMode={form.identity_type === 'nric' ? 'numeric' : 'text'}
              placeholder={form.identity_type === 'nric' ? '030101141234' : ''} />
          </Field>
          {form.identity_type !== 'nric' && (
            <Field label="Nationality" bm="Warganegara">
              <input className={inputCls} value={form.nationality} onChange={set('nationality')} />
            </Field>
          )}
          <Field label="Date of birth" bm="Tarikh lahir">
            <input type="date" className={inputCls} value={form.date_of_birth} onChange={set('date_of_birth')} />
          </Field>
          <Field label="Phone number" bm="No. telefon" error={errors.phone}>
            <input className={inputCls} value={form.phone} onChange={set('phone')}
              inputMode="tel" autoComplete="tel" placeholder="012-3456789" />
          </Field>
          <Field label="Email" bm="Emel" error={errors.email}>
            <input className={inputCls} value={form.email} onChange={set('email')}
              inputMode="email" autoComplete="email" />
          </Field>
          <Field label="Residential address" bm="Alamat kediaman">
            <textarea className={inputCls} rows="2" value={form.residential_address}
              onChange={set('residential_address')} autoComplete="street-address" />
          </Field>
        </Section>

        <Section title="Job / Pekerjaan">
          <Field label="Position applied for" bm="Jawatan dipohon">
            <select className={inputCls} value={form.position} onChange={set('position')}>
              <option value="">— select / pilih —</option>
              {POSITIONS.map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Employment type" bm="Jenis pekerjaan">
            <div className="flex gap-3">
              {[['full_time', 'Full time'], ['part_time', 'Part time']].map(([v, l]) => (
                <button type="button" key={v} onClick={() => setForm((f) => ({ ...f, employment_type: v }))}
                  className={'flex-1 rounded-lg border px-3 py-2.5 ' +
                    (form.employment_type === v ? 'bg-brand text-white border-brand' : 'bg-white border-slate-300')}>
                  {l}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Expected salary" bm="Gaji dijangka (cth: RM8 sejam / RM2000 sebulan)">
            <input className={inputCls} value={form.expected_salary} onChange={set('expected_salary')}
              placeholder="RM8 per hour / RM2000 per month" />
          </Field>
          <Field label="Working experience" bm="Pengalaman kerja">
            <textarea className={inputCls} rows="2" value={form.working_experience} onChange={set('working_experience')} />
          </Field>
          <Field label="Education background" bm="Latar belakang pendidikan">
            <textarea className={inputCls} rows="2" value={form.education_background} onChange={set('education_background')} />
          </Field>
          <Field label="Skills" bm="Kemahiran">
            <input className={inputCls} value={form.skills} onChange={set('skills')} />
          </Field>
          <Field label="How did you hear about Onni?" bm="Bagaimana anda tahu tentang Onni?">
            <input className={inputCls} value={form.referral_source} onChange={set('referral_source')} />
          </Field>
        </Section>

        <Section title="Bank (for salary) / Bank (untuk gaji)">
          <Field label="Bank" bm="Pilih bank anda" error={errors.bank_name}>
            <select className={inputCls} value={form.bank_name} onChange={set('bank_name')}>
              <option value="">— select / pilih —</option>
              {banks.map((b) => <option key={b}>{b}</option>)}
            </select>
          </Field>
          <Field label="Account number (digits only)" bm="No. akaun (nombor sahaja)" error={errors.account_no}>
            <input className={inputCls} value={form.account_no} onChange={set('account_no')} inputMode="numeric" />
          </Field>
        </Section>

        <Section title="Emergency contact / Hubungan kecemasan">
          <Field label="Name" bm="Nama">
            <input className={inputCls} value={form.emergency_contact_name} onChange={set('emergency_contact_name')} />
          </Field>
          <Field label="Phone" bm="No. telefon">
            <input className={inputCls} value={form.emergency_contact_phone} onChange={set('emergency_contact_phone')} inputMode="tel" />
          </Field>
          <Field label="Relationship" bm="Hubungan (cth: Ibu, Bapa, Pasangan)">
            <input className={inputCls} value={form.emergency_contact_relationship} onChange={set('emergency_contact_relationship')} />
          </Field>
        </Section>

        <Section title="Documents / Dokumen">
          <p className="text-xs text-slate-500 -mt-1">
            Photos or PDF, max 10 MB each. Documents upload after you submit —
            if you are offline they can be re-sent later.
          </p>
          {DOCS.map(([key, en, bm]) => (
            <Field key={key} label={en} bm={bm}>
              <input type="file" accept="image/*,.pdf" capture="environment"
                className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-brand file:text-white file:px-3 file:py-2"
                onChange={(e) => setFiles((f) => ({ ...f, [key]: e.target.files[0] }))} />
              {files[key] && <span className="text-xs text-emerald-700">✓ {files[key].name}</span>}
            </Field>
          ))}
          <Field label="Typhoid vaccination expiry date" bm="Tarikh luput vaksin tifoid">
            <input type="date" className={inputCls} value={form.typhoid_expiry} onChange={set('typhoid_expiry')} />
          </Field>
        </Section>

        <button disabled={busy}
          className="w-full rounded-xl bg-brand text-white font-semibold py-3.5 text-base disabled:opacity-50">
          {busy ? 'Submitting… / Menghantar…' : 'Submit registration / Hantar pendaftaran'}
        </button>
        <p className="text-xs text-slate-500 text-center pb-6">
          Your data is used for employment administration only (PDPA 2010).
        </p>
      </form>
    </Shell>
  )
}

function Section({ title, children }) {
  return (
    <section className="rounded-xl bg-white shadow-sm border border-slate-200 p-4 space-y-4">
      <h2 className="font-semibold text-brand">{title}</h2>
      {children}
    </section>
  )
}

function Shell({ children }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-brand text-white px-4 py-3 sticky top-0 z-10">
        <h1 className="font-bold text-lg max-w-xl mx-auto">Onni — Staff Registration
          <span className="block text-xs font-normal opacity-80">Pendaftaran Pekerja</span>
        </h1>
      </header>
      <main className="max-w-xl mx-auto px-4 py-5">{children}</main>
    </div>
  )
}
