import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { StepShell, primaryButtonClass, secondaryButtonClass } from './StepShell'
import {
  fetchDocumentTypes,
  fetchEnrolment,
  fetchPortal,
  prepareEnrolment,
} from '../../lib/enrolment'
import { toErrorMessage } from '../../lib/auth'

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex flex-wrap justify-between gap-2 border-b border-slate-100 py-2 last:border-0">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="text-sm font-medium text-slate-900">{value || '—'}</dd>
    </div>
  )
}

export function ReviewPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { data: enrolment, isPending } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })
  const { data: portal } = useQuery({ queryKey: ['portal'], queryFn: () => fetchPortal() })
  const { data: docTypes } = useQuery({
    queryKey: ['portal-documents', enrolment?.applicant_type],
    queryFn: () => fetchDocumentTypes(enrolment!.applicant_type),
    enabled: Boolean(enrolment?.applicant_type),
  })

  const prepare = useMutation({
    mutationFn: () => prepareEnrolment(enrolmentId),
    onSuccess: (updated) => {
      queryClient.setQueryData(['enrolment', enrolmentId], updated)
      queryClient.invalidateQueries({ queryKey: ['enrolments'] })
      navigate(`/enrolment/${enrolmentId}/prepared`)
    },
    onError: (err) => setError(toErrorMessage(err, 'Could not prepare this application.')),
  })

  if (isPending) {
    return (
      <StepShell current="review" title="Review your application">
        <p className="text-sm text-slate-600">Loading…</p>
      </StepShell>
    )
  }

  const p = enrolment?.personal_details
  const a = enrolment?.address
  const applicantLabel =
    portal?.applicant_types.find((t) => t.id === enrolment?.applicant_type)?.label ??
    enrolment?.applicant_type

  const progress = enrolment?.progress
  const accepted = new Set(progress?.documents_accepted ?? [])
  const labelFor = (slot: string) => docTypes?.find((d) => d.id === slot)?.label ?? slot
  const canPrepare = progress?.can_prepare ?? false

  return (
    <StepShell
      current="review"
      title="Review your application"
      description="Check these details before preparing your document pack."
    >
      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Applicant type</h2>
        <dl className="mt-2">
          <Row label="Type" value={applicantLabel} />
        </dl>
        <Link
          to={`/enrolment/${enrolmentId}/personal`}
          className="mt-2 inline-block text-sm font-medium text-saathi-600 hover:underline"
        >
          Edit details
        </Link>
      </section>

      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Personal details</h2>
        <dl className="mt-2">
          <Row label="Full name" value={p?.full_name} />
          <Row label="Date of birth" value={p?.date_of_birth} />
          <Row label="Gender" value={p?.gender} />
          {p?.guardian_name && <Row label="Parent / guardian" value={p.guardian_name} />}
          <Row label="Mobile" value={p?.mobile} />
          <Row label="Email" value={p?.email} />
        </dl>
      </section>

      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Address</h2>
        <dl className="mt-2">
          <Row label="House / street" value={a?.address_line1} />
          <Row label="Area" value={a?.address_line2} />
          <Row label="Landmark" value={a?.landmark} />
          <Row label="Village / town / city" value={a?.village_town_city} />
          <Row label="District" value={a?.district} />
          <Row label="State" value={a?.state} />
          <Row label="PIN code" value={a?.pincode} />
        </dl>
        <Link
          to={`/enrolment/${enrolmentId}/address`}
          className="mt-2 inline-block text-sm font-medium text-saathi-600 hover:underline"
        >
          Edit address
        </Link>
      </section>

      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Documents</h2>
        <ul className="mt-2 space-y-1">
          {(progress?.documents_required ?? []).map((slot) => {
            const done = accepted.has(slot)
            return (
              <li key={slot} className="flex items-center gap-2 text-sm">
                <span
                  aria-hidden
                  className={[
                    'grid h-5 w-5 place-items-center rounded-full text-[11px] font-semibold',
                    done ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-600',
                  ].join(' ')}
                >
                  {done ? '✓' : '·'}
                </span>
                <span className={done ? 'text-slate-900' : 'text-slate-600'}>{labelFor(slot)}</span>
                {!done && <span className="text-xs text-amber-700">not ready yet</span>}
              </li>
            )
          })}
        </ul>
        <Link
          to={`/enrolment/${enrolmentId}/documents`}
          className="mt-2 inline-block text-sm font-medium text-saathi-600 hover:underline"
        >
          {progress?.documents ? 'Review documents' : 'Finish the documents'}
        </Link>
      </section>

      <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600">
        Preparing an application only creates your local document pack. Nothing is sent to UIDAI or
        any government system.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          className={primaryButtonClass}
          disabled={prepare.isPending || !canPrepare}
          onClick={() => prepare.mutate()}
        >
          {prepare.isPending ? 'Preparing…' : 'Prepare my application'}
        </button>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => navigate(`/enrolment/${enrolmentId}/documents`)}
        >
          Back
        </button>
        {!canPrepare && (
          <span className="text-sm text-slate-600">
            Complete every step above to prepare your document pack.
          </span>
        )}
      </div>
    </StepShell>
  )
}
