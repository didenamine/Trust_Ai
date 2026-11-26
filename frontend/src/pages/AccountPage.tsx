import { zodResolver } from '@hookform/resolvers/zod'
import { isAxiosError } from 'axios'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'

const infoSchema = z.object({
  fullName: z.string().max(255, 'Trop long (255 caractères maximum)').optional(),
  email: z.string().email('Adresse e-mail invalide'),
})
type InfoForm = z.infer<typeof infoSchema>

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Le mot de passe actuel est requis'),
    newPassword: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
    confirmPassword: z.string(),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirmPassword'],
  })
type PasswordForm = z.infer<typeof passwordSchema>

const INPUT_CLASS =
  'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none'
const CARD_CLASS = 'space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm'
const PRIMARY_BUTTON_CLASS =
  'rounded-lg bg-brand-600 px-4 py-2 font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50'

function accountErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
  }
  return fallback
}

export default function AccountPage() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <p className="text-slate-500">Chargement…</p>
  }
  // RequireAuth already redirects an anonymous visitor; this only guards the render below.
  if (!user) {
    return null
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Mon compte</h1>
      <PersonalInfoCard fullName={user.full_name} email={user.email} />
      <PasswordCard />
      <DangerZoneCard email={user.email} />
    </section>
  )
}

function PersonalInfoCard({ fullName, email }: { fullName: string | null; email: string }) {
  const { updateAccount } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InfoForm>({
    resolver: zodResolver(infoSchema),
    defaultValues: { fullName: fullName ?? '', email },
  })

  const onSubmit = async (values: InfoForm) => {
    setServerError(null)
    setSuccess(false)
    try {
      await updateAccount({ email: values.email, fullName: values.fullName ?? '' })
      setSuccess(true)
    } catch (error) {
      setServerError(accountErrorMessage(error, "Impossible d'enregistrer ces informations."))
    }
  }

  return (
    <div className={CARD_CLASS}>
      <h2 className="text-lg font-semibold">Informations personnelles</h2>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="account-full-name" className="block text-sm font-medium">
            Nom complet
          </label>
          <input
            id="account-full-name"
            type="text"
            className={INPUT_CLASS}
            {...register('fullName')}
          />
          {errors.fullName && (
            <p className="mt-1 text-sm text-red-600">{errors.fullName.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="account-email" className="block text-sm font-medium">
            E-mail
          </label>
          <input
            id="account-email"
            type="email"
            autoComplete="email"
            className={INPUT_CLASS}
            {...register('email')}
          />
          {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
        </div>

        {serverError && <p className="text-sm text-red-600">{serverError}</p>}
        {success && (
          <p
            role="status"
            className="rounded border border-green-200 bg-green-50 p-2 text-sm text-green-800"
          >
            Informations mises à jour.
          </p>
        )}

        <button type="submit" disabled={isSubmitting} className={PRIMARY_BUTTON_CLASS}>
          {isSubmitting ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </form>
    </div>
  )
}

function PasswordCard() {
  const { changePassword } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) })

  const onSubmit = async (values: PasswordForm) => {
    setServerError(null)
    setSuccess(false)
    try {
      await changePassword({
        currentPassword: values.currentPassword,
        newPassword: values.newPassword,
      })
      setSuccess(true)
      reset()
    } catch (error) {
      setServerError(accountErrorMessage(error, 'Mot de passe actuel incorrect.'))
    }
  }

  return (
    <div className={CARD_CLASS}>
      <h2 className="text-lg font-semibold">Mot de passe</h2>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="current-password" className="block text-sm font-medium">
            Mot de passe actuel
          </label>
          <input
            id="current-password"
            type="password"
            autoComplete="current-password"
            className={INPUT_CLASS}
            {...register('currentPassword')}
          />
          {errors.currentPassword && (
            <p className="mt-1 text-sm text-red-600">{errors.currentPassword.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="new-password" className="block text-sm font-medium">
            Nouveau mot de passe
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            className={INPUT_CLASS}
            {...register('newPassword')}
          />
          {errors.newPassword && (
            <p className="mt-1 text-sm text-red-600">{errors.newPassword.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="confirm-password" className="block text-sm font-medium">
            Confirmer le nouveau mot de passe
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            className={INPUT_CLASS}
            {...register('confirmPassword')}
          />
          {errors.confirmPassword && (
            <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
          )}
        </div>

        {serverError && <p className="text-sm text-red-600">{serverError}</p>}
        {success && (
          <p
            role="status"
            className="rounded border border-green-200 bg-green-50 p-2 text-sm text-green-800"
          >
            Mot de passe modifié.
          </p>
        )}

        <button type="submit" disabled={isSubmitting} className={PRIMARY_BUTTON_CLASS}>
          {isSubmitting ? 'Modification…' : 'Changer le mot de passe'}
        </button>
      </form>
    </div>
  )
}

function DangerZoneCard({ email }: { email: string }) {
  const { deleteAccount } = useAuth()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  const [confirmEmail, setConfirmEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const canConfirm = confirmEmail.trim().toLowerCase() === email.toLowerCase()

  const cancel = () => {
    setConfirming(false)
    setConfirmEmail('')
    setError(null)
  }

  const handleDelete = async () => {
    setError(null)
    setIsDeleting(true)
    try {
      await deleteAccount()
      navigate('/')
    } catch (deleteError) {
      setError(accountErrorMessage(deleteError, 'Impossible de supprimer le compte.'))
      setIsDeleting(false)
    }
  }

  return (
    <div className="space-y-4 rounded border border-red-200 bg-red-50 p-6">
      <h2 className="text-lg font-semibold text-red-800">Zone dangereuse</h2>

      {!confirming ? (
        <>
          <p className="text-sm text-red-700">
            Supprimer votre compte efface définitivement votre profil, votre CV et vos offres
            enregistrées. Cette action est irréversible.
          </p>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="rounded border border-red-600 px-4 py-2 text-sm font-medium text-red-700"
          >
            Supprimer mon compte
          </button>
        </>
      ) : (
        <>
          <p className="text-sm text-red-700">
            Pour confirmer, saisissez votre e-mail (<strong>{email}</strong>) :
          </p>
          <input
            type="email"
            value={confirmEmail}
            onChange={(event) => setConfirmEmail(event.target.value)}
            aria-label="Confirmer avec votre e-mail"
            className="w-full rounded border border-red-300 px-3 py-2"
          />
          {error && <p className="text-sm text-red-700">{error}</p>}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleDelete}
              disabled={!canConfirm || isDeleting}
              className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isDeleting ? 'Suppression…' : 'Supprimer définitivement'}
            </button>
            <button
              type="button"
              onClick={cancel}
              className="rounded border border-slate-300 px-4 py-2 text-sm"
            >
              Annuler
            </button>
          </div>
        </>
      )}
    </div>
  )
}
