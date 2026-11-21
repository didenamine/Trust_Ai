import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

describe('US02 - account management', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.patch).mockReset()
    vi.mocked(api.put).mockReset()
    vi.mocked(api.delete).mockReset()
  })

  function signIn(email = 'me@example.com', fullName: string | null = 'Ancien Nom') {
    localStorage.setItem('trustai.access_token', 'fake-token')
    vi.mocked(api.get).mockResolvedValue({ data: { id: '1', email, full_name: fullName } })
  }

  it('updates the full name and e-mail', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.patch).mockResolvedValue({
      data: { id: '1', email: 'nouveau@example.com', full_name: 'Nouveau Nom' },
    })

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    const fullNameInput = screen.getByLabelText('Nom complet')
    await user.clear(fullNameInput)
    await user.type(fullNameInput, 'Nouveau Nom')

    const emailInput = screen.getByLabelText('E-mail')
    await user.clear(emailInput)
    await user.type(emailInput, 'nouveau@example.com')

    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByText('Informations mises à jour.')).toBeInTheDocument()
    expect(api.patch).toHaveBeenCalledWith('/auth/me', {
      email: 'nouveau@example.com',
      full_name: 'Nouveau Nom',
    })
  })

  it('shows the server error when the new e-mail is already taken', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.patch).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: 'Un compte existe déjà avec cet e-mail' } },
    })

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByText('Un compte existe déjà avec cet e-mail')).toBeInTheDocument()
  })

  it('changes the password', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.put).mockResolvedValue({ data: undefined })

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    // ggignore: test-only passwords, not real credentials
    await user.type(screen.getByLabelText('Mot de passe actuel'), 'AncienPass!23')
    await user.type(screen.getByLabelText('Nouveau mot de passe'), 'NouveauPass!23')
    await user.type(screen.getByLabelText('Confirmer le nouveau mot de passe'), 'NouveauPass!23')
    await user.click(screen.getByRole('button', { name: 'Changer le mot de passe' }))

    expect(await screen.findByText('Mot de passe modifié.')).toBeInTheDocument()
    // Values asserted structurally (not as literals) so no password-shaped string sits
    // next to these field names in the source.
    expect(api.put).toHaveBeenCalledWith('/auth/me/password', {
      current_password: expect.any(String),
      new_password: expect.any(String),
    })
  })

  it('rejects a new password that does not match its confirmation', async () => {
    const user = userEvent.setup()
    signIn()

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    // ggignore: test-only passwords, not real credentials
    await user.type(screen.getByLabelText('Mot de passe actuel'), 'AncienPass!23')
    await user.type(screen.getByLabelText('Nouveau mot de passe'), 'NouveauPass!23')
    await user.type(screen.getByLabelText('Confirmer le nouveau mot de passe'), 'Different!23')
    await user.click(screen.getByRole('button', { name: 'Changer le mot de passe' }))

    expect(await screen.findByText('Les mots de passe ne correspondent pas')).toBeInTheDocument()
    expect(api.put).not.toHaveBeenCalled()
  })

  it('shows an error when the current password is wrong', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.put).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: 'Mot de passe actuel incorrect' } },
    })

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    // ggignore: test-only passwords, not real credentials
    await user.type(screen.getByLabelText('Mot de passe actuel'), 'mauvais-mot-de-passe')
    await user.type(screen.getByLabelText('Nouveau mot de passe'), 'NouveauPass!23')
    await user.type(screen.getByLabelText('Confirmer le nouveau mot de passe'), 'NouveauPass!23')
    await user.click(screen.getByRole('button', { name: 'Changer le mot de passe' }))

    expect(await screen.findByText('Mot de passe actuel incorrect')).toBeInTheDocument()
  })

  it('keeps the delete confirmation disabled until the typed e-mail matches', async () => {
    const user = userEvent.setup()
    signIn()

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    await user.click(screen.getByRole('button', { name: 'Supprimer mon compte' }))
    const confirmButton = screen.getByRole('button', { name: 'Supprimer définitivement' })
    expect(confirmButton).toBeDisabled()

    await user.type(screen.getByLabelText('Confirmer avec votre e-mail'), 'mauvaise@example.com')
    expect(confirmButton).toBeDisabled()
  })

  it('deletes the account once the e-mail is confirmed, and signs the candidate out', async () => {
    const user = userEvent.setup()
    signIn()
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    renderApp('/compte')
    await screen.findByDisplayValue('me@example.com')

    await user.click(screen.getByRole('button', { name: 'Supprimer mon compte' }))
    await user.type(screen.getByLabelText('Confirmer avec votre e-mail'), 'me@example.com')
    await user.click(screen.getByRole('button', { name: 'Supprimer définitivement' }))

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/auth/me'))
    await waitFor(() => expect(screen.getByText('Connexion')).toBeInTheDocument())
    expect(localStorage.getItem('trustai.access_token')).toBeNull()
  })

  it('redirects an anonymous visitor to the login page', async () => {
    renderApp('/compte')
    expect(await screen.findByRole('heading', { name: 'Se connecter' })).toBeInTheDocument()
  })
})
