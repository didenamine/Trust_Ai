import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ATS_QUERY_KEY, fetchATSAnalysis, type ATSBand } from '../lib/ats'
import { fetchCurrentCV, formatFileSize } from '../lib/cv'
import { fetchMatching, type MatchingBand, type MatchingResult } from '../lib/matching'
import { fetchMyOffers, type JobOfferSummary } from '../lib/offers'
import { fetchMyProfile } from '../lib/profile'

const PROFILE_QUERY_KEY = ['profile', 'me']
const CV_QUERY_KEY = ['cv', 'me']

const ATS_BAND_LABELS: Record<ATSBand, string> = {
  low: 'Faible',
  to_improve: 'À améliorer',
  good: 'Bon',
  excellent: 'Excellent',
}
const ATS_BAND_STYLES: Record<ATSBand, string> = {
  low: 'bg-red-50 text-red-700 border-red-200',
  to_improve: 'bg-amber-50 text-amber-700 border-amber-200',
  good: 'bg-green-50 text-green-700 border-green-200',
  excellent: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

const MATCHING_BAND_LABELS: Record<MatchingBand, string> = {
  excellent: 'Excellente compatibilité',
  good: 'Bonne compatibilité',
  moderate: 'Compatibilité modérée',
  low: 'Faible compatibilité',
}
const MATCHING_BAND_STYLES: Record<MatchingBand, string> = {
  excellent: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  good: 'bg-green-50 text-green-700 border-green-200',
  moderate: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-red-50 text-red-700 border-red-200',
}

type LatestMatch = { offer: JobOfferSummary; matching: MatchingResult }

/** Tries the candidate's most recent offers until one already has a matching score. */
async function fetchLatestMatch(offers: JobOfferSummary[]): Promise<LatestMatch | null> {
  for (const offer of offers.slice(0, 3)) {
    try {
      const matching = await fetchMatching(offer.id)
      return { offer, matching }
    } catch {
      // Not analysed, or no profile yet: try the next offer.
    }
  }
  return null
}

function DashboardCard({
  title,
  action,
  children,
}: {
  title: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  )
}

function CardLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-block self-start rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
    >
      {label}
    </Link>
  )
}

function EmptyState({ text, to, label }: { text: string; to: string; label: string }) {
  return (
    <div className="flex flex-1 flex-col items-start justify-center gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
      <p className="text-sm text-slate-600">{text}</p>
      <CardLink to={to} label={label} />
    </div>
  )
}

