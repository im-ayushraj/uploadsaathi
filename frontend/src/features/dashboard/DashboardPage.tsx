import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { deleteEnrolment, fetchEnrolments, fetchPortal } from '../../lib/enrolment'
import type { Enrolment } from '../../lib/enrolment'

function statusChip(status: string) {
  const prepared = status === 'prepared'
  return (
    <span
      className={[
        'rounded-full px-2 py-0.5 text-[11px] font-medium',
        prepared ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800',
      ].join(' ')}
    >
      {prepared ? 'Prepared' : 'Draft'}
    </span>
  )
}

/** Sends a draft back to the step the applicant still has to complete. */
function resumePath(e: Enrolment): string {
  if (e.status === 'prepared') return `/enrolment/${e.id}/prepared`
  if (!e.personal_details) return `/enrolment/${e.id}/personal`
  if (!e.address) return `/enrolment/${e.id}/address`
  return `/enrolment/${e.id}/review`
}

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: enrolments, isPending } = useQuery({
    queryKey: ['enrolments'],
    queryFn: fetchEnrolments,
  })
  const { data: portal } = useQuery({ queryKey: ['portal'], queryFn: () => fetchPortal() })

  const remove = useMutation({
    mutationFn: (id: number) => deleteEnrolment(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['enrolments'] }),
  })

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold">Namaste, {user?.full_name.split(' ')[0]}</h1>
      <p className="mt-1 text-sm text-slate-600">
        Prepare the documents for your enrolment, then carry them to a centre.
      </p>

      <section className="mt-6 rounded-xl border border-saathi-100 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold">{portal?.portal_name ?? 'Aadhaar Enrolment'}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {portal?.journey_note ??
            'This prototype prepares the document portion of the journey only.'}
        </p>
        <button
          type="button"
          onClick={() => navigate('/enrolment/new')}
          className="mt-4 rounded-lg bg-saathi-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-saathi-700"
        >
          New Aadhaar enrolment
        </button>
      </section>

      <section className="mt-8">
        <h2 className="text-base font-semibold">Your applications</h2>

        {isPending && <p className="mt-2 text-sm text-slate-600">Loading…</p>}

        {enrolments?.length === 0 && (
          <p className="mt-2 rounded-xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-600">
            No applications yet. Start a new enrolment to prepare your documents.
          </p>
        )}

        <ul className="mt-3 space-y-3">
          {enrolments?.map((e) => (
            <li
              key={e.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">
                    {e.personal_details?.full_name || 'Untitled application'}
                  </span>
                  {statusChip(e.status)}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {e.applicant_type.replace(/_/g, ' ')} · started{' '}
                  {new Date(e.created_at).toLocaleDateString()}
                  {e.reference_code ? ` · ${e.reference_code}` : ''}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  to={resumePath(e)}
                  className="rounded-lg bg-saathi-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-saathi-700"
                >
                  {e.status === 'prepared' ? 'View' : 'Continue'}
                </Link>
                {e.status !== 'prepared' && (
                  <button
                    type="button"
                    onClick={() => remove.mutate(e.id)}
                    disabled={remove.isPending}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-60"
                  >
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
