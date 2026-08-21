import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchHealth } from '../../lib/health'

export function LandingPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    retry: 1,
  })

  const backend = isPending
    ? { label: 'Checking backend…', tone: 'text-ink-600' }
    : isError
      ? { label: 'Backend unreachable', tone: 'text-red-600' }
      : { label: `Backend ${data.status} · database ${data.database}`, tone: 'text-green-700' }

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <p className="text-sm font-semibold tracking-wide text-saathi-600">UPLOADSAATHI</p>
      <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
        Make any document portal-ready — without losing readability.
      </h1>
      <p className="mt-4 text-ink-600">
        Most people can take a photo of a document. Far fewer can make it satisfy a portal&apos;s
        file size, format and dimension rules. UploadSaathi does that part automatically.
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to="/signup"
          className="rounded-lg bg-saathi-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-saathi-700"
        >
          Get started
        </Link>
        <Link
          to="/login"
          className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold hover:bg-white"
        >
          I already have an account
        </Link>
      </div>

      <div className="mt-8 rounded-xl border border-saathi-100 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-ink-900">System status</h2>
        <p className={`mt-1 text-sm ${backend.tone}`} role="status">
          {backend.label}
        </p>
        {data && (
          <p className="mt-1 text-xs text-ink-600">
            {data.app} v{data.version} ({data.env})
          </p>
        )}
      </div>
    </main>
  )
}
