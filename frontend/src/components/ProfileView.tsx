import type { ReactNode } from 'react'
import {
  EDUCATION_LEVEL_LABELS,
  EMPLOYMENT_TYPE_LABELS,
  LANGUAGE_LEVEL_LABELS,
  SKILL_LEVEL_LABELS,
  formatDuration,
  formatPartialDate,
  formatPeriod,
  totalExperienceMonths,
  type CandidateProfile,
  type Skill,
} from '../lib/profile'

/** US07: read-only view of the candidate's profile, section by section. */
export default function ProfileView({ profile }: Readonly<{ profile: CandidateProfile }>) {
  const info = profile.personal_info
  const months = totalExperienceMonths(profile)
  const hardSkills = profile.skills.filter((skill) => skill.category === 'hard')
  const softSkills = profile.skills.filter((skill) => skill.category === 'soft')

  return (
    <div className="space-y-4">
      <Section title="Identité">
        <p className="text-lg font-semibold">{info.full_name ?? 'Nom non renseigné'}</p>
        {info.headline && <p className="text-slate-700">{info.headline}</p>}
        <dl className="mt-2 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
          <Detail label="E-mail" value={info.email} />
          <Detail label="Téléphone" value={info.phone} />
          <Detail label="Localisation" value={info.location} />
          <Detail
            label="Langue du profil"
            value={profile.language === 'fr' ? 'Français' : 'Anglais'}
          />
          {months > 0 && <Detail label="Expérience" value={formatDuration(months)} />}
        </dl>
        {info.links.length > 0 && (
          <ul className="mt-2 space-y-1 text-sm">
            {info.links.map((link) => (
              <li key={link}>
                <a href={link} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                  {link}
                </a>
              </li>
            ))}
          </ul>
        )}
        {profile.summary && (
          <p className="mt-3 whitespace-pre-line text-slate-700">{profile.summary}</p>
        )}
      </Section>

      <Section title={`Compétences (${profile.skills.length})`}>
        {profile.skills.length === 0 ? (
          <Empty>Aucune compétence renseignée.</Empty>
        ) : (
          <div className="space-y-3">
            <SkillGroup title="Compétences techniques" skills={hardSkills} />
            <SkillGroup title="Savoir-être" skills={softSkills} />
          </div>
        )}
      </Section>

      <Section title={`Expériences professionnelles (${profile.experiences.length})`}>
        {profile.experiences.length === 0 ? (
          <Empty>Aucune expérience renseignée.</Empty>
        ) : (
          <ul className="space-y-4">
            {profile.experiences.map((experience, index) => (
              <li key={experience.id ?? index} aria-label={experience.job_title}>
                <p className="font-medium">
                  {experience.job_title}
                  {experience.company && (
                    <span className="text-slate-600"> · {experience.company}</span>
                  )}
                </p>
                <Meta
                  parts={[
                    formatPeriod(experience),
                    experience.employment_type &&
                      EMPLOYMENT_TYPE_LABELS[experience.employment_type],
                    experience.location,
                  ]}
                />
                {experience.description && (
                  <p className="mt-1 whitespace-pre-line text-sm text-slate-700">
                    {experience.description}
                  </p>
                )}
                {experience.achievements.length > 0 && (
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
                    {experience.achievements.map((achievement) => (
                      <li key={achievement}>{achievement}</li>
                    ))}
                  </ul>
                )}
                {experience.skills.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500">{experience.skills.join(' · ')}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={`Formations (${profile.education.length})`}>
        {profile.education.length === 0 ? (
          <Empty>Aucune formation renseignée.</Empty>
        ) : (
          <ul className="space-y-3">
            {profile.education.map((education, index) => (
              <li key={education.id ?? index}>
                <p className="font-medium">{education.degree}</p>
                <Meta
                  parts={[
                    education.institution,
                    education.level && EDUCATION_LEVEL_LABELS[education.level],
                    formatPeriod(education),
                  ]}
                />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={`Langues (${profile.languages.length})`}>
        {profile.languages.length === 0 ? (
          <Empty>Aucune langue renseignée.</Empty>
        ) : (
          <ul className="space-y-1 text-sm">
            {profile.languages.map((language) => (
              <li key={language.code ?? language.name}>
                <span className="font-medium">{language.name}</span>
                {language.level && (
                  <span className="text-slate-600"> · {LANGUAGE_LEVEL_LABELS[language.level]}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {profile.certifications.length > 0 && (
        <Section title={`Certifications (${profile.certifications.length})`}>
          <ul className="space-y-1 text-sm">
            {profile.certifications.map((certification, index) => (
              <li key={certification.id ?? index}>
                <span className="font-medium">{certification.name}</span>
                <Meta
                  inline
                  parts={[
                    certification.issuer,
                    certification.issue_date && formatPartialDate(certification.issue_date),
                  ]}
                />
              </li>
            ))}
          </ul>
        </Section>
      )}

      {profile.projects.length > 0 && (
        <Section title={`Projets (${profile.projects.length})`}>
          <ul className="space-y-3">
            {profile.projects.map((project, index) => (
              <li key={project.id ?? index}>
                <p className="font-medium">{project.name}</p>
                <Meta parts={[formatPeriod(project)]} />
                {project.description && (
                  <p className="mt-1 text-sm text-slate-700">{project.description}</p>
                )}
                {project.skills.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500">{project.skills.join(' · ')}</p>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

function Section({ title, children }: Readonly<{ title: string; children: ReactNode }>) {
  return (
    <section className="rounded border border-slate-200 bg-white p-4" aria-label={title}>
      <h2 className="mb-2 font-semibold">{title}</h2>
      {children}
    </section>
  )
}

function Detail({ label, value }: Readonly<{ label: string; value: string | null }>) {
  if (!value) return null
  return (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd>{value}</dd>
    </>
  )
}

function Meta({
  parts,
  inline = false,
}: Readonly<{ parts: (string | null | undefined)[]; inline?: boolean }>) {
  const text = parts.filter(Boolean).join(' · ')
  if (!text) return null
  return inline ? (
    <span className="text-sm text-slate-500"> · {text}</span>
  ) : (
    <p className="text-sm text-slate-500">{text}</p>
  )
}

function SkillGroup({ title, skills }: Readonly<{ title: string; skills: Skill[] }>) {
  if (skills.length === 0) return null
  return (
    <div>
      <h3 className="text-sm text-slate-500">{title}</h3>
      <ul className="mt-1 flex flex-wrap gap-2">
        {skills.map((skill) => (
          <li key={skill.name} className="rounded-full bg-slate-100 px-3 py-1 text-sm">
            {skill.name}
            {skill.level && (
              <span className="text-slate-500"> · {SKILL_LEVEL_LABELS[skill.level]}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Empty({ children }: Readonly<{ children: ReactNode }>) {
  return <p className="text-sm text-slate-500">{children}</p>
}
