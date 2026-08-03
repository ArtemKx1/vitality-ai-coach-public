import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AuthProvider } from "@/components/auth-provider"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ConnectGarminPage } from "@/pages/ConnectGarminPage"
import { AuthCallbackPage } from "@/pages/AuthCallbackPage"
import { LoginPage } from "@/pages/LoginPage"
import { SignupPage } from "@/pages/SignupPage"
import { SetupPage } from "@/pages/SetupPage"
import { AppPage } from "@/pages/AppPage"
import { TermsPage } from "@/pages/TermsPage"
import { PrivacyPage } from "@/pages/PrivacyPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

export default function App() {
  const base = import.meta.env.VITE_BASE || "/"
  return (
    <BrowserRouter basename={base}>
      <AuthProvider>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/connect-garmin" element={<ConnectGarminPage />} />
            <Route path="/app" element={<AppPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  )
}
