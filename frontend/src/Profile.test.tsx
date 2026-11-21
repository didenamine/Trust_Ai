import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, type AxiosResponse } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'

vi.mock('./lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn() },
}))

const ME = { id: '1', email: 'me@example.com', full_name: null }

const CV_PROFILE = {
  source: 'cv_analysis',
  cv_document_id: 'cv-1',
  updated_at: '2026-11-20T10:00:00Z',
  profile: {
    schema_version: 1,
    language: 'fr',
    personal_info: {
      full_name: 'Sarra Benali',
      headline: 'Développeuse full-stack',
      email: 'sarra@example.fr',
      phone: null,
      location: 'Tunis, Tunisie',
      links: ['github.com/sarra'],
    },
    summary: 'Développeuse full-stack de 5 ans d’expérience.',
    skills: [
      { name: 'Python', category: 'hard', level: 'advanced' },
      { name: 'React', category: 'hard', level: null },
    ],
    experiences: [
      {
        id: 'exp-1',
        job_title: 'Développeuse',
        company: 'Acme',
        location: null,
        employment_type: 'full_time',
        start_date: '2021-03',
        end_date: null,
        is_current: true,
        description: null,
        achievements: ['A réduit les délais de 30 %'],
        skills: ['Python', 'React'],
      },
    ],
    education: [],
    languages: [{ name: 'Arabe', code: 'ar', level: 'native' }],
    certifications: [],
    projects: [],
  },
}

function apiError(status: number, detail?: string) {
  return new AxiosError('error', String(status), undefined, undefined, {
    status,
    data: detail ? { detail } : {},
  } as AxiosResponse)
}

function mockGet(profile: object | null) {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === '/auth/me') return { data: ME }
    if (url === '/profile/me') {
      if (profile) return { data: profile }
      throw apiError(404, 'Aucun profil')
    }
    throw new Error(`unexpected GET ${url}`)
  })
}

