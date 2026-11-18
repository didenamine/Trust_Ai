import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { requestPasswordReset } from '../lib/auth'

const forgotPasswordSchema = z.object({
  email: z.string().email('Adresse e-mail invalide'),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState<string | null>(null)
  const [devResetLink, setDevResetLink] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({ resolver: zodResolver(forgotPasswordSchema) })

  const onSubmit = async (values: ForgotPasswordForm) => {
    setMessage(null)
    setDevResetLink(null)
    const result = await requestPasswordReset(values.email)
    setMessage(result.detail)
    // Pas de serveur mail pour l'instant (US01) : en développement, l'API renvoie
    // directement le jeton pour que le flux reste testable de bout en bout.
    if (result.reset_token) {
      setDevResetLink(`/reinitialiser-mot-de-passe?token=${encodeURIComponent(result.reset_token)}`)
    }
  }

  return (
    <section className="mx-auto max-w-sm space-y-6">
      <h1 className="text-2xl font-bold">Mot de passe oublié</h1>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            {...register('email')}
          />
          {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {isSubmitting ? 'Envoi…' : 'Envoyer le lien de réinitialisation'}
        </button>
      </form>

      {message && <p className="text-sm text-slate-700">{message}</p>}
      {devResetLink && (
        <p className="text-sm text-amber-700">
          Mode développement (pas de serveur mail) :{' '}
          <Link to={devResetLink} className="underline">
            lien de réinitialisation
          </Link>
        </p>
      )}

      <Link to="/connexion" className="block text-sm text-blue-600 underline">
        Retour à la connexion
      </Link>
    </section>
  )
}
