import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { deleteOffer, fetchMyOffers, type JobOfferSummary } from '../lib/offers'

const LONG_DESCRIPTION_CHARS = 280
const LONG_DESCRIPTION_LINES = 4

function OfferCard({ offer }: { offer: JobOfferSummary }) {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const remove = useMutation({
    mutationFn: () => deleteOffer(offer.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['offers'] }),
  })
  const isLong =
    offer.description.length > LONG_DESCRIPTION_CHARS ||
    offer.description.split('\n').length > LONG_DESCRIPTION_LINES
  const addedOn = new Date(offer.created_at).toLocaleDateString('fr-FR')
  const clamp = expanded ? '' : 'line-clamp-4'

  return (
    <li className="space-y-2 rounded border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold">{offer.title}</h2>
      <p className="text-xs text-slate-500">
        {offer.source_type === 'url' ? 'Ajoutée par lien' : 'Texte collé'} · le {addedOn}
        {offer.source_url && (
          <>
            {' · '}
            <a
              href={offer.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline"
            >
              Annonce d'origine
            </a>
          </>
        )}
      </p>
      {offer.description ? (
        <>
          <p className={`whitespace-pre-line text-sm text-slate-700 ${clamp}`}>
            {offer.description}
          </p>
          {isLong && (
            <button
              type="button"
              aria-expanded={expanded}
              onClick={() => setExpanded(!expanded)}
              className="text-sm text-blue-600 underline"
            >
              {expanded ? 'Voir moins' : 'Voir plus'}
            </button>
          )}
        </>
      ) : (
        <p className="text-sm italic text-slate-500">Pas de description.</p>
      )}
      <div className="pt-1">
        {confirming ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span>Supprimer cette offre ?</span>
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
              className="rounded bg-red-600 px-3 py-1 text-white disabled:opacity-50"
            >
              {remove.isPending ? 'Suppression...' : 'Oui, supprimer'}
            </button>
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => {
                remove.reset()
                setConfirming(false)
              }}
              className="text-slate-600 underline"
            >
              Annuler
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label={`Supprimer ${offer.title}`}
            onClick={() => setConfirming(true)}
            className="text-sm text-red-600 underline"
          >
            Supprimer
          </button>
        )}
        {remove.isError && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            Impossible de supprimer l'offre. Réessayez.
          </p>
        )}
      </div>
    </li>
  )
}

export default function MyOffersPage() {
  const { user } = useAuth()
  // The user id is part of the key so a cached list is never shown to another account.
  const {
    data: offers,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['offers', user?.id],
    queryFn: fetchMyOffers,
  })

  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Mes offres</h1>
        <Link to="/offres/nouvelle" className="rounded bg-blue-600 px-3 py-2 text-sm text-white">
          Ajouter une offre
        </Link>
      </div>

      {isPending && <p className="text-slate-500">Chargement de vos offres…</p>}

      {isError && (
        <div role="alert" className="space-y-2 rounded border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-700">Impossible de charger vos offres.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="text-sm text-blue-600 underline"
          >
            Réessayer
          </button>
        </div>
      )}

      {offers && offers.length === 0 && (
        <p className="text-slate-600">Vous n'avez encore ajouté aucune offre.</p>
      )}

      {offers && offers.length > 0 && (
        <ul className="space-y-3">
          {offers.map((offer) => (
            <OfferCard key={offer.id} offer={offer} />
          ))}
        </ul>
      )}
    </section>
  )
}
