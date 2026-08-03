export function DeviceIcon({ deviceName, className }: { deviceName: string; className?: string }) {
  const name = deviceName.toLowerCase()

  let icon: string
  if (name.includes("edge")) {
    icon = "🚴"
  } else if (name.includes("forerunner") || name.includes("approach")) {
    icon = "🏃"
  } else if (name.includes("index")) {
    icon = "⚖️"
  } else if (name.includes("instinct")) {
    icon = "🧭"
  } else {
    icon = "⌚"
  }

  return <span className={className}>{icon}</span>
}
