import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

type Health = { status: string }

export default function HomePage() {
  const { user } = useAuth()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.get<Health>('/health')).data,
  })

  return (
    <section className="mx-auto max-w-2xl space-y-6 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-brand-700">TrustAI</h1>
        <p className="text-slate-600">
          Analyse de CV, offres d&apos;emploi et score de compatibilité.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        {user ? (
          <Link
            to="/tableau-de-bord"
            className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white transition-colors hover:bg-brand-700"
          >
            Aller à mon tableau de bord
          </Link>
        ) : (
          <>
            <Link
              to="/inscription"
              className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white transition-colors hover:bg-brand-700"
            >
              Créer un compte
            </Link>
            <Link
              to="/connexion"
              className="rounded-lg border border-slate-300 px-5 py-2.5 font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Se connecter
            </Link>
          </>
        )}
      </div>

      <p className="text-xs text-slate-400">
        API :{' '}
        {isLoading ? (
          <span>vérification…</span>
        ) : isError ? (
          <span className="text-red-500">injoignable</span>
        ) : (
          <span className="text-green-600">{data?.status}</span>
        )}
      </p>
    </section>
  )
}
