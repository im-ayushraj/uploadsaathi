import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { primaryButtonClass, secondaryButtonClass } from './StepShell'
import { RequirementSummary } from './RequirementSummary'
import { formatBytes } from '../../lib/enrolment'
import type { DocumentType } from '../../lib/enrolment'
import {
  acceptDocument,
  deleteDocument,
  fetchDocumentObjectUrl,
  uploadDocument,
} from '../../lib/documents'
import type { EnrolmentDocument, UploadOutcome, UploadResponse } from '../../lib/documents'

/** Engine step codes → what actually happened, in citizen language. */
const STEP_LABELS: Record<string, string> = {
  auto_orient: 'Turned the photo the right way up',
  strip_metadata: 'Removed hidden camera data',
  flatten_alpha: 'Placed the image on a white background',
  greyscale: 'Converted to black and white',
  convert: 'Changed the file type to fit the portal’s rules',
  resize: 'Resized to fit the portal’s limits',
  recompress: 'Compressed the image',
  target_size_search: 'Found the highest quality that still fits the size limit',
  pdf_optimise_structure: 'Cleaned up the PDF’s internal structure',
  pdf_downsample_images: 'Reduced the resolution of images inside the PDF',
}

const WARNING_LABELS: Record<string, string> = {
  size_target_not_reached_readability_floor_hit:
    'We stopped before the size limit because going further would have made this unreadable.',
  output_below_portal_minimum_size: 'The result is smaller than the portal’s minimum file size.',
  significant_resolution_reduction:
    'The resolution was reduced noticeably. Please check it still reads clearly.',
  heavy_compression_applied:
    'Heavy compression was needed. Please check it still reads clearly.',
  searchable_text_layer_lost: 'The PDF’s selectable text was lost — the pages are now images.',
  transparency_flattened_onto_white: 'Transparent areas were filled with white.',
}

/** Advisory only, and true of almost every phone photo — showing it would just add noise. */
const HIDDEN_WARNINGS = new Set(['dpi_not_declared_by_file'])

function humanise(code: string): string {
  const belowDpi = /^dpi_below_recommended_(\d+)$/.exec(code)
  if (belowDpi) {
    return `The portal recommends around ${belowDpi[1]} DPI. This file declares less, which is usually still fine for a clear photo.`
  }
  const rasterised = /^pages_rasterised_at_(\d+)dpi_text_layer_removed$/.exec(code)
  if (rasterised) {
    return `The PDF pages were turned into images at ${rasterised[1]} DPI to fit the size limit, so the text is no longer selectable.`
  }
  return WARNING_LABELS[code] ?? code.replace(/_/g, ' ')
}

function StatusPill({ document }: { document?: EnrolmentDocument }) {
  if (!document) {
    return (
      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
        Not uploaded
      </span>
    )
  }
  if (document.accepted) {
    return (
      <span className="rounded-full bg-green-100 px-2.5 py-1 text-[11px] font-semibold text-green-800">
        ✓ Ready to upload
      </span>
    )
  }
  return (
    <span
      className={
        document.ready
          ? 'rounded-full bg-saathi-100 px-2.5 py-1 text-[11px] font-semibold text-saathi-700'
          : 'rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800'
      }
    >
      {document.ready ? 'Waiting for your confirmation' : 'Needs a different file'}
    </span>
  )
}

/** The before → after moment: the one thing the citizen came here for. */
function BeforeAfter({ outcome }: { outcome: UploadOutcome }) {
  const shrank = outcome.optimized_size < outcome.original_size
  return (
    <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-slate-50 p-3 text-sm">
      <span className="text-slate-500 line-through">{formatBytes(outcome.original_size)}</span>
      <span aria-hidden className="text-slate-400">
        →
      </span>
      <span className="font-semibold text-slate-900">{formatBytes(outcome.optimized_size)}</span>
      {shrank && (
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">
          {outcome.reduction_percent}% smaller
        </span>
      )}
      {outcome.readable && (
        <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-700 ring-1 ring-slate-200">
          Readable ✓
        </span>
      )}
      <span className="text-xs text-slate-600">
        {outcome.format}
        {outcome.width && outcome.height ? ` · ${outcome.width}×${outcome.height} px` : ''}
        {outcome.pages ? ` · ${outcome.pages} page${outcome.pages === 1 ? '' : 's'}` : ''}
      </span>
    </div>
  )
}

/** The stored file, fetched with the auth header and shown from a blob URL. */
function Preview({ enrolmentId, document }: { enrolmentId: number; document: EnrolmentDocument }) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    fetchDocumentObjectUrl(enrolmentId, document.id)
      .then((u) => {
        objectUrl = u
        if (cancelled) URL.revokeObjectURL(u)
        else setUrl(u)
      })
      .catch(() => setUrl(null))
    return () => {
      cancelled = true
      setUrl(null)
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [enrolmentId, document.id, document.updated_at])

  if (!url) return null
  if (document.format.toLowerCase() === 'pdf') {
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="mt-3 inline-block text-sm font-medium text-saathi-700 underline"
      >
        Open the prepared PDF
      </a>
    )
  }
  return (
    <img
      src={url}
      alt="Prepared document preview"
      className="mt-3 max-h-56 rounded-lg border border-slate-200 object-contain"
    />
  )
}

