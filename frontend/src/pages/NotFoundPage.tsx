import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-bold">Page introuvable</h1>
      <Link to="/" className="text-blue-600 underline">
        Retour à l'accueil
      </Link>
    </section>
  )
}
