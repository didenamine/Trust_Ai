import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { createOffer, getOfferErrorMessage, type CreateOfferResult } from '../lib/offers'

const MIN_TEXT_LENGTH = 50
const MAX_TEXT_LENGTH = 50_000

function isHttpUrl(value: string): boolean {
  try {
    const { protocol } = new URL(value)
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}

// One schema for both modes: only the field of the chosen mode is validated.
const offerSchema = z
  .object({
    mode: z.enum(['url', 'text']),
    url: z.string().trim(),
    text: z.string().trim(),
  })
  .superRefine((values, ctx) => {
    if (values.mode === 'url' && !isHttpUrl(values.url)) {
      ctx.addIssue({
        code: 'custom',
        path: ['url'],
        message: 'Entrez une adresse valide commençant par http:// ou https://',
      })
    }
    if (values.mode === 'text' && values.text.length < MIN_TEXT_LENGTH) {
      ctx.addIssue({
        code: 'custom',
        path: ['text'],
        message: `L'offre doit contenir au moins ${MIN_TEXT_LENGTH} caractères.`,
      })
    }
    if (values.mode === 'text' && values.text.length > MAX_TEXT_LENGTH) {
      ctx.addIssue({
        code: 'custom',
        path: ['text'],
        message: "L'offre est trop longue (50 000 caractères au maximum).",
      })
    }
  })

type OfferForm = z.infer<typeof offerSchema>

const inputClass = 'w-full rounded border border-slate-300 px-3 py-2'

export default function AddOfferPage() {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<OfferForm>({
    resolver: zodResolver(offerSchema),
    defaultValues: { mode: 'url', url: '', text: '' },
  })
  const [result, setResult] = useState<CreateOfferResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const mode = watch('mode')

  const onSubmit = async (values: OfferForm) => {
    setError(null)
    setResult(null)
    try {
      const created = await createOffer(
        values.mode === 'url' ? { url: values.url } : { text: values.text },
      )
      setResult(created)
      reset({ mode: values.mode, url: '', text: '' })
    } catch (err) {
      setError(getOfferErrorMessage(err))
    }
  }

  const switchToText = () => {
    setError(null)
    setValue('mode', 'text')
  }

  return (
    <section className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Ajouter une offre d'emploi</h1>
      <p className="text-sm text-slate-600">
        Collez le lien de l'offre (son contenu est récupéré automatiquement) ou le texte de
        l'annonce.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <fieldset className="space-y-1">
          <legend className="text-sm font-medium">Source de l'offre</legend>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" value="url" {...register('mode')} />
              Lien (URL)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" value="text" {...register('mode')} />
              Texte collé
            </label>
          </div>
        </fieldset>

        {mode === 'url' ? (
          <div>
            <label htmlFor="offer-url" className="mb-1 block text-sm font-medium">
              Lien de l'offre
            </label>
            <input
              id="offer-url"
              type="url"
              autoComplete="off"
              placeholder="https://..."
              className={inputClass}
              {...register('url')}
            />
            {errors.url && <p className="mt-1 text-sm text-red-600">{errors.url.message}</p>}
            <p className="mt-1 text-xs text-slate-500">
              Certains sites (LinkedIn, Indeed...) bloquent la récupération automatique : utilisez
              alors « Texte collé ».
            </p>
          </div>
        ) : (
          <div>
            <label htmlFor="offer-text" className="mb-1 block text-sm font-medium">
              Texte de l'offre
            </label>
            <textarea
              id="offer-text"
              rows={12}
              placeholder="Collez ici l'intégralité de l'annonce..."
              className={inputClass}
              {...register('text')}
            />
            {errors.text && <p className="mt-1 text-sm text-red-600">{errors.text.message}</p>}
          </div>
        )}

        {error && (
          <div role="alert" className="space-y-2 rounded border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">{error}</p>
            {mode === 'url' && (
              <button
                type="button"
                onClick={switchToText}
                className="text-sm text-blue-600 underline"
              >
                Coller le texte à la place
              </button>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {isSubmitting
            ? mode === 'url'
              ? "Récupération de l'offre..."
              : 'Enregistrement...'
            : "Ajouter l'offre"}
        </button>
      </form>

      {result && (
        <div
          role="status"
          className="space-y-2 rounded border border-green-200 bg-green-50 p-4 text-sm"
        >
          <p className="font-medium text-green-800">
            {result.alreadyAdded
              ? 'Cette offre est déjà dans votre liste.'
              : 'Offre ajoutée avec succès.'}
          </p>
          {result.offer.source_url && (
            <p className="break-all text-slate-600">{result.offer.source_url}</p>
          )}
          <p className="font-medium">Contenu enregistré :</p>
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded bg-white p-3">
            {result.offer.content}
          </pre>
        </div>
      )}
    </section>
  )
}
