import { type ReactNode } from "react"
import { Link } from "react-router-dom"

import { SEO } from "@/components/SEO"
import { AuthSidePanel } from "@/components/auth/AuthSidePanel"
import { AuthSocialSection } from "@/components/auth/AuthSocialSection"

interface AuthLayoutProps {
  title: string
  description: string
  canonical: string
  activeTab: "login" | "signup"
  children: ReactNode
}

export function AuthLayout({ title, description, canonical, activeTab, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-paper-white flex flex-col lg:flex-row w-full">
      <SEO title={title} description={description} canonical={canonical} />
      <AuthSidePanel />
      <div className="flex-1 flex flex-col justify-center items-center p-6 lg:p-10 bg-paper-white relative min-h-0 overflow-y-auto">
        <Link to="/" className="absolute top-6 left-6 flex items-center gap-1.5 text-sm font-inter text-charcoal hover:text-obsidian transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          Back to home
        </Link>

        <div className="w-full max-w-md bg-paper-white rounded-3xl p-8 shadow-[0_4px_24px_rgba(16,55,132,0.03),0_1px_3px_rgba(16,55,132,0.02)] border border-outline-variant/20 relative z-10">
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-full bg-obsidian flex items-center justify-center">
                <span className="text-paper-white text-xs font-inter font-bold">V</span>
              </div>
              <span className="font-inter font-semibold text-sm text-obsidian">Vitality AI Coach</span>
            </div>
          </div>

          <div className="bg-surface-container-low p-1 rounded-full flex mb-8 w-full max-w-[280px] mx-auto border border-outline-variant/30">
            <Link
              to="/login"
              className={`flex-1 inline-flex items-center justify-center py-2 px-4 rounded-full font-inter text-sm font-semibold transition-all text-center leading-none ${
                activeTab === "login"
                  ? "bg-paper-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] text-primary"
                  : "text-charcoal hover:text-primary"
              }`}
            >
              Log In
            </Link>
            <Link
              to="/signup"
              className={`flex-1 inline-flex items-center justify-center py-2 px-4 rounded-full font-inter text-sm font-semibold transition-all text-center leading-none ${
                activeTab === "signup"
                  ? "bg-paper-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] text-primary"
                  : "text-charcoal hover:text-primary"
              }`}
            >
              Create Account
            </Link>
          </div>

          {children}

          <AuthSocialSection />
        </div>
      </div>
    </div>
  )
}
