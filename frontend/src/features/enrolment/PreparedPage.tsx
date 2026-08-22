import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchEnrolment, fetchPortal } from '../../lib/enrolment'

/** Synthetic demo centres — illustrative only, not a real UIDAI centre directory. */
const DEMO_CENTRES = [
  {
    name: 'Demo Aadhaar Seva Kendra — Patna Central',
    address: 'Sample Complex, Station Road, Patna 800001',
    timing: 'Mon–Sat, 9:30 am – 5:30 pm',
  },
  {
    name: 'Demo Enrolment Centre — District Post Office',
    address: 'Model Ward 4, District HQ',
    timing: 'Mon–Fri, 10:00 am – 4:00 pm',
  },
]

const CHECKLIST = [
  'Carry the original documents you prepared here, plus one printed copy each.',
  'Biometrics (photograph, fingerprints, iris) are captured at the centre — they cannot be uploaded.',
  'A child under 5 must be accompanied by a parent or guardian with their own proof of identity.',
  'Keep the acknowledgement slip the centre gives you; it carries your enrolment number.',
]

export function PreparedPage() {
  const { id } = useParams()
  const enrolmentId = Number(id)

  const { data: enrolment } = useQuery({
    queryKey: ['enrolment', enrolmentId],
    queryFn: () => fetchEnrolment(enrolmentId),
  })
  const { data: portal } = useQuery({ queryKey: ['portal'], queryFn: () => fetchPortal() })

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <div className="rounded-xl border border-green-200 bg-green-50 p-5">
        <p className="text-sm font-semibold text-green-800">Application prepared</p>
        <h1 className="mt-1 text-2xl font-bold text-green-900">
          Your document pack is ready to carry
        </h1>
        {enrolment?.reference_code && (
          <p className="mt-2 text-sm text-green-900">
            Prototype reference:{' '}
            <span className="font-mono font-semibold">{enrolment.reference_code}</span>
          </p>
        )}
      </div>

      <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
        <h2 className="text-base font-semibold text-amber-900">What this does and does not do</h2>
        <p className="mt-2 text-sm text-amber-900">
          {portal?.journey_note ??
            'This prototype prepares the digital/document portion of the journey. Real Aadhaar enrolment requires visiting an Aadhaar Enrolment Centre.'}
        </p>
        <p className="mt-2 text-sm text-amber-900">
          No application has been submitted anywhere. No Aadhaar system was contacted, and no
          identity verification was performed.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-base font-semibold">Before you go to the centre</h2>
        <ul className="mt-2 space-y-2">
          {CHECKLIST.map((item) => (
            <li key={item} className="flex gap-2 text-sm text-slate-700">
              <span aria-hidden className="text-saathi-600">
                •
              </span>
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6">
        <h2 className="text-base font-semibold">Enrolment centre information</h2>
        <p className="mt-1 text-sm text-slate-600">
          The centres below are sample demo entries for this prototype. For real centres and
          appointments, check the official UIDAI website (uidai.gov.in) directly.
        </p>
        <div className="mt-3 space-y-3">
          {DEMO_CENTRES.map((centre) => (
            <div key={centre.name} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold">{centre.name}</p>
              <p className="mt-1 text-sm text-slate-600">{centre.address}</p>
              <p className="mt-1 text-xs text-slate-500">{centre.timing}</p>
              <p className="mt-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                Demo entry — not a real centre
              </p>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-8">
        <Link
          to="/dashboard"
          className="rounded-lg bg-saathi-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-saathi-700"
        >
          Back to dashboard
        </Link>
      </div>
    </main>
  )
}
