import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { StepShell, inputClass, primaryButtonClass, secondaryButtonClass } from './StepShell'
import {
  fetchEnrolment,
  personalDetailsSchema,
  updateEnrolment,
  type PersonalDetails,
} from '../../lib/enrolment'
import { toErrorMessage } from '../../lib/auth'

const EMPTY: PersonalDetails = {
  full_name: '',
  date_of_birth: '',
  gender: 'female',
  guardian_name: '',
  email: '',
  mobile: '',
}

export function PersonalDetailsPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<PersonalDetails | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: enrolment } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })

  const values = form ?? enrolment?.personal_details ?? EMPTY
  const isMinor = enrolment?.applicant_type !== 'adult'

  function set<K extends keyof PersonalDetails>(key: K, value: string) {
    setForm({ ...(values as PersonalDetails), [key]: value })
  }

  const save = useMutation({
    mutationFn: (details: PersonalDetails) =>
      updateEnrolment(enrolmentId, { personal_details: details }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['enrolment', enrolmentId], updated)
      navigate(`/enrolment/${enrolmentId}/address`)
    },
    onError: (err) => setError(toErrorMessage(err, 'Could not save these details.')),
  })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    // Blank optional fields are sent as null rather than empty strings.
    const cleaned = {
      ...values,
      guardian_name: values.guardian_name?.trim() || null,
      email: values.email?.trim() || null,
      mobile: values.mobile?.trim() || null,
    }
    const parsed = personalDetailsSchema.safeParse(cleaned)
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Check the fields and try again.')
      return
    }
    setError(null)
    save.mutate(parsed.data)
  }

  return (
    <StepShell
      current="personal"
      title="Applicant details"
      description="Use demo details only. This prototype never asks for an Aadhaar number."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="full_name" className="block text-sm font-medium text-slate-800">
            Full name (as it should appear)
          </label>
          <input
            id="full_name"
            className={inputClass}
            value={values.full_name}
            onChange={(e) => set('full_name', e.target.value)}
            required
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="date_of_birth" className="block text-sm font-medium text-slate-800">
              Date of birth
            </label>
            <input
              id="date_of_birth"
              type="date"
              className={inputClass}
              value={values.date_of_birth}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => set('date_of_birth', e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="gender" className="block text-sm font-medium text-slate-800">
              Gender
            </label>
            <select
              id="gender"
              className={inputClass}
              value={values.gender}
              onChange={(e) => set('gender', e.target.value)}
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="transgender">Transgender</option>
            </select>
          </div>
        </div>

        {isMinor && (
          <div>
            <label htmlFor="guardian_name" className="block text-sm font-medium text-slate-800">
              Parent or guardian name
            </label>
            <input
              id="guardian_name"
              className={inputClass}
              value={values.guardian_name ?? ''}
              onChange={(e) => set('guardian_name', e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">
              Required at the enrolment centre for applicants under 18.
            </p>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="mobile" className="block text-sm font-medium text-slate-800">
              Mobile number <span className="text-slate-400">(optional)</span>
            </label>
            <input
              id="mobile"
              inputMode="numeric"
              className={inputClass}
              value={values.mobile ?? ''}
              onChange={(e) => set('mobile', e.target.value.replace(/\D/g, '').slice(0, 10))}
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-800">
              Email <span className="text-slate-400">(optional)</span>
            </label>
            <input
              id="email"
              type="email"
              className={inputClass}
              value={values.email ?? ''}
              onChange={(e) => set('email', e.target.value)}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-3 pt-2">
          <button type="submit" className={primaryButtonClass} disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save and continue'}
          </button>
          <button
            type="button"
            className={secondaryButtonClass}
            onClick={() => navigate('/dashboard')}
          >
            Save later
          </button>
        </div>
      </form>
    </StepShell>
  )
}
