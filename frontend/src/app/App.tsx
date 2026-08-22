import { Navigate, Route, Routes } from 'react-router-dom'
import { PrototypeBanner } from '../components/PrototypeBanner'
import { AppHeader } from '../components/AppHeader'
import { LandingPage } from '../features/landing/LandingPage'
import { AuthProvider } from '../features/auth/AuthContext'
import { RedirectIfAuthenticated, RequireAuth } from '../features/auth/RequireAuth'
import { LoginPage } from '../features/auth/LoginPage'
import { SignupPage } from '../features/auth/SignupPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { ApplicantTypePage } from '../features/enrolment/ApplicantTypePage'
import { PersonalDetailsPage } from '../features/enrolment/PersonalDetailsPage'
import { AddressPage } from '../features/enrolment/AddressPage'
import { DocumentRequirementsPage } from '../features/enrolment/DocumentRequirementsPage'
import { ReviewPage } from '../features/enrolment/ReviewPage'
import { PreparedPage } from '../features/enrolment/PreparedPage'

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
              <Route path="/enrolment/new" element={<ApplicantTypePage />} />
              <Route path="/enrolment/:id/personal" element={<PersonalDetailsPage />} />
              <Route path="/enrolment/:id/address" element={<AddressPage />} />
              <Route path="/enrolment/:id/documents" element={<DocumentRequirementsPage />} />
              <Route path="/enrolment/:id/review" element={<ReviewPage />} />
              <Route path="/enrolment/:id/prepared" element={<PreparedPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </AuthProvider>
  )
}
