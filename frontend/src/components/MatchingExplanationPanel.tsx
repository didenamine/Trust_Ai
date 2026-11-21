import type { MatchingBand, MatchingResult } from '../lib/matching'

const BAND_STYLES: Record<MatchingBand, { bg: string; text: string; border: string; label: string }> = {
  excellent: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    label: 'Excellente compatibilité',
  },
  good: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    label: 'Bonne compatibilité',
  },
  moderate: {
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
    label: 'Compatibilité modérée',
  },
  low: {
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
    label: 'Faible compatibilité',
  },
}

export default function MatchingExplanationPanel({ matching }: { matching: MatchingResult }) {
  const { total_score, band, dimension_scores, details, strengths, improvements } = matching
  const bandStyle = BAND_STYLES[band]

  return (
    <div
      role="region"
      aria-label="Explication du matching"
      className="mt-4 space-y-4 rounded-lg border border-slate-200 bg-slate-50/70 p-4"
    >
      {/* Header score global */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Score de compatibilité</h3>
          <p className="text-xs text-slate-500">
            Calculé sur la base de vos compétences, votre expérience et votre niveau d'études.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-slate-900">{total_score}%</span>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${bandStyle.bg} ${bandStyle.text} ${bandStyle.border}`}
          >
            {bandStyle.label}
          </span>
        </div>
      </div>

      {/* Critères détaillés du score (US12 / US13) */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Détail des critères (Pondération)
        </h4>
        <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
          {/* Compétences 50% */}
          <div className="rounded border border-slate-200 bg-white p-2.5">
            <div className="flex justify-between font-medium">
              <span>Compétences</span>
              <span className="text-slate-600">
                {dimension_scores.skills.points} / {dimension_scores.skills.weight} pts
              </span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-blue-600"
                style={{ width: `${Math.round(dimension_scores.skills.ratio * 100)}%` }}
              />
            </div>
          </div>

          {/* Expérience 30% */}
          <div className="rounded border border-slate-200 bg-white p-2.5">
            <div className="flex justify-between font-medium">
              <span>Expérience</span>
              <span className="text-slate-600">
                {dimension_scores.experience.points} / {dimension_scores.experience.weight} pts
              </span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-indigo-600"
                style={{ width: `${Math.round(dimension_scores.experience.ratio * 100)}%` }}
              />
            </div>
          </div>

          {/* Formation 20% */}
          <div className="rounded border border-slate-200 bg-white p-2.5">
            <div className="flex justify-between font-medium">
              <span>Formation</span>
              <span className="text-slate-600">
                {dimension_scores.education.points} / {dimension_scores.education.weight} pts
              </span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-teal-600"
                style={{ width: `${Math.round(dimension_scores.education.ratio * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Points forts (US13) */}
      {strengths.length > 0 && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-3 text-xs sm:text-sm">
          <h4 className="flex items-center gap-1.5 font-semibold text-emerald-800">
            <svg
              className="h-4 w-4 flex-shrink-0 text-emerald-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            Points forts
          </h4>
          <ul className="mt-2 space-y-1 text-emerald-900">
            {strengths.map((str, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-emerald-500">•</span>
                <span>{str}</span>
              </li>
            ))}
          </ul>
          {details.matched_skills.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1.5 pt-2 border-t border-emerald-200/60">
              {details.matched_skills.map((s) => (
                <span
                  key={s.name}
                  className="rounded bg-white px-2 py-0.5 text-xs font-medium text-emerald-800 border border-emerald-200 shadow-sm"
                >
                  ✓ {s.name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compétences manquantes et axes d'amélioration (US13) */}
      {(details.missing_skills.length > 0 || improvements.length > 0) && (
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs sm:text-sm">
          <h4 className="flex items-center gap-1.5 font-semibold text-amber-800">
            <svg
              className="h-4 w-4 flex-shrink-0 text-amber-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            Compétences manquantes & axes d'amélioration
          </h4>
          {improvements.length > 0 && (
            <ul className="mt-2 space-y-1 text-amber-900">
              {improvements.map((imp, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="text-amber-500">•</span>
                  <span>{imp}</span>
                </li>
              ))}
            </ul>
          )}
          {details.missing_skills.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1.5 pt-2 border-t border-amber-200/60">
              {details.missing_skills.map((s) => (
                <span
                  key={s.name}
                  className="rounded bg-white px-2 py-0.5 text-xs font-medium text-amber-800 border border-amber-200 shadow-sm"
                >
                  ✕ {s.name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
