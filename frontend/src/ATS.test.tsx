import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, type AxiosResponse } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'
import type { ATSAnalysisResponse, ATSAnalysisResult, ATSScore } from './lib/ats'

vi.mock('./lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
}))

const ME = { id: '1', email: 'me@example.com', full_name: null }

const CV = {
  id: 'cv-1',
  original_filename: 'mon-cv.pdf',
  content_type: 'application/pdf',
  size_bytes: 120 * 1024,
  uploaded_at: '2026-11-19T10:00:00Z',
}

const SCORE: ATSScore = {
  total: 72,
  band: 'good',
  scoring_version: 1,
  denominator: 98,
  dimensions: [
    {
      key: 'readability',
      label_key: 'ats.dimension.readability',
      weight: 40,
      points: 36,
      status: 'ok',
      applicable: true,
      reason_code: null,
    },
    {
      key: 'sections',
      label_key: 'ats.dimension.sections',
      weight: 28,
      points: 24,
      status: 'ok',
      applicable: true,
      reason_code: null,
    },
    {
      key: 'keywords',
      label_key: 'ats.dimension.keywords',
      weight: 25,
      points: 11,
      status: 'warning',
      applicable: true,
      reason_code: null,
    },
  ],
  criteria: [
    {
      key: 'sections.skills',
      label_key: 'ats.criterion.section.skills',
      weight: 6,
      points: 4.8,
      status: 'warning',
      applicable: true,
      reason_code: 'section.skills.too_few_skills',
    },
    {
      key: 'keywords.specificity',
      label_key: 'ats.criterion.keywords.specificity',
      weight: 9,
      points: 4.5,
      status: 'warning',
      applicable: true,
      reason_code: 'keywords.no_specific_terms',
    },
    {
      key: 'sections.summary',
      label_key: 'ats.criterion.section.summary',
      weight: 3,
      points: 0,
      status: 'na',
      applicable: false,
      reason_code: 'section.na',
    },
  ],
  na_sections: ['summary', 'languages', 'certifications'],
}

const RESULT: ATSAnalysisResult = {
  language: 'fr',
  sections: [
    {
      section: 'contact',
      status: 'ok',
      present: true,
      detection: 'contact_signals',
      line: 1,
      order_index: 0,
      checks: { has_email: true, has_phone: true, has_link: false },
      issues: [],
    },
    {
      section: 'experience',
      status: 'ok',
      present: true,
      detection: 'heading_alias',
      line: 8,
      order_index: 1,
      checks: { has_entries: true, has_dates: true, has_multiple_entries: true },
      issues: [],
    },
    {
      section: 'skills',
      status: 'warning',
      present: true,
      detection: 'heading_alias',
      line: 20,
      order_index: 2,
      checks: { has_entries: true, has_skill_list: false },
      issues: ['section.skills.too_few_skills'],
    },
    {
      section: 'summary',
      status: 'na',
      present: false,
      detection: 'none',
      line: null,
      order_index: null,
      checks: {},
      issues: [],
    },
  ],
  keywords: {
    specific_count: 4,
    action_verb_count: 2,
    generic_count: 1,
    verified_count: 7,
    repeated_count: 1,
    max_occurrences: 5,
    specificity_ratio: 0.8,
    terminology_issues: 0,
  },
  keyword_findings: [
    {
      canonical: 'Python',
      kind: 'hard_skill',
      verified: true,
      line: 21,
      section: 'skills',
      occurrences: 2,
      alias_count: 0,
      in_skills_section: true,
      in_context_section: false,
    },
    {
      canonical: 'React',
      kind: 'tool',
      verified: true,
      line: 21,
      section: 'skills',
      occurrences: 1,
      alias_count: 0,
      in_skills_section: true,
      in_context_section: false,
    },
  ],
  readability: [
    {
      code: 'docx.body_only_tables',
      severity: 'warning',
      location: 'table',
      page: null,
      line: null,
      degraded_extraction: false,
      deduction: 0,
    },
  ],
  score: SCORE,
  limitations: ['ats.estimate_only', 'ats.no_target_job', 'ats.no_ocr'],
}

const ATS: ATSAnalysisResponse = {
  id: 'ats-1',
  cv_document_id: CV.id,
  cv_uploaded_at: CV.uploaded_at,
  created_at: '2026-11-20T10:00:00Z',
  updated_at: '2026-11-20T10:00:00Z',
  scoring_version: 1,
  score: SCORE,
  result: RESULT,
}

function apiError(status: number, detail?: string) {
  return new AxiosError('error', String(status), undefined, undefined, {
    status,
    data: detail ? { detail } : {},
  } as AxiosResponse)
}

