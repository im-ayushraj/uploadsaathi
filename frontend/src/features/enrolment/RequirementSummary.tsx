import { formatBytes } from '../../lib/enrolment'
import type { DocumentType } from '../../lib/enrolment'

/** The portal's rules for one document, straight from configuration — never hardcoded here. */
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
