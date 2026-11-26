import type { ATSAnalysisResponse, ATSCriterion, ATSKeywordFinding, ATSStatus } from '../../lib/ats'

const SECTION_LABELS: Record<string, string> = {
  contact: 'Coordonnées',
  summary: 'Résumé / profil',
  experience: 'Expérience professionnelle',
  education: 'Formation',
  skills: 'Compétences',
  certifications: 'Certifications',
  languages: 'Langues',
}

const BAND_LABELS: Record<string, string> = {
  low: 'Faible',
  to_improve: 'À améliorer',
  good: 'Bon',
  excellent: 'Excellent',
}

const BAND_STYLES: Record<string, string> = {
  low: 'bg-red-50 text-red-700 border-red-200',
  to_improve: 'bg-amber-50 text-amber-700 border-amber-200',
  good: 'bg-green-50 text-green-700 border-green-200',
  excellent: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

const STATUS_LABELS: Record<ATSStatus, string> = {
  ok: 'OK',
  warning: 'À améliorer',
  missing: 'Absent',
  na: 'Non applicable',
}

const STATUS_STYLES: Record<ATSStatus, string> = {
  ok: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  missing: 'bg-red-50 text-red-700',
  na: 'bg-slate-100 text-slate-500',
}

const DIMENSION_LABELS: Record<string, string> = {
  readability: 'Lisibilité du document',
  sections: 'Sections du CV',
  keywords: 'Qualité des mots-clés',
}

const CRITERION_LABELS: Record<string, string> = {
  'readability.text_integrity': 'Texte extractible et intact',
  'readability.reading_order': 'Ordre de lecture',
  'readability.layout': 'Complexité de la mise en page',
  'readability.accessibility': 'Accessibilité du contenu',
  'keywords.specificity': 'Précision des mots-clés',
  'keywords.placement': 'Placement des mots-clés',
  'keywords.terminology': 'Cohérence de la terminologie',
  'keywords.repetition': 'Répétition des mots-clés',
}

const REASON_MESSAGES: Record<string, string> = {
  'section.missing': 'Section absente du CV.',
  'section.no_content': 'La section est présente mais semble vide.',
  'section.experience.no_dates': 'Les dates des expériences sont peu lisibles.',
  'section.education.no_dates': 'Les dates des formations sont peu lisibles.',
  'section.skills.too_few_skills': 'La liste de compétences est trop courte.',
  'section.summary.not_concise': 'Le résumé est absent ou trop long.',
  'section.languages.no_level': 'Le niveau des langues n’est pas indiqué.',
  'keywords.no_specific_terms': 'Peu de compétences techniques explicites ont été détectées.',
  'keywords.no_placement': 'Les mots-clés ne sont pas assez présents dans les sections adaptées.',
  'keywords.variant_terminology': 'Plusieurs variantes d’un même terme sont utilisées.',
  'keywords.repetition': 'Certains termes sont répétés de façon excessive.',
  'section.na': 'Section absente : elle n’est pas prise en compte dans le score.',
}

const READABILITY_MESSAGES: Record<string, string> = {
  'pdf.image_only_page': 'Une page contient des images sans texte extractible.',
  'pdf.multi_column': 'Une mise en page en colonnes a été détectée.',
  'docx.multi_column_section': 'Le document utilise plusieurs colonnes.',
  'docx.body_only_tables': 'Le contenu principal est organisé dans des tableaux.',
  'common.text_truncated': 'Le CV est long : seule une première partie a pu être analysée.',
  'docx.textbox_content_not_extracted':
    'Du texte se trouve dans des zones de texte que l’extraction ne lit pas.',
  'common.contact_in_header_only': 'Les coordonnées sont uniquement dans l’en-tête.',
  'docx.images_detected': 'Des images sont présentes dans le document.',
}

const LIMITATION_MESSAGES: Record<string, string> = {
  'ats.estimate_only':
    'Ce score est une estimation de compatibilité ATS, pas une garantie de passage.',
  'ats.no_target_job':
    'Aucune offre ciblée n’est sélectionnée : les mots-clés sont évalués seuls, sans comparaison avec un poste.',
  'ats.no_ocr': 'Les documents scannés sans texte extractible ne peuvent pas être analysés.',
}

function StatusBadge({ status }: Readonly<{ status: ATSStatus }>) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

function criterionLabel(criterion: ATSCriterion): string {
  if (criterion.key.startsWith('sections.')) {
    const section = criterion.key.slice('sections.'.length)
    return SECTION_LABELS[section] ?? section
  }
  return DIMENSION_LABELS[criterion.key] ?? CRITERION_LABELS[criterion.key] ?? criterion.label_key
}

function ratio(criterion: ATSCriterion): number {
  if (!criterion.applicable || criterion.weight <= 0) return 0
  return Math.min(Math.max(criterion.points / criterion.weight, 0), 1)
}

function DimensionBar({ criterion }: Readonly<{ criterion: ATSCriterion }>) {
  const value = Math.round(ratio(criterion) * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">{criterionLabel(criterion)}</span>
        <span className="text-slate-500">
          {criterion.points.toFixed(1).replace('.', ',')} / {criterion.weight}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded bg-slate-100"
        role="meter"
        aria-label={criterionLabel(criterion)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <div className="h-full rounded bg-brand-600" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

function CriterionList({ criteria }: Readonly<{ criteria: ATSCriterion[] }>) {
  return (
    <ul className="space-y-2">
      {criteria.map((criterion) => (
        <li key={criterion.key} className="flex items-start justify-between gap-3 text-sm">
          <div>
            <p className="font-medium">{criterionLabel(criterion)}</p>
            {criterion.reason_code && REASON_MESSAGES[criterion.reason_code] && (
              <p className="text-slate-500">{REASON_MESSAGES[criterion.reason_code]}</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-xs text-slate-500">
              {criterion.points.toFixed(1).replace('.', ',')} / {criterion.weight}
            </span>
            <StatusBadge status={criterion.status} />
          </div>
        </li>
      ))}
    </ul>
  )
}

function KeywordRow({ keyword }: Readonly<{ keyword: ATSKeywordFinding }>) {
  const placement = keyword.in_skills_section
    ? 'section Compétences'
    : keyword.in_context_section
      ? 'section Expérience'
      : 'autre section'
  return (
    <li className="flex items-center justify-between gap-3 text-sm">
      <span className="font-medium">{keyword.canonical}</span>
      <span className="text-xs text-slate-500">
        {placement} · {keyword.occurrences} occurrence{keyword.occurrences > 1 ? 's' : ''}
      </span>
    </li>
  )
}

export default function ATSReport({ analysis }: Readonly<{ analysis: ATSAnalysisResponse }>) {
  const { score, result } = analysis
  const sections = [...result.sections].sort(
    (left, right) => (left.order_index ?? 99) - (right.order_index ?? 99),
  )
  const topKeywords = result.keyword_findings.filter(
    (keyword) => keyword.verified && ['hard_skill', 'tool', 'method'].includes(keyword.kind),
  )
  const readability = result.readability

  return (
    <div className="space-y-6">
      <section
        className={`rounded border p-5 ${BAND_STYLES[score.band] ?? BAND_STYLES.low}`}
        aria-label="Score ATS"
      >
        <p className="text-sm font-medium">Score ATS estimé</p>
        <p className="mt-1 text-4xl font-bold">{score.total} / 100</p>
        <p className="mt-1 text-sm">{BAND_LABELS[score.band] ?? score.band}</p>
        <p className="mt-2 text-xs opacity-80">
          Score calculé sur {score.denominator} points applicables (version {score.scoring_version}
          ).
        </p>
      </section>

      <section
        className="space-y-4 rounded border border-slate-200 bg-white p-5"
        aria-label="Détail du score"
      >
        <h2 className="font-semibold">Détail du score</h2>
        {score.dimensions.map((criterion) => (
          <DimensionBar key={criterion.key} criterion={criterion} />
        ))}
        <div className="border-t border-slate-200 pt-4">
          <CriterionList criteria={score.criteria} />
        </div>
      </section>

      <section className="rounded border border-slate-200 bg-white p-5" aria-label="Sections du CV">
        <h2 className="font-semibold">Sections détectées</h2>
        <ul className="mt-3 space-y-2">
          {sections.map((section) => (
            <li key={section.section} className="flex items-center justify-between gap-3 text-sm">
              <div>
                <p className="font-medium">{SECTION_LABELS[section.section] ?? section.section}</p>
                {section.line !== null && (
                  <p className="text-xs text-slate-500">ligne {section.line}</p>
                )}
              </div>
              <StatusBadge status={section.status} />
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded border border-slate-200 bg-white p-5" aria-label="Mots-clés">
        <h2 className="font-semibold">Mots-clés</h2>
        <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
          <p className="rounded bg-slate-50 p-3">
            <span className="block text-xl font-semibold">{result.keywords.specific_count}</span>
            <span className="text-slate-600">termes spécifiques vérifiés</span>
          </p>
          <p className="rounded bg-slate-50 p-3">
            <span className="block text-xl font-semibold">{result.keywords.action_verb_count}</span>
            <span className="text-slate-600">verbes d’action</span>
          </p>
          <p className="rounded bg-slate-50 p-3">
            <span className="block text-xl font-semibold">{result.keywords.repeated_count}</span>
            <span className="text-slate-600">termes trop répétés</span>
          </p>
        </div>
        {topKeywords.length > 0 && (
          <ul className="mt-4 space-y-2 border-t border-slate-200 pt-4">
            {topKeywords.slice(0, 20).map((keyword) => (
              <KeywordRow key={`${keyword.kind}-${keyword.canonical}`} keyword={keyword} />
            ))}
          </ul>
        )}
      </section>

      <section className="rounded border border-slate-200 bg-white p-5" aria-label="Lisibilité ATS">
        <h2 className="font-semibold">Lisibilité par un ATS</h2>
        {readability.length === 0 ? (
          <p className="mt-2 text-sm text-green-700">Aucun problème de lecture détecté.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {readability.map((finding) => (
              <li key={finding.code} className="text-sm">
                <span className="font-medium">
                  {READABILITY_MESSAGES[finding.code] ?? finding.code}
                </span>
                {finding.page !== null && (
                  <span className="text-slate-500"> (page {finding.page})</span>
                )}
                {finding.degraded_extraction && (
                  <span className="ml-2 rounded bg-red-50 px-2 py-0.5 text-xs text-red-700">
                    Extraction dégradée
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="rounded border border-slate-200 bg-slate-50 p-5"
        aria-label="Limites de l'analyse"
      >
        <h2 className="font-semibold">À savoir</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
          {result.limitations.map((code) => (
            <li key={code}>{LIMITATION_MESSAGES[code] ?? code}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
