import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

type Health = { status: string }

export default function HomePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.get<Health>('/health')).data,
  })

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">TrustAI</h1>
      <p className="text-slate-600">Analyse de CV, offres d'emploi et score de compatibilité.</p>
      <p className="text-sm">
        API :{' '}
        {isLoading ? (
          <span className="text-slate-500">vérification…</span>
        ) : isError ? (
          <span className="text-red-600">injoignable</span>
        ) : (
          <span className="text-green-700">{data?.status}</span>
        )}
      </p>
    </section>
  )
}
