import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'
import type { OfferAnalysis } from './lib/offerAnalysis'
import type { JobOfferSummary } from './lib/offers'

vi.mock('./lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
}))

const offer: JobOfferSummary = {
  id: 'offer-1',
  source_type: 'text',
  source_url: null,
  title: 'Développeur full-stack (CDI)',
  description: '3 à 5 ans d’expérience, React, Python, Bac+5.',
  created_at: '2026-11-20T10:00:00Z',
}

const analysis: OfferAnalysis = {
  id: 'analysis-1',
  offer_id: offer.id,
  created_at: '2026-11-21T10:00:00Z',
  updated_at: '2026-11-21T10:00:00Z',
  requirements: {
    schema_version: 1,
    language: 'fr',
    job_title: 'Développeur full-stack',
    skills: [
      { name: 'React', category: 'hard', level: 'advanced' },
      { name: 'Communication', category: 'soft', level: null },
    ],
    experiences: [
      {
        min_years: 3,
        max_years: 5,
        job_title: 'Développeur full-stack',
        employment_type: 'full_time',
        description: 'Trois à cinq ans d’expérience en développement web',
        skills: ['React'],
      },
    ],
    education: [
      {
        level: 'master',
        degree: 'Master en informatique',
        field_of_study: 'informatique',
        description: 'Bac+5 en informatique ou diplôme d’ingénieur',
      },
    ],
  },
}

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/offres']}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function mockApiGet() {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === '/auth/me') {
      return { data: { id: '1', email: 'me@example.com', full_name: null } }
    }
    if (url === '/offers') return { data: [offer] }
    throw new Error(`unexpected GET ${url}`)
  })
}

describe('US09 - analyse automatique de l’offre', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
    vi.mocked(api.delete).mockReset()
  })

  it('analyses a saved offer and shows its structured requirements', async () => {
    mockApiGet()
    vi.mocked(api.post).mockResolvedValue({ data: analysis, status: 201 })
    const user = userEvent.setup()

    renderApp()
    expect(
      await screen.findByRole('heading', { name: 'Développeur full-stack (CDI)' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Analyser l’offre' }))

    const panel = await screen.findByRole('region', { name: "Exigences de l'offre" })
    expect(within(panel).getByText(/Poste : Développeur full-stack/)).toBeInTheDocument()
    expect(within(panel).getByText('React')).toBeInTheDocument()
    expect(within(panel).getByText(/Compétence technique/)).toBeInTheDocument()
    expect(within(panel).getByText(/Avancé/)).toBeInTheDocument()
    expect(within(panel).getByText(/3 à 5 ans/)).toBeInTheDocument()
    expect(within(panel).getByText(/Bac\+5 \(Master/)).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/offers/offer-1/analyze', null, undefined)
  })

  it('refreshes an analysis that is already displayed', async () => {
    mockApiGet()
    vi.mocked(api.post).mockResolvedValue({ data: analysis, status: 200 })
    const user = userEvent.setup()

    renderApp()
    await user.click(await screen.findByRole('button', { name: 'Analyser l’offre' }))
    await screen.findByRole('region', { name: "Exigences de l'offre" })
    await user.click(screen.getByRole('button', { name: 'Actualiser l’analyse' }))

    expect(api.post).toHaveBeenLastCalledWith('/offers/offer-1/analyze', null, {
      params: { refresh: true },
    })
  })

  it('shows the API error message when the analysis cannot be produced', async () => {
    mockApiGet()
    vi.mocked(api.post).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 422,
        data: { detail: "Langue de l'offre non prise en charge : l'offre doit être en français" },
      },
    })
    const user = userEvent.setup()

    renderApp()
    await user.click(await screen.findByRole('button', { name: 'Analyser l’offre' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Langue de l.offre non prise en charge/,
    )
    expect(screen.queryByRole('region', { name: "Exigences de l'offre" })).not.toBeInTheDocument()
  })
})
