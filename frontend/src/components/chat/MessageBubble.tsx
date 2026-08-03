import { memo, useState } from "react"
import { renderMarkdown } from "./MarkdownRenderer"

interface Message {
  id: number
  role: "user" | "bot"
  text: string
  timestamp: string
}

interface MessageBubbleProps {
  msg: Message
  msgIndex: number
  initials: string
  speakingMsgIdx: number | null
  onSpeakToggle: (idx: number, text: string) => void
}

function MessageBubbleInner({ msg, msgIndex, initials, speakingMsgIdx, onSpeakToggle }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isSpeaking = speakingMsgIdx === msgIndex

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard not available */ }
  }

  return (
    <div className={`flex gap-3 group ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-xs font-inter font-semibold ${
          msg.role === "user"
            ? "bg-surgical-blue/10 text-surgical-blue"
            : "bg-obsidian text-paper-white"
        }`}
      >
        {msg.role === "user" ? initials : "AI"}
      </div>

      <div className={`max-w-[85%] md:max-w-[70%] min-w-0 ${msg.role === "user" ? "text-right" : ""}`}>
        <div
          className={`rounded-[18px] px-4 py-3 min-w-0 break-words ${
            msg.role === "user"
              ? "bg-obsidian text-paper-white rounded-br-[6px]"
              : "bg-paper-white border border-outline-variant/30 text-obsidian rounded-bl-[6px]"
          }`}
        >
          {msg.role === "bot" ? (
            renderMarkdown(msg.text)
          ) : (
            <p className="text-sm font-inter leading-relaxed whitespace-pre-wrap">{msg.text}</p>
          )}
        </div>

        {msg.timestamp && (
          <div className={`flex items-center mt-1 ${msg.role === "user" ? "justify-end" : "justify-between"}`}>
            <p className={`text-xs text-slate font-inter ${msg.role === "bot" ? "text-left" : "text-right"}`}>
              {msg.timestamp}
            </p>
            {msg.role === "bot" && (
              <div className="flex items-center gap-1">
                <button
                  onClick={handleCopy}
                  title="Copy to clipboard"
                  className="w-7 h-7 rounded-md flex items-center justify-center text-slate hover:text-obsidian hover:bg-surface transition-colors"
                >
                  {copied ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  )}
                </button>
                <button
                  onClick={() => onSpeakToggle(msgIndex, msg.text)}
                  title={isSpeaking ? "Stop reading" : "Read aloud"}
                  className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${
                    isSpeaking
                      ? "text-error hover:text-error/80 bg-error/10"
                      : "text-slate hover:text-obsidian hover:bg-surface"
                  }`}
                >
                  {isSpeaking ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="6" y="4" width="4" height="16" />
                      <rect x="14" y="4" width="4" height="16" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                    </svg>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export const MessageBubble = memo(MessageBubbleInner)
