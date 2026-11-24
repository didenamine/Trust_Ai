import type { ReactNode } from 'react'

/**
 * Shared split-screen frame for the login and sign-up pages: the form on the
 * left, a decorative brand-gradient panel (hidden on small screens) on the
 * right. Purely visual — no behavior.
 */
export default function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl md:grid-cols-2">
        <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-900 via-brand-800 to-slate-900 p-10 text-white md:flex">
          <div
            aria-hidden
            className="pointer-events-none absolute -top-16 -left-16 h-72 w-72 rounded-full bg-brand-400 opacity-60 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -right-14 -bottom-20 h-80 w-80 rounded-full bg-brand-300 opacity-40 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute top-1/3 right-1/4 h-40 w-40 rounded-full bg-white opacity-10 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.25)_1px,transparent_0)] [background-size:24px_24px]"
          />

          <p className="relative z-10 text-lg font-bold">TrustAI</p>

          <div className="relative z-10 space-y-3">
            <h2 className="text-2xl font-bold leading-snug text-balance">{title}</h2>
            <p className="text-sm text-brand-100">{subtitle}</p>
          </div>
        </div>

        <div className="p-8 sm:p-10">{children}</div>
      </div>
    </div>
  )
}
