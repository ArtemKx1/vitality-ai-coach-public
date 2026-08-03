import { Link } from "react-router-dom"
import { SEO } from "@/components/SEO"

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-paper-white">
      <SEO
        title="Privacy Policy"
        description="Vitality AI Coach privacy policy. Learn how we collect, use, and protect your personal health and fitness data."
        canonical="/privacy"
        noindex
      />
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-inter text-charcoal hover:text-obsidian transition-colors mb-8">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          Back to home
        </Link>
        <h1 className="font-inter font-bold text-[36px] leading-[1.15] tracking-[-0.03em] text-obsidian mb-8">Privacy Policy</h1>
        <div className="font-inter text-[15px] leading-relaxed text-charcoal space-y-5">
          <p>Last updated: June 2026</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">1. Information We Collect</h2>
          <p>We collect information you provide when creating an account (name, email) and data synced from your Garmin Connect account (activity metrics, heart rate, sleep data, and other health-related information).</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">2. How We Use Your Information</h2>
          <p>Your data is used to generate AI-powered coaching insights, training recommendations, and recovery analysis. We do not sell your personal data to third parties.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">3. Data Encryption</h2>
          <p>Your Garmin Connect credentials are encrypted at rest using AES-256 encryption. All data transmitted between your device and our servers is protected via TLS encryption.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">4. Data Storage</h2>
          <p>Your data is stored securely on Supabase PostgreSQL with encryption at rest. We retain your data for as long as your account is active. You may request deletion of your data at any time.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">5. Third-Party Services</h2>
          <p>We integrate with Garmin Connect for data synchronization. Your data is subject to Garmin's privacy policy when transmitted through their services. We also use Supabase for database hosting and Google OAuth for authentication.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">6. Your Rights</h2>
          <p>You have the right to access, update, and delete your personal data. You can request data export or account deletion by contacting artem.kx@proton.me.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">7. Changes to This Policy</h2>
          <p>We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated date.</p>

          <h2 className="font-inter font-semibold text-xl text-obsidian mt-8 mb-2">8. Contact</h2>
          <p>For privacy-related inquiries, contact artem.kx@proton.me.</p>
        </div>
      </div>
    </div>
  )
}
