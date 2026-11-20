import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout() {
  const { user, isLoading, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold">
            TrustAI
          </Link>
          {!isLoading && (
            <div className="flex items-center gap-4 text-sm">
              {user ? (
                <>
                  <Link to="/offres/nouvelle" className="text-blue-600 underline">
                    Ajouter une offre
                  </Link>
                  <span className="text-slate-600">{user.email}</span>
                  <button onClick={handleLogout} className="text-blue-600 underline">
                    Se déconnecter
                  </button>
                </>
              ) : (
                <>
                  <Link to="/connexion" className="text-blue-600 underline">
                    Connexion
                  </Link>
                  <Link to="/inscription" className="text-blue-600 underline">
                    Inscription
                  </Link>
                </>
              )}
            </div>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
