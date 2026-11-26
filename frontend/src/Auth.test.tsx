import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'

vi.mock('./lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
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

describe('US01 - authentication', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('registers a candidate then logs them in automatically', async () => {
    const user = userEvent.setup()
    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === '/auth/register') {
        return { data: { id: '1', email: 'new@example.com', full_name: null } }
      }
      if (url === '/auth/login') {
        return { data: { access_token: 'fake-token', token_type: 'bearer' } }
      }
      throw new Error(`unexpected POST ${url}`)
    })
    vi.mocked(api.get).mockResolvedValue({
      data: { id: '1', email: 'new@example.com', full_name: null },
    })

    renderApp('/inscription')

    await user.type(screen.getByLabelText('E-mail'), 'new@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'S3cret!23')
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }))

    await waitFor(() => expect(screen.getByText('new@example.com')).toBeInTheDocument())
    // US06: a new candidate starts at the CV screen, with manual entry available.
    expect(await screen.findByRole('heading', { name: 'Mon CV' })).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Remplir mon profil manuellement' }),
    ).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith(
      '/auth/register',
      expect.objectContaining({ email: 'new@example.com', password: 'S3cret!23' }),
    )
    expect(localStorage.getItem('trustai.access_token')).toBe('fake-token')
  })

  it('shows an error when the login credentials are rejected', async () => {
    const user = userEvent.setup()
    vi.mocked(api.post).mockRejectedValue(new Error('401'))

    renderApp('/connexion')

    await user.type(screen.getByLabelText('E-mail'), 'bad@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByText('E-mail ou mot de passe incorrect.')).toBeInTheDocument()
    expect(localStorage.getItem('trustai.access_token')).toBeNull()
  })

  it('logs an existing candidate in and lands on the dashboard', async () => {
    const user = userEvent.setup()
    const notFound = Object.assign(new Error('not found'), {
      isAxiosError: true,
      response: { status: 404 },
    })
    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === '/auth/login') {
        return { data: { access_token: 'fake-token', token_type: 'bearer' } }
      }
      throw new Error(`unexpected POST ${url}`)
    })
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/auth/me') {
        return { data: { id: '1', email: 'me@example.com', full_name: null } }
      }
      if (url === '/offers') return { data: [] }
      if (url === '/profile/me' || url === '/cv/me' || url === '/ats/me') throw notFound
      throw new Error(`unexpected GET ${url}`)
    })

    renderApp('/connexion')

    await user.type(screen.getByLabelText('E-mail'), 'me@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'S3cret!23')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('heading', { name: 'Tableau de bord' })).toBeInTheDocument()
  })

  it('restores the session from a stored token and can log out', async () => {
    const user = userEvent.setup()
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.get).mockResolvedValue({
      data: { id: '1', email: 'me@example.com', full_name: null },
    })

    renderApp('/')

    await waitFor(() => expect(screen.getByText('me@example.com')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Se déconnecter' }))

    expect(screen.getByText('Connexion')).toBeInTheDocument()
    expect(localStorage.getItem('trustai.access_token')).toBeNull()
  })
})
