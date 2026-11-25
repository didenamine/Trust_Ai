import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { fetchSkillGaps, type PrioritizedSkill } from '../lib/skillGaps'

const CATEGORY_LABELS: Record<PrioritizedSkill['category'], string> = {
  hard: 'Compétence technique',
  soft: 'Savoir-être',
}

function SkillRow({
  skill,
  offersConsidered,
}: {
  skill: PrioritizedSkill
  offersConsidered: number
}) {
  const ratio = offersConsidered > 0 ? skill.missing_in_offers / offersConsidered : 0

  return (
    <li className="space-y-1.5 rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900">{skill.name}</p>
          <p className="text-xs text-slate-500">{CATEGORY_LABELS[skill.category]}</p>
        </div>
        <span className="shrink-0 rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700">
          manque dans {skill.missing_in_offers}/{offersConsidered} offres
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-brand-600"
          style={{ width: `${Math.round(ratio * 100)}%` }}
        />
      </div>
    </li>
  )
}

function SkillGapList({
  skills,
  offersConsidered,
}: {
  skills: PrioritizedSkill[]
  offersConsidered: number
}) {
  return (
    <>
      <p className="text-sm text-slate-500">
        D&apos;après {offersConsidered} offre(s) analysée(s).
      </p>
      <ul className="space-y-3">
        {skills.map((skill) => (
          <SkillRow key={skill.name} skill={skill} offersConsidered={offersConsidered} />
        ))}
      </ul>
    </>
  )
}

export default function SkillGapsPage() {
  const { user } = useAuth()
  const query = useQuery({
    queryKey: ['skill-gaps', user?.id],
    queryFn: fetchSkillGaps,
  })

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compétences manquantes</h1>
        <p className="mt-1 text-slate-600">
          Les compétences qui reviennent le plus souvent dans vos offres analysées, mais que vous
          n&apos;avez pas encore : ciblez-les en priorité.
        </p>
      </div>

      {query.isPending && <p className="text-slate-500">Chargement…</p>}

      {query.isError && (
        <div role="alert" className="space-y-2 rounded border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-700">Impossible de calculer vos compétences manquantes.</p>
          <button
            type="button"
            onClick={() => query.refetch()}
            className="text-sm text-brand-600 underline"
          >
            Réessayer
          </button>
        </div>
      )}

      {query.isSuccess && query.data === null && (
        <div className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm text-slate-600">
            Créez votre profil candidat pour identifier vos compétences manquantes.
          </p>
          <Link
            to="/mon-profil"
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Créer mon profil
          </Link>
        </div>
      )}

      {query.isSuccess && query.data !== null && query.data.offers_considered === 0 && (
        <div className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm text-slate-600">
            Analysez au moins une offre pour identifier vos compétences manquantes.
          </p>
          <Link
            to="/offres"
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Voir mes offres
          </Link>
        </div>
      )}

      {query.isSuccess &&
        query.data !== null &&
        query.data.offers_considered > 0 &&
        query.data.skills.length === 0 && (
          <p
            role="status"
            className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800"
          >
            Aucune compétence manquante : votre profil couvre les compétences demandées par vos{' '}
            {query.data.offers_considered} offre(s) analysée(s).
          </p>
        )}

      {query.isSuccess && query.data !== null && query.data.skills.length > 0 && (
        <SkillGapList skills={query.data.skills} offersConsidered={query.data.offers_considered} />
      )}
    </section>
  )
}
