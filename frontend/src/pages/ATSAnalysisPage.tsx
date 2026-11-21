import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import ATSReport from '../components/ats/ATSReport'
import { ATS_QUERY_KEY, analyzeCVForATS, atsErrorMessage, fetchATSAnalysis } from '../lib/ats'
import { fetchCurrentCV, formatFileSize } from '../lib/cv'

const CV_QUERY_KEY = ['cv', 'me']

function RunButton({
  isPending,
  onClick,
  label = 'Analyser mon CV',
}: Readonly<{ isPending: boolean; onClick: () => void; label?: string }>) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending}
      className="rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
    >
      {isPending ? 'Analyse en cours…' : label}
    </button>
  )
}

export default function ATSAnalysisPage() {
  const queryClient = useQueryClient()
  const currentCV = useQuery({ queryKey: CV_QUERY_KEY, queryFn: fetchCurrentCV })
  const analysis = useQuery({
    queryKey: ATS_QUERY_KEY,
    queryFn: fetchATSAnalysis,
    enabled: Boolean(currentCV.data),
  })

  const runAnalysis = useMutation({
    mutationFn: analyzeCVForATS,
    onSuccess: (result) => queryClient.setQueryData(ATS_QUERY_KEY, result),
  })

  const cv = currentCV.data
  const result = analysis.data
  const isStale = Boolean(result && cv && result.cv_uploaded_at !== cv.uploaded_at)

  if (currentCV.isLoading || analysis.isLoading) {
    return (
      <p role="status" className="text-slate-500">
        Chargement de l’analyse ATS…
      </p>
    )
  }
  if (currentCV.isError || analysis.isError) {
    return (
      <section className="space-y-3 rounded border border-red-200 bg-red-50 p-5" role="alert">
        <p className="font-medium">Impossible de récupérer l’analyse ATS.</p>
        <button
          type="button"
          onClick={() => {
            void currentCV.refetch()
            void analysis.refetch()
          }}
          className="rounded border border-red-300 px-3 py-1.5 text-sm font-medium"
        >
          Réessayer
        </button>
      </section>
    )
  }
  if (!cv) {
    return (
      <section className="space-y-3 rounded border border-slate-200 bg-white p-5">
        <h1 className="text-2xl font-bold">Analyse ATS</h1>
        <p className="text-slate-600">Importez d’abord votre CV pour pouvoir l’analyser.</p>
        <Link
          to="/mon-cv"
          className="inline-block rounded bg-slate-900 px-4 py-2 font-medium text-white"
        >
          Importer mon CV
        </Link>
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Analyse ATS</h1>
          <p className="mt-1 text-sm text-slate-600">
            {cv.original_filename} · {formatFileSize(cv.size_bytes)} · importé le{' '}
            {new Date(cv.uploaded_at).toLocaleDateString('fr-FR')}
          </p>
        </div>
        {result && !isStale && (
          <RunButton
            isPending={runAnalysis.isPending}
            onClick={() => runAnalysis.mutate()}
            label="Relancer l’analyse"
          />
        )}
      </div>

      {runAnalysis.isError && (
        <p
          role="alert"
          className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {atsErrorMessage(runAnalysis.error)}
        </p>
      )}

      {isStale ? (
        <div className="space-y-3 rounded border border-amber-200 bg-amber-50 p-5">
          <p className="font-medium">Ce résultat correspond à une version précédente du CV.</p>
          <p className="text-sm text-slate-600">
            Relancez l’analyse pour obtenir un score sur le CV actuellement importé.
          </p>
          <RunButton isPending={runAnalysis.isPending} onClick={() => runAnalysis.mutate()} />
        </div>
      ) : !result ? (
        <div className="space-y-3 rounded border border-slate-200 bg-white p-5">
          <p className="font-medium">Ce CV n’a pas encore été analysé selon les critères ATS.</p>
          <p className="text-sm text-slate-600">
            L’analyse vérifie les sections, la qualité des mots-clés et la lisibilité du document.
          </p>
          <RunButton isPending={runAnalysis.isPending} onClick={() => runAnalysis.mutate()} />
        </div>
      ) : (
        <ATSReport analysis={result} />
      )}
    </section>
  )
}
