import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'

export function AppHeader() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
        <Link to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-saathi-600 text-sm font-bold text-white">
            US
          </span>
          <span className="text-sm font-semibold">UploadSaathi</span>
        </Link>

        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-slate-600 sm:inline">{user?.full_name}</span>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-saathi-600 hover:bg-saathi-50"
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-lg bg-saathi-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-saathi-700"
            >
              Get started
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}
