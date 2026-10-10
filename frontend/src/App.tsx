import { type FormEvent, type ReactElement, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, FileText, ShieldCheck, Sparkles, XCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Verdict = 'SUPPORTED' | 'CONTRADICTED' | 'QUALIFIED' | 'NOT_FOUND' | 'UNCERTAIN'

type ClaimItem = {
  claim: string
  verdict: Verdict
  severity: 'low' | 'medium' | 'high'
  reason: string
  confidence: number
  quote: string
  source_section: string
  explanation: string
  recommended_change: string
}

type Report = {
  overall_score: number
  status: string
  summary: Record<string, number>
  claims: ClaimItem[]
  mode: 'SIMULATED' | 'LIVE'
  simulated: boolean
}

const badgeClasses: Record<Verdict, string> = {
  SUPPORTED: 'bg-teal-100 text-teal-700 border-teal-200',
  CONTRADICTED: 'bg-red-100 text-red-700 border-red-200',
  QUALIFIED: 'bg-amber-100 text-amber-700 border-amber-200',
  NOT_FOUND: 'bg-slate-200 text-slate-700 border-slate-300',
  UNCERTAIN: 'bg-slate-100 text-slate-700 border-slate-300',
}

const verdictIcon: Record<Verdict, ReactElement> = {
  SUPPORTED: <CheckCircle2 className="h-4 w-4" aria-hidden="true" />,
  CONTRADICTED: <XCircle className="h-4 w-4" aria-hidden="true" />,
  QUALIFIED: <AlertTriangle className="h-4 w-4" aria-hidden="true" />,
  NOT_FOUND: <FileText className="h-4 w-4" aria-hidden="true" />,
  UNCERTAIN: <Sparkles className="h-4 w-4" aria-hidden="true" />,
}

function App() {
  const [accessMode, setAccessMode] = useState<'welcome' | 'guest' | 'auth'>('welcome')
  const [authConfigured, setAuthConfigured] = useState(false)
  const [authForm, setAuthForm] = useState({ email: '', password: '', mode: 'sign_in' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [guestHistory, setGuestHistory] = useState<Report[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [form, setForm] = useState({
    headline: 'Free shipping on every order',
    description: 'Get a premium water bottle and save 35% today with a 30-day guarantee. Offer ends soon.',
    offer: 'Free shipping and 35% off',
    call_to_action: 'Shop now',
    landing_page_url: '',
    landing_page_text: 'We offer standard shipping for $9.99. Select products do not include free shipping. Our guarantee covers defects only. Pricing starts at $22.00.',
  })

  useEffect(() => {
    fetch(`${API_BASE}/api/auth-status`)
      .then((res) => res.json())
      .then((data) => setAuthConfigured(Boolean(data.configured)))
      .catch(() => setAuthConfigured(false))
  }, [])

  const statusSummary = useMemo(() => {
    if (!report) return []
    return Object.entries(report.summary).map(([label, count]) => ({ label, count }))
  }, [report])

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          headline: form.headline,
          description: form.description,
          offer: form.offer,
          call_to_action: form.call_to_action,
          landing_page_text: form.landing_page_text,
          landing_page_url: form.landing_page_url,
          mock_mode: true,
          guest_session: true,
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Unable to analyze the ad.')
      }
      setReport(data)
      setGuestHistory((current) => [data, ...current].slice(0, 4))
      setAccessMode('guest')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">PS03</p>
              <h1 className="text-lg font-bold text-slate-900">Ad Auditor</h1>
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-slate-300"
            onClick={() => setReport(null)}
          >
            Clear report
          </button>
        </div>
      </header>

      {!report && (
        <main className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[1.2fr_1.8fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-600">Welcome</p>
            <h2 className="mt-4 text-4xl font-bold leading-tight text-slate-900">
              Every Ad Promise. Verified Against the Page.
            </h2>
            <p className="mt-4 text-base text-slate-600">
              Compare ad claims to the landing page and flag unsupported, contradicted, or qualified marketing claims before they reach customers.
            </p>

            <div className="mt-8 grid gap-4">
              <button
                type="button"
                onClick={() => setAccessMode('auth')}
                className="rounded-xl bg-indigo-600 px-5 py-4 text-left text-base font-semibold text-white shadow-sm transition hover:bg-indigo-500"
              >
                Sign in / Create an account
              </button>
              <button
                type="button"
                onClick={() => setAccessMode('guest')}
                className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4 text-left text-base font-semibold text-slate-900 transition hover:border-slate-300"
              >
                Continue as Guest
              </button>
            </div>

            <div className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              {authConfigured ? (
                <span className="font-medium text-emerald-700">Supabase auth is configured.</span>
              ) : (
                <span className="font-medium text-amber-700">Authentication not configured. Guest mode is active.</span>
              )}
            </div>

            {accessMode === 'auth' && (
              <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4" role="alert">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-700">Authentication path</p>
                {authConfigured ? (
                  <div className="mt-3 space-y-3">
                    <div className="grid gap-3">
                      <input
                        aria-label="Email address"
                        value={authForm.email}
                        onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                        placeholder="Email"
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-900"
                      />
                      <input
                        aria-label="Password"
                        type="password"
                        value={authForm.password}
                        onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                        placeholder="Password"
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-900"
                      />
                    </div>
                    <div className="flex gap-3">
                      <button type="button" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">Sign in</button>
                      <button type="button" className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">Create account</button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-slate-700">Auth is not configured in this environment. Use the guest flow to run audits now, or configure Supabase to enable account-based history.</p>
                )}
              </div>
            )}

            {accessMode === 'guest' && (
              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4" role="status">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">Guest session</p>
                <p className="mt-2 text-sm text-slate-700">Guest history is temporary and disappears when the session ends. No shared guest account or saved localStorage history is used.</p>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Quick audit</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-900">Ad and landing page review</h3>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{accessMode === 'guest' ? 'Guest session' : 'Authenticated path'}</span>
            </div>

            <form className="space-y-5" onSubmit={handleAnalyze}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm font-medium text-slate-700">
                  Headline
                  <input
                    value={form.headline}
                    onChange={(e) => setForm({ ...form, headline: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                  />
                </label>
                <label className="block text-sm font-medium text-slate-700">
                  Call to action
                  <input
                    value={form.call_to_action}
                    onChange={(e) => setForm({ ...form, call_to_action: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                  />
                </label>
              </div>

              <label className="block text-sm font-medium text-slate-700">
                Description
                <textarea
                  rows={4}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                />
              </label>

              <label className="block text-sm font-medium text-slate-700">
                Offer / promotion
                <input
                  value={form.offer}
                  onChange={(e) => setForm({ ...form, offer: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                />
              </label>

              <label className="block text-sm font-medium text-slate-700">
                Landing page URL
                <input
                  value={form.landing_page_url}
                  onChange={(e) => setForm({ ...form, landing_page_url: e.target.value })}
                  placeholder="https://example.com"
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                />
              </label>

              <label className="block text-sm font-medium text-slate-700">
                Landing page text (optional paste override)
                <textarea
                  rows={4}
                  value={form.landing_page_text}
                  onChange={(e) => setForm({ ...form, landing_page_text: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none ring-0 focus:border-indigo-500"
                />
              </label>

              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
              )}

              <div className="flex items-center justify-between gap-4 pt-2">
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-300"
                  onClick={() => setGuestHistory([])}
                >
                  Clear session
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Analyzing…' : 'Check claims'}
                </button>
              </div>
            </form>

            {guestHistory.length > 0 && (
              <div className="mt-8 border-t border-slate-200 pt-5">
                <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Recent guest results</p>
                <div className="space-y-2">
                  {guestHistory.map((item, index) => (
                    <div key={`${item.status}-${index}`} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                      <span className="font-medium text-slate-700">Audit #{guestHistory.length - index}</span>
                      <span className="rounded-full bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700">{item.overall_score}/100</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </main>
      )}

      {report && (
        <main className="mx-auto max-w-7xl px-6 py-10">
          <div className="mb-8 flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Audit dashboard</p>
              <h2 className="mt-2 text-3xl font-bold text-slate-900">Ad compliance report</h2>
            </div>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
              {report.mode} • {report.simulated ? 'SIMULATED' : 'Verified'}
            </span>
          </div>

          <section className="grid gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Overall score</p>
              <p className="mt-3 text-3xl font-bold text-slate-900">{report.overall_score}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Claims checked</p>
              <p className="mt-3 text-3xl font-bold text-slate-900">{report.claims.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Overview</p>
              <p className="mt-3 text-lg font-semibold text-slate-900">{report.status}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Mode</p>
              <p className="mt-3 text-lg font-semibold text-slate-900">{report.mode}</p>
            </div>
          </section>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Verdict distribution</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-5">
              {statusSummary.map(({ label, count }) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</p>
                  <p className="mt-3 text-2xl font-bold text-slate-900">{count}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-8 space-y-5">
            {report.claims.map((claim, index) => (
              <article key={`${claim.claim}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Claim {index + 1}</p>
                    <h3 className="mt-2 text-xl font-semibold text-slate-900">{claim.claim}</h3>
                  </div>
                  <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${badgeClasses[claim.verdict]}`}>
                    {verdictIcon[claim.verdict]} {claim.verdict}
                  </span>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Severity</p>
                    <p className="mt-2 font-medium capitalize text-slate-900">{claim.severity}</p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Confidence</p>
                    <p className="mt-2 font-medium text-slate-900">{claim.confidence}</p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Source section</p>
                    <p className="mt-2 font-medium text-slate-900">{claim.source_section}</p>
                  </div>
                </div>

                <div className="mt-4 space-y-3 text-sm text-slate-700">
                  <p><span className="font-semibold text-slate-900">Reason:</span> {claim.reason}</p>
                  <p><span className="font-semibold text-slate-900">Evidence quote:</span> “{claim.quote || 'No direct quote found'}”</p>
                  <p><span className="font-semibold text-slate-900">Explanation:</span> {claim.explanation}</p>
                  <p><span className="font-semibold text-slate-900">Recommendation:</span> {claim.recommended_change}</p>
                </div>
              </article>
            ))}
          </section>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Recommended ad copy changes</h3>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              {report.claims.map((claim, index) => (
                <li key={`${claim.claim}-rec-${index}`} className="rounded-lg border border-slate-200 bg-white p-3">
                  <span className="font-semibold text-slate-900">{claim.claim}</span> — {claim.recommended_change}
                </li>
              ))}
            </ul>
          </section>
        </main>
      )}
    </div>
  )
}

export default App
