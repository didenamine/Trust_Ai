import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../context/AuthContext'

const loginSchema = z.object({
  email: z.string().email('Adresse e-mail invalide'),
  password: z.string().min(1, 'Le mot de passe est requis'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (values: LoginForm) => {
    setServerError(null)
    try {
      await login(values.email, values.password)
      navigate('/tableau-de-bord')
    } catch {
      setServerError('E-mail ou mot de passe incorrect.')
    }
  }

  return (
    <AuthLayout
      title="Content de vous revoir."
      subtitle="Connectez-vous pour retrouver votre profil, votre CV et vos offres."
    >
      <h1 className="text-2xl font-bold">Se connecter</h1>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
            {...register('email')}
          />
          {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
            {...register('password')}
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        {serverError && <p className="text-sm text-red-600">{serverError}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>

      <div className="mt-6 flex justify-between text-sm">
        <Link to="/inscription" className="text-brand-600 underline">
          Créer un compte
        </Link>
        <Link to="/mot-de-passe-oublie" className="text-brand-600 underline">
          Mot de passe oublié ?
        </Link>
      </div>
    </AuthLayout>
  )
}
