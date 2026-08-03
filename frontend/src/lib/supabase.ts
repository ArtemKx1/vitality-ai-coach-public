import { createClient } from "@supabase/supabase-js"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// Supabase is OPTIONAL — it only powers Google OAuth / magic-link on the web.
// Self-hosted instances without it get email/password auth only, and the
// social login section is hidden. The stub keeps the rest of the app working.
export const supabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)

const noopResolve = async () => ({ data: { session: null }, error: null })

export const supabase = supabaseConfigured
  ? createClient(supabaseUrl!, supabaseAnonKey!, { auth: { flowType: "pkce" } })
  : ({
      auth: {
        getSession: noopResolve,
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        signInWithOAuth: noopResolve,
        signInWithOtp: noopResolve,
        signInWithIdToken: noopResolve,
        signInWithPassword: noopResolve,
        signUp: noopResolve,
        signOut: noopResolve,
      },
    } as unknown as ReturnType<typeof createClient>)
