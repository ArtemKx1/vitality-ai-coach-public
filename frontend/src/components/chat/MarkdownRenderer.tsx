import { useMemo } from "react"
import { marked } from "marked"
import DOMPurify from "dompurify"

marked.setOptions({
  breaks: true,
  gfm: true,
})

export function renderMarkdown(text: string) {
  const html = useMemo(() => {
    const raw = marked.parse(text) as string
    return DOMPurify.sanitize(raw)
  }, [text])

  return (
    <div
      className="prose prose-sm min-w-0 break-words prose-p:my-1 prose-pre:bg-cloud-gray prose-pre:p-3 prose-pre:rounded-xl prose-pre:overflow-x-auto prose-code:bg-cloud-gray prose-code:px-1 prose-code:rounded prose-code:text-sm prose-strong:font-semibold prose-a:text-surgical-blue prose-a:underline prose-ul:list-disc prose-ol:list-decimal prose-li:ml-4 prose-li:break-words [&_p]:text-sm [&_p]:leading-relaxed [&_p]:break-words [&_strong]:font-semibold [&_em]:italic [&_table]:w-full [&_table]:table-fixed [&_table]:border-collapse [&_th]:border [&_th]:border-outline-variant [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-semibold [&_th]:break-words [&_td]:border [&_td]:border-outline-variant [&_td]:px-2 [&_td]:py-1.5 [&_td]:break-words [&_td]:text-xs"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
