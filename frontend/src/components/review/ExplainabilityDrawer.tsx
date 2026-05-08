import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { clausesApi } from '../../api/clauses'
import RiskBadge from './RiskBadge'
import type { ContributingFactor } from '../../types'

const IMPACT_COLORS: Record<ContributingFactor['impact'], string> = {
  HIGH: 'text-red-600 bg-red-50',
  MEDIUM: 'text-amber-600 bg-amber-50',
  LOW: 'text-green-600 bg-green-50',
}

interface Props {
  clauseId: string
}

export default function ExplainabilityDrawer({ clauseId }: Props) {
  const [open, setOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['explanation', clauseId],
    queryFn: () => clausesApi.getExplanation(clauseId).then((r) => r.data),
    enabled: open,
  })

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 text-sm text-indigo-600 border border-indigo-200 px-3 py-1.5 rounded-md hover:bg-indigo-50 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Explain Risk
      </button>

      {/* Overlay */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/30" />
        </div>
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-[480px] bg-white z-50 shadow-2xl transform transition-transform duration-300 ${
          open ? 'translate-x-0' : 'translate-x-full'
        } flex flex-col`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">Risk Explanation</h2>
          <button
            onClick={() => setOpen(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {isLoading && (
            <div className="flex items-center justify-center h-32">
              <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {data && (
            <>
              {data.degraded_mode && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
                  <p className="font-semibold mb-1">Degraded Mode Active</p>
                  <p>Some analysis sources failed. Results may be incomplete.</p>
                  {data.failed_sources.length > 0 && (
                    <p className="mt-1 text-xs text-amber-700">
                      Failed: {data.failed_sources.join(', ')}
                    </p>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Overall Risk</p>
                  <RiskBadge level={data.overall_risk} size="md" />
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500 mb-1">Risk Score</p>
                  <p className="text-2xl font-bold text-gray-900">{data.score.toFixed(1)}</p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Contributing Factors</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b border-gray-100">
                        <th className="text-left pb-2 font-medium">Source</th>
                        <th className="text-left pb-2 font-medium">Finding</th>
                        <th className="text-right pb-2 font-medium">Weight</th>
                        <th className="text-right pb-2 font-medium">Impact</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {data.contributing_factors.map((factor, idx) => (
                        <tr key={idx}>
                          <td className="py-2 text-gray-600 pr-2">{factor.source}</td>
                          <td className="py-2 text-gray-700 pr-2">{factor.finding}</td>
                          <td className="py-2 text-right text-gray-600">{factor.weight.toFixed(2)}</td>
                          <td className="py-2 text-right">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${IMPACT_COLORS[factor.impact]}`}>
                              {factor.impact}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {data.missing_clauses.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Missing Clauses</h3>
                  <ul className="space-y-1">
                    {data.missing_clauses.map((clause, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="text-red-400 mt-0.5">•</span>
                        {clause}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.conflicts.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Conflicts</h3>
                  <ul className="space-y-1">
                    {data.conflicts.map((conflict, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="text-amber-500 mt-0.5">!</span>
                        {conflict}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}