function ScoreBadge({ label, className }: { label: string; className: string }) {
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${className}`}>
      {label}
    </span>
  )
}

function ProfileCard() {
  const query = useQuery({ queryKey: PROFILE_QUERY_KEY, queryFn: fetchMyProfile })

  if (query.isPending) {
    return (
      <DashboardCard title="Profil">
        <p className="text-sm text-slate-500">Chargement…</p>
      </DashboardCard>
    )
  }

  const response = query.data
  if (!response) {
    return (
      <DashboardCard title="Profil">
        <EmptyState
          text="Vous n'avez pas encore de profil candidat."
          to="/mon-profil"
          label="Créer mon profil"
        />
      </DashboardCard>
    )
  }

  const { personal_info, skills } = response.profile
  const topSkills = skills.slice(0, 5)

  return (
    <DashboardCard title="Profil">
      <p className="font-medium text-slate-900">{personal_info.full_name ?? 'Nom non renseigné'}</p>
      {personal_info.headline && <p className="text-sm text-slate-600">{personal_info.headline}</p>}
      {topSkills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {topSkills.map((skill) => (
            <span
              key={skill.name}
              className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700"
            >
              {skill.name}
            </span>
          ))}
        </div>
      )}
      <CardLink to="/mon-profil" label="Voir mon profil" />
    </DashboardCard>
  )
}

function CVCard() {
  const query = useQuery({ queryKey: CV_QUERY_KEY, queryFn: fetchCurrentCV })

  if (query.isPending) {
    return (
      <DashboardCard title="CV actuel">
        <p className="text-sm text-slate-500">Chargement…</p>
      </DashboardCard>
    )
  }

  const cv = query.data
  if (!cv) {
    return (
      <DashboardCard title="CV actuel">
        <EmptyState
          text="Vous n'avez pas encore importé de CV."
          to="/mon-cv"
          label="Importer mon CV"
        />
      </DashboardCard>
    )
  }

  return (
    <DashboardCard title="CV actuel">
      <p className="truncate font-medium text-slate-900">{cv.original_filename}</p>
      <p className="text-sm text-slate-600">
        {formatFileSize(cv.size_bytes)} · importé le{' '}
        {new Date(cv.uploaded_at).toLocaleDateString('fr-FR')}
      </p>
      <CardLink to="/mon-cv" label="Gérer mon CV" />
    </DashboardCard>
  )
}

function ATSCard() {
  const query = useQuery({ queryKey: ATS_QUERY_KEY, queryFn: fetchATSAnalysis })

  if (query.isPending) {
    return (
      <DashboardCard title="Analyse ATS">
        <p className="text-sm text-slate-500">Chargement…</p>
      </DashboardCard>
    )
  }

  const analysis = query.data
  if (!analysis) {
    return (
      <DashboardCard title="Analyse ATS">
        <EmptyState
          text="Votre CV n'a pas encore été analysé selon des critères ATS."
          to="/analyse-ats"
          label="Analyser mon CV"
        />
      </DashboardCard>
    )
  }

  const { total, band } = analysis.score
  return (
    <DashboardCard
      title="Analyse ATS"
      action={<ScoreBadge label={ATS_BAND_LABELS[band]} className={ATS_BAND_STYLES[band]} />}
    >
      <p className="text-3xl font-bold text-slate-900">{total}%</p>
      <CardLink to="/analyse-ats" label="Voir le détail" />
    </DashboardCard>
  )
}

function MatchingCard() {
  const { user } = useAuth()
  const offersQuery = useQuery({ queryKey: ['offers', user?.id], queryFn: fetchMyOffers })
  const matchQuery = useQuery({
    queryKey: ['dashboard-matching', user?.id, offersQuery.data?.map((o) => o.id).join(',')],
    queryFn: () => fetchLatestMatch(offersQuery.data ?? []),
    enabled: offersQuery.data !== undefined,
  })

  if (
    offersQuery.isPending ||
    (offersQuery.data && offersQuery.data.length > 0 && matchQuery.isPending)
  ) {
    return (
      <DashboardCard title="Compatibilité">
        <p className="text-sm text-slate-500">Chargement…</p>
      </DashboardCard>
    )
  }

  if (!offersQuery.data || offersQuery.data.length === 0) {
    return (
      <DashboardCard title="Compatibilité">
        <EmptyState
          text="Ajoutez une offre pour calculer votre compatibilité."
          to="/offres/nouvelle"
          label="Ajouter une offre"
        />
      </DashboardCard>
    )
  }

  const latest = matchQuery.data
  if (!latest) {
    return (
      <DashboardCard title="Compatibilité">
        <EmptyState
          text="Analysez une offre pour voir votre score de compatibilité."
          to="/offres"
          label="Voir mes offres"
        />
      </DashboardCard>
    )
  }

  const { offer, matching } = latest
  return (
    <DashboardCard
      title="Compatibilité"
      action={
        <ScoreBadge
          label={MATCHING_BAND_LABELS[matching.band]}
          className={MATCHING_BAND_STYLES[matching.band]}
        />
      }
    >
      <p className="text-3xl font-bold text-slate-900">{matching.total_score}%</p>
      <p className="truncate text-sm text-slate-600">avec « {offer.title} »</p>
      <CardLink to="/offres" label="Voir mes offres" />
    </DashboardCard>
  )
}

function ApplicationsCard() {
  return (
    <DashboardCard title="Candidatures">
      <div className="flex flex-1 flex-col items-start justify-center gap-1 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
        <p className="text-sm font-medium text-slate-600">Bientôt disponible</p>
        <p className="text-sm text-slate-500">
          Le suivi de vos candidatures arrivera dans une prochaine version.
        </p>
      </div>
    </DashboardCard>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <p className="mt-1 text-slate-600">
          Bonjour {user?.full_name ?? user?.email}, voici un aperçu de votre recherche
          d&apos;emploi.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <ProfileCard />
        <CVCard />
        <ATSCard />
        <MatchingCard />
        <ApplicationsCard />
      </div>
    </section>
  )
}