export function DocumentSlot({
  enrolmentId,
  doc,
  stored,
  locked,
}: {
  enrolmentId: number
  doc: DocumentType
  stored?: EnrolmentDocument
  locked?: boolean
}) {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [response, setResponse] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['enrolment-documents', enrolmentId] })
    void queryClient.invalidateQueries({ queryKey: ['enrolment', enrolmentId] })
  }

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument({ enrolmentId, documentType: doc.id, file }),
    onSuccess: (data) => {
      setResponse(data)
      setError(null)
      refresh()
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'We could not prepare this file. Please try again.')
    },
  })

  const accept = useMutation({
    mutationFn: () => acceptDocument(enrolmentId, stored!.id),
    onSuccess: () => {
      setResponse(null)
      refresh()
    },
  })

  const remove = useMutation({
    mutationFn: () => deleteDocument(enrolmentId, stored!.id),
    onSuccess: () => {
      setResponse(null)
      refresh()
    },
  })

  const onPick = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = '' // so picking the same file again re-runs the optimiser
    if (!file) return
    setResponse(null)
    setError(null)
    upload.mutate(file)
  }

  const outcome = response?.outcome
  const busy = upload.isPending
  const shownWarnings = (outcome?.warnings ?? []).filter((w) => !HIDDEN_WARNINGS.has(w))

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-base font-semibold">{doc.label}</h2>
        {doc.short_label && (
          <span className="rounded-full bg-saathi-100 px-2 py-0.5 text-[11px] font-medium text-saathi-700">
            {doc.short_label}
          </span>
        )}
        <span className="ml-auto">
          <StatusPill document={stored} />
        </span>
      </div>

      <p className="mt-1 text-sm text-slate-600">{doc.help}</p>
      {doc.examples.length > 0 && (
        <p className="mt-2 text-sm text-slate-600">
          <span className="font-medium text-slate-800">Any one of:</span> {doc.examples.join(', ')}
        </p>
      )}
      <RequirementSummary doc={doc} />

      {busy && (
        <p className="mt-4 text-sm font-medium text-saathi-700" role="status">
          Checking your file and preparing it for the portal…
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      {!busy && response && (
        <div
          className={[
            'mt-4 rounded-lg border p-3',
            response.ready ? 'border-green-200 bg-green-50/60' : 'border-amber-200 bg-amber-50/60',
          ].join(' ')}
        >
          <p className="text-sm font-semibold text-slate-900">{response.message}</p>
          {outcome && <BeforeAfter outcome={outcome} />}

          {outcome && outcome.steps.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-slate-700">
              {outcome.steps.map((step) => (
                <li key={step}>• {STEP_LABELS[step] ?? step.replace(/_/g, ' ')}</li>
              ))}
            </ul>
          )}

          {shownWarnings.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-amber-800">
              {shownWarnings.map((w) => (
                <li key={w}>! {humanise(w)}</li>
              ))}
            </ul>
          )}

          {response.document && <Preview enrolmentId={enrolmentId} document={response.document} />}
        </div>
      )}

      {!busy && !response && stored && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-sm">
          <p className="text-slate-700">
            <span className="font-medium">{stored.original_filename ?? 'Your file'}</span> —{' '}
            {formatBytes(stored.original_size)} → {formatBytes(stored.optimized_size)} (
            {stored.format.toUpperCase()})
          </p>
          {!stored.ready && (
            <p className="mt-2 text-amber-800">
              This file does not meet the portal’s rules yet. Please choose a different one.
            </p>
          )}
          <Preview enrolmentId={enrolmentId} document={stored} />
        </div>
      )}

      {!locked && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept={doc.requirement.accepted_formats.map((f) => `.${f}`).join(',')}
            className="hidden"
            onChange={onPick}
            aria-label={`Choose a file for ${doc.label}`}
          />
          <button
            type="button"
            className={stored?.accepted ? secondaryButtonClass : primaryButtonClass}
            disabled={busy}
            onClick={() => fileInput.current?.click()}
          >
            {busy ? 'Preparing…' : stored ? 'Choose a different file' : 'Choose a file'}
          </button>

          {stored && !stored.accepted && stored.ready && (
            <button
              type="button"
              className={primaryButtonClass}
              disabled={accept.isPending}
              onClick={() => accept.mutate()}
            >
              {accept.isPending ? 'Saving…' : 'Use this file'}
            </button>
          )}

          {stored && (
            <button
              type="button"
              className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
            >
              Remove
            </button>
          )}
        </div>
      )}
    </section>
  )
}
