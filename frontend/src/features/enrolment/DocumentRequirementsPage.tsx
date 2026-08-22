import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { StepShell, primaryButtonClass, secondaryButtonClass } from './StepShell'
import { DocumentSlot } from './DocumentSlot'
import { fetchDocumentTypes, fetchEnrolment } from '../../lib/enrolment'
import { fetchDocuments } from '../../lib/documents'

export function DocumentRequirementsPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)
  const navigate = useNavigate()

  const { data: enrolment } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })

  const { data: docs, isPending } = useQuery({
    queryKey: ['portal-documents', enrolment?.applicant_type],
    queryFn: () => fetchDocumentTypes(enrolment!.applicant_type),
    enabled: Boolean(enrolment?.applicant_type),
  })

  const { data: uploaded } = useQuery({
    queryKey: ['enrolment-documents', enrolmentId],
    queryFn: () => fetchDocuments(enrolmentId),
    enabled: Number.isFinite(enrolmentId),
  })

  const locked = Boolean(enrolment && enrolment.status !== 'draft')
  const bySlot = new Map((uploaded ?? []).map((d) => [d.document_type, d]))
  const acceptedCount = (uploaded ?? []).filter((d) => d.accepted).length
  const total = docs?.length ?? 0
  const allDone = total > 0 && acceptedCount === total

  return (
    <StepShell
      current="documents"
      title="Your documents"
      description="Upload whatever you have — a phone photo is fine. UploadSaathi resizes and compresses each file to match this portal's rules while keeping it readable."
    >
      {isPending && <p className="text-sm text-slate-600">Loading requirements…</p>}

      {total > 0 && (
        <p className="mb-4 text-sm font-medium text-slate-700">
          {acceptedCount} of {total} documents ready
        </p>
      )}

      <div className="space-y-4">
        {docs?.map((doc) => (
          <DocumentSlot
            key={doc.id}
            enrolmentId={enrolmentId}
            doc={doc}
            stored={bySlot.get(doc.id)}
            locked={locked}
          />
        ))}
      </div>

      <p className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
        Your files stay in this prototype. Nothing is sent to UIDAI or any other portal, and the
        original upload is never stored — only the prepared version you accept.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
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
        {!allDone && total > 0 && (
          <span className="text-sm text-slate-600">
            You can review now, but every document must be ready before you can prepare the
            application.
          </span>
        )}
      </div>
    </StepShell>
  )
}
