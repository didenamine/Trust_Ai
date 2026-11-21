import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ATS_QUERY_KEY, analyzeCVForATS, atsErrorMessage } from '../lib/ats'
import {
  ACCEPTED_CV_EXTENSIONS,
  MAX_CV_SIZE_MB,
  analysisErrorMessage,
  analyzeCV,
  fetchCurrentCV,
  formatFileSize,
  uploadCV,
  uploadErrorMessage,
  validateCVFile,
  type CV,
} from '../lib/cv'
import { fetchMyProfile, type ProfileResponse } from '../lib/profile'

const CV_QUERY_KEY = ['cv', 'me']
const PROFILE_QUERY_KEY = ['profile', 'me']

export default function CVUploadPage() {
  const { user, isLoading: isAuthLoading } = useAuth()

  if (isAuthLoading) {
    return <p className="text-slate-500">Chargement…</p>
  }
  if (!user) {
    return <Navigate to="/connexion" replace />
  }
  return <CVUpload />
}

function CVUpload() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const currentCV = useQuery({ queryKey: CV_QUERY_KEY, queryFn: fetchCurrentCV })
  const currentProfile = useQuery({ queryKey: PROFILE_QUERY_KEY, queryFn: fetchMyProfile })

  // US05: the CV is analysed automatically right after the import.
  const analysis = useMutation({
    mutationFn: analyzeCV,
    onSuccess: (profile) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, profile)
      // Let the candidate review and correct what the LLM extracted.
      navigate('/mon-profil')
    },
  })

  const upload = useMutation({
    mutationFn: uploadCV,
    onSuccess: (cv) => {
      queryClient.setQueryData(CV_QUERY_KEY, cv)
      // An ATS result always belongs to one uploaded file: forget the old one.
      queryClient.setQueryData(ATS_QUERY_KEY, null)
      setSelectedFile(null)
      analysis.mutate()
    },
  })

  // US24: manual ATS analysis only; never run it automatically after an upload.
  const atsAnalysis = useMutation({
    mutationFn: analyzeCVForATS,
    onSuccess: (result) => {
      queryClient.setQueryData(ATS_QUERY_KEY, result)
      navigate('/analyse-ats')
    },
  })

  const selectFile = (file: File | undefined) => {
    upload.reset()
    if (!file) {
      return
    }
    const error = validateCVFile(file)
    setFileError(error)
    setSelectedFile(error ? null : file)
  }

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0])
    // Allow choosing the same file again after an error.
    event.target.value = ''
  }

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files[0])
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (selectedFile) {
      upload.mutate(selectedFile)
    }
  }

  const cv = currentCV.data

  return (
    <section className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Mon CV</h1>
        <p className="mt-1 text-slate-600">
          Importez votre CV pour que la plateforme puisse l'analyser et remplir votre profil.
        </p>
        <p className="mt-2 text-sm text-slate-600">
          Pas de CV sous la main ?{' '}
          <Link to="/mon-profil" className="text-blue-600 underline">
            Remplir mon profil manuellement
          </Link>
        </p>
      </div>

      {currentCV.isLoading ? (
        <p className="text-slate-500">Chargement…</p>
      ) : currentCV.isError ? (
        <p className="text-sm text-red-600">Impossible de récupérer votre CV actuel.</p>
      ) : cv ? (
        <div className="rounded border border-slate-200 bg-white p-4" aria-label="CV actuel">
          <p className="text-sm text-slate-500">CV actuel</p>
          <p className="font-medium">{cv.original_filename}</p>
          <p className="text-sm text-slate-500">
            {formatFileSize(cv.size_bytes)} · importé le{' '}
            {new Date(cv.uploaded_at).toLocaleDateString('fr-FR')}
          </p>
        </div>
      ) : (
        <p className="text-slate-600">Vous n'avez pas encore importé de CV.</p>
      )}

      <form className="space-y-4" onSubmit={onSubmit}>
        <label
          htmlFor="cv-file"
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          className={`block cursor-pointer rounded border-2 border-dashed p-6 text-center ${
            isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white'
          }`}
        >
          <span className="block font-medium">
            {selectedFile ? selectedFile.name : 'Choisir un fichier ou le déposer ici'}
          </span>
          <span className="mt-1 block text-sm text-slate-500">
            PDF ou DOCX, {MAX_CV_SIZE_MB} Mo maximum
          </span>
        </label>
        <input
          id="cv-file"
          type="file"
          aria-label="Fichier du CV"
          accept={ACCEPTED_CV_EXTENSIONS.join(',')}
          className="sr-only"
          onChange={onInputChange}
        />

        {fileError && <p className="text-sm text-red-600">{fileError}</p>}
        {upload.isError && (
          <p className="text-sm text-red-600">{uploadErrorMessage(upload.error)}</p>
        )}
        {upload.isSuccess && <p className="text-sm text-green-700">Votre CV a bien été importé.</p>}

        <button
          type="submit"
          disabled={!selectedFile || upload.isPending}
          className="w-full rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {upload.isPending ? 'Import…' : cv ? 'Remplacer mon CV' : 'Importer mon CV'}
        </button>
      </form>

      {cv && (
        <>
          <CVAnalysis
            cv={cv}
            profile={currentProfile.data ?? null}
            isPending={analysis.isPending}
            error={analysis.isError ? analysisErrorMessage(analysis.error) : null}
            onAnalyze={() => analysis.mutate()}
          />
          <ATSCard
            isPending={atsAnalysis.isPending}
            error={atsAnalysis.isError ? atsErrorMessage(atsAnalysis.error) : null}
            onAnalyze={() => atsAnalysis.mutate()}
          />
        </>
      )}
    </section>
  )
}

