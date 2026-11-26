import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Wrap routes that need a signed-in candidate: anonymous visitors go to the login page. */
export default function RequireAuth() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <p className="text-slate-500">Chargement…</p>
  if (!user) return <Navigate to="/connexion" replace />
  return <Outlet />
}
