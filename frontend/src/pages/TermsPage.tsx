import { Link } from "react-router-dom"
import { SEO } from "@/components/SEO"

export function TermsPage() {
  return (
    <div className="min-h-screen bg-paper-white">
      <SEO
        title="Terms of Service"
        description="Terms of Service for Vitality AI Coach. Read our terms and conditions for using our AI health and fitness coaching platform."
        canonical="/terms"
        noindex
      />
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-inter text-charcoal hover:text-obsidian transition-colors mb-8">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          Back to home
        </Link>
        <h1 className="font-inter font-bold text-[36px] leading-[1.15] tracking-[-0.03em] text-obsidian mb-8">Terms of Service</h1>
        <div className="font-inter text-[15px] leading-relaxed text-charcoal space-y-5">
          <p>Last updated: June 2026</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">1. Acceptance of Terms</h2>
          <p>By accessing or using Vitality AI Coach, you agree to be bound by these Terms of Service. If you do not agree, do not use the service.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">2. Description of Service</h2>
          <p>Vitality AI Coach provides AI-powered coaching insights based on data synced from your Garmin Connect account. The service is for informational and educational purposes only.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">3. User Responsibilities</h2>
          <p>You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account. You agree to provide accurate and complete information when creating your account.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">4. Data Sync & Privacy</h2>
          <p>By connecting your Garmin Connect account, you authorize us to sync your health and activity data. Your Garmin credentials are encrypted at rest and used solely for data synchronization. See our Privacy Policy for details.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">5. Medical Disclaimer</h2>
          <p>Vitality AI Coach is not a medical device and does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional regarding any health concerns.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">6. Limitation of Liability</h2>
          <p>Vitality AI Coach is provided "as is" without warranties of any kind. We are not liable for any damages arising from your use of the service.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">7. Changes to Terms</h2>
          <p>We reserve the right to modify these terms at any time. Changes will be posted on this page with an updated date.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">8. Contact</h2>
          <p>For questions about these terms, please contact artem.kx@proton.me.</p>
        </div>
      </div>
    </div>
  )
}
