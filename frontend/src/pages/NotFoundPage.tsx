import { Link } from "react-router-dom"
import { VitalityLogo } from "@/components/VitalityLogo"

export function NotFoundPage() {
  return (
    <div className="bg-paper-white text-primary font-inter antialiased min-h-screen flex flex-col items-center justify-center px-6">
      <div className="max-w-lg text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <Link to="/" className="flex items-center gap-[10px]">
            <VitalityLogo showSubtitle showIcon />
          </Link>
        </div>

        {/* 404 */}
        <div className="space-y-4">
          <h1 className="font-inter font-semibold text-[120px] md:text-[160px] leading-[0.85] tracking-[-0.04em] text-obsidian">
            404
          </h1>
          <h2 className="font-inter font-semibold text-[28px] md:text-[36px] leading-[1.2] tracking-[-0.03em] text-primary">
            Page not found
          </h2>
          <p className="font-inter text-base md:text-lg text-charcoal max-w-md mx-auto leading-relaxed">
            The page you're looking for doesn't exist or has been moved. Let's get you back on track.
          </p>
        </div>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-3 px-8 py-4 rounded-full bg-obsidian text-paper-white font-inter text-base font-medium shadow-[0_2px_8px_rgba(16,55,132,0.03)] hover:opacity-90 transition-opacity"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Go to Vitality AI Coach
          </Link>
        </div>

        {/* Subtle footer text */}
        <p className="font-inter text-xs text-charcoal/60 pt-4">
          If you believe this is an error, please contact support.
        </p>
      </div>
    </div>
  )
}
