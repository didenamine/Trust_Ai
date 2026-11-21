import type {
  EducationRequirement,
  ExperienceRequirement,
  OfferRequirements,
  RequiredSkill,
} from '../lib/offerAnalysis'
import {
  EDUCATION_LEVEL_LABELS,
  EMPLOYMENT_TYPE_LABELS,
  SKILL_CATEGORY_LABELS,
  SKILL_LEVEL_LABELS,
} from '../lib/profile'

function yearsLabel(requirement: ExperienceRequirement): string | null {
  const { min_years: min, max_years: max } = requirement
  if (min !== null && max !== null) return `${min} à ${max} ans`
  if (min !== null) return `${min} ans minimum`
  if (max !== null) return `${max} ans maximum`
  return null
}

function SkillLine({ skill }: { skill: RequiredSkill }) {
  const level = skill.level ? SKILL_LEVEL_LABELS[skill.level] : null
  return (
    <li>
      <span className="font-medium">{skill.name}</span>
      {' · '}
      {SKILL_CATEGORY_LABELS[skill.category]}
      {level && ` · ${level}`}
    </li>
  )
}

function ExperienceLine({ requirement }: { requirement: ExperienceRequirement }) {
  const years = yearsLabel(requirement)
  const type = requirement.employment_type
    ? EMPLOYMENT_TYPE_LABELS[requirement.employment_type]
    : null
  return (
    <li className="space-y-1">
      <p className="font-medium">
        {requirement.job_title ?? 'Poste non précisé'}
        {(years || type) && ` — ${[years, type].filter(Boolean).join(' · ')}`}
      </p>
      {requirement.description && <p className="text-slate-700">{requirement.description}</p>}
      {requirement.skills.length > 0 && (
        <p className="text-xs text-slate-600">Compétences : {requirement.skills.join(', ')}</p>
      )}
    </li>
  )
}

function EducationLine({ requirement }: { requirement: EducationRequirement }) {
  const level = requirement.level ? EDUCATION_LEVEL_LABELS[requirement.level] : null
  return (
    <li className="space-y-1">
      <p className="font-medium">{level ?? 'Niveau non précisé'}</p>
      {requirement.degree && <p className="text-slate-700">{requirement.degree}</p>}
      {requirement.field_of_study && (
        <p className="text-xs text-slate-600">Domaine : {requirement.field_of_study}</p>
      )}
      {requirement.description && <p className="text-slate-700">{requirement.description}</p>}
    </li>
  )
}

/** US09: the structured requirements, displayed inline on the "my offers" page. */
export default function OfferRequirementsPanel({
  requirements,
}: {
  requirements: OfferRequirements
}) {
  return (
    <section
      aria-label="Exigences de l'offre"
      className="space-y-3 rounded border border-blue-200 bg-blue-50 p-3 text-sm"
    >
      <div>
        <h3 className="font-semibold">Exigences de l’offre</h3>
        <p>Poste : {requirements.job_title ?? 'Non précisé'}</p>
      </div>

      <div>
        <h4 className="font-semibold">Compétences</h4>
        {requirements.skills.length > 0 ? (
          <ul className="list-inside list-disc space-y-0.5">
            {requirements.skills.map((skill, index) => (
              <SkillLine key={`${skill.name}-${index}`} skill={skill} />
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">Non précisées.</p>
        )}
      </div>

      <div>
        <h4 className="font-semibold">Expérience</h4>
        {requirements.experiences.length > 0 ? (
          <ul className="list-inside list-disc space-y-2">
            {requirements.experiences.map((requirement, index) => (
              <ExperienceLine key={index} requirement={requirement} />
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">Non précisée.</p>
        )}
      </div>

      <div>
        <h4 className="font-semibold">Formation</h4>
        {requirements.education.length > 0 ? (
          <ul className="list-inside list-disc space-y-2">
            {requirements.education.map((requirement, index) => (
              <EducationLine key={index} requirement={requirement} />
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">Non précisée.</p>
        )}
      </div>
    </section>
  )
}
