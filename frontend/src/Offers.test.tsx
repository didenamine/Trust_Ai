import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'
import type { JobOfferSummary } from './lib/offers'

vi.mock('./lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
}))

const OFFER_URL = 'https://jobs.example.com/offres/42'
const OFFER_TEXT =
  "Développeur Python backend. Vous concevez des API REST avec FastAPI et PostgreSQL. 3 ans d'expérience minimum."
const NO_CONTENT_DETAIL =
  "Aucun texte d'offre n'a pu être extrait de cette page. Collez plutôt le texte de l'offre."

const savedOffer = {
  id: 'offer-1',
  source_type: 'url',
  source_url: OFFER_URL,
  content: 'Stage PFE Data Scientist\nBestlab · Tunis\n\nAnalyse de données et modèles prédictifs.',
  created_at: '2026-11-20T10:00:00Z',
}

function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function signIn() {
  localStorage.setItem('trustai.access_token', 'fake-token')
  vi.mocked(api.get).mockResolvedValue({
    data: { id: '1', email: 'me@example.com', full_name: null },
  })
}

describe('US08 - add a job offer', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('redirects an anonymous visitor to the login page', async () => {
    renderApp('/offres/nouvelle')

    expect(await screen.findByLabelText('E-mail')).toBeInTheDocument()
    expect(screen.queryByLabelText("Lien de l'offre")).not.toBeInTheDocument()
  })

  it('adds an offer from a URL and shows the saved content', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.post).mockResolvedValue({ status: 201, data: savedOffer })
    renderApp('/offres/nouvelle')

    await user.type(await screen.findByLabelText("Lien de l'offre"), OFFER_URL)
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(await screen.findByText('Offre ajoutée avec succès.')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/offers', { url: OFFER_URL })
    expect(screen.getByText(/Stage PFE Data Scientist/)).toBeInTheDocument()
  })

  it('adds an offer from pasted text', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.post).mockResolvedValue({
      status: 201,
      data: { ...savedOffer, source_type: 'text', source_url: null, content: OFFER_TEXT },
    })
    renderApp('/offres/nouvelle')

    await user.click(await screen.findByLabelText('Texte collé'))
    await user.click(screen.getByLabelText("Texte de l'offre"))
    await user.paste(OFFER_TEXT)
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(await screen.findByText('Offre ajoutée avec succès.')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/offers', { text: OFFER_TEXT })
  })

  it('tells the user when the offer was already in their list', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.post).mockResolvedValue({ status: 200, data: savedOffer })
    renderApp('/offres/nouvelle')

    await user.type(await screen.findByLabelText("Lien de l'offre"), OFFER_URL)
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(await screen.findByText('Cette offre est déjà dans votre liste.')).toBeInTheDocument()
  })

  it('rejects an empty or invalid URL without calling the API', async () => {
    const user = userEvent.setup()
    signIn()
    renderApp('/offres/nouvelle')

    await user.click(await screen.findByRole('button', { name: "Ajouter l'offre" }))

    expect(
      await screen.findByText('Entrez une adresse valide commençant par http:// ou https://'),
    ).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('rejects a pasted text that is too short', async () => {
    const user = userEvent.setup()
    signIn()
    renderApp('/offres/nouvelle')

    await user.click(await screen.findByLabelText('Texte collé'))
    await user.click(screen.getByLabelText("Texte de l'offre"))
    await user.paste('trop court')
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(
      await screen.findByText("L'offre doit contenir au moins 50 caractères."),
    ).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('shows the API error and offers to paste the text instead', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.post).mockRejectedValue({
      isAxiosError: true,
      response: { status: 422, data: { detail: NO_CONTENT_DETAIL } },
    })
    renderApp('/offres/nouvelle')

    await user.type(await screen.findByLabelText("Lien de l'offre"), OFFER_URL)
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(await screen.findByRole('alert')).toHaveTextContent(NO_CONTENT_DETAIL)

    await user.click(screen.getByRole('button', { name: 'Coller le texte à la place' }))

    expect(screen.getByLabelText("Texte de l'offre")).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a generic message when the server cannot be reached', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.post).mockRejectedValue(new Error('Network Error'))
    renderApp('/offres/nouvelle')

    await user.type(await screen.findByLabelText("Lien de l'offre"), OFFER_URL)
    await user.click(screen.getByRole('button', { name: "Ajouter l'offre" }))

    expect(
      await screen.findByText('Impossible de joindre le serveur. Réessayez dans un instant.'),
    ).toBeInTheDocument()
  })
})

const LONG_DESCRIPTION = 'Vous concevez des API REST avec FastAPI. '.repeat(10)

const summaries: JobOfferSummary[] = [
  {
    id: 'offer-1',
    source_type: 'url',
    source_url: OFFER_URL,
    title: 'Stage PFE Data Scientist',
    description: 'Bestlab · Tunis\n\nAnalyse de données et modèles prédictifs.',
    created_at: '2026-11-20T10:00:00Z',
  },
  {
    id: 'offer-2',
    source_type: 'text',
    source_url: null,
    title: 'Développeur Python backend',
    description: LONG_DESCRIPTION,
    created_at: '2026-11-19T09:00:00Z',
  },
]