const LANGUAGE_LABELS = { fr: 'français', en: 'anglais' } as const

function CVAnalysis({
  cv,
  profile,
  isPending,
  error,
  onAnalyze,
}: Readonly<{
  cv: CV
  profile: ProfileResponse | null
  isPending: boolean
  error: string | null
  onAnalyze: () => void
}>) {
  // Only show a result that comes from the analysis of *this* CV.
  const result =
    profile?.source === 'cv_analysis' && profile.cv_document_id === cv.id ? profile.profile : null

  return (
    <div
      className="space-y-3 rounded border border-slate-200 bg-white p-4"
      aria-label="Analyse du CV"
    >
      <h2 className="font-semibold">Analyse du CV</h2>

      {isPending ? (
        <p role="status" className="text-sm text-slate-600">
          Analyse de votre CV en cours… Cela peut prendre jusqu'à une minute.
        </p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : result ? (
        <div className="text-sm">
          <p className="text-green-700">Votre CV a été analysé.</p>
          <p className="text-slate-600">
            CV en {LANGUAGE_LABELS[result.language]} : {result.skills.length} compétences,{' '}
            {result.experiences.length} expériences, {result.education.length} formations,{' '}
            {result.languages.length} langues.
          </p>
        </div>
      ) : (
        <p className="text-sm text-slate-600">Ce CV n'a pas encore été analysé.</p>
      )}

      {!isPending && (
        <button
          type="button"
          onClick={onAnalyze}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium"
        >
          {result || error ? "Relancer l'analyse" : 'Analyser mon CV'}
        </button>
      )}
    </div>
  )
}

/** US24: manual ATS check, kept separate from the US05 profile extraction. */
function ATSCard({
  isPending,
  error,
  onAnalyze,
}: Readonly<{
  isPending: boolean
  error: string | null
  onAnalyze: () => void
}>) {
  return (
    <div className="space-y-3 rounded border border-slate-200 bg-white p-4" aria-label="Score ATS">
      <h2 className="font-semibold">Score ATS</h2>
      <p className="text-sm text-slate-600">
        Vérifiez les sections, la qualité des mots-clés et la lisibilité de votre CV par un logiciel
        de recrutement. L'analyse est manuelle : aucun poste n'est comparé à votre CV.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={isPending}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {isPending ? 'Calcul du score en cours…' : 'Vérifier le score ATS'}
        </button>
        <Link to="/analyse-ats" className="text-sm text-blue-600 underline">
          Voir le rapport ATS
        </Link>
      </div>
    </div>
  )
}
