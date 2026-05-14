import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { contractsApi } from '../api/contracts'
import { useContractWS } from '../hooks/useContractWS'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import ContractViewer from '../components/review/ContractViewer'
import ExplainabilityDrawer from '../components/review/ExplainabilityDrawer'
import ExportMenu from '../components/export/ExportMenu'
import RiskBadge from '../components/review/RiskBadge'

const STAGE_LABELS: Record<string, string> = {
  ocr: 'Running OCR on document…',
  clause_extraction: 'Extracting clauses with AI…',
  risk_analysis: 'Analysing risk across all clauses…',
  recommendation: 'Generating recommendations…',
  cleanup: 'Finalising review…',
  post_decision: 'Recording decision…',
}

const PROCESSING_STATUSES = ['UPLOADED', 'PROCESSING', 'OCR_COMPLETE', 'EXTRACTION_COMPLETE']

export default function ReviewPage() {
  const { contractId } = useParams<{ contractId: string }>()
  const navigate = useNavigate()
  const [selectedClauseId] = useState<string | null>(null)

  useContractWS(contractId ?? null)

  const { data: contract, refetch: refetchContract } = useQuery({
    queryKey: ['contract', contractId],
    queryFn: () => contractsApi.getContract(contractId!).then((r) => r.data),
    enabled: !!contractId,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'COMPLETED' ? false : 4000
    },
  })

  const { data: clauses = [], refetch: refetchClauses } = useQuery({
    queryKey: ['clauses', contractId],
    queryFn: () => contractsApi.getClauses(contractId!).then((r) => r.data),
    enabled: !!contractId,
    refetchOnWindowFocus: false,
    refetchInterval: contract?.status === 'REVIEW_READY' ? 5000 : false,
  })

  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!contractId || !contract || contract.status === 'COMPLETED') return
    contractsApi.getFileBlobUrl(contractId).then(setPdfUrl).catch(() => setPdfUrl(null))
  }, [contractId, contract?.status])
  const firstClauseId = clauses[0]?.clause_id ?? null
  const isProcessing = contract && PROCESSING_STATUSES.includes(contract.status)
  const isCompleted = contract?.status === 'COMPLETED'

  const approvedCount = clauses.filter(c => c.status === 'approved').length
  const rejectedCount = clauses.filter(c => c.status === 'rejected').length
  const modifiedCount = clauses.filter(c => c.status === 'need_changes').length
  const undecidedCount = clauses.filter(c => !['approved', 'rejected', 'need_changes'].includes(c.status ?? '')).length
  const allDecided = clauses.length > 0 && undecidedCount === 0
  const [completing, setCompleting] = useState(false)

  const handleComplete = async () => {
    if (!contractId) return
    setCompleting(true)
    try {
      await contractsApi.complete(contractId)
      await refetchContract()
      await refetchClauses()
    } catch {
      // keep completing=true to avoid re-enabling button on error
    } finally {
      setCompleting(false)
    }
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <TopBar />
        <main className="flex-1 overflow-hidden flex flex-col p-4 gap-3 soft-appear">

          {/* Processing banner */}
          {isProcessing && (
            <div className="flex items-center gap-3 bg-teal-50/90 border border-teal-200 rounded-xl px-4 py-3 flex-shrink-0 shadow-sm">
              <div className="w-4 h-4 border-2 border-teal-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-teal-900">
                  {contract.current_stage
                    ? (STAGE_LABELS[contract.current_stage] ?? `Processing: ${contract.current_stage}`)
                    : 'Processing contract…'}
                </p>
                <p className="text-xs text-teal-700 mt-0.5">This may take a minute. You can leave this page and come back.</p>
              </div>
            </div>
          )}

          {/* Header bar */}
          <div className="flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div>
                <h1 className="text-base font-bold text-slate-950 truncate max-w-md">
                  {contract?.filename ?? 'Loading…'}
                </h1>
                {contract && (
                  <div className="flex items-center gap-2 mt-0.5">
                    <RiskBadge level={contract.final_risk ?? 'UNKNOWN'} />
                    <span className="text-xs text-slate-500">{contract.status === 'COMPLETED' ? 'Completed' : (contract.current_stage ?? 'Processing')}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-slate-500">{clauses.length} clauses</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {firstClauseId && !isCompleted && (
                <ExplainabilityDrawer clauseId={selectedClauseId ?? firstClauseId} />
              )}
              <ExportMenu
                contractFileName={contract?.filename ?? 'contract'}
                clauses={clauses}
              />
              {contractId && !isCompleted && (
                <button
                  onClick={handleComplete}
                  disabled={completing || contract?.status !== 'REVIEW_READY' || !allDecided}
                  className="btn-primary py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={contract?.status !== 'REVIEW_READY' ? 'Waiting for AI analysis to complete…' : !allDecided ? `${undecidedCount} clause(s) still need your decision` : undefined}
                >
                  {completing ? 'Completing...' : 'Complete Review'}
                </button>
              )}
            </div>
          </div>

          {/* Main content */}
          <div className="flex-1 overflow-hidden">
            {isCompleted ? (
              /* Completion screen */
              <div className="flex flex-col items-center justify-center h-full gap-6">
                <div className="premium-panel p-10 max-w-lg w-full flex flex-col items-center gap-6 text-center">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center shadow-inner">
                    <svg className="w-8 h-8 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>

                  <div>
                    <h2 className="text-xl font-bold text-slate-950">Review Complete</h2>
                    <p className="text-sm text-slate-500 mt-1">{contract?.filename}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-500">Final Risk:</span>
                    <RiskBadge level={contract?.final_risk ?? 'UNKNOWN'} />
                  </div>

                  <div className="flex gap-3 w-full justify-center">
                    <div className="flex flex-col items-center bg-emerald-50 border border-emerald-100 rounded-xl px-6 py-3 flex-1">
                      <span className="text-2xl font-bold text-emerald-700">{approvedCount}</span>
                      <span className="text-xs text-emerald-600 mt-0.5">Approved</span>
                    </div>
                    <div className="flex flex-col items-center bg-red-50 border border-red-100 rounded-xl px-6 py-3 flex-1">
                      <span className="text-2xl font-bold text-red-700">{rejectedCount}</span>
                      <span className="text-xs text-red-600 mt-0.5">Rejected</span>
                    </div>
                    <div className="flex flex-col items-center bg-amber-50 border border-amber-100 rounded-xl px-6 py-3 flex-1">
                      <span className="text-2xl font-bold text-amber-700">{modifiedCount}</span>
                      <span className="text-xs text-amber-600 mt-0.5">Modified</span>
                    </div>
                  </div>

                  <div className="flex gap-3 w-full">
                    <ExportMenu
                      contractFileName={contract?.filename ?? 'contract'}
                      clauses={clauses}
                    />
                    <button
                      onClick={() => navigate('/dashboard')}
                      className="btn-secondary flex-1"
                    >
                      Back to Dashboard
                    </button>
                  </div>
                </div>
              </div>
            ) : contractId ? (
              <ContractViewer
                contractId={contractId}
                pdfUrl={pdfUrl}
                clauses={clauses}
                onClauseUpdated={() => refetchClauses()}
              />
            ) : null}
          </div>

        </main>
      </div>
    </div>
  )
}
