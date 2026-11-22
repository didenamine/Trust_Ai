import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import CVAdaptationPanel from './components/CVAdaptationPanel'
import { AuthProvider } from './context/AuthContext'
import type { CVAdaptation } from './lib/adaptation'
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
  description: 'React, Python et Kubernetes.',
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
      { name: 'React', category: 'hard', level: null },
      { name: 'Kubernetes', category: 'hard', level: null },
    ],
    experiences: [],
    education: [],
  },
}

const adaptation: CVAdaptation = {
  id: 'adaptation-1',
  offer_id: offer.id,
  matching_score: 72,
  missing_skills: ['Kubernetes'],
  created_at: '2026-11-22T10:00:00Z',
  updated_at: '2026-11-22T10:00:00Z',
  adapted_cv: {
    schema_version: 1,
    language: 'fr',
    headline: 'Développeuse full-stack Python / React',
    summary: 'Développeuse full-stack à l’aise avec Python et React, habituée aux API REST.',
    highlighted_skills: ['Python', 'React', 'FastAPI'],
    experiences: [
      {
        experience_id: 'exp-dev',
        description: 'Évolution d’une application React / TypeScript.',
        achievements: ['Réalisation reformulée'],
      },
    ],
    changes: ['Résumé recentré sur Python et React, demandés par l’offre.'],
  },
}

const profileResponse = {
  profile: {
    experiences: [{ id: 'exp-dev', job_title: 'Développeuse web', company: 'Startup Exemple' }],
  },
}

function newQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPanel() {
  return render(
    <QueryClientProvider client={newQueryClient()}>
      <CVAdaptationPanel adaptation={adaptation} />
    </QueryClientProvider>,
  )
}

function renderApp() {
  return render(
    <QueryClientProvider client={newQueryClient()}>
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
    if (url === '/profile/me') return { data: profileResponse }
    throw new Error(`unexpected GET ${url}`)
  })
}

describe('US14 - CV adapté (CVAdaptationPanel)', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
  })

  it('shows the adapted content, what changed and the skills it could not add', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: profileResponse })
    renderPanel()

    const panel = screen.getByRole('region', { name: "CV adapté à l'offre" })
    expect(within(panel).getByText('Développeuse full-stack Python / React')).toBeInTheDocument()
    expect(within(panel).getByText(/habituée aux API REST/)).toBeInTheDocument()

    const skills = within(panel).getByRole('list', { name: 'Compétences mises en avant' })
    expect(
      within(skills)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['Python', 'React', 'FastAPI'])

    expect(await within(panel).findByText('Développeuse web · Startup Exemple')).toBeInTheDocument()
    expect(within(panel).getByText(/application React \/ TypeScript/)).toBeInTheDocument()
    expect(within(panel).getByText('Réalisation reformulée')).toBeInTheDocument()
    expect(within(panel).getByText(/Résumé recentré/)).toBeInTheDocument()
    expect(within(panel).getByText('✕ Kubernetes')).toBeInTheDocument()
    expect(within(panel).getByText(/n’est pas vérifié/)).toBeInTheDocument()
    expect(within(panel).getByText(/compatibilité de départ : 72 %/)).toBeInTheDocument()
  })

  it('still shows the experiences when the profile cannot be read', () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network down'))
    renderPanel()

    const panel = screen.getByRole('region', { name: "CV adapté à l'offre" })
    expect(within(panel).getByText('Expérience')).toBeInTheDocument()
    expect(within(panel).getByText(/application React \/ TypeScript/)).toBeInTheDocument()
  })
})

describe('US14 - adapter son CV depuis Mes offres', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
    vi.mocked(api.delete).mockReset()
  })

  it('offers the adaptation only once the offer has been analysed', async () => {
    mockApiGet()
    vi.mocked(api.post).mockResolvedValueOnce({ data: analysis, status: 201 })
    const user = userEvent.setup()

    renderApp()
    await screen.findByRole('heading', { name: 'Développeur full-stack (CDI)' })
    expect(screen.queryByRole('button', { name: 'Adapter mon CV' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Analyser l’offre' }))
    expect(await screen.findByRole('button', { name: 'Adapter mon CV' })).toBeInTheDocument()
  })

  it('adapts the CV to the selected offer and shows the result', async () => {
    mockApiGet()
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: analysis, status: 201 })
      .mockResolvedValueOnce({ data: adaptation, status: 201 })
    const user = userEvent.setup()

    renderApp()
    await user.click(await screen.findByRole('button', { name: 'Analyser l’offre' }))
    await user.click(await screen.findByRole('button', { name: 'Adapter mon CV' }))

    const panel = await screen.findByRole('region', { name: "CV adapté à l'offre" })
    expect(within(panel).getByText('Développeuse full-stack Python / React')).toBeInTheDocument()
    expect(within(panel).getByText('✕ Kubernetes')).toBeInTheDocument()
    expect(api.post).toHaveBeenLastCalledWith('/adaptations/offer-1')
    expect(screen.getByRole('button', { name: 'Régénérer le CV adapté' })).toBeInTheDocument()
  })

  it('shows the API message when the CV cannot be adapted', async () => {
    mockApiGet()
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: analysis, status: 201 })
      .mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          status: 404,
          data: {
            detail: 'Profil candidat introuvable. Importez votre CV ou remplissez votre profil.',
          },
        },
      })
    const user = userEvent.setup()

    renderApp()
    await user.click(await screen.findByRole('button', { name: 'Analyser l’offre' }))
    await user.click(await screen.findByRole('button', { name: 'Adapter mon CV' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/Profil candidat introuvable/)
    expect(screen.queryByRole('region', { name: "CV adapté à l'offre" })).not.toBeInTheDocument()
  })
})
