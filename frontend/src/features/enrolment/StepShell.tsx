import type { ReactNode } from 'react'

export const WIZARD_STEPS = [
  { key: 'type', label: 'Applicant type' },
  { key: 'personal', label: 'Personal details' },
  { key: 'address', label: 'Address' },
  { key: 'documents', label: 'Documents' },
  { key: 'review', label: 'Review' },
] as const

export type StepKey = (typeof WIZARD_STEPS)[number]['key']

export function StepIndicator({ current }: { current: StepKey }) {
  const currentIndex = WIZARD_STEPS.findIndex((s) => s.key === current)

  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" aria-label="Progress">
      {WIZARD_STEPS.map((step, i) => {
        const done = i < currentIndex
        const active = i === currentIndex
        return (
          <li key={step.key} className="flex items-center gap-2">
            <span
              className={[
                'grid h-5 w-5 place-items-center rounded-full text-[11px] font-semibold',
                active
                  ? 'bg-saathi-600 text-white'
                  : done
                    ? 'bg-green-600 text-white'
                    : 'bg-slate-200 text-slate-600',
              ].join(' ')}
              aria-hidden
            >
              {done ? '✓' : i + 1}
            </span>
            <span
              className={active ? 'font-semibold text-saathi-700' : 'text-slate-500'}
              aria-current={active ? 'step' : undefined}
            >
              {step.label}
            </span>
            {i < WIZARD_STEPS.length - 1 && <span className="text-slate-300">›</span>}
          </li>
        )
      })}
    </ol>
  )
}

export function StepShell({
  title,
  description,
  current,
  children,
}: {
  title: string
  description?: string
  current: StepKey
  children: ReactNode
}) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <StepIndicator current={current} />
      <h1 className="mt-5 text-2xl font-bold">{title}</h1>
      {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
      <div className="mt-6">{children}</div>
    </main>
  )
}

export const inputClass =
  'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-saathi-500 focus:outline-none focus:ring-2 focus:ring-saathi-500/30'

export const primaryButtonClass =
  'rounded-lg bg-saathi-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-saathi-700 disabled:opacity-60'

export const secondaryButtonClass =
  'rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold hover:bg-slate-50'
