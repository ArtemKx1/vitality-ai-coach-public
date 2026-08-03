import { Helmet } from "react-helmet-async"

const VITE_BASE = import.meta.env.VITE_BASE || "/"
const SITE_URL = `${import.meta.env.VITE_SITE_URL || ""}${VITE_BASE}`

interface SEOProps {
  title?: string
  description?: string
  canonical?: string
  ogImage?: string
  ogType?: string
  noindex?: boolean
  jsonLd?: object
}

export function SEO({
  title,
  description,
  canonical,
  ogImage = `${SITE_URL}vitality-ai-logo.png`,
  ogType = "website",
  noindex = false,
  jsonLd,
}: SEOProps) {
  const fullTitle = title ? `${title} | Vitality AI Coach` : "Vitality AI Coach — Your Personal AI Health & Fitness Coach"
  const url = canonical ? `${SITE_URL}${canonical}` : undefined

  return (
    <Helmet>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      {url && <link rel="canonical" href={url} />}
      {noindex && <meta name="robots" content="noindex, nofollow" />}

      {/* Open Graph */}
      <meta property="og:type" content={ogType} />
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:site_name" content="Vitality AI Coach" />
      <meta property="og:image" content={ogImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      {url && <meta property="og:url" content={url} />}

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={ogImage} />

      {/* Theme */}
      <meta name="theme-color" content="#779bc1" />

      {/* JSON-LD */}
      {jsonLd && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      )}
    </Helmet>
  )
}
