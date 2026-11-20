import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, type AxiosResponse } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { api } from './lib/api'

vi.mock('./lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
}))

const ME = { id: '1', email: 'me@example.com', full_name: null }
const STORED_CV = {
  id: 'cv-1',
  original_filename: 'ancien-cv.pdf',
  content_type: 'application/pdf',
  size_bytes: 120 * 1024,
  uploaded_at: '2026-11-19T10:00:00Z',
}

function apiError(status: number, detail?: string) {
  return new AxiosError('error', String(status), undefined, undefined, {
    status,
    data: detail ? { detail } : {},
  } as AxiosResponse)
}

function mockGet(currentCV: typeof STORED_CV | null) {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === '/auth/me') return { data: ME }
    if (url === '/cv/me') {
      if (currentCV) return { data: currentCV }
      throw apiError(404, 'Aucun CV importé')
    }
    throw new Error(`unexpected GET ${url}`)
  })
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/mon-cv']}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function pdfFile(name = 'mon-cv.pdf', size?: number) {
  const file = new File(['%PDF-1.7'], name, { type: 'application/pdf' })
  if (size !== undefined) {
    Object.defineProperty(file, 'size', { value: size })
  }
  return file
}

describe('US03 - import du CV', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('redirects to the login page when not logged in', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Se connecter' })).toBeInTheDocument()
  })

  describe('when logged in', () => {
    beforeEach(() => {
      localStorage.setItem('trustai.access_token', 'fake-token')
    })

    it('uploads a PDF as multipart form data and shows it as the current CV', async () => {
      const user = userEvent.setup()
      mockGet(null)
      vi.mocked(api.post).mockResolvedValue({
        data: { ...STORED_CV, original_filename: 'mon-cv.pdf' },
      })
      renderPage()

      expect(await screen.findByText("Vous n'avez pas encore importé de CV.")).toBeInTheDocument()
      await user.upload(screen.getByLabelText('Fichier du CV'), pdfFile())
      await user.click(screen.getByRole('button', { name: 'Importer mon CV' }))

      expect(await screen.findByText('Votre CV a bien été importé.')).toBeInTheDocument()
      expect(screen.getByLabelText('CV actuel')).toHaveTextContent('mon-cv.pdf')

      const [url, body, config] = vi.mocked(api.post).mock.calls[0]
      expect(url).toBe('/cv')
      expect(body).toBeInstanceOf(FormData)
      expect((body as FormData).get('file')).toBeInstanceOf(File)
      expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } })
    })

    it('shows the current CV and offers to replace it', async () => {
      mockGet(STORED_CV)
      renderPage()

      expect(await screen.findByLabelText('CV actuel')).toHaveTextContent('ancien-cv.pdf')
      expect(screen.getByRole('button', { name: 'Remplacer mon CV' })).toBeDisabled()
    })

    it('rejects a file that is not a PDF or DOCX before sending it', async () => {
      // applyAccept: false simulates a user picking "All files" in the file dialog.
      const user = userEvent.setup({ applyAccept: false })
      mockGet(null)
      renderPage()

      await user.upload(
        await screen.findByLabelText('Fichier du CV'),
        new File(['hello'], 'notes.txt', { type: 'text/plain' }),
      )

      expect(
        screen.getByText('Format non accepté : seuls les fichiers PDF et DOCX sont acceptés.'),
      ).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Importer mon CV' })).toBeDisabled()
      expect(api.post).not.toHaveBeenCalled()
    })

    it('rejects a file over the maximum size before sending it', async () => {
      const user = userEvent.setup()
      mockGet(null)
      renderPage()

      await user.upload(
        await screen.findByLabelText('Fichier du CV'),
        pdfFile('gros.pdf', 5 * 1024 * 1024 + 1),
      )

      expect(screen.getByText('Le fichier dépasse la taille maximale de 5 Mo.')).toBeInTheDocument()
      expect(api.post).not.toHaveBeenCalled()
    })

    it("shows the API's message when the server rejects the file", async () => {
      const user = userEvent.setup()
      mockGet(null)
      vi.mocked(api.post).mockRejectedValue(
        apiError(415, 'Format non accepté : le fichier doit être un PDF ou un DOCX valide'),
      )
      renderPage()

      await user.upload(await screen.findByLabelText('Fichier du CV'), pdfFile('faux.pdf'))
      await user.click(screen.getByRole('button', { name: 'Importer mon CV' }))

      await waitFor(() =>
        expect(
          screen.getByText('Format non accepté : le fichier doit être un PDF ou un DOCX valide.'),
        ).toBeInTheDocument(),
      )
      expect(screen.getByText("Vous n'avez pas encore importé de CV.")).toBeInTheDocument()
    })
  })
})
