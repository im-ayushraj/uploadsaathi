import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { StepShell, inputClass, primaryButtonClass, secondaryButtonClass } from './StepShell'
import { addressSchema, fetchEnrolment, updateEnrolment, type AddressInput } from '../../lib/enrolment'
import { toErrorMessage } from '../../lib/auth'

const EMPTY: AddressInput = {
  address_line1: '',
  address_line2: '',
  landmark: '',
  village_town_city: '',
  district: '',
  state: '',
  pincode: '',
}

export function AddressPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AddressInput | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: enrolment } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })

  const values = form ?? enrolment?.address ?? EMPTY

  function set<K extends keyof AddressInput>(key: K, value: string) {
    setForm({ ...(values as AddressInput), [key]: value })
  }

  const save = useMutation({
    mutationFn: (address: AddressInput) => updateEnrolment(enrolmentId, { address }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['enrolment', enrolmentId], updated)
      navigate(`/enrolment/${enrolmentId}/documents`)
    },
    onError: (err) => setError(toErrorMessage(err, 'Could not save this address.')),
  })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const cleaned = {
      ...values,
      address_line2: values.address_line2?.trim() || null,
      landmark: values.landmark?.trim() || null,
    }
    const parsed = addressSchema.safeParse(cleaned)
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Check the fields and try again.')
      return
    }
    setError(null)
    save.mutate(parsed.data)
  }

  return (
    <StepShell
      current="address"
      title="Address"
      description="This should match the address on your proof-of-address document."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="address_line1" className="block text-sm font-medium text-slate-800">
            House number and street
          </label>
          <input
            id="address_line1"
            className={inputClass}
            value={values.address_line1}
            onChange={(e) => set('address_line1', e.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="address_line2" className="block text-sm font-medium text-slate-800">
            Area / locality <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="address_line2"
            className={inputClass}
            value={values.address_line2 ?? ''}
            onChange={(e) => set('address_line2', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="landmark" className="block text-sm font-medium text-slate-800">
            Landmark <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="landmark"
            className={inputClass}
            value={values.landmark ?? ''}
            onChange={(e) => set('landmark', e.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="village_town_city"
              className="block text-sm font-medium text-slate-800"
            >
              Village / town / city
            </label>
            <input
              id="village_town_city"
              className={inputClass}
              value={values.village_town_city}
              onChange={(e) => set('village_town_city', e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="district" className="block text-sm font-medium text-slate-800">
              District
            </label>
            <input
              id="district"
              className={inputClass}
              value={values.district}
              onChange={(e) => set('district', e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="state" className="block text-sm font-medium text-slate-800">
              State
            </label>
            <input
              id="state"
              className={inputClass}
              value={values.state}
              onChange={(e) => set('state', e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="pincode" className="block text-sm font-medium text-slate-800">
              PIN code
            </label>
            <input
              id="pincode"
              inputMode="numeric"
              className={inputClass}
              value={values.pincode}
              onChange={(e) => set('pincode', e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
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
            onClick={() => navigate(`/enrolment/${enrolmentId}/personal`)}
          >
            Back
          </button>
        </div>
      </form>
    </StepShell>
  )
}
