import { z } from 'zod'
import { api } from './api'

/** Portal configuration — the UI renders whatever the backend config declares. */
export const requirementSchema = z.object({
  accepted_formats: z.array(z.string()),
  max_bytes: z.number(),
  min_bytes: z.number(),
  min_width: z.number().nullable(),
  min_height: z.number().nullable(),
  max_width: z.number().nullable(),
  max_height: z.number().nullable(),
  min_dpi: z.number().nullable(),
  max_pages: z.number().nullable(),
  colour_mode: z.string(),
})

export const documentTypeSchema = z.object({
  id: z.string(),
  label: z.string(),
  short_label: z.string(),
  help: z.string(),
  examples: z.array(z.string()),
  requirement: requirementSchema,
})

export const applicantTypeSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  required_documents: z.array(z.string()),
  is_primary_demo: z.boolean(),
})

export const portalSchema = z.object({
  portal_id: z.string(),
  portal_name: z.string(),
  authority_note: z.string(),
  journey_note: z.string(),
  config_version: z.string(),
  applicant_types: z.array(applicantTypeSchema),
})

export type Requirement = z.infer<typeof requirementSchema>
export type DocumentType = z.infer<typeof documentTypeSchema>
export type ApplicantType = z.infer<typeof applicantTypeSchema>
export type Portal = z.infer<typeof portalSchema>

export const AADHAAR = 'aadhaar'

export async function fetchPortal(portalId = AADHAAR): Promise<Portal> {
  const { data } = await api.get(`/portals/${portalId}`)
  return portalSchema.parse(data)
}

export async function fetchDocumentTypes(
  applicantType: string,
  portalId = AADHAAR,
): Promise<DocumentType[]> {
  const { data } = await api.get(`/portals/${portalId}/documents`, {
    params: { applicant_type: applicantType },
  })
  return z.array(documentTypeSchema).parse(data)
}

/** Enrolments */
export const personalDetailsSchema = z.object({
  full_name: z.string().trim().min(2, 'Enter the full name'),
  date_of_birth: z.string().min(1, 'Enter the date of birth'),
  gender: z.enum(['male', 'female', 'transgender']),
  guardian_name: z.string().trim().max(120).optional().nullable(),
  email: z.string().trim().email('Enter a valid email').optional().nullable(),
  mobile: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit mobile number')
    .optional()
    .nullable(),
})

export const addressSchema = z.object({
  address_line1: z.string().trim().min(3, 'Enter the house / street details'),
  address_line2: z.string().trim().max(160).optional().nullable(),
  landmark: z.string().trim().max(120).optional().nullable(),
  village_town_city: z.string().trim().min(2, 'Enter the village, town or city'),
  district: z.string().trim().min(2, 'Enter the district'),
  state: z.string().trim().min(2, 'Enter the state'),
  pincode: z
    .string()
    .trim()
    .regex(/^[1-9]\d{5}$/, 'Enter a valid 6-digit PIN code'),
})

export const progressSchema = z.object({
  applicant_type: z.boolean(),
  personal_details: z.boolean(),
  address: z.boolean(),
  documents: z.boolean(),
  documents_required: z.array(z.string()).default([]),
  documents_accepted: z.array(z.string()).default([]),
  can_prepare: z.boolean(),
})

export const enrolmentSchema = z.object({
  id: z.number(),
  portal_id: z.string(),
  applicant_type: z.string(),
  status: z.string(),
  personal_details: personalDetailsSchema.nullable().optional(),
  address: addressSchema.nullable().optional(),
  reference_code: z.string().nullable().optional(),
  prepared_at: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const enrolmentDetailSchema = enrolmentSchema.extend({ progress: progressSchema })

export type PersonalDetails = z.infer<typeof personalDetailsSchema>
export type AddressInput = z.infer<typeof addressSchema>
export type Enrolment = z.infer<typeof enrolmentSchema>
export type EnrolmentDetail = z.infer<typeof enrolmentDetailSchema>

export async function createEnrolment(applicantType: string): Promise<EnrolmentDetail> {
  const { data } = await api.post('/enrolments', {
    applicant_type: applicantType,
    portal_id: AADHAAR,
  })
  return enrolmentDetailSchema.parse(data)
}

export async function fetchEnrolments(): Promise<Enrolment[]> {
  const { data } = await api.get('/enrolments')
  return z.array(enrolmentSchema).parse(data)
}

export async function fetchEnrolment(id: number): Promise<EnrolmentDetail> {
  const { data } = await api.get(`/enrolments/${id}`)
  return enrolmentDetailSchema.parse(data)
}

export async function updateEnrolment(
  id: number,
  patch: {
    applicant_type?: string
    personal_details?: PersonalDetails
    address?: AddressInput
  },
): Promise<EnrolmentDetail> {
  const { data } = await api.patch(`/enrolments/${id}`, patch)
  return enrolmentDetailSchema.parse(data)
}

export async function prepareEnrolment(id: number): Promise<EnrolmentDetail> {
  const { data } = await api.post(`/enrolments/${id}/prepare`)
  return enrolmentDetailSchema.parse(data)
}

export async function deleteEnrolment(id: number): Promise<void> {
  await api.delete(`/enrolments/${id}`)
}

/** Human-readable byte size, e.g. 2097152 -> "2 MB". */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${Math.round(kb)} KB`
  const mb = kb / 1024
  return `${mb % 1 === 0 ? mb : mb.toFixed(2)} MB`
}
