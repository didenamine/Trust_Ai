import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'

vi.mock('./lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

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

const ME = { id: '1', email: 'me@example.com', full_name: 'Ikram' }

function mockGet(handlers: Record<string, unknown>) {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    for (const [pattern, value] of Object.entries(handlers)) {
      if (url === pattern || url.startsWith(pattern)) {
        if (value instanceof Error) throw value
        return { data: value }
      }
    }
    throw Object.assign(new Error(`unexpected GET ${url}`), {
      isAxiosError: true,
      response: { status: 404 },
    })
  })
}

function notFound() {
  return Object.assign(new Error('not found'), { isAxiosError: true, response: { status: 404 } })
}

describe('US31 - dashboard', () => {
  beforeEach(() => {
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.get).mockReset()
  })

  it('redirects an anonymous visitor to the login page', async () => {
    localStorage.clear()
    mockGet({})
    renderApp('/tableau-de-bord')
    expect(await screen.findByRole('heading', { name: 'Se connecter' })).toBeInTheDocument()
  })

  it('shows an empty state for every block when the candidate has nothing yet', async () => {
    mockGet({
      '/auth/me': ME,
      '/profile/me': notFound(),
      '/cv/me': notFound(),
      '/ats/me': notFound(),
      '/offers': [],
    })

    renderApp('/tableau-de-bord')

    expect(await screen.findByRole('heading', { name: 'Tableau de bord' })).toBeInTheDocument()
    expect(
      await screen.findByText("Vous n'avez pas encore de profil candidat."),
    ).toBeInTheDocument()
    expect(await screen.findByText("Vous n'avez pas encore importé de CV.")).toBeInTheDocument()
    expect(
      await screen.findByText("Votre CV n'a pas encore été analysé selon des critères ATS."),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Ajoutez une offre pour calculer votre compatibilité.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Bientôt disponible')).toBeInTheDocument()
  })

  it('shows the profile, CV and ATS blocks once they exist', async () => {
    mockGet({
      '/auth/me': ME,
      '/profile/me': {
        profile: {
          schema_version: 1,
          language: 'fr',
          personal_info: {
            full_name: 'Sarra Ben Ali',
            headline: 'Développeuse full-stack junior',
            email: null,
            phone: null,
            location: null,
            links: [],
          },
          summary: null,
          skills: [
            { name: 'Python', category: 'hard', level: 'advanced' },
            { name: 'React', category: 'hard', level: 'intermediate' },
          ],
          experiences: [],
          education: [],
          languages: [],
          certifications: [],
          projects: [],
        },
        source: 'manual',
        cv_document_id: null,
        updated_at: '2026-01-01T00:00:00Z',
      },
      '/cv/me': {
        id: 'cv-1',
        original_filename: 'mon-cv.pdf',
        content_type: 'application/pdf',
        size_bytes: 102400,
        uploaded_at: '2026-01-02T00:00:00Z',
      },
      '/ats/me': {
        id: 'ats-1',
        cv_document_id: 'cv-1',
        cv_uploaded_at: '2026-01-02T00:00:00Z',
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
        scoring_version: 1,
        score: {
          total: 82,
          band: 'good',
          scoring_version: 1,
          denominator: 100,
          dimensions: [],
          criteria: [],
          na_sections: [],
        },
        result: {},
      },
      '/offers': [],
    })

    renderApp('/tableau-de-bord')

    expect(await screen.findByText('Sarra Ben Ali')).toBeInTheDocument()
    expect(screen.getByText('Développeuse full-stack junior')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('mon-cv.pdf')).toBeInTheDocument()
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(screen.getByText('Bon')).toBeInTheDocument()
  })

  it('shows the compatibility score once an offer has been matched', async () => {
    mockGet({
      '/auth/me': ME,
      '/profile/me': notFound(),
      '/cv/me': notFound(),
      '/ats/me': notFound(),
      '/offers': [
        {
          id: 'offer-1',
          source_type: 'text',
          source_url: null,
          title: 'Développeur full-stack',
          description: '...',
          created_at: '2026-01-03T00:00:00Z',
        },
      ],
      '/matching/offer-1': {
        total_score: 74,
        band: 'good',
        dimension_scores: {
          skills: { weight: 1, points: 1, max_points: 1, ratio: 1 },
          experience: { weight: 1, points: 1, max_points: 1, ratio: 1 },
          education: { weight: 1, points: 1, max_points: 1, ratio: 1 },
        },
        details: {
          matched_skills: [],
          missing_skills: [],
          experience: { candidate_years: 0, required_years: 0, meets_requirement: true },
          education: {
            candidate_level: null,
            required_level: null,
            candidate_rank: null,
            required_rank: null,
            meets_requirement: true,
          },
        },
        strengths: [],
        improvements: [],
      },
    })

    renderApp('/tableau-de-bord')

    expect(await screen.findByText('74%')).toBeInTheDocument()
    expect(screen.getByText('avec « Développeur full-stack »')).toBeInTheDocument()
    expect(screen.getByText('Bonne compatibilité')).toBeInTheDocument()
  })

  it('invites the candidate to analyse an offer when none has a score yet', async () => {
    mockGet({
      '/auth/me': ME,
      '/profile/me': notFound(),
      '/cv/me': notFound(),
      '/ats/me': notFound(),
      '/offers': [
        {
          id: 'offer-1',
          source_type: 'text',
          source_url: null,
          title: 'Développeur full-stack',
          description: '...',
          created_at: '2026-01-03T00:00:00Z',
        },
      ],
      '/matching/offer-1': notFound(),
    })

    renderApp('/tableau-de-bord')

    await waitFor(() =>
      expect(
        screen.getByText('Analysez une offre pour voir votre score de compatibilité.'),
      ).toBeInTheDocument(),
    )
  })
})