function mockGet({
  cv = CV,
  ats = null as ATSAnalysisResponse | null,
  atsError = false,
}: {
  cv?: typeof CV | null
  ats?: ATSAnalysisResponse | null
  atsError?: boolean
} = {}) {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === '/auth/me') return { data: ME }
    if (url === '/cv/me') {
      if (cv) return { data: cv }
      throw apiError(404, 'Aucun CV importé')
    }
    if (url === '/ats/me') {
      if (atsError) throw apiError(500)
      if (ats) return { data: ats }
      throw apiError(404, "Ce CV n'a pas encore d'analyse ATS")
    }
    if (url === '/profile/me') throw apiError(404, 'Aucun profil')
    throw new Error(`unexpected GET ${url}`)
  })
}

function renderPage(path = '/analyse-ats') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
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

describe('US24 - analyse ATS du CV importé', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
  })

  it('asks for a CV before offering an ATS analysis', async () => {
    mockGet({ cv: null })
    renderPage()

    expect(
      await screen.findByText('Importez d’abord votre CV pour pouvoir l’analyser.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Importer mon CV' })).toHaveAttribute('href', '/mon-cv')
    expect(api.post).not.toHaveBeenCalled()
  })

  it('runs the analysis manually and displays the transparent report', async () => {
    const user = userEvent.setup()
    mockGet()
    vi.mocked(api.post).mockResolvedValue({ data: ATS })
    renderPage()

    expect(
      await screen.findByText('Ce CV n’a pas encore été analysé selon les critères ATS.'),
    ).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Analyser mon CV' }))

    expect(await screen.findByLabelText('Score ATS')).toHaveTextContent('72 / 100')
    expect(screen.getByLabelText('Score ATS')).toHaveTextContent(
      'Score calculé sur 98 points applicables',
    )
    expect(screen.getByLabelText('Détail du score')).toHaveTextContent('Compétences')
    expect(screen.getByLabelText('Mots-clés')).toHaveTextContent('Python')
    expect(screen.getByLabelText('Lisibilité ATS')).toHaveTextContent(
      'Le contenu principal est organisé dans des tableaux.',
    )
    expect(vi.mocked(api.post).mock.calls.map(([url]) => url)).toEqual(['/ats/me/analyze'])
  })

  it('shows an existing result without running a new analysis', async () => {
    mockGet({ ats: ATS })
    renderPage()

    expect(await screen.findByLabelText('Score ATS')).toHaveTextContent('72 / 100')
    expect(screen.getByRole('button', { name: 'Relancer l’analyse' })).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it("shows the API's message and can retry after a failure", async () => {
    const user = userEvent.setup()
    mockGet()
    vi.mocked(api.post)
      .mockRejectedValueOnce(
        apiError(422, "Aucun texte n'a pu être lu dans ce CV (document scanné ou image ?)."),
      )
      .mockResolvedValueOnce({ data: ATS })
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Analyser mon CV' }))
    expect(await screen.findByText(/Aucun texte n'a pu être lu dans ce CV/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Analyser mon CV' }))

    expect(await screen.findByLabelText('Score ATS')).toHaveTextContent('72 / 100')
    expect(vi.mocked(api.post).mock.calls).toHaveLength(2)
  })

  it('warns when the result belongs to a previous version of the CV', async () => {
    const user = userEvent.setup()
    mockGet({ ats: { ...ATS, cv_uploaded_at: '2026-11-01T10:00:00Z' } })
    vi.mocked(api.post).mockResolvedValue({ data: ATS })
    renderPage()

    expect(
      await screen.findByText('Ce résultat correspond à une version précédente du CV.'),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Score ATS')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Analyser mon CV' }))

    expect(await screen.findByLabelText('Score ATS')).toHaveTextContent('72 / 100')
  })

  it('exposes the manual action on /mon-cv and navigates to the report', async () => {
    const user = userEvent.setup()
    // Like the real backend: once analysed, GET /ats/me returns the saved result
    // (the report page reloads it, which raced with the assertion below).
    let saved: typeof ATS | null = null
    mockGet()
    const baseGet = vi.mocked(api.get).getMockImplementation()!
    vi.mocked(api.get).mockImplementation(async (url: string) =>
      url === '/ats/me' && saved ? { data: saved } : baseGet(url),
    )
    vi.mocked(api.post).mockImplementation(async () => {
      saved = ATS
      return { data: ATS }
    })
    renderPage('/mon-cv')

    await user.click(await screen.findByRole('button', { name: 'Vérifier le score ATS' }))

    expect(await screen.findByText('72 / 100')).toBeInTheDocument()
    expect(vi.mocked(api.post).mock.calls.map(([url]) => url)).toEqual(['/ats/me/analyze'])
    expect(screen.queryByRole('heading', { name: 'Mon CV' })).not.toBeInTheDocument()
  })

  it('shows a reload button when the current CV cannot be fetched', async () => {
    const user = userEvent.setup()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') return { data: ME }
      throw apiError(500)
    })
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossible de récupérer l’analyse ATS.',
    )
    await user.click(screen.getByRole('button', { name: 'Réessayer' }))
    await waitFor(() => expect(api.get).toHaveBeenCalled())
  })
})
