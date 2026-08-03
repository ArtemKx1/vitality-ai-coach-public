import { Button } from "@/components/ui/button"
import { DeviceIcon } from "@/components/DeviceIcon"

interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

interface Device {
  display_name: string
  type_name: string | null
  last_synced_at: string
}

interface User {
  full_name?: string
  email?: string
  garmin_connected: boolean
  last_sync?: string | null
}

interface ChatSidebarProps {
  conversations: Conversation[]
  activeConvId: number | null
  convLoading: boolean
  user: User
  status: "ready" | "syncing" | "error"
  devices: Device[]
  lastSync: string | null
  onNewChat: () => void
  onSelectConversation: (id: number) => void
  onDeleteConversation: (id: number, e: React.MouseEvent) => void
  onSync: () => Promise<void>
  onConnectGarmin: () => void
  isOpen: boolean
  onClose: () => void
}

export function ChatSidebar({
  conversations,
  activeConvId,
  convLoading,
  user,
  status,
  devices,
  lastSync,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onSync,
  onConnectGarmin,
  isOpen,
  onClose,
}: ChatSidebarProps) {
  const initials = user.full_name
    ? user.full_name.split(" ").map((s: string) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase()
    : user.email?.[0].toUpperCase() ?? "U"

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={onClose} />
      )}
      <aside className={`fixed inset-y-0 left-0 z-50 w-72 flex flex-col border-r border-outline-variant/30 bg-paper-white transform transition-transform duration-200 ease-in-out md:relative md:translate-x-0 md:z-auto ${isOpen ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="p-4">
        <Button variant="default" className="w-full rounded-full h-10 text-sm gap-1.5" onClick={onNewChat}>
          + New Chat
        </Button>
      </div>

      <div className="px-4 mb-2">
        <p className="text-xs font-inter font-semibold text-slate uppercase tracking-wider">Conversations</p>
      </div>

      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        {convLoading ? (
          <p className="px-3 py-2 text-sm text-slate font-inter">Loading...</p>
        ) : conversations.length === 0 ? (
          <p className="px-3 py-2 text-sm text-slate font-inter">No conversations yet</p>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`w-full text-left px-3 py-2 text-sm font-inter rounded-lg transition-colors flex items-center justify-between group ${
                activeConvId === conv.id
                  ? "bg-surface text-obsidian font-medium"
                  : "text-charcoal hover:bg-surface"
              }`}
            >
              <span className="truncate">{conv.title}</span>
              <span
                onClick={(e) => onDeleteConversation(conv.id, e)}
                className="md:opacity-0 md:group-hover:opacity-100 text-slate hover:text-red-500 transition-opacity text-xs cursor-pointer shrink-0 ml-2 -mr-1 px-1 py-0.5"
              >
                ✕
              </span>
            </button>
          ))
        )}
      </nav>

      <div className="p-4 border-t border-outline-variant/30 space-y-3">
        {!user.garmin_connected && (
          <div className="mb-1 p-3 rounded-xl bg-surgical-blue/5 border border-surgical-blue/20">
            <p className="text-xs font-inter text-surgical-blue font-medium mb-1.5">Connect Garmin to get started</p>
            <button
              onClick={onConnectGarmin}
              className="text-xs font-inter font-semibold text-surgical-blue hover:underline"
            >
              Connect now →
            </button>
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-obsidian flex items-center justify-center">
            <span className="text-paper-white text-xs font-inter font-semibold">{initials}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-inter font-medium text-obsidian truncate">{user.full_name}</p>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${status === "syncing" ? "bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.6)]" : user.garmin_connected ? "bg-emerald-500" : "bg-slate-300"}`} />
              <p className="text-xs font-inter text-slate">
                {user.garmin_connected ? "Garmin connected" : "Garmin not connected"}
              </p>
            </div>
          </div>
        </div>

        {user.garmin_connected && devices.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-inter font-semibold text-obsidian/50 uppercase tracking-wider">Devices</p>
            {devices.map((d, i) => (
              <div key={i} className="flex items-center gap-2.5">
                <DeviceIcon deviceName={d.display_name} className="text-obsidian/60 shrink-0" />
                <span className="text-xs font-inter text-obsidian/80 font-medium truncate">{d.display_name}</span>
              </div>
            ))}
          </div>
        )}

        {user.garmin_connected && (
          <div className="pt-1 space-y-2">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 rounded-full text-xs h-8"
                onClick={onSync}
                disabled={status === "syncing"}
              >
                {status === "syncing" ? "Syncing..." : "Sync Now"}
              </Button>
            </div>
            {(lastSync ?? user.last_sync) && (
              <p className="text-[11px] font-inter text-charcoal/60 text-center">
                Last sync: {new Date(lastSync ?? user.last_sync!).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </p>
            )}
          </div>
        )}
      </div>
    </aside>
    </>
  )
}
