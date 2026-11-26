import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import CVAdaptationPanel from './components/CVAdaptationPanel'
import { AuthProvider } from './context/AuthContext'
import type { ATSCVDocument, CVAdaptation } from './lib/adaptation'
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

const cvDocument: ATSCVDocument = {
  language: 'fr',
  contact: {
    full_name: 'Sarra Ben Ali',
    headline: 'Développeuse full-stack Python / React',
    email: 'sarra.benali@example.com',
    phone: '+216 20 000 000',
    location: 'Tunis, Tunisie',
    links: ['https://github.com/sarra-ben-ali'],
  },
  summary: 'Développeuse full-stack à l’aise avec Python et React, habituée aux API REST.',
  skill_groups: [
    { label: 'Compétences techniques', skills: ['Python', 'React', 'FastAPI'] },
    { label: 'Compétences comportementales', skills: ['Communication'] },
  ],
  experiences: [
    {
      job_title: 'Développeuse web',
      company: 'Startup Exemple',
      location: 'Ariana',
      period: '09/2025 - Présent',
      description: 'Évolution d’une application React / TypeScript.',
      bullets: ['Réalisation reformulée'],
      technologies: ['React', 'TypeScript'],
    },
  ],
  projects: [],
  education: [
    {
      degree: 'Licence en génie logiciel',
      institution: 'Institut Supérieur Exemple',
      location: 'Tunis',
      period: '2022 - 2025',
      description: null,
    },
  ],
  certifications: [{ name: 'Professional Scrum Master I', issuer: 'Scrum.org', date: '11/2024' }],
  languages: [{ name: 'Français', level: 'C1' }],
  section_titles: {
    contact: 'Coordonnées',
    summary: 'Profil professionnel',
    skills: 'Compétences',
    experience: 'Expérience professionnelle',
    projects: 'Projets',
    education: 'Formation',
    certifications: 'Certifications',
    languages: 'Langues',
  },
  missing_sections: [],
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
    summary: cvDocument.summary,
    highlighted_skills: ['Python', 'React', 'FastAPI'],
    experiences: [],
    changes: ['Résumé recentré sur Python et React, demandés par l’offre.'],
  },
  document: cvDocument,
  ats_text: 'Sarra Ben Ali\nDéveloppeuse full-stack Python / React\n\nPROFIL PROFESSIONNEL\n',
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

describe('US14 - CV adapté (CVAdaptationPanel)', () => {
  it('shows the complete CV in ATS order, what changed and the skills it could not add', () => {
    render(<CVAdaptationPanel adaptation={adaptation} />)

    const panel = screen.getByRole('region', { name: "CV adapté à l'offre" })
    const cv = within(panel).getByRole('article', { name: 'Aperçu du CV au format ATS' })

    expect(within(cv).getByText('Sarra Ben Ali')).toBeInTheDocument()
    expect(within(cv).getByText('Développeuse full-stack Python / React')).toBeInTheDocument()
    expect(
      within(cv).getByText('Tunis, Tunisie | +216 20 000 000 | sarra.benali@example.com'),
    ).toBeInTheDocument()
    expect(
      within(cv)
        .getAllByRole('heading')
        .map((heading) => heading.textContent),
    ).toEqual([
      'Profil professionnel',
      'Compétences',
      'Expérience professionnelle',
      'Formation',
      'Certifications',
      'Langues',
    ])

    expect(within(cv).getByText(/habituée aux API REST/)).toBeInTheDocument()
    expect(within(cv).getByText(/Python, React, FastAPI/)).toBeInTheDocument()
    expect(within(cv).getByText('Développeuse web | Startup Exemple | Ariana')).toBeInTheDocument()
    expect(within(cv).getByText('09/2025 - Présent')).toBeInTheDocument()
    expect(within(cv).getByText('Réalisation reformulée')).toBeInTheDocument()
    expect(within(cv).getByText(/Technologies : React, TypeScript/)).toBeInTheDocument()
    expect(
      within(cv).getByText('Licence en génie logiciel | Institut Supérieur Exemple | Tunis'),
    ).toBeInTheDocument()
    expect(
      within(cv).getByText('Professional Scrum Master I | Scrum.org | 11/2024'),
    ).toBeInTheDocument()
    expect(within(cv).getByText('Français (C1)')).toBeInTheDocument()

    expect(within(panel).getByText(/Résumé recentré/)).toBeInTheDocument()
    expect(within(panel).getByText('✕ Kubernetes')).toBeInTheDocument()
    expect(within(panel).getByText(/n’est pas vérifié/)).toBeInTheDocument()
    expect(within(panel).getByText(/compatibilité de départ : 72 %/)).toBeInTheDocument()
  })

  it('tells the candidate which standard sections the profile cannot fill', () => {
    const incomplete: CVAdaptation = {
      ...adaptation,
      document: { ...cvDocument, education: [], missing_sections: ['education'] },
    }
    render(<CVAdaptationPanel adaptation={incomplete} />)

    expect(
      screen.getByText(/Sections à compléter dans votre profil : Formation/),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Formation' })).not.toBeInTheDocument()
  })

  it('copies the CV as plain text', async () => {
    const user = userEvent.setup()
    render(<CVAdaptationPanel adaptation={adaptation} />)

    await user.click(screen.getByRole('button', { name: 'Copier le texte' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Copié')
    expect(await navigator.clipboard.readText()).toBe(adaptation.ats_text)
    expect(screen.getByRole('button', { name: 'Télécharger (.txt)' })).toBeInTheDocument()
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
    expect(within(panel).getByText('Sarra Ben Ali')).toBeInTheDocument()
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
