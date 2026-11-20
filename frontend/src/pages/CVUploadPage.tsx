import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  ACCEPTED_CV_EXTENSIONS,
  MAX_CV_SIZE_MB,
  fetchCurrentCV,
  formatFileSize,
  uploadCV,
  uploadErrorMessage,
  validateCVFile,
} from '../lib/cv'

const CV_QUERY_KEY = ['cv', 'me']

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const currentCV = useQuery({ queryKey: CV_QUERY_KEY, queryFn: fetchCurrentCV })

  const upload = useMutation({
    mutationFn: uploadCV,
    onSuccess: (cv) => {
      queryClient.setQueryData(CV_QUERY_KEY, cv)
      setSelectedFile(null)
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
          Importez votre CV pour que la plateforme puisse l'analyser.
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
    </section>
  )
}
