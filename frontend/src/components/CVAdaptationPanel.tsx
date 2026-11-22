import { useState, type ReactNode } from 'react'
import type { CVAdaptation } from '../lib/adaptation'

function downloadText(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const link = window.document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <h4 className="border-b border-slate-300 pb-0.5 text-xs font-bold uppercase tracking-wide">
        {title}
      </h4>
      {children}
    </div>
  )
}

/** US14: the CV adapted to an offer, as a complete ATS-friendly CV, on the "my offers" page. */
export default function CVAdaptationPanel({ adaptation }: { adaptation: CVAdaptation }) {
  const { document: cv, adapted_cv: adapted, ats_text: text } = adaptation
  const { missing_skills: missingSkills, matching_score: score } = adaptation
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
  const titles = cv.section_titles
  const technologies = cv.language === 'fr' ? 'Technologies :' : 'Technologies:'
  const details = [cv.contact.location, cv.contact.phone, cv.contact.email]
    .filter(Boolean)
    .join(' | ')

  async function copyText() {
    try {
      await navigator.clipboard.writeText(text)
      setCopyStatus('copied')
    } catch {
      setCopyStatus('failed')
    }
  }

  return (
    <section
      aria-label="CV adapté à l'offre"
      className="space-y-3 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm"
    >
      <div>
        <h3 className="font-semibold">CV adapté à l’offre</h3>
        <p className="text-xs text-slate-600">
          Calculé à partir de l’écart entre votre profil et l’offre (compatibilité de départ :{' '}
          {score} %).
        </p>
      </div>

      <p className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
        Ce contenu est généré par une IA et n’est pas vérifié : relisez-le et corrigez-le avant de
        l’utiliser dans votre CV.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={copyText}
          className="rounded border border-emerald-600 bg-white px-3 py-1 text-xs text-emerald-700"
        >
          Copier le texte
        </button>
        <button
          type="button"
          onClick={() => downloadText('cv-adapte.txt', text)}
          className="rounded border border-emerald-600 bg-white px-3 py-1 text-xs text-emerald-700"
        >
          Télécharger (.txt)
        </button>
        {copyStatus === 'copied' && (
          <span role="status" className="text-xs text-emerald-700">
            Copié dans le presse-papiers.
          </span>
        )}
        {copyStatus === 'failed' && (
          <span role="status" className="text-xs text-red-700">
            Copie impossible : sélectionnez le texte à la main.
          </span>
        )}
      </div>

      <article
        aria-label="Aperçu du CV au format ATS"
        className="space-y-3 rounded border border-slate-200 bg-white p-4"
      >
        <header className="space-y-0.5">
          {cv.contact.full_name && <p className="text-lg font-bold">{cv.contact.full_name}</p>}
          {cv.contact.headline && <p>{cv.contact.headline}</p>}
          {details && <p className="text-xs text-slate-600">{details}</p>}
          {cv.contact.links.map((link) => (
            <p key={link} className="text-xs text-slate-600">
              {link}
            </p>
          ))}
        </header>

        {cv.summary && (
          <Section title={titles.summary}>
            <p className="whitespace-pre-line">{cv.summary}</p>
          </Section>
        )}

        {cv.skill_groups.length > 0 && (
          <Section title={titles.skills}>
            {cv.skill_groups.map((group) => (
              <p key={group.label}>
                <span className="font-medium">{group.label} :</span> {group.skills.join(', ')}
              </p>
            ))}
          </Section>
        )}

        {cv.experiences.length > 0 && (
          <Section title={titles.experience}>
            <ul className="space-y-3">
              {cv.experiences.map((experience, index) => (
                <li key={index} className="space-y-0.5">
                  <p className="font-medium">
                    {[experience.job_title, experience.company, experience.location]
                      .filter(Boolean)
                      .join(' | ')}
                  </p>
                  {experience.period && (
                    <p className="text-xs text-slate-500">{experience.period}</p>
                  )}
                  {experience.description && (
                    <p className="whitespace-pre-line text-slate-700">{experience.description}</p>
                  )}
                  {experience.bullets.length > 0 && (
                    <ul className="list-inside list-disc text-slate-700">
                      {experience.bullets.map((bullet, bulletIndex) => (
                        <li key={bulletIndex}>{bullet}</li>
                      ))}
                    </ul>
                  )}
                  {experience.technologies.length > 0 && (
                    <p className="text-xs text-slate-600">
                      {technologies} {experience.technologies.join(', ')}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {cv.projects.length > 0 && (
          <Section title={titles.projects}>
            <ul className="space-y-2">
              {cv.projects.map((project, index) => (
                <li key={index} className="space-y-0.5">
                  <p className="font-medium">
                    {[project.name, project.period].filter(Boolean).join(' | ')}
                  </p>
                  {project.description && (
                    <p className="whitespace-pre-line text-slate-700">{project.description}</p>
                  )}
                  {project.technologies.length > 0 && (
                    <p className="text-xs text-slate-600">
                      {technologies} {project.technologies.join(', ')}
                    </p>
                  )}
                  {project.url && <p className="text-xs text-slate-600">{project.url}</p>}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {cv.education.length > 0 && (
          <Section title={titles.education}>
            <ul className="space-y-2">
              {cv.education.map((item, index) => (
                <li key={index} className="space-y-0.5">
                  <p className="font-medium">
                    {[item.degree, item.institution, item.location].filter(Boolean).join(' | ')}
                  </p>
                  {item.period && <p className="text-xs text-slate-500">{item.period}</p>}
                  {item.description && (
                    <p className="whitespace-pre-line text-slate-700">{item.description}</p>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {cv.certifications.length > 0 && (
          <Section title={titles.certifications}>
            <ul>
              {cv.certifications.map((item, index) => (
                <li key={index}>
                  {[item.name, item.issuer, item.date].filter(Boolean).join(' | ')}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {cv.languages.length > 0 && (
          <Section title={titles.languages}>
            <ul>
              {cv.languages.map((item, index) => (
                <li key={index}>{item.level ? `${item.name} (${item.level})` : item.name}</li>
              ))}
            </ul>
          </Section>
        )}
      </article>

      {adapted.changes.length > 0 && (
        <div>
          <h4 className="font-semibold">Ce qui a changé</h4>
          <ul className="list-inside list-disc text-slate-700">
            {adapted.changes.map((change, index) => (
              <li key={index}>{change}</li>
            ))}
          </ul>
        </div>
      )}

      {cv.missing_sections.length > 0 && (
        <p className="text-xs text-slate-700">
          Sections à compléter dans votre profil :{' '}
          {cv.missing_sections.map((section) => titles[section] ?? section).join(', ')}.
        </p>
      )}

      {missingSkills.length > 0 && (
        <div>
          <h4 className="font-semibold">Compétences demandées absentes de votre profil</h4>
          <p className="text-xs text-slate-600">
            Elles n’ont pas été ajoutées à votre CV : ajoutez-les à votre profil seulement si vous
            les maîtrisez réellement.
          </p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {missingSkills.map((name) => (
              <span
                key={name}
                className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs text-rose-700"
              >
                {`✕ ${name}`}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
