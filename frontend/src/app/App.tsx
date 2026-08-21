import { Navigate, Route, Routes } from 'react-router-dom'
import { PrototypeBanner } from '../components/PrototypeBanner'
import { AppHeader } from '../components/AppHeader'
import { LandingPage } from '../features/landing/LandingPage'
import { AuthProvider } from '../features/auth/AuthContext'
import { RedirectIfAuthenticated, RequireAuth } from '../features/auth/RequireAuth'
import { LoginPage } from '../features/auth/LoginPage'
import { SignupPage } from '../features/auth/SignupPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'

export default function App() {
  return (
    <AuthProvider>
      <div className="flex min-h-screen flex-col">
        <PrototypeBanner />
        <AppHeader />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />

            <Route element={<RedirectIfAuthenticated />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
            </Route>

            <Route element={<RequireAuth />}>
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </AuthProvider>
  )
}
