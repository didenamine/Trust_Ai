import { useQuery } from '@tanstack/react-query'
import type { CVAdaptation } from '../lib/adaptation'
import { fetchMyProfile } from '../lib/profile'

const PROFILE_QUERY_KEY = ['profile', 'me']

/** US14: the CV adapted to an offer, displayed inline on the "my offers" page. */
export default function CVAdaptationPanel({ adaptation }: { adaptation: CVAdaptation }) {
  const { adapted_cv: cv, missing_skills: missingSkills, matching_score: score } = adaptation
  const profile = useQuery({ queryKey: PROFILE_QUERY_KEY, queryFn: fetchMyProfile })
  const profileExperiences = profile.data?.profile.experiences ?? []

  const experienceLabel = (id: string) => {
    const experience = profileExperiences.find((item) => item.id === id)
    if (!experience) return 'Expérience'
    return experience.company
      ? `${experience.job_title} · ${experience.company}`
      : experience.job_title
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

      {cv.headline && (
        <div>
          <h4 className="font-semibold">Titre</h4>
          <p>{cv.headline}</p>
        </div>
      )}

      {cv.summary && (
        <div>
          <h4 className="font-semibold">Résumé</h4>
          <p className="whitespace-pre-line">{cv.summary}</p>
        </div>
      )}

      {cv.highlighted_skills.length > 0 && (
        <div>
          <h4 className="font-semibold">Compétences, de la plus à la moins pertinente</h4>
          <ol aria-label="Compétences mises en avant" className="mt-1 flex flex-wrap gap-1.5">
            {cv.highlighted_skills.map((name) => (
              <li
                key={name}
                className="rounded-full border border-emerald-300 bg-white px-2 py-0.5 text-xs"
              >
                {name}
              </li>
            ))}
          </ol>
        </div>
      )}

      {cv.experiences.length > 0 && (
        <div>
          <h4 className="font-semibold">Expériences reformulées</h4>
          <ul className="space-y-2">
            {cv.experiences.map((experience) => (
              <li key={experience.experience_id}>
                <p className="font-medium">{experienceLabel(experience.experience_id)}</p>
                {experience.description && (
                  <p className="whitespace-pre-line text-slate-700">{experience.description}</p>
                )}
                {experience.achievements.length > 0 && (
                  <ul className="list-inside list-disc text-slate-700">
                    {experience.achievements.map((achievement, index) => (
                      <li key={index}>{achievement}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {cv.changes.length > 0 && (
        <div>
          <h4 className="font-semibold">Ce qui a changé</h4>
          <ul className="list-inside list-disc text-slate-700">
            {cv.changes.map((change, index) => (
              <li key={index}>{change}</li>
            ))}
          </ul>
        </div>
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
