import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { StepShell, primaryButtonClass } from './StepShell'
import { createEnrolment, fetchPortal } from '../../lib/enrolment'
import { toErrorMessage } from '../../lib/auth'

export function ApplicantTypePage() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: portal, isPending } = useQuery({ queryKey: ['portal'], queryFn: () => fetchPortal() })

  const create = useMutation({
    mutationFn: (applicantType: string) => createEnrolment(applicantType),
    onSuccess: (enrolment) => navigate(`/enrolment/${enrolment.id}/personal`),
    onError: (err) => setError(toErrorMessage(err, 'Could not start the application.')),
  })

  return (
    <StepShell
      current="type"
      title="Who is this enrolment for?"
      description="This decides which documents you will need. Choose the option that matches the applicant."
    >
      {isPending && <p className="text-sm text-slate-600">Loading options…</p>}

      <div className="space-y-3">
        {portal?.applicant_types.map((type) => (
          <label
            key={type.id}
            className={[
              'flex cursor-pointer gap-3 rounded-xl border p-4 transition',
              selected === type.id
                ? 'border-saathi-500 bg-saathi-50 ring-2 ring-saathi-500/25'
                : 'border-slate-200 bg-white hover:border-saathi-300',
            ].join(' ')}
          >
            <input
              type="radio"
              name="applicant_type"
              value={type.id}
              checked={selected === type.id}
              onChange={() => setSelected(type.id)}
              className="mt-1 h-4 w-4 accent-saathi-600"
            />
            <span>
              <span className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                {type.label}
                {type.is_primary_demo && (
                  <span className="rounded-full bg-saathi-100 px-2 py-0.5 text-[11px] font-medium text-saathi-700">
                    Demo path
                  </span>
                )}
              </span>
              <span className="mt-1 block text-sm text-slate-600">{type.description}</span>
              <span className="mt-1 block text-xs text-slate-500">
                {type.required_documents.length} document
                {type.required_documents.length === 1 ? '' : 's'} required
              </span>
            </span>
          </label>
        ))}
      </div>

      {portal && (
        <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600">
          {portal.journey_note}
        </p>
      )}

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6">
        <button
          type="button"
          className={primaryButtonClass}
          disabled={!selected || create.isPending}
          onClick={() => selected && create.mutate(selected)}
        >
          {create.isPending ? 'Starting…' : 'Continue'}
        </button>
      </div>
    </StepShell>
  )
}
