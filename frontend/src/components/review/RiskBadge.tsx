import type { RiskLevel } from '../../types'

interface Props {
  level: RiskLevel
  size?: 'sm' | 'md'
}

const CONFIG: Record<RiskLevel, { bg: string; text: string; label: string }> = {
  GREEN: { bg: 'bg-green-100', text: 'text-green-800', label: 'Green' },
  AMBER: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Amber' },
  RED: { bg: 'bg-red-100', text: 'text-red-800', label: 'Red' },
  UNKNOWN: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Unknown' },
}

export default function RiskBadge({ level, size = 'sm' }: Props) {
  const { bg, text, label } = CONFIG[level]
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'

  return (
    <span className={`inline-flex items-center font-medium rounded-full ${bg} ${text} ${sizeClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
        level === 'GREEN' ? 'bg-green-500' :
        level === 'AMBER' ? 'bg-amber-500' :
        level === 'RED' ? 'bg-red-500' : 'bg-gray-400'
      }`} />
      {label}
    </span>
  )
}
