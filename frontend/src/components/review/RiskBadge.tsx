import type { RiskCategory } from '../../types'

interface Props {
  level: RiskCategory | null | undefined
  size?: 'sm' | 'md'
}

const CONFIG: Record<string, { bg: string; text: string; ring: string; dot: string; label: string }> = {
  GREEN: { bg: 'bg-emerald-50', text: 'text-emerald-800', ring: 'ring-emerald-200', dot: 'bg-emerald-500', label: 'Green' },
  AMBER: { bg: 'bg-amber-50', text: 'text-amber-800', ring: 'ring-amber-200', dot: 'bg-amber-500', label: 'Amber' },
  RED: { bg: 'bg-red-50', text: 'text-red-800', ring: 'ring-red-200', dot: 'bg-red-500', label: 'Red' },
  UNKNOWN: { bg: 'bg-slate-100', text: 'text-slate-600', ring: 'ring-slate-200', dot: 'bg-slate-400', label: 'Unknown' },
}

export default function RiskBadge({ level, size = 'sm' }: Props) {
  const { bg, text, ring, dot, label } = CONFIG[level ?? 'UNKNOWN'] ?? CONFIG['UNKNOWN']
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'

  return (
    <span className={`inline-flex items-center font-semibold rounded-full ring-1 ${bg} ${text} ${ring} ${sizeClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dot}`} />
      {label}
    </span>
  )
}
