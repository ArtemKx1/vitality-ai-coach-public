export function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center bg-obsidian text-paper-white text-xs font-inter font-semibold">
        AI
      </div>
      <div className="bg-paper-white border border-outline-variant/30 text-obsidian rounded-[18px] rounded-bl-[6px] px-4 py-3">
        <div className="flex gap-1.5 items-center py-0.5">
          <span className="w-2 h-2 bg-obsidian/30 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 bg-obsidian/30 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 bg-obsidian/30 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  )
}
