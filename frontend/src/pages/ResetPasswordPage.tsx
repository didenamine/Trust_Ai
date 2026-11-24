import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { confirmPasswordReset } from '../lib/auth'

const resetPasswordSchema = z.object({
  newPassword: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
})

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({ resolver: zodResolver(resetPasswordSchema) })

  const onSubmit = async (values: ResetPasswordForm) => {
    setServerError(null)
    try {
      await confirmPasswordReset({ token, newPassword: values.newPassword })
      navigate('/connexion')
    } catch {
      setServerError('Ce lien de réinitialisation est invalide ou a expiré.')
    }
  }

  if (!token) {
    return (
      <section className="mx-auto max-w-sm space-y-4">
        <h1 className="text-2xl font-bold">Lien invalide</h1>
        <p className="text-sm text-slate-600">
          Ce lien de réinitialisation est incomplet. Demandez-en un nouveau.
        </p>
        <Link to="/mot-de-passe-oublie" className="text-sm text-brand-600 underline">
          Mot de passe oublié
        </Link>
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-sm space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold">Choisir un nouveau mot de passe</h1>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="newPassword" className="block text-sm font-medium">
            Nouveau mot de passe
          </label>
          <input
            id="newPassword"
            type="password"
            autoComplete="new-password"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
            {...register('newPassword')}
          />
          {errors.newPassword && (
            <p className="mt-1 text-sm text-red-600">{errors.newPassword.message}</p>
          )}
        </div>

        {serverError && <p className="text-sm text-red-600">{serverError}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Enregistrement…' : 'Changer le mot de passe'}
        </button>
      </form>
    </section>
  )
}
