import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `rounded-lg px-3 py-1.5 font-medium transition-colors ${
    isActive
      ? 'bg-brand-50 text-brand-700'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`
}

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
        <nav className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <Link to="/" className="text-lg font-bold text-brand-700">
            TrustAI
          </Link>
          {!isLoading && (
            <div className="flex flex-wrap items-center gap-1 text-sm">
              {user ? (
                <>
                  <NavLink to="/tableau-de-bord" className={navLinkClass}>
                    Tableau de bord
                  </NavLink>
                  <NavLink to="/mon-cv" className={navLinkClass}>
                    Mon CV
                  </NavLink>
                  <NavLink to="/mon-profil" className={navLinkClass}>
                    Mon profil
                  </NavLink>
                  <NavLink to="/offres" className={navLinkClass}>
                    Mes offres
                  </NavLink>
                  <NavLink to="/offres/nouvelle" className={navLinkClass}>
                    Ajouter une offre
                  </NavLink>
                  <NavLink to="/compte" className={navLinkClass}>
                    Mon compte
                  </NavLink>
                  <span className="mx-1 hidden h-5 w-px bg-slate-200 sm:block" aria-hidden />
                  <span className="hidden px-1 text-slate-500 sm:inline">{user.email}</span>
                  <button
                    onClick={handleLogout}
                    className="rounded-lg px-3 py-1.5 font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
                  >
                    Se déconnecter
                  </button>
                </>
              ) : (
                <>
                  <NavLink to="/connexion" className={navLinkClass}>
                    Connexion
                  </NavLink>
                  <NavLink to="/inscription" className={navLinkClass}>
                    Inscription
                  </NavLink>
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
