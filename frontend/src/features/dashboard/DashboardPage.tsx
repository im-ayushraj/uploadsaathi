import { useAuth } from '../auth/AuthContext'

export function DashboardPage() {
  const { user } = useAuth()

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold">Namaste, {user?.full_name.split(' ')[0]}</h1>
      <p className="mt-1 text-sm text-slate-600">
        Signed in as {user?.email} · {user?.mobile}
      </p>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold">Your applications</h2>
        <p className="mt-1 text-sm text-slate-600">
          The Aadhaar enrolment document-preparation journey is added in the next step.
        </p>
      </div>
    </main>
  )
}
