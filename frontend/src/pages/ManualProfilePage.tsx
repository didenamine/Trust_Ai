import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import ProfileForm from '../components/ProfileForm'
import ProfileView from '../components/ProfileView'
import { useAuth } from '../context/AuthContext'
import {
  emptyProfileForm,
  fetchMyProfile,
  formValuesToProfile,
  profileToFormValues,
  saveMyProfile,
  type ProfileFormValues,
} from '../lib/profile'

const PROFILE_QUERY_KEY = ['profile', 'me']

function saveErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
  }
  return "Impossible d'enregistrer le profil. Vérifiez les champs et réessayez."
}

export default function ManualProfilePage() {
  const { user, isLoading: isAuthLoading } = useAuth()

  if (isAuthLoading) {
    return <p className="text-slate-500">Chargement…</p>
  }
  if (!user) {
    return <Navigate to="/connexion" replace />
  }
  return <ManualProfile />
}

function ManualProfile() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)
  // US07: an existing profile is shown read-only first; editing is a deliberate step.
  const [isEditing, setIsEditing] = useState(false)

  const profileQuery = useQuery({ queryKey: PROFILE_QUERY_KEY, queryFn: fetchMyProfile })

  const save = useMutation({
    mutationFn: (values: ProfileFormValues) => saveMyProfile(formValuesToProfile(values)),
    onSuccess: (response) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, response)
      setServerError(null)
      setIsEditing(false)
      // Stay on the same page so the candidate sees the confirmation and the saved profile.
      navigate('/mon-profil', { replace: true })
    },
    onError: (error) => setServerError(saveErrorMessage(error)),
  })

  const onSubmit = (values: ProfileFormValues) => {
    setServerError(null)
    save.reset()
    save.mutate(values)
  }

  const startEditing = () => {
    save.reset()
    setServerError(null)
    setIsEditing(true)
  }

  const cancelEditing = () => {
    setServerError(null)
    setIsEditing(false)
  }

  if (profileQuery.isLoading) {
    return <p className="text-slate-500">Chargement…</p>
  }
  if (profileQuery.isError) {
    return <p className="text-sm text-red-600">Impossible de récupérer votre profil.</p>
  }

  const response = profileQuery.data

  // No profile yet: US06 manual entry, straight into the form.
  if (!response) {
    return (
      <section className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Mon profil</h1>
          <p className="mt-1 text-slate-600">
            Renseignez votre profil manuellement, sans importer de CV. Vous pourrez le consulter et
            le corriger à tout moment.
          </p>
        </div>
        <ProfileForm
          defaultValues={emptyProfileForm()}
          isSaving={save.isPending}
          serverError={serverError}
          onSubmit={onSubmit}
        />
      </section>
    )
  }

  const fromCV = response.source === 'cv_analysis'

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Mon profil</h1>
          <p className="mt-1 text-slate-600">
            {isEditing
              ? 'Corrigez les informations inexactes puis enregistrez.'
              : 'Consultez votre profil et corrigez-le si une information est inexacte.'}
          </p>
        </div>
        {!isEditing && (
          <button
            type="button"
            onClick={startEditing}
            className="rounded bg-slate-900 px-4 py-2 font-medium text-white"
          >
            Modifier mon profil
          </button>
        )}
      </div>

      {save.isSuccess && !isEditing && (
        <p
          role="status"
          className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800"
        >
          Votre profil a bien été enregistré.
        </p>
      )}

      {isEditing ? (
        <ProfileForm
          defaultValues={profileToFormValues(response.profile)}
          source={response.source}
          updatedAt={response.updated_at}
          isSaving={save.isPending}
          serverError={serverError}
          onSubmit={onSubmit}
          onCancel={cancelEditing}
        />
      ) : (
        <>
          <p
            className={`rounded border p-3 text-sm ${
              fromCV
                ? 'border-blue-200 bg-blue-50 text-blue-800'
                : 'border-slate-200 bg-white text-slate-600'
            }`}
          >
            {fromCV
              ? "Ce profil a été généré automatiquement à partir de votre CV. Vérifiez les informations : l'IA peut se tromper."
              : 'Ce profil a été saisi manuellement.'}{' '}
            Dernière mise à jour le {new Date(response.updated_at).toLocaleDateString('fr-FR')}.
          </p>
          <ProfileView profile={response.profile} />
        </>
      )}
    </section>
  )
}
