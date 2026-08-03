import { cn } from "@/lib/utils"

interface GarminTextProps {
  className?: string
  color?: string
}

export function GarminText({ className, color = "#007CC3" }: GarminTextProps) {
  return (
    <span className={cn("inline-flex items-baseline", className)}>
      <span>Garmi</span>
      <span className="relative inline-flex">
        n
        <svg
          viewBox="0 0 12 8"
          fill={color}
          className="w-[0.6em] h-[0.4em] absolute -top-[0.5em] left-1/2 -translate-x-1/2"
          aria-hidden="true"
        >
          <path d="M6 0L12 8H0Z" />
        </svg>
      </span>
    </span>
  )
}
