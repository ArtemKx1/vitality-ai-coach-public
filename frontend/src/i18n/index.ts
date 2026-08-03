import en from "./en.json"

export type Locale = "en"

const messages: Record<Locale, Record<string, string>> = { en }

let currentLocale: Locale = "en"

export function setLocale(locale: Locale) {
  currentLocale = locale
}

export function t(key: string, params?: Record<string, string>): string {
  let text = messages[currentLocale]?.[key] || key
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, v)
    }
  }
  return text
}

export { messages }
