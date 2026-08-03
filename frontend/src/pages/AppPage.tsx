import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"

import { OnboardingModal } from "@/components/OnboardingModal"
import { SEO } from "@/components/SEO"
import { ChatSidebar } from "@/components/chat/ChatSidebar"
import { MessageBubble } from "@/components/chat/MessageBubble"
import { Lobby } from "@/components/chat/Lobby"
import { Suggestions } from "@/components/chat/Suggestions"
import { ChatInput } from "@/components/chat/ChatInput"
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator"
import { DeleteConfirmModal } from "@/components/chat/DeleteConfirmModal"
import { useAuth, apiFetch, type User } from "@/lib/auth"

interface Message {
  id: number
  role: "user" | "bot"
  text: string
  timestamp: string
}

interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

interface HealthRange {
  earliest_date: string | null
  latest_date: string | null
  total_days: number
  backfill: {
    in_progress: boolean
    completed: number
    total: number
    percent: number
  } | null
}

export function AppPage() {
  const { user, isLoading, logout, updateUser } = useAuth()
  const navigate = useNavigate()

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [status, setStatus] = useState<"ready" | "syncing" | "error">("ready")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConvId, setActiveConvId] = useState<number | null>(null)
  const [convLoading, setConvLoading] = useState(true)
  const [devices, setDevices] = useState<{ display_name: string; type_name: string | null; last_synced_at: string }[]>([])
  const [lastSync, setLastSync] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [healthRange, setHealthRange] = useState<HealthRange | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [speakingMsgIdx, setSpeakingMsgIdx] = useState<number | null>(null)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const messagesOffsetRef = useRef(0)

  const chatRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const ttsAbortRef = useRef<AbortController | null>(null)
  const activeConvRef = useRef<number | null>(null)
  const msgCountRef = useRef(0)
  const prevStreamingRef = useRef(false)
  activeConvRef.current = activeConvId
  const localMsgIdRef = useRef(-1)

  const authFetch = useCallback(async (path: string, options: RequestInit = {}): Promise<Response> => {
    const API_BASE = import.meta.env.VITE_API_URL || "/api/v1"
    const token = () => localStorage.getItem("token")
    const doReq = (tkn: string | null) =>
      fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tkn}`,
          ...(options.headers as Record<string, string>),
        },
      })
    const tkn = token()
    console.log(`[Garmin] authFetch ${path} - token: ${tkn ? tkn.substring(0, 20) + "..." : "null"}`)
    let res = await doReq(tkn)
    console.log(`[Garmin] authFetch ${path} - status: ${res.status}`)
    if (res.status === 401) {
      console.log(`[Garmin] authFetch ${path} - got 401, attempting refresh...`)
      try {
        const { data: { session } } = await (await import("@/lib/supabase")).supabase.auth.getSession()
        if (session?.user) {
          const refreshRes = await fetch(`${API_BASE}/auth/social-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: session.user.email,
              full_name: session.user.user_metadata?.full_name || session.user.email,
              provider: session.user.app_metadata?.provider || "google",
              token: session.access_token || "",
            }),
          })
          if (refreshRes.ok) {
            const { access_token: newTk } = await refreshRes.json()
            localStorage.setItem("token", newTk)
            res = await doReq(newTk)
          }
        }
      } catch { /* continue with original 401 */ }
    }
    return res
  }, [])

  useEffect(() => {
    if (!isLoading && !user) navigate("/login")
  }, [isLoading, user, navigate])

  useEffect(() => {
    const msgAdded = messages.length !== msgCountRef.current
    const streamEnded = prevStreamingRef.current && !streaming
    if (msgAdded || streamEnded) {
      msgCountRef.current = messages.length
      if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
    prevStreamingRef.current = streaming
  }, [messages, streaming])

  useEffect(() => {
    if (!healthRange?.backfill?.in_progress) return
    const interval = setInterval(() => {
      apiFetch<HealthRange>("/health/range").then(setHealthRange).catch(() => {})
    }, 5000)
    return () => clearInterval(interval)
  }, [healthRange?.backfill?.in_progress, apiFetch])

  const loadConversations = useCallback(async () => {
    try {
      const convs = await apiFetch<Conversation[]>("/chat/conversations")
      console.log("[Garmin] Conversations loaded:", convs.length, convs)
      setConversations(convs)
    } catch (e) {
      console.error("[Garmin] Failed to load conversations:", e)
    }
    setConvLoading(false)
  }, [apiFetch])

  useEffect(() => {
    if (!user) return
    console.log("[Garmin] AppPage useEffect - user:", user.id, user.email, "token:", localStorage.getItem("token")?.substring(0, 20) + "...")
    if (!user.onboarding_completed) {
      setShowOnboarding(true)
    }
    loadConversations()
    apiFetch<any[]>("/devices").then((d) => { console.log("[Garmin] Devices:", d.length); setDevices(d) }).catch((e) => console.error("[Garmin] Devices error:", e))
    if (user.garmin_connected) {
      apiFetch<HealthRange>("/health/range").then((r) => { console.log("[Garmin] Health range:", r); setHealthRange(r) }).catch((e) => console.error("[Garmin] Health range error:", e))
    }
  }, [user, loadConversations, apiFetch])

  useEffect(() => {
    if (!user?.garmin_connected) return
    const sync = () => {
      console.log("[Garmin] Starting sync...")
      authFetch("/sync?days=2", { method: "POST" }).then((res) => {
        console.log("[Garmin] Sync response:", res.status, res.ok)
        if (res.ok) {
          res.json().then((data) => console.log("[Garmin] Sync data:", data)).catch(() => {})
          apiFetch<any[]>("/devices").then(setDevices).catch(() => {})
          setLastSync(new Date().toISOString())
        } else {
          res.text().then((t) => console.error("[Garmin] Sync error body:", t)).catch(() => {})
        }
      }).catch((e) => console.error("[Garmin] Sync failed:", e))
    }
    const id = setInterval(sync, 15 * 60 * 1000)
    return () => clearInterval(id)
  }, [user?.garmin_connected, apiFetch, authFetch])

  const loadMessages = useCallback(async (convId: number) => {
    setMessagesLoading(true)
    try {
      const msgs = await apiFetch<{ id: number; role: string; content: string; created_at: string }[]>(
        `/chat/conversations/${convId}/messages?offset=0&limit=50`
      )
      const formatted: Message[] = msgs.map((m) => ({
        id: m.id,
        role: (m.role === "assistant" ? "bot" : m.role) as "user" | "bot",
        text: m.content,
        timestamp: new Date(m.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      }))
      setMessages(formatted)
      messagesOffsetRef.current = msgs.length
      setHasMoreMessages(msgs.length === 50)
      setActiveConvId(convId)
    } catch { /* ignore */ }
    setMessagesLoading(false)
  }, [apiFetch])

  const loadMoreMessages = useCallback(async () => {
    if (!hasMoreMessages || activeConvId === null) return
    setMessagesLoading(true)
    try {
      const msgs = await apiFetch<{ id: number; role: string; content: string; created_at: string }[]>(
        `/chat/conversations/${activeConvId}/messages?offset=${messagesOffsetRef.current}&limit=50`
      )
      if (msgs.length === 0) {
        setHasMoreMessages(false)
        return
      }
      const formatted: Message[] = msgs.map((m) => ({
        id: m.id,
        role: (m.role === "assistant" ? "bot" : m.role) as "user" | "bot",
        text: m.content,
        timestamp: new Date(m.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      }))
      setMessages((prev) => [...formatted, ...prev])
      messagesOffsetRef.current += msgs.length
      if (msgs.length < 50) setHasMoreMessages(false)
    } catch { /* ignore */ }
    setMessagesLoading(false)
  }, [hasMoreMessages, activeConvId, apiFetch])

  const newChat = () => {
    setActiveConvId(null)
    setMessages([
      {
        id: 0,
        role: "bot",
        text: "Hi! I'm your AI coach. Ask me anything about your Garmin data.",
        timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      },
    ])
    setSuggestions([])
    setSidebarOpen(false)
  }

  const speakingMsgIdxRef = useRef(speakingMsgIdx)
  speakingMsgIdxRef.current = speakingMsgIdx

  const handleSpeakToggle = useCallback(async (idx: number, text: string) => {
    ttsAbortRef.current?.abort()
    audioRef.current?.pause()
    audioRef.current = null

    if (speakingMsgIdxRef.current === idx) {
      setSpeakingMsgIdx(null)
      return
    }

    const controller = new AbortController()
    ttsAbortRef.current = controller
    setSpeakingMsgIdx(idx)

    try {
      const res = await authFetch("/tts", {
        method: "POST",
        body: JSON.stringify({ text }),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error("TTS failed")
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setSpeakingMsgIdx(null); URL.revokeObjectURL(url); audioRef.current = null }
      audio.onerror = () => { setSpeakingMsgIdx(null); URL.revokeObjectURL(url); audioRef.current = null }
      await audio.play()
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return
      console.error("TTS error:", e)
      setSpeakingMsgIdx(null)
    }
  }, [])

  const deleteConv = async (convId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setSidebarOpen(false)
    setDeleteConfirmId(convId)
  }

  const confirmDelete = async () => {
    if (deleteConfirmId === null) return
    try {
      await apiFetch(`/chat/conversations/${deleteConfirmId}`, { method: "DELETE" })
      setConversations((prev) => prev.filter((c) => c.id !== deleteConfirmId))
      if (activeConvId === deleteConfirmId) {
        setActiveConvId(null)
        setMessages([])
      }
    } catch { /* ignore */ }
    setDeleteConfirmId(null)
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || streaming) return

    localMsgIdRef.current -= 1
    const msgId = localMsgIdRef.current
    const userMsg: Message = {
      id: msgId,
      role: "user",
      text,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setStreaming(true)
    setSuggestions([])

    try {
      const res = await authFetch("/chat/stream", {
        method: "POST",
        body: JSON.stringify({ message: text, days: 14, conversation_id: activeConvRef.current }),
      })
      if (!res.ok) throw new Error(await res.text())

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let fullText = ""
      let newConvId: number | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6)
            if (payload === "[DONE]") continue
            try {
              const data = JSON.parse(payload)
              if (data.token) {
                fullText += data.token
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last && last.role === "bot" && !last.timestamp) {
                    updated[updated.length - 1] = { ...last, text: fullText }
                  } else {
                    updated.push({ id: msgId - 1, role: "bot", text: fullText, timestamp: "" })
                  }
                  return updated
                })
              }
              if (data.conversation_id) {
                newConvId = data.conversation_id
              }
              if (data.suggestions) {
                setSuggestions(data.suggestions)
              }
            } catch { /* skip */ }
          }
        }
      }

      if (newConvId) {
        setActiveConvId(newConvId)
      }
      loadConversations()

      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last && last.role === "bot" && !last.timestamp) {
          updated[updated.length - 1] = {
            ...last,
            timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
          }
        }
        return updated
      })
    } catch (err) {
      localMsgIdRef.current -= 1
      setMessages((prev) => [
        ...prev,
        {
          id: localMsgIdRef.current,
          role: "bot",
          text: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        },
      ])
    }
    setStreaming(false)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleOnboardingComplete = async (data: { goal: string; activities: string[]; fitness_level: string; equipment: string }) => {
    try {
      const updatedUser = await apiFetch<User>("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ ...data, activities: JSON.stringify(data.activities), onboarding_completed: true }),
      })
      updateUser(updatedUser)
    } catch { /* ignore */ }
    setShowOnboarding(false)
  }

  const handleSync = async () => {
    setStatus("syncing")
    try {
      console.log("[Garmin] Manual sync starting...")
      const res = await authFetch("/sync/now")
      console.log("[Garmin] Manual sync response:", res.status, res.ok)
      if (res.ok) {
        const data = await res.json()
        console.log("[Garmin] Manual sync data:", data)
        const devs = await apiFetch<any[]>("/devices")
        setDevices(devs)
        setLastSync(new Date().toISOString())
      } else {
        const err = await res.text()
        console.error("[Garmin] Manual sync error:", err)
      }
      setStatus(res.ok ? "ready" : "error")
    } catch (e) { console.error("[Garmin] Manual sync exception:", e); setStatus("error") }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-obsidian/20 border-t-obsidian rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="h-dvh bg-surface flex overflow-x-hidden">
      <SEO
        title="Chat"
        description="Your personal AI health and fitness coach. Chat with AI about your Garmin data."
        noindex
      />
      {showOnboarding && <OnboardingModal onComplete={handleOnboardingComplete} />}
      {deleteConfirmId !== null && (
        <DeleteConfirmModal
          onConfirm={confirmDelete}
          onCancel={() => setDeleteConfirmId(null)}
        />
      )}
      <ChatSidebar
        conversations={conversations}
        activeConvId={activeConvId}
        convLoading={convLoading}
        user={user}
        status={status}
        devices={devices}
        lastSync={lastSync}
        onNewChat={newChat}
        onSelectConversation={(id) => { loadMessages(id); setSidebarOpen(false) }}
        onDeleteConversation={deleteConv}
        onSync={handleSync}
        onConnectGarmin={() => navigate("/connect-garmin")}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-4 md:px-6 h-14 border-b border-outline-variant/30 bg-paper-white">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg hover:bg-surface transition-colors"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
            <h2 className="font-inter font-semibold text-base text-obsidian">Vitality AI Coach</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { logout().then(() => navigate("/")) }}
              className="text-sm text-charcoal hover:text-obsidian font-inter px-3 py-1 rounded-full hover:bg-surface transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        <div
          ref={chatRef}
          onScroll={(e) => {
            const el = e.currentTarget
            if (el.scrollTop === 0 && hasMoreMessages && !messagesLoading) {
              loadMoreMessages()
            }
          }}
          className="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-6 space-y-4 md:space-y-6"
        >
          {messagesLoading && hasMoreMessages && (
            <div className="flex justify-center py-2">
              <div className="w-5 h-5 border-2 border-obsidian/20 border-t-obsidian rounded-full animate-spin" />
            </div>
          )}
          {messages.length === 0 ? (
            messagesLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-8 h-8 border-2 border-obsidian/20 border-t-obsidian rounded-full animate-spin" />
              </div>
            ) : (
              <Lobby user={user} healthRange={healthRange} onSendMessage={sendMessage} />
            )
          ) : (
            <>
              {messages.map((msg, i) => (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  msgIndex={i}
                  initials={
                    user.full_name
                      ? user.full_name.split(" ").map((s: string) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase()
                      : user.email?.[0].toUpperCase() ?? "U"
                  }
                  speakingMsgIdx={speakingMsgIdx}
                  onSpeakToggle={handleSpeakToggle}
                />
              ))}
              {streaming && messages[messages.length - 1]?.role === "user" && (
                <ThinkingIndicator />
              )}
              {!streaming && suggestions.length > 0 && (
                <Suggestions userGarminConnected={user.garmin_connected} onSelect={sendMessage} suggestions={suggestions} />
              )}
            </>
          )}
        </div>

        <div className="px-4 md:px-6 py-4 border-t border-outline-variant/30 bg-paper-white shrink-0">
          <ChatInput
            input={input}
            onInputChange={setInput}
            onSend={() => sendMessage(input)}
            onKeyDown={handleKeyDown}
            streaming={streaming}
            inputRef={inputRef}
          />
        </div>
      </div>
    </div>
  )
}
