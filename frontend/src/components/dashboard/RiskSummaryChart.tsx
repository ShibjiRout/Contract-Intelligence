import type { Contract, RiskCategory } from '../../types'

interface Props {
  contracts: Contract[]
}

const RISK_CONFIG: { level: RiskCategory | 'UNKNOWN'; label: string; bg: string; text: string; border: string }[] = [
  { level: 'GREEN', label: 'Low Risk', bg: 'bg-emerald-50/90', text: 'text-emerald-800', border: 'border-emerald-200' },
  { level: 'AMBER', label: 'Medium Risk', bg: 'bg-amber-50/90', text: 'text-amber-800', border: 'border-amber-200' },
  { level: 'RED', label: 'High Risk', bg: 'bg-red-50/90', text: 'text-red-800', border: 'border-red-200' },
  { level: 'UNKNOWN', label: 'Unknown', bg: 'bg-white/90', text: 'text-slate-600', border: 'border-slate-200' },
]

export default function RiskSummaryChart({ contracts }: Props) {
  const counts = contracts.reduce<Record<string, number>>(
    (acc, c) => {
      const risk = c.final_risk ?? 'UNKNOWN'
      acc[risk] = (acc[risk] ?? 0) + 1
      return acc
    },
    { GREEN: 0, AMBER: 0, RED: 0, UNKNOWN: 0 }
  )

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {RISK_CONFIG.map(({ level, label, bg, text, border }) => (
        <div
          key={level}
          className={`rounded-xl border ${border} ${bg} px-4 py-4 text-center shadow-sm premium-card-hover`}
        >
          <p className={`text-3xl font-bold ${text}`}>{counts[level]}</p>
          <p className={`text-xs font-medium mt-1 ${text}`}>{label}</p>
        </div>
      ))}
    </div>
  )
}
