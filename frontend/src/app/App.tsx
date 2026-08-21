import { Route, Routes } from 'react-router-dom'
import { PrototypeBanner } from '../components/PrototypeBanner'
import { LandingPage } from '../features/landing/LandingPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <PrototypeBanner />
      <Routes>
        <Route path="/" element={<LandingPage />} />
      </Routes>
    </div>
  )
}
