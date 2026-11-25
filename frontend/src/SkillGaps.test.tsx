import { render, screen } from '@testing-library/react'
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

function notFound() {
  return Object.assign(new Error('not found'), { isAxiosError: true, response: { status: 404 } })
}

function signIn() {
  localStorage.setItem('trustai.access_token', 'fake-token')
}

describe('US33 - skill gaps', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    localStorage.clear()
  })

  it('redirects an anonymous visitor to the login page', async () => {
    renderApp('/competences-manquantes')
    expect(await screen.findByRole('heading', { name: 'Se connecter' })).toBeInTheDocument()
  })

  it('invites the candidate to create a profile when they have none', async () => {
    signIn()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') return { data: ME }
      if (url === '/matching/skill-gaps') throw notFound()
      throw new Error(`unexpected GET ${url}`)
    })

    renderApp('/competences-manquantes')

    expect(
      await screen.findByText(
        'Créez votre profil candidat pour identifier vos compétences manquantes.',
      ),
    ).toBeInTheDocument()
  })

  it('invites the candidate to analyse an offer when none has been analysed yet', async () => {
    signIn()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') return { data: ME }
      if (url === '/matching/skill-gaps') return { data: { skills: [], offers_considered: 0 } }
      throw new Error(`unexpected GET ${url}`)
    })

    renderApp('/competences-manquantes')

    expect(
      await screen.findByText(
        'Analysez au moins une offre pour identifier vos compétences manquantes.',
      ),
    ).toBeInTheDocument()
  })

  it('shows a congratulatory message when nothing is missing', async () => {
    signIn()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') return { data: ME }
      if (url === '/matching/skill-gaps') return { data: { skills: [], offers_considered: 3 } }
      throw new Error(`unexpected GET ${url}`)
    })

    renderApp('/competences-manquantes')

    expect(await screen.findByText(/Aucune compétence manquante/)).toBeInTheDocument()
  })

  it('ranks the most frequently missing skill first', async () => {
    signIn()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') return { data: ME }
      if (url === '/matching/skill-gaps') {
        return {
          data: {
            offers_considered: 2,
            skills: [
              { name: 'Java', category: 'hard', missing_in_offers: 2 },
              { name: 'AWS', category: 'hard', missing_in_offers: 1 },
            ],
          },
        }
      }
      throw new Error(`unexpected GET ${url}`)
    })

    renderApp('/competences-manquantes')

    expect(await screen.findByText('Java')).toBeInTheDocument()
    expect(screen.getByText('manque dans 2/2 offres')).toBeInTheDocument()
    expect(screen.getByText('AWS')).toBeInTheDocument()
    expect(screen.getByText('manque dans 1/2 offres')).toBeInTheDocument()
  })
})
