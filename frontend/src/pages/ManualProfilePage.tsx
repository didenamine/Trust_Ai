import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import ProfileForm from '../components/ProfileForm'
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

  const profileQuery = useQuery({ queryKey: PROFILE_QUERY_KEY, queryFn: fetchMyProfile })

  const save = useMutation({
    mutationFn: (values: ProfileFormValues) => saveMyProfile(formValuesToProfile(values)),
    onSuccess: (response) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, response)
      setServerError(null)
      // Stay on the same page so the candidate sees the confirmation and can keep editing.
      navigate('/mon-profil', { replace: true })
    },
    onError: (error) => setServerError(saveErrorMessage(error)),
  })

  const onSubmit = (values: ProfileFormValues) => {
    setServerError(null)
    save.reset()
    save.mutate(values)
  }

  if (profileQuery.isLoading) {
    return <p className="text-slate-500">Chargement…</p>
  }
  if (profileQuery.isError) {
    return <p className="text-sm text-red-600">Impossible de récupérer votre profil.</p>
  }

  const response = profileQuery.data

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Mon profil</h1>
        <p className="mt-1 text-slate-600">
          Renseignez votre profil manuellement, sans importer de CV. Vous pourrez le consulter et le
          corriger à tout moment.
        </p>
      </div>

      {save.isSuccess && (
        <p className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Votre profil a bien été enregistré.
        </p>
      )}

      <ProfileForm
        defaultValues={response ? profileToFormValues(response.profile) : emptyProfileForm()}
        source={response?.source ?? null}
        updatedAt={response?.updated_at ?? null}
        isSaving={save.isPending}
        serverError={serverError}
        onSubmit={onSubmit}
      />
    </section>
  )
}
