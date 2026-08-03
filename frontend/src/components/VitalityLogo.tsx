import { cn } from "@/lib/utils"

interface VitalityLogoProps {
  className?: string
  showSubtitle?: boolean
  showIcon?: boolean
}

export function VitalityLogo({ className, showSubtitle = false, showIcon = false }: VitalityLogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      {showIcon && (
        <img
          src={`${import.meta.env.BASE_URL}vitality-ai-logo.png`}
          alt="Vitality AI Coach"
          className="h-[36px] w-[36px] object-contain rounded-[8px]"
        />
      )}
      <span className="inline-flex flex-col items-start gap-0">
        <span className="font-inter font-bold text-[20px] leading-[1.2] tracking-[-0.02em] text-primary whitespace-nowrap">
          Vitality AI Coach
        </span>
        {showSubtitle && (
          <span className="font-inter text-[11px] leading-none tracking-[0.02em] text-charcoal/60">
            for Garmin
          </span>
        )}
      </span>
    </span>
  )
}
