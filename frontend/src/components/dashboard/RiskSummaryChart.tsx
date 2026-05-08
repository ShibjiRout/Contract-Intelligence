import type { Contract, RiskLevel } from '../../types'

interface Props {
  contracts: Contract[]
}

const RISK_CONFIG: { level: RiskLevel; label: string; bg: string; text: string; border: string }[] = [
  { level: 'GREEN', label: 'Low Risk', bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  { level: 'AMBER', label: 'Medium Risk', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  { level: 'RED', label: 'High Risk', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  { level: 'UNKNOWN', label: 'Unknown', bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' },
]

export default function RiskSummaryChart({ contracts }: Props) {
  const counts = contracts.reduce<Record<RiskLevel, number>>(
    (acc, c) => {
      acc[c.final_risk] = (acc[c.final_risk] ?? 0) + 1
      return acc
    },
    { GREEN: 0, AMBER: 0, RED: 0, UNKNOWN: 0 }
  )

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {RISK_CONFIG.map(({ level, label, bg, text, border }) => (
        <div
          key={level}
          className={`rounded-lg border ${border} ${bg} px-4 py-4 text-center`}
        >
          <p className={`text-3xl font-bold ${text}`}>{counts[level]}</p>
          <p className={`text-xs font-medium mt-1 ${text}`}>{label}</p>
        </div>
      ))}
    </div>
  )
}