function savedResponse(profile: unknown, source = 'manual') {
  return {
    data: { profile, source, cv_document_id: null, updated_at: '2026-11-21T10:00:00Z' },
  }
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/mon-profil']}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('US06 - saisie manuelle du profil', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.get).mockReset()
    vi.mocked(api.put).mockReset()
  })

  it('redirects to the login page when not logged in', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Se connecter' })).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalledWith('/profile/me')
  })

  describe('when logged in', () => {
    beforeEach(() => {
      localStorage.setItem('trustai.access_token', 'fake-token')
    })

    it('shows an empty form when the candidate has no profile yet', async () => {
      mockGet(null)
      renderPage()

      expect(await screen.findByRole('heading', { name: 'Mon profil' })).toBeInTheDocument()
      expect(screen.getByLabelText('Nom complet')).toHaveValue('')
      expect(screen.getByLabelText('Langue du profil')).toHaveValue('fr')
      expect(screen.getByRole('button', { name: 'Ajouter une compétence' })).toBeInTheDocument()
      expect(api.put).not.toHaveBeenCalled()
    })

    it('prefills the form with an existing CV-generated profile', async () => {
      mockGet(CV_PROFILE)
      renderPage()

      expect(await screen.findByLabelText('Nom complet')).toHaveValue('Sarra Benali')
      expect(screen.getByLabelText('E-mail')).toHaveValue('sarra@example.fr')
      expect(screen.getAllByLabelText('Compétence')[0]).toHaveValue('Python')
      expect(screen.getByLabelText('Intitulé du poste')).toHaveValue('Développeuse')
      expect(screen.getByText(/Ce profil a été généré à partir de votre CV/)).toBeInTheDocument()
    })

    it('saves a manual profile using the common model without any CV', async () => {
      const user = userEvent.setup()
      mockGet(null)
      vi.mocked(api.put).mockImplementation(async (_url: string, body?: unknown) =>
        savedResponse(body),
      )
      renderPage()

      await user.type(await screen.findByLabelText('Nom complet'), 'Sarra Benali')
      await user.type(screen.getByLabelText('E-mail'), 'sarra@example.fr')
      await user.type(screen.getByLabelText('Téléphone'), '+216 20 000 000')
      await user.click(screen.getByRole('button', { name: 'Ajouter une compétence' }))
      await user.type(screen.getAllByLabelText('Compétence')[0], 'Python')
      await user.click(screen.getByRole('button', { name: 'Enregistrer mon profil' }))

      expect(await screen.findByText('Votre profil a bien été enregistré.')).toBeInTheDocument()
      // Saving must keep the candidate on the profile form, not bounce to the home page.
      expect(screen.getByRole('heading', { name: 'Mon profil' })).toBeInTheDocument()
      expect(screen.queryByText('API :')).not.toBeInTheDocument()
      expect(api.put).toHaveBeenCalledTimes(1)
      const [url, payload] = vi.mocked(api.put).mock.calls[0]
      expect(url).toBe('/profile/me')
      expect(payload).toMatchObject({
        schema_version: 1,
        language: 'fr',
        personal_info: {
          full_name: 'Sarra Benali',
          headline: null,
          email: 'sarra@example.fr',
          phone: '+216 20 000 000',
          location: null,
          links: [],
        },
        summary: null,
        skills: [{ name: 'Python', category: 'hard', level: null }],
        experiences: [],
        education: [],
        languages: [],
        certifications: [],
        projects: [],
      })
    })

    it('blocks an invalid e-mail before calling the API and shows the error', async () => {
      const user = userEvent.setup()
      mockGet(null)
      renderPage()

      await user.type(await screen.findByLabelText('E-mail'), 'pas-un-email')
      await user.click(screen.getByRole('button', { name: 'Enregistrer mon profil' }))

      expect(await screen.findByText('Adresse e-mail invalide')).toBeInTheDocument()
      expect(api.put).not.toHaveBeenCalled()
    })

    it('blocks a full name containing digits', async () => {
      const user = userEvent.setup()
      mockGet(null)
      renderPage()

      await user.type(await screen.findByLabelText('Nom complet'), 'Sarra123')
      await user.click(screen.getByRole('button', { name: 'Enregistrer mon profil' }))

      expect(
        await screen.findByText('Le nom complet ne doit contenir que des lettres'),
      ).toBeInTheDocument()
      expect(api.put).not.toHaveBeenCalled()
    })

    it('requires the Tunisian phone format', async () => {
      const user = userEvent.setup()
      mockGet(null)
      renderPage()

      await user.type(await screen.findByLabelText('Téléphone'), '12345678')
      await user.click(screen.getByRole('button', { name: 'Enregistrer mon profil' }))

      expect(await screen.findByText('Format attendu : +216 00 000 000')).toBeInTheDocument()
      expect(api.put).not.toHaveBeenCalled()
    })

    it('saves an analysed profile whose CV has a foreign phone and an initial', async () => {
      // Regression: the form must not block profiles coming from a CV (US05).
      const user = userEvent.setup()
      mockGet({
        ...CV_PROFILE,
        profile: {
          ...CV_PROFILE.profile,
          personal_info: {
            ...CV_PROFILE.profile.personal_info,
            full_name: 'S. Benali',
            phone: '+33 6 12 34 56 78',
          },
        },
      })
      vi.mocked(api.put).mockImplementation(async (_url: string, body?: unknown) =>
        savedResponse(body),
      )
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Enregistrer mon profil' }))

      expect(await screen.findByText('Votre profil a bien été enregistré.')).toBeInTheDocument()
      expect(vi.mocked(api.put).mock.calls[0][1]).toMatchObject({
        personal_info: { full_name: 'S. Benali', phone: '+33 6 12 34 56 78' },
      })
    })

    it('rejects an invalid date and a missing skill name', async () => {
      const user = userEvent.setup()
      mockGet(null)
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Ajouter une expérience' }))
      await user.type(screen.getByLabelText('Début'), 'mars 2021')
      await user.click(screen.getByRole('button', { name: 'Ajouter une compétence' }))
      await user.click(screen.getByRole('button', { name: 'Enregistrer mon profil' }))

      expect(await screen.findByText('Format attendu : AAAA ou AAAA-MM')).toBeInTheDocument()
      expect(screen.getAllByText('Compétence requis').length).toBeGreaterThan(0)
      expect(api.put).not.toHaveBeenCalled()
    })

    it("shows the API's message when the server rejects the profile", async () => {
      const user = userEvent.setup()
      mockGet(null)
      vi.mocked(api.put).mockRejectedValue(
        apiError(422, 'La date de fin est antérieure à la date de début'),
      )
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Enregistrer mon profil' }))

      expect(
        await screen.findByText('La date de fin est antérieure à la date de début'),
      ).toBeInTheDocument()
    })

    it('prevents a second save while the first one is pending', async () => {
      const user = userEvent.setup()
      mockGet(null)
      vi.mocked(api.put).mockReturnValue(new Promise(() => {}))
      renderPage()

      const submit = await screen.findByRole('button', { name: 'Enregistrer mon profil' })
      await user.click(submit)

      const pending = await screen.findByRole('button', { name: 'Enregistrement…' })
      expect(pending).toBeDisabled()
      await user.click(pending)
      await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1))
    })
  })
})
