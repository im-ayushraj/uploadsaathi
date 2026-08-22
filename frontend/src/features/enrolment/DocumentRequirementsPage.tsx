import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { StepShell, primaryButtonClass, secondaryButtonClass } from './StepShell'
import { fetchDocumentTypes, fetchEnrolment, formatBytes } from '../../lib/enrolment'
import type { DocumentType } from '../../lib/enrolment'

export function RequirementSummary({ doc }: { doc: DocumentType }) {
  const r = doc.requirement
  const chips = [
    `Max ${formatBytes(r.max_bytes)}`,
    r.accepted_formats.map((f) => f.toUpperCase()).join(' / '),
    r.min_width && r.min_height ? `At least ${r.min_width}×${r.min_height} px` : null,
    r.max_pages ? `Up to ${r.max_pages} page${r.max_pages === 1 ? '' : 's'}` : null,
    r.colour_mode !== 'any' ? `${r.colour_mode} only` : null,
  ].filter(Boolean) as string[]

  return (
    <ul className="mt-3 flex flex-wrap gap-2">
      {chips.map((chip) => (
        <li
          key={chip}
          className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700"
        >
          {chip}
        </li>
      ))}
    </ul>
  )
}

export function DocumentRequirementsPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)
  const navigate = useNavigate()

  const { data: enrolment } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })

  const { data: docs, isPending } = useQuery({
    queryKey: ['documents', enrolment?.applicant_type],
    queryFn: () => fetchDocumentTypes(enrolment!.applicant_type),
    enabled: Boolean(enrolment?.applicant_type),
  })

  return (
    <StepShell
      current="documents"
      title="Documents you will need"
      description="Every rule below comes from the portal's configuration. UploadSaathi will make your files match them."
    >
      {isPending && <p className="text-sm text-slate-600">Loading requirements…</p>}

      <div className="space-y-4">
        {docs?.map((doc) => (
          <section key={doc.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold">{doc.label}</h2>
              {doc.short_label && (
                <span className="rounded-full bg-saathi-100 px-2 py-0.5 text-[11px] font-medium text-saathi-700">
                  {doc.short_label}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-slate-600">{doc.help}</p>

            {doc.examples.length > 0 && (
              <p className="mt-2 text-sm text-slate-600">
                <span className="font-medium text-slate-800">Any one of:</span>{' '}
                {doc.examples.join(', ')}
              </p>
            )}

            <RequirementSummary doc={doc} />
          </section>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-saathi-100 bg-saathi-50 p-4 text-sm text-slate-700">
        <p className="font-semibold text-saathi-700">Uploading comes next</p>
        <p className="mt-1">
          File selection and automatic optimisation are added in the UploadSaathi step. For now you
          can review your application and prepare it.
        </p>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          className={primaryButtonClass}
          onClick={() => navigate(`/enrolment/${enrolmentId}/review`)}
        >
          Continue to review
        </button>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => navigate(`/enrolment/${enrolmentId}/address`)}
        >
          Back
        </button>
      </div>
    </StepShell>
  )
}
