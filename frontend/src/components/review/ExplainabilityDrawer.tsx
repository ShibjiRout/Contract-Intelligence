import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { clausesApi } from '../../api/clauses'

interface Props {
  clauseId: string
}

export default function ExplainabilityDrawer({ clauseId }: Props) {
  const [open, setOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['recommendation', clauseId],
    queryFn: () => clausesApi.getRecommendation(clauseId).then((r) => r.data),
    enabled: open,
  })

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-secondary px-3 py-1.5">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        AI Analysis
      </button>

      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/30" />
        </div>
      )}

      <div className={`fixed top-0 right-0 h-full w-[500px] bg-white z-50 shadow-2xl transform transition-transform duration-300 ${
        open ? 'translate-x-0' : 'translate-x-full'
      } flex flex-col`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">AI Analysis</h2>
          <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {isLoading && (
            <div className="flex items-center justify-center h-32">
              <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {data && (
            <>
              {/* Legal Intent */}
              {data.legal_intent && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Legal Intent</h3>
                  <p className="text-sm text-slate-700 bg-slate-50 rounded-md px-3 py-2 border border-slate-200">
                    {data.legal_intent}
                  </p>
                </div>
              )}

              {/* Gap from Gold Standard */}
              {data.gap_summary && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Gap from Gold Standard</h3>
                  <p className="text-sm text-amber-800 bg-amber-50 rounded-md px-3 py-2 border border-amber-100">
                    {data.gap_summary}
                  </p>
                </div>
              )}

              {/* Policy Violation */}
              {data.violation_message && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Policy Violation</h3>
                  <p className="text-sm text-red-800 bg-red-50 rounded-md px-3 py-2 border border-red-100">
                    {data.violation_message}
                  </p>
                </div>
              )}

              {/* Precedent */}
              {data.precedent ? (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Precedent Found</h3>
                  <div className="text-sm text-indigo-800 bg-indigo-50 rounded-md px-3 py-2 border border-indigo-100 space-y-1">
                    <p><span className="font-semibold">Party:</span> {data.precedent.party}</p>
                    <p><span className="font-semibold">Date:</span> {data.precedent.date}</p>
                    <p><span className="font-semibold">Contract:</span> {data.precedent.contract_id}</p>
                  </div>
                </div>
              ) : (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Precedent</h3>
                  <p className="text-sm text-slate-500 italic">No prior acceptance of this clause type found.</p>
                </div>
              )}

              {/* AI Recommendation */}
              {data.ai_recommendation && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">AI Recommendation</h3>
                  <div className="text-sm text-teal-900 bg-teal-50 rounded-md px-3 py-3 border border-teal-100 whitespace-pre-line leading-relaxed">
                    {data.ai_recommendation}
                  </div>
                </div>
              )}
            </>
          )}

          {!isLoading && !data && (
            <p className="text-sm text-slate-400 text-center mt-10">No analysis available for this clause.</p>
          )}
        </div>
      </div>
    </>
  )
}
