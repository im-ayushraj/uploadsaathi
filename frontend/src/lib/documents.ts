import { z } from 'zod'
import { api } from './api'

/** Mirrors the backend UploadOutcome — what UploadSaathi did to one file. */
export const uploadOutcomeSchema = z.object({
  filename: z.string(),
  original_size: z.number(),
  optimized_size: z.number(),
  format: z.string(),
  mime_type: z.string().nullable().optional(),
  reduction_percent: z.number(),
  size_valid: z.boolean(),
  format_valid: z.boolean(),
  quality_status: z.string(),
  accepted: z.boolean(),
  readable: z.boolean(),
  steps: z.array(z.string()).default([]),
  issues: z.array(z.string()).default([]),
  warnings: z.array(z.string()).default([]),
  notes: z.array(z.string()).default([]),
  width: z.number().nullable().optional(),
  height: z.number().nullable().optional(),
  pages: z.number().nullable().optional(),
  quality_used: z.number().nullable().optional(),
  scale_applied: z.number().default(1),
  mode: z.string().default('balanced'),
})

export const enrolmentDocumentSchema = z.object({
  id: z.number(),
  document_type: z.string(),
  status: z.string(),
  original_filename: z.string().nullable().optional(),
  original_size: z.number(),
  optimized_size: z.number(),
  format: z.string(),
  mime_type: z.string().nullable().optional(),
  quality_status: z.string(),
  /** The citizen confirmed this file. */
  accepted: z.boolean(),
  /** UploadSaathi says the file meets the portal's rules. */
  ready: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const uploadResponseSchema = z.object({
  ready: z.boolean(),
  outcome: uploadOutcomeSchema,
  document: enrolmentDocumentSchema.nullable(),
  message: z.string(),
})

export type UploadOutcome = z.infer<typeof uploadOutcomeSchema>
export type EnrolmentDocument = z.infer<typeof enrolmentDocumentSchema>
export type UploadResponse = z.infer<typeof uploadResponseSchema>

export type OptimizationMode = 'balanced' | 'aggressive'

const base = (enrolmentId: number) => `/enrolments/${enrolmentId}/documents`

export async function fetchDocuments(enrolmentId: number): Promise<EnrolmentDocument[]> {
  const { data } = await api.get(base(enrolmentId))
  return z.array(enrolmentDocumentSchema).parse(data)
}

export async function uploadDocument(opts: {
  enrolmentId: number
  documentType: string
  file: File
  mode?: OptimizationMode
}): Promise<UploadResponse> {
  const form = new FormData()
  form.append('document_type', opts.documentType)
  form.append('mode', opts.mode ?? 'balanced')
  form.append('file', opts.file)
  // Optimising a large scan takes longer than an ordinary API call.
  const { data } = await api.post(base(opts.enrolmentId), form, { timeout: 120000 })
  return uploadResponseSchema.parse(data)
}

export async function acceptDocument(
  enrolmentId: number,
  documentId: number,
): Promise<EnrolmentDocument> {
  const { data } = await api.post(`${base(enrolmentId)}/${documentId}/accept`)
  return enrolmentDocumentSchema.parse(data)
}

export async function deleteDocument(enrolmentId: number, documentId: number): Promise<void> {
  await api.delete(`${base(enrolmentId)}/${documentId}`)
}

/**
 * The file endpoint needs the auth header, so a preview cannot be a plain `src` URL.
 * Callers must revoke the returned object URL when they are done with it.
 */
export async function fetchDocumentObjectUrl(
  enrolmentId: number,
  documentId: number,
): Promise<string> {
  const { data } = await api.get(`${base(enrolmentId)}/${documentId}/file`, {
    responseType: 'blob',
  })
  return URL.createObjectURL(data as Blob)
}
