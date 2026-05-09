import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { contractsApi } from '../api/contracts'
import { useContractWS } from '../hooks/useContractWS'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import ContractViewer from '../components/review/ContractViewer'
import ExplainabilityDrawer from '../components/review/ExplainabilityDrawer'
import ExportMenu from '../components/export/ExportMenu'
import RiskBadge from '../components/review/RiskBadge'

export default function ReviewPage() {
  const { contractId } = useParams<{ contractId: string }>()
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null)

  useContractWS(contractId ?? null)

  const { data: contract } = useQuery({
    queryKey: ['contract', contractId],
    queryFn: () => contractsApi.getContract(contractId!).then((r) => r.data),
    enabled: !!contractId,
  })

  const { data: clauses = [], refetch: refetchClauses } = useQuery({
    queryKey: ['clauses', contractId],
    queryFn: () => contractsApi.getClauses(contractId!).then((r) => r.data),
    enabled: !!contractId,
  })

  const pdfUrl: string | null = contract
    ? `${import.meta.env.VITE_API_URL}/contracts/${contractId}/file`
    : null
  const firstClauseId = clauses[0]?.clause_id ?? null

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-hidden flex flex-col p-4 gap-3">
          {/* Header bar */}
          <div className="flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div>
                <h1 className="text-base font-semibold text-gray-900 truncate max-w-md">
                  {contract?.filename ?? 'Loading…'}
                </h1>
                {contract && (
                  <div className="flex items-center gap-2 mt-0.5">
                    <RiskBadge level={contract.final_risk ?? 'UNKNOWN'} />
                    <span className="text-xs text-gray-500">{contract.current_stage ?? 'Processing'}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-gray-500">{clauses.length} clauses</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {firstClauseId && (
                <ExplainabilityDrawer clauseId={selectedClauseId ?? firstClauseId} />
              )}
              <ExportMenu
                contractFileName={contract?.filename ?? 'contract'}
                clauses={clauses}
              />
            </div>
          </div>

          {/* Main viewer */}
          <div className="flex-1 overflow-hidden">
            {contractId && (
              <ContractViewer
                contractId={contractId}
                pdfUrl={pdfUrl}
                clauses={clauses}
                onClauseUpdated={() => refetchClauses()}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
