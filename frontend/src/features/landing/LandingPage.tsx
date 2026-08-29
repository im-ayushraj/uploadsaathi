import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchHealth } from '../../lib/health'

export function LandingPage() {
  const { data, isPending, isError, failureCount, refetch, isFetching } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    // The demo runs on a free host that sleeps when idle. A first visit can therefore fail once or
    // twice while the instance boots — that is waking up, not being broken, so keep trying.
    retry: 4,
    retryDelay: 4000,
  })

  // A sleeping host does not refuse the connection, it holds it open while it boots. So a check
  // that is merely taking a long time counts as waking up, just like one that failed and retried.
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!isPending) {
      setSlow(false)
      return
    }
    const timer = setTimeout(() => setSlow(true), 4000)
    return () => clearTimeout(timer)
  }, [isPending])

  const waking = isPending && (slow || failureCount > 0)

  const backend = waking
    ? { label: 'Waking the demo server — this can take up to a minute…', tone: 'text-amber-700' }
    : isPending
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
        {waking && (
          <p className="mt-1 text-xs text-ink-600">
            The prototype is hosted on a free plan, so the server sleeps when nobody is using it.
            The first request wakes it.
          </p>
        )}
        {isError && (
          <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            <p className="text-sm font-semibold">
              This almost always means the demo server is asleep — not that it is broken.
            </p>
            <p className="mt-1">
              The prototype is hosted on a free plan, which shuts the server down when nobody has
              used it for a while. Opening this page has already started waking it up.
            </p>
            <p className="mt-1">
              <span className="font-semibold">What to do:</span> wait 5–60 seconds and try again —
              or just sign in, and the login request itself will wake the server. It works normally
              from then on.
            </p>
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isFetching}
              className="mt-2 rounded-lg bg-amber-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-800 disabled:opacity-60"
            >
              {isFetching ? 'Checking again…' : 'Try again'}
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
