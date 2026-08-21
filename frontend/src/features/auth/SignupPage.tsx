import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { signupSchema, toErrorMessage } from '../../lib/auth'

export function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', mobile: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const parsed = signupSchema.safeParse(form)
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Check the fields and try again.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await signup(parsed.data)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(toErrorMessage(err, 'Could not create your account. Please try again.'))
      setSubmitting(false)
    }
  }

  const inputClass =
    'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-saathi-500 focus:outline-none focus:ring-2 focus:ring-saathi-500/30'

  return (
    <main className="mx-auto max-w-md px-4 py-10">
      <h1 className="text-2xl font-bold">Create your account</h1>
      <p className="mt-1 text-sm text-slate-600">
        A synthetic demo account. No real identity data — you can use a fake name and a test
        number.
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="full_name" className="block text-sm font-medium text-slate-800">
            Full name
          </label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            autoComplete="name"
            required
            value={form.full_name}
            onChange={(e) => set('full_name', e.target.value)}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-slate-800">
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(e) => set('email', e.target.value)}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="mobile" className="block text-sm font-medium text-slate-800">
            Mobile number
          </label>
          <input
            id="mobile"
            name="mobile"
            type="tel"
            inputMode="numeric"
            autoComplete="tel"
            required
            placeholder="10-digit number, e.g. 98765 43210"
            value={form.mobile}
            onChange={(e) => set('mobile', e.target.value.replace(/[^\d+ ]/g, ''))}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-800">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={64}
            value={form.password}
            onChange={(e) => set('password', e.target.value)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-saathi-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-saathi-700 disabled:opacity-60"
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-4 text-sm text-slate-600">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-saathi-600 hover:underline">
          Sign in
        </Link>
      </p>
    </main>
  )
}