/** GET /auth/me answers with a user; GET /offers answers with `offers` or fails. */
function mockApiGet(offers: JobOfferSummary[] | Error) {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === '/auth/me') {
      return { data: { id: '1', email: 'me@example.com', full_name: null } }
    }
    if (url === '/offers') {
      if (offers instanceof Error) throw offers
      return { data: offers }
    }
    throw new Error(`unexpected GET ${url}`)
  })
}

describe('US08 - my offers', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('lists my offers with their title and description', async () => {
    mockApiGet(summaries)

    renderApp('/offres')

    expect(
      await screen.findByRole('heading', { name: 'Stage PFE Data Scientist' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Développeur Python backend' })).toBeInTheDocument()
    expect(screen.getByText(/Analyse de données et modèles prédictifs/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "Annonce d'origine" })).toHaveAttribute(
      'href',
      OFFER_URL,
    )
  })

  it('shows a message when I have no offer yet', async () => {
    mockApiGet([])

    renderApp('/offres')

    expect(await screen.findByText("Vous n'avez encore ajouté aucune offre.")).toBeInTheDocument()
  })

  it('shows an error with a retry button when the list cannot be loaded', async () => {
    const user = userEvent.setup()
    mockApiGet(new Error('Network Error'))

    renderApp('/offres')

    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de charger vos offres.')

    mockApiGet(summaries)
    await user.click(screen.getByRole('button', { name: 'Réessayer' }))

    expect(
      await screen.findByRole('heading', { name: 'Stage PFE Data Scientist' }),
    ).toBeInTheDocument()
  })

  it('expands and collapses a long description', async () => {
    const user = userEvent.setup()
    mockApiGet(summaries)
    renderApp('/offres')

    const button = await screen.findByRole('button', { name: 'Voir plus' })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    await user.click(button)

    expect(screen.getByRole('button', { name: 'Voir moins' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })
})

describe('US08 - delete an offer', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
    vi.mocked(api.delete).mockReset()
  })

  it('deletes an offer after confirmation and refreshes the list', async () => {
    const user = userEvent.setup()
    mockApiGet(summaries)
    vi.mocked(api.delete).mockResolvedValue({ status: 204 })
    renderApp('/offres')

    await user.click(
      await screen.findByRole('button', { name: 'Supprimer Stage PFE Data Scientist' }),
    )
    expect(screen.getByText('Supprimer cette offre ?')).toBeInTheDocument()

    mockApiGet([summaries[1]])
    await user.click(screen.getByRole('button', { name: 'Oui, supprimer' }))

    await waitFor(() =>
      expect(
        screen.queryByRole('heading', { name: 'Stage PFE Data Scientist' }),
      ).not.toBeInTheDocument(),
    )
    expect(api.delete).toHaveBeenCalledWith('/offers/offer-1')
    expect(screen.getByRole('heading', { name: 'Développeur Python backend' })).toBeInTheDocument()
  })

  it('does nothing when the deletion is cancelled', async () => {
    const user = userEvent.setup()
    mockApiGet(summaries)
    renderApp('/offres')

    await user.click(
      await screen.findByRole('button', { name: 'Supprimer Stage PFE Data Scientist' }),
    )
    await user.click(screen.getByRole('button', { name: 'Annuler' }))

    expect(screen.queryByText('Supprimer cette offre ?')).not.toBeInTheDocument()
    expect(api.delete).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Stage PFE Data Scientist' })).toBeInTheDocument()
  })

  it('shows an error and keeps the offer when the deletion fails', async () => {
    const user = userEvent.setup()
    mockApiGet(summaries)
    vi.mocked(api.delete).mockRejectedValue(new Error('Network Error'))
    renderApp('/offres')

    await user.click(
      await screen.findByRole('button', { name: 'Supprimer Stage PFE Data Scientist' }),
    )
    await user.click(screen.getByRole('button', { name: 'Oui, supprimer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Impossible de supprimer l'offre.")
    expect(screen.getByRole('heading', { name: 'Stage PFE Data Scientist' })).toBeInTheDocument()
  })

  it('treats an offer that is already gone as deleted', async () => {
    const user = userEvent.setup()
    mockApiGet(summaries)
    vi.mocked(api.delete).mockRejectedValue({ isAxiosError: true, response: { status: 404 } })
    renderApp('/offres')

    await user.click(
      await screen.findByRole('button', { name: 'Supprimer Stage PFE Data Scientist' }),
    )
    mockApiGet([summaries[1]])
    await user.click(screen.getByRole('button', { name: 'Oui, supprimer' }))

    await waitFor(() =>
      expect(
        screen.queryByRole('heading', { name: 'Stage PFE Data Scientist' }),
      ).not.toBeInTheDocument(),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
